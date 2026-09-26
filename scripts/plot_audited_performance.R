#!/usr/bin/env Rscript
# Draw audited timing summaries only. This script never imports or fits Amelia.
# Rscript scripts/plot_audited_performance.R \
#   --native docs/validation/2026-09-23-development/benchmark-summary-audit-v2.json \
#   --hybrid docs/validation/2026-09-23-development/hybrid-summary.json \
#   --native-host "Mac M4" --hybrid-host "Mac M4" --same-host \
#   --output-prefix results/local/figures/mac-audited
# Outputs: verified PDF/PNG (SVG if available), plotted data, and provenance JSON.
# --same-host is an explicit CALLER ATTESTATION requiring upstream host evidence;
# it is not a machine identity check. Without it no timing ratios are calculated.
# Optional ratios compare CPU/GPU of the same dtype INSIDE one product route and
# one audited suite. Never divide native timings by hybrid timings or mix dtypes.

parse_options <- function(args) {
  result <- list(same_host = FALSE)
  allowed <- c("--native", "--hybrid", "--native-host", "--hybrid-host", "--output-prefix")
  index <- 1L
  while (index <= length(args)) {
    key <- args[[index]]
    if (key == "--same-host") {
      if (isTRUE(result$same_host)) stop("Repeated --same-host")
      result$same_host <- TRUE
      index <- index + 1L
    } else {
      if (!key %in% allowed || index == length(args) || !is.null(result[[key]])) {
        stop("Supply --native PATH [--hybrid PATH] [--native-host LABEL] ",
             "[--hybrid-host LABEL] [--same-host] --output-prefix PATH")
      }
      result[[key]] <- args[[index + 1L]]
      index <- index + 2L
    }
  }
  if (is.null(result[["--native"]]) || is.null(result[["--output-prefix"]])) {
    stop("--native and --output-prefix are required")
  }
  if (isTRUE(result$same_host) && (is.null(result[["--native-host"]]) ||
      (!is.null(result[["--hybrid"]]) && is.null(result[["--hybrid-host"]])))) {
    stop("--same-host requires explicit host labels and caller-held upstream host evidence")
  }
  if (isTRUE(result$same_host) && !is.null(result[["--hybrid"]]) &&
      !identical(result[["--native-host"]], result[["--hybrid-host"]])) {
    stop("Same-host attestation conflicts with the two host labels")
  }
  result
}
options <- parse_options(commandArgs(trailingOnly = TRUE))
if (dir.exists(".R-library")) .libPaths(c(normalizePath(".R-library"), .libPaths()))
if (!requireNamespace("jsonlite", quietly = TRUE)) stop("Project dependency jsonlite is required")

