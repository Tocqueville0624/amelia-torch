#!/usr/bin/env Rscript
# Reproduce figures from independently audited summaries only; never runs fits.
# Rscript scripts/plot_benchmarks.R --native path/to/benchmark-summary.json \
#   --hybrid path/to/hybrid-summary.json --output-prefix results/local/figures/timings
# Omit --hybrid for a native/reference-only figure. Writes PDF and PNG; also SVG
# when a working Cairo device is available. Device loading is tested by opening
# it, not by trusting capabilities("cairo") on machines without its shared libs.
# Different suites were run at different wall-clock times: plot durations, not
# an assertion of causal speedup.

args <- commandArgs(trailingOnly = TRUE)
if (length(args) %% 2L != 0L || !length(args)) {
  stop("Supply --native PATH [--hybrid PATH] --output-prefix PATH")
}
keys <- args[seq.int(1L, length(args), 2L)]
if (anyDuplicated(keys) || any(!keys %in% c("--native", "--hybrid", "--output-prefix"))) {
  stop("Unknown or repeated option")
}
options <- setNames(args[seq.int(2L, length(args), 2L)], keys)
if (!all(c("--native", "--output-prefix") %in% names(options))) stop("Missing required option")
if (dir.exists(".R-library")) .libPaths(c(normalizePath(".R-library"), .libPaths()))
if (!requireNamespace("jsonlite", quietly = TRUE)) stop("Install existing project dependency jsonlite")

read_audit <- function(path, kind) {
  audit <- jsonlite::read_json(path, simplifyVector = FALSE)
  if (!isTRUE(audit$all_passed) || length(audit$audit_errors)) stop(kind, " audit did not pass")
  if (is.null(audit$measurements) || !length(audit$measurements)) stop("Empty audit")
  if (kind == "native" && (!identical(audit$schema_version, 2L) ||
                          is.null(audit$scope$expected_tasks))) {
    stop("Use version 2 independent native audit, not the older summary")
  }
  if (kind == "hybrid" && !identical(audit$kind, "independent_R_pipeline_PyTorch_EM_audit")) {
    stop("Expected independently audited hybrid summary")
  }
  records <- lapply(audit$measurements, function(row) {
    if (!isTRUE(row$independent_quality_audit_passed) || length(row$audit_errors)) {
      stop("A measurement did not pass the independent audit")
    }
    values <- unlist(c(row$median_seconds, row$iqr_seconds), use.names = FALSE)
    if (!is.numeric(values) || length(values) != 3L || any(!is.finite(values)) ||
        any(values <= 0) || values[2L] > values[1L] || values[1L] > values[3L]) {
      stop("Invalid median or IQR")
    }
    if (is.null(row$m) || is.null(row$requested_measured_runs) || is.null(row$requested_warmups)) {
      stop("Missing imputation or run-count evidence")
    }
    data.frame(dataset = row$dataset, method = row$method, suite = kind,
               seconds = values[1L], q25 = values[2L], q75 = values[3L],
               m = row$m, repeats = row$requested_measured_runs,
               warmups = row$requested_warmups, stringsAsFactors = FALSE)
  })
  result <- do.call(rbind, records)
  actual <- paste(result$dataset, result$method, sep = "/")
  plan <- if (kind == "native") audit$scope$expected_tasks else audit$scope$planned_order
  expected <- vapply(plan, function(task) {
    if (kind == "native") paste(unlist(task), collapse = "/") else
      paste(task$dataset, task$method, sep = "/")
  }, character(1L))
  if (anyDuplicated(actual) || anyDuplicated(expected) || !setequal(actual, expected)) {
    stop("Summary does not contain its entire planned grid")
  }
  list(data = result, rows = audit$scope$rows_per_dataset)
}

native <- read_audit(options[["--native"]], "native")
all_data <- native$data
if ("--hybrid" %in% names(options)) {
  hybrid <- read_audit(options[["--hybrid"]], "hybrid")
  if (!identical(native$rows, hybrid$rows) ||
      !setequal(native$data$dataset, hybrid$data$dataset)) {
    stop("Native/hybrid dataset and row-count scopes differ")
  }
  all_data <- rbind(all_data, hybrid$data)
}
if (any(vapply(all_data[c("m", "repeats", "warmups")], function(x) length(unique(x)) != 1L,
               logical(1L)))) stop("Incomparable m, warmup or repetition counts")