positive_integer <- function(value, zero = FALSE) {
  is.numeric(value) && length(value) == 1L && is.finite(value) &&
    value == as.integer(value) && value >= if (zero) 0L else 1L
}
read_audit <- function(path, route) {
  audit <- jsonlite::read_json(path, simplifyVector = FALSE)
  if (!isTRUE(audit$all_passed) || length(audit$audit_errors) || !length(audit$measurements)) {
    stop("Input must be a complete, successful independent audit: ", route)
  }
  if (route == "native" && (!identical(audit$schema_version, 2L) ||
      is.null(audit$scope$expected_tasks))) stop("Native summary requires audit schema version 2")
  if (route == "hybrid" &&
      !identical(audit$kind, "independent_R_pipeline_PyTorch_EM_audit")) {
    stop("Hybrid summary requires the independent R pipeline audit")
  }
  if (!positive_integer(audit$scope$rows_per_dataset)) stop("Missing valid sample size")
  records <- lapply(audit$measurements, function(row) {
    if (!isTRUE(row$independent_quality_audit_passed) || length(row$audit_errors) ||
        !identical(row$exit_status, 0L)) stop("Measurement failed its recorded audit/process check")
    if (route == "hybrid" && !isTRUE(row$source_unchanged_during_process)) {
      stop("Hybrid source-unchanged evidence is required")
    }
    values <- unlist(c(row$median_seconds, row$iqr_seconds), use.names = FALSE)
    if (!is.numeric(values) || length(values) != 3L || any(!is.finite(values)) ||
        any(values <= 0) || values[2L] > values[1L] || values[1L] > values[3L]) {
      stop("Invalid median/IQR")
    }
    if (!positive_integer(row$m) || !positive_integer(row$requested_measured_runs) ||
        !positive_integer(row$requested_warmups, zero = TRUE) ||
        !identical(row$measured_runs, row$requested_measured_runs) ||
        row$warmup_and_measured_runs_audited != row$requested_warmups + row$requested_measured_runs) {
      stop("Incomplete requested repeat/warmup evidence")
    }
    if (length(row$result_sha256) != 1L || !grepl("^[0-9a-f]{64}$", row$result_sha256)) {
      stop("Missing recorded report fingerprint")
    }
    data.frame(dataset = row$dataset, method = row$method, route = route,
               seconds = values[1L], q25 = values[2L], q75 = values[3L],
               n = audit$scope$rows_per_dataset, m = row$m,
               repeats = row$requested_measured_runs, warmups = row$requested_warmups,
               result_sha256 = row$result_sha256, stringsAsFactors = FALSE)
  })
  result <- do.call(rbind, records)
  plan <- if (route == "native") audit$scope$expected_tasks else audit$scope$planned_order
  expected <- vapply(plan, function(task) {
    if (route == "native") paste(unlist(task), collapse = "/") else
      paste(task$dataset, task$method, sep = "/")
  }, character(1L))
  actual <- paste(result$dataset, result$method, sep = "/")
  if (anyDuplicated(expected) || anyDuplicated(actual) || !setequal(expected, actual)) {
    stop("Audit is missing planned tasks or contains duplicate/unplanned tasks")
  }
  result
}

native <- read_audit(options[["--native"]], "native")
hybrid <- if (!is.null(options[["--hybrid"]])) read_audit(options[["--hybrid"]], "hybrid") else NULL
all_data <- rbind(native, hybrid)
if (any(vapply(all_data[c("n", "m", "repeats", "warmups")],
               function(values) length(unique(values)) != 1L, logical(1L)))) {
  stop("Combined figure requires matching n, m, requested repeats and warmups")
}
if (!is.null(hybrid) && !setequal(native$dataset, hybrid$dataset)) {
  stop("Native/hybrid dataset scopes differ")
}
method_label <- function(method) {
  labels <- c(r_serial = "R Amelia serial [R RNG]", cpu64 = "CPU float64",
              cpu32 = "CPU float32", cuda64 = "CUDA float64", cuda32 = "CUDA float32",
              mps32 = "MPS float32")
  if (grepl("^r_snow[1-9][0-9]*$", method)) {
    return(paste0("R Amelia PSOCK ", sub("r_snow", "", method), " [R RNG]"))
  }
  if (!method %in% names(labels)) stop("Unknown method; no fabricated label: ", method)
  unname(labels[[method]])
}
all_data$label <- vapply(all_data$method, method_label, character(1L))
reference <- grepl("^r_", all_data$method)
all_data$product <- ifelse(reference, "Original R Amelia",
                           ifelse(all_data$route == "native", "Python native", "R full pipeline"))
all_data$rng <- ifelse(reference | all_data$route == "hybrid", "R RNG", "NumPy PCG64")
if (any(reference & all_data$route == "hybrid")) stop("Unexpected reference row inside hybrid audit")
method_order <- unique(c("r_serial", sort(all_data$method[grepl("^r_snow", all_data$method)]),
                         "cpu64", "cpu32", "cuda64", "cuda32", "mps32"))
all_data <- all_data[order(match(all_data$route, c("native", "hybrid")),
                           match(all_data$method, method_order)), ]
dataset_labels <- c(covertype = "Covertype", household_power = "Household power",
                     year_prediction_msd = "YearPredictionMSD")
datasets <- unique(all_data$dataset)
datasets <- c(intersect(names(dataset_labels), datasets), setdiff(datasets, names(dataset_labels)))
for (dataset in setdiff(datasets, names(dataset_labels))) dataset_labels[[dataset]] <- dataset
native_host <- if (is.null(options[["--native-host"]])) "not specified" else options[["--native-host"]]
hybrid_host <- if (is.null(options[["--hybrid-host"]])) "not specified" else options[["--hybrid-host"]]

# Deliberately no original-R/native ratio: different implementations and RNGs.
# Also no cross-suite native/hybrid ratio: different bridges and wall-clock batches.
ratios <- list()
if (isTRUE(options$same_host)) {
  for (route in unique(all_data$route)) for (dataset in datasets) {
    d <- all_data[all_data$route == route & all_data$dataset == dataset, ]
    for (gpu in intersect(c("cuda64", "cuda32", "mps32"), d$method)) {
      cpu <- if (endsWith(gpu, "64")) "cpu64" else "cpu32"
      if (!cpu %in% d$method) next
      ratios[[length(ratios) + 1L]] <- list(
        dataset = dataset, route = route, cpu = cpu, gpu = gpu,
        dtype = if (endsWith(gpu, "64")) "float64" else "float32",
        cpu_median_divided_by_gpu_median = d$seconds[d$method == cpu] / d$seconds[d$method == gpu],
        interpretation = "Descriptive same-dtype same-suite ratio; >1 means GPU route took less wall time. Caller attests common host; not a causal attribution or ratio CI."
      )
    }
  }
}

prefix <- options[["--output-prefix"]]
outputs <- paste0(prefix, c(".pdf", ".png", ".svg", "-metadata.json", "-plotted-data.csv"))
if (any(file.exists(outputs))) stop("Use a fresh output prefix; existing figures are preserved")
dir.create(dirname(prefix), recursive = TRUE, showWarnings = FALSE)
width <- if (is.null(hybrid)) 10 else 16
height <- 3.5 * length(datasets) + 1.5
colors <- c("Original R Amelia" = "#747D8C", "Python native" = "#2874A6", "R full pipeline" = "#C06418")
columns <- if (is.null(hybrid)) 1L else 2L
draw <- function() {
  par(mfrow = c(length(datasets), columns), mar = c(4, 11, 3.2, 1.8),
      oma = c(5, 0, 5, 0), family = "sans", las = 1)
  for (dataset in datasets) {
    reference_data <- all_data[all_data$dataset == dataset & all_data$product == "Original R Amelia", ]
    native_data <- all_data[all_data$dataset == dataset & all_data$route == "native", ]
    hybrid_data <- all_data[all_data$dataset == dataset & all_data$route == "hybrid", ]
    panels <- list(native = native_data)
    if (!is.null(hybrid)) panels$hybrid <- if (isTRUE(options$same_host)) {
      rbind(reference_data, hybrid_data)
    } else hybrid_data
    axis_max <- max(all_data$q75[all_data$dataset == dataset]) * 1.25
    for (route in names(panels)) {
      d <- panels[[route]]
      d <- d[rev(seq_len(nrow(d))), ]
      labels <- ifelse(d$product == "Original R Amelia", d$label,
                        paste(if (route == "native") "Python" else "R + torch", d$label))
      title <- paste0(dataset_labels[[dataset]], " | ",
                      if (route == "native") "Python native" else "R full pipeline")
      positions <- barplot(d$seconds, horiz = TRUE, names.arg = labels,
                           col = colors[d$product], border = NA, xlim = c(0, axis_max),
                           cex.names = 0.82,
                           xlab = "Wall time (seconds; lower is faster)")
      segments(d$q25, positions, d$q75, positions)
      segments(d$q25, positions - 0.05, d$q25, positions + 0.05)
      segments(d$q75, positions - 0.05, d$q75, positions + 0.05)
      text(d$q75, positions, labels = paste0(" ", formatC(d$seconds, format = "f", digits = 2)),
           pos = 4, cex = 0.8)
      mtext(title, side = 3, line = 1.8, cex = 0.95, font = 2)
      mtext(if (route == "native") paste0("Host: ", native_host, "; torch uses NumPy PCG64") else
              paste0("Host: ", hybrid_host, "; bridge/transfers included; R RNG"),
            side = 3, line = 0.4, cex = 0.7)
    }
  }
  mtext("Imputation wall times from audited benchmark snapshots", outer = TRUE,
        side = 3, line = 3, cex = 1.2)
  mtext(sprintf("n = %s per dataset; m = %d; median with IQR across %d repeats; %d warmups excluded",
                format(unique(all_data$n), big.mark = ","), unique(all_data$m),
                unique(all_data$repeats), unique(all_data$warmups)),
        outer = TRUE, side = 3, line = 1.6, cex = 0.92)
  mtext("Same time scale within each dataset; different scales across datasets. Only recorded methods are shown.",
        outer = TRUE, side = 3, line = 0.5, cex = 0.82)
  notes <- c(
    if (!is.null(hybrid) && isTRUE(options$same_host))
      "R reference bars are repeated from the native audit for context; reference and torch are different implementations."
    else "R reference bars appear only in the native-audit panel; reference and torch are different implementations and RNGs.",
    "R full pipeline includes preprocessing, bootstrap, draws, postprocessing and bridge costs; native Python omits the R bridge.",
    "Suites ran in different wall-clock batches. Startup/import and post-run scoring are excluded. IQR is not a confidence interval.",
    if (isTRUE(options$same_host))
      "Common host is caller-attested, not verified by this plotter. Optional ratios only pair same dtype inside the same route/suite."
    else "Host identity is not verified. No speedup ratios are calculated; do not interpret cross-host or mixed-dtype differences as GPU gains."
  )
  for (i in seq_along(notes)) mtext(notes[[i]], outer = TRUE, side = 1, line = i - 0.1, cex = 0.72)
}