method_names <- c(r_serial = "R Amelia serial", r_snow4 = "R Amelia PSOCK 4",
                  cpu64 = "CPU float64", cpu32 = "CPU float32", mps32 = "MPS float32",
                  cuda64 = "CUDA float64", cuda32 = "CUDA float32")
if (any(!all_data$method %in% names(method_names))) stop("Unrecognized method")
all_data$label <- unname(method_names[all_data$method])
torch <- !grepl("^r_", all_data$method)
all_data$label[torch] <- paste(ifelse(all_data$suite[torch] == "hybrid", "R + torch", "Python"),
                             all_data$label[torch])
all_data$group <- ifelse(all_data$suite == "hybrid", "R + PyTorch EM",
                        ifelse(torch, "Python native", "R Amelia"))
colors <- c("R Amelia" = "#687386", "Python native" = "#2874A6", "R + PyTorch EM" = "#D97727")
dataset_names <- c(covertype = "Covertype (10 variables)",
                   household_power = "Household power (7 variables)",
                   year_prediction_msd = "YearPredictionMSD (90 variables)")
datasets <- names(dataset_names)[names(dataset_names) %in% all_data$dataset]
if (length(datasets) != length(unique(all_data$dataset))) stop("Unrecognized dataset")
all_data <- all_data[order(match(all_data$suite, c("native", "hybrid")),
                           match(all_data$method, names(method_names))), ]

prefix <- options[["--output-prefix"]]
outputs <- paste0(prefix, c(".pdf", ".svg", ".png", "-metadata.json"))
if (any(file.exists(outputs))) stop("Refusing to overwrite figures; choose a fresh output prefix")
dir.create(dirname(prefix), recursive = TRUE, showWarnings = FALSE)
width <- 11
height <- 3.3 * length(datasets) + 1
draw <- function() {
  par(mfrow = c(length(datasets), 1L), mar = c(4, 12, 2, 2), oma = c(3, 0, 4, 0),
      family = "sans", las = 1)
  for (dataset in datasets) {
    d <- all_data[all_data$dataset == dataset, ]
    d <- d[rev(seq_len(nrow(d))), ]
    positions <- barplot(d$seconds, horiz = TRUE, names.arg = d$label,
                         col = colors[d$group], border = NA,
                         xlim = c(0, max(d$q75) * 1.23), cex.names = 0.8,
                         main = dataset_names[[dataset]], xlab = "Wall time (seconds)")
    # Segments also draw an honest zero-width IQR without arrows() warnings.
    segments(d$q25, positions, d$q75, positions)
    segments(d$q25, positions - 0.04, d$q25, positions + 0.04)
    segments(d$q75, positions - 0.04, d$q75, positions + 0.04)
    text(d$q75, positions, labels = sprintf("  %.2f", d$seconds), pos = 4, cex = 0.8)
  }
  mtext(sprintf("Same-machine imputation timings: n = %s, m = %s",
                format(native$rows, big.mark = ","), unique(all_data$m)), outer = TRUE,
        side = 3, line = 2, cex = 1.15)
  mtext(sprintf("Median and IQR across %s runs; %s warmups excluded. Each panel has its own time axis.",
                unique(all_data$repeats), unique(all_data$warmups)), outer = TRUE,
        side = 3, line = 0.7, cex = 0.85)
  note <- if ("--hybrid" %in% names(options)) {
    "Complete-truth block MCAR inputs. Native and hybrid suites ran at different wall-clock times."
  } else {
    "Complete-truth block MCAR inputs. Native Python timings omit the R/Python bridge."
  }
  mtext(note,
        outer = TRUE, side = 1, line = 1, cex = 0.8)
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
inputs <- options[intersect(c("--native", "--hybrid"), names(options))]
metadata <- list(schema_version = 1L,
                 source_script_md5 = unname(tools::md5sum(sub("^--file=", "",
                   grep("^--file=", commandArgs(FALSE), value = TRUE)[[1L]]))),
                 inputs = lapply(unname(inputs), function(path) {
                   list(file = basename(path), md5 = unname(tools::md5sum(path)))
                 }),
                 outputs = artifacts,
                 svg_available = !is.null(svg_result),
                 plotting_only = TRUE)
jsonlite::write_json(metadata, paste0(prefix, "-metadata.json"), pretty = TRUE,
                     auto_unbox = TRUE, null = "null")