validate_file <- function(path, format) {
  if (!file.exists(path) || is.na(file.info(path)$size) || file.info(path)$size < 100) {
    stop("Graphics device did not produce a nonempty output file")
  }
  signature <- readBin(path, what = "raw", n = 128L)
  valid <- switch(format,
                  pdf = identical(signature[seq_len(5L)], charToRaw("%PDF-")),
                  png = identical(signature[seq_len(8L)],
                                  as.raw(c(137, 80, 78, 71, 13, 10, 26, 10))),
                  svg = grepl("<svg", rawToChar(signature), fixed = TRUE),
                  FALSE)
  if (!isTRUE(valid)) stop("Output file does not match its declared graphics format")
}

render_file <- function(format, backend, opener) {
  path <- paste0(prefix, ".", format)
  temporary <- tempfile(pattern = ".benchmark-plot-", tmpdir = dirname(prefix),
                        fileext = paste0(".", format))
  previous <- unname(dev.list())
  device <- NULL
  on.exit({
    # This also closes a device when its opener creates it and then raises.
    for (number in setdiff(unname(dev.list()), previous)) dev.off(number)
    if (file.exists(temporary)) unlink(temporary)
  }, add = TRUE)
  # Failed Cairo opens can warn and return without opening any device. Promoting
  # these warnings prevents plot() from silently creating an unrelated Rplots.pdf.
  withCallingHandlers(opener(temporary), warning = function(w) {
    new <- setdiff(unname(dev.list()), previous)
    for (number in new) dev.off(number)
    stop(conditionMessage(w), call. = FALSE)
  })
  new <- setdiff(unname(dev.list()), previous)
  if (length(new) != 1L) stop("Graphics device did not actually open")
  device <- new[[1L]]
  dev.set(device)
  draw()
  dev.off(device)
  device <- NULL
  validate_file(temporary, format)
  if (file.exists(path) || !file.copy(temporary, path, overwrite = FALSE)) {
    stop("Could not publish figure without overwriting an existing file")
  }
  validate_file(path, format)
  cat("Verified", format, "via", backend, ":", path, "\n")
  list(file = basename(path), format = format, backend = backend,
       bytes = unname(file.info(path)$size), md5 = unname(tools::md5sum(path)))
}

# Base PDF has no Cairo/XQuartz dependency and preserves vector quality.
artifacts <- list(render_file("pdf", "base-R-pdf", function(path) {
  pdf(path, width = width, height = height, useDingbats = FALSE)
}))
png_candidates <- list()
if (identical(Sys.info()[["sysname"]], "Darwin")) {
  png_candidates[["macOS-quartz-png"]] <- function(path) {
    png(path, width = round(150 * width), height = round(150 * height),
        res = 150, type = "quartz")
  }
}
png_candidates[["cairo-png"]] <- function(path) {
  png(path, width = round(150 * width), height = round(150 * height),
      res = 150, type = "cairo")
}
if (.Platform$OS.type == "windows") {
  png_candidates[["Windows-native-png"]] <- function(path) {
    png(path, width = round(150 * width), height = round(150 * height),
        res = 150, type = "windows")
  }
}
png_result <- NULL
for (backend in names(png_candidates)) {
  png_result <- tryCatch(render_file("png", backend, png_candidates[[backend]]),
                         error = function(e) {
                           message("PNG backend unavailable: ", backend)
                           NULL
                         })
  if (!is.null(png_result)) break
}
if (is.null(png_result)) stop("No PNG device produced a valid file; the verified PDF is available")
artifacts <- append(artifacts, list(png_result))
svg_result <- tryCatch(render_file("svg", "cairo-svg", function(path) {
  svg(path, width = width, height = height)
}), error = function(e) {
  message("Cairo SVG unavailable; the verified PDF provides vector output")
  NULL
})
if (!is.null(svg_result)) artifacts <- append(artifacts, list(svg_result))
# Export exactly the unique source observations, not repeated reference bars.
write.csv(all_data, paste0(prefix, "-plotted-data.csv"), row.names = FALSE, na = "")
input_paths <- Filter(Negate(is.null), options[c("--native", "--hybrid")])
metadata <- list(
  schema_version = 1L, kind = "plot_of_audited_benchmark_summaries", plotting_only = TRUE,
  source_script_md5 = unname(tools::md5sum(sub("^--file=", "",
    grep("^--file=", commandArgs(FALSE), value = TRUE)[[1L]]))),
  inputs = lapply(unname(input_paths), function(path) {
    list(file = basename(path), md5 = unname(tools::md5sum(path)))
  }),
  host_labels = list(native = native_host, hybrid = if (is.null(hybrid)) NULL else hybrid_host),
  same_host_caller_attestation = isTRUE(options$same_host), host_identity_verified_by_plotter = FALSE,
  evidence_policy = "Input audit flags, planned grid, per-row process/quality/count/timing fields are checked. This plotter does not rerun the independent auditor or authenticate host identity; retain upstream reports and host evidence.",
  timing_policy = "Only reported median seconds and IQR are plotted. With --same-host, R reference bars repeat native-suite observations in the hybrid panel for context; otherwise they only appear in the native panel. Native and hybrid are different product routes; no ratios cross routes, hosts or dtypes.",
  ratio_policy = "Ratios require --same-host caller attestation plus host labels and only compare CPU/GPU of identical dtype within one audited suite. These are ratios of medians, not paired-run estimators or confidence intervals. Values below 1 mean slower GPU route.",
  ratios = ratios, observations = nrow(all_data), outputs = artifacts,
  plotted_data = list(file = basename(paste0(prefix, "-plotted-data.csv")),
                      md5 = unname(tools::md5sum(paste0(prefix, "-plotted-data.csv")))),
  svg_available = !is.null(svg_result),
  absent_method_policy = "Unrecorded methods (including unavailable CUDA/MPS precisions) are omitted, never assigned zero or extrapolated."
)
jsonlite::write_json(metadata, paste0(prefix, "-metadata.json"), pretty = TRUE,
                     auto_unbox = TRUE, null = "null", digits = NA)
cat("Verified plot artifacts and provenance written; no imputation was run.\n")
