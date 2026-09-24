# Hybrid R-pipeline/PyTorch-EM runner. Invoke from the repository root:
# Rscript scripts/benchmark_hybrid.R path/to/config.json
# Derived from the strict reference runner; no currently-running runner is modified.
# Numeric input/truth/mask CSVs have headers and no row-name column.
# Input parsing and quality summaries are outside the timed interval.
.libPaths(c(file.path(getwd(), ".R-library"), .libPaths()))
# Export local library discovery only to this process and its children;
# do not modify the user's R startup files. Replicates remain serial here.
Sys.setenv(R_LIBS_USER = paste(.libPaths(), collapse = .Platform$path.sep))
RNGkind("L'Ecuyer-CMRG")
stopifnot(requireNamespace("jsonlite", quietly = TRUE))
stopifnot(as.character(packageVersion("Amelia")) == "1.8.3")
stopifnot(requireNamespace("ameliatorch", quietly = TRUE))
stopifnot(requireNamespace("reticulate", quietly = TRUE))
cli <- commandArgs(trailingOnly = TRUE)
if (length(cli) != 1L) stop("Supply exactly one configuration JSON file")
config <- jsonlite::read_json(cli[[1]], simplifyVector = TRUE)
required <- c("input_csv", "truth_csv", "mask_csv", "output_json", "m", "seeds")
if (!all(required %in% names(config))) stop("Missing required configuration fields")
setting <- function(name, default) if (is.null(config[[name]])) default else config[[name]]
read_numeric <- function(path) {
  frame <- read.csv(path, check.names = FALSE, na.strings = c("", "NA", "NaN", "nan"))
  # read.csv represents an all-NA numeric column as logical; preserve it for the
  # official Amelia input checker rather than rejecting it during CSV parsing.
  if (!all(vapply(frame, function(col) is.numeric(col) || (is.logical(col) && all(is.na(col))), logical(1)))) {
    stop("CSV columns must be numeric")
  }
  frame[] <- lapply(frame, as.numeric)
  as.matrix(frame)
}
x <- read_numeric(config$input_csv)
truth <- read_numeric(config$truth_csv)
mask <- read_numeric(config$mask_csv)
if (!identical(dim(x), dim(truth)) || !identical(dim(x), dim(mask))) {
  stop("Input, truth and heldout mask shapes must agree")
}
if (anyNA(mask) || any(!(mask %in% c(0, 1)))) stop("Mask must contain only numeric 0 or 1")
mask <- mask == 1
if (any(mask & !is.na(x))) stop("Heldout mask cells must be missing in input")
if (any(mask & !is.finite(truth))) stop("Heldout truth cells must be finite")
if (any(is.infinite(x)) || any(is.infinite(truth))) stop("Infinite input values are not supported")
seeds <- as.integer(config$seeds)
if (!length(seeds) || anyNA(seeds)) stop("Provide at least one valid seed")
m <- as.integer(config$m)
warmups <- as.integer(setting("warmups", 2L))
warmup_seed <- as.integer(setting("warmup_seed", 20360923L))
warmup_seeds <- warmup_seed + seq_len(warmups) - 1L
ncpus <- as.integer(setting("ncpus", 1L))
parallel_mode <- setting("parallel", "no")
if (!identical(parallel_mode, "no") || ncpus != 1L) {
  stop("The hybrid benchmark uses serial R replicate scheduling only")
}
if (m < 1 || warmups < 0) stop("m must be positive and warmups nonnegative")
device <- setting("device", "cpu")
dtype <- setting("dtype", "float64")
threads <- as.integer(setting("threads", 4L))
if (threads < 1L) stop("threads must be positive")
if (!(device %in% c("cpu", "mps", "cuda"))) stop("Unsupported device")
if (!(dtype %in% c("float32", "float64"))) stop("Unsupported dtype")
if (device == "mps" && Sys.getenv("PYTORCH_ENABLE_MPS_FALLBACK") != "0") {
  stop("Set PYTORCH_ENABLE_MPS_FALLBACK=0 before Python initializes")
}
python <- Sys.getenv("RETICULATE_PYTHON", unset = "")
if (!nzchar(python)) stop("RETICULATE_PYTHON must select the calling environment explicitly")
# Initial binding/import and thread configuration are excluded from per-call timing.
# The public API still performs its normal context setup, R/Python conversions,
# transfer, EM and R postprocessing inside every timed call.
ameliatorch::use_amelia_python(python = python)
torch <- reticulate::import("torch", convert = FALSE)
backends <- reticulate::import("amelia_torch.backends", convert = FALSE)
invisible(reticulate::import("amelia_torch.em", convert = TRUE))
torch$set_num_threads(threads)
invisible(backends$resolve_backend(device, dtype))
torch_device <- torch$device(device)
if (device == "cuda") {
  torch$backends$cuda$matmul$allow_tf32 <- FALSE
  torch$backends$cudnn$allow_tf32 <- FALSE
}
py_value <- function(value) reticulate::py_to_r(value)
synchronize <- function() invisible(backends$synchronize(torch_device))
synchronize()
empri <- setting("empri", NULL)
autopri <- setting("autopri", 0.05)
tolerance <- setting("tolerance", 1e-4)
emburn <- as.numeric(setting("emburn", c(0, 0)))
startvals <- setting("startvals", 0)
boot_type <- setting("boot.type", "ordinary")
if (!(boot_type %in% c("ordinary", "none"))) stop("boot.type must be ordinary or none")

truth_scale <- apply(truth, 2, sd, na.rm = TRUE)
scored_columns <- colSums(mask) > 0
if (any(scored_columns & (!is.finite(truth_scale) | truth_scale <= 0))) {
  stop("Scored truth columns must have positive finite sample SD")
}
observed <- !is.na(x)
wholly_missing_input_rows <- rowSums(is.na(x)) == ncol(x)
ext <- extSoftVersion()
version_of <- function(name) {
  if (requireNamespace(name, quietly = TRUE)) as.character(packageVersion(name)) else NULL
}
installed_bridge_fingerprints <- function() {
  root <- system.file(package = "ameliatorch")
  relative <- c("DESCRIPTION", "NAMESPACE", "R/ameliatorch.rdb", "R/ameliatorch.rdx")
  libraries <- list.files(file.path(root, "libs"), pattern = "\\.(so|dll|dylib)$",
                          recursive = TRUE)
  relative <- c(relative, file.path("libs", libraries))
  paths <- file.path(root, relative)
  available <- file.exists(paths)
  hashes <- as.list(unname(tools::md5sum(paths[available])))
  names(hashes) <- relative[available]
  hashes
}
report <- list(
  schema_version = 1L, implementation = "R Amelia pipeline with PyTorch EM",
  engine = "R-Amelia-pipeline-with-PyTorch-EM", reference_version = "1.8.3",
  bridge_version = as.character(packageVersion("ameliatorch")),
  cpu_work = c("original R preprocessing", "original R bootstrap and RNG",
               "original R conditional draws", "original R postprocessing"),
  non_em_work_dtype = "Original R numeric double; dtype setting applies to the PyTorch EM kernel",
  requested_em_backend = list(device = device, dtype = dtype),
  provenance = setting("provenance", NULL),
  config = list(n = nrow(x), p = ncol(x), m = m, seeds = seeds,
                warmups = warmups, warmup_seeds = warmup_seeds,
                ncpus = ncpus, parallel = parallel_mode,
                torch_threads = threads, device = device, em_dtype = dtype,
                empri = empri, autopri = autopri, tolerance = tolerance,
                emburn = emburn, startvals = startvals, boot.type = boot_type,
                missing_cells = sum(is.na(x)), heldout_cells = sum(mask),
                completely_missing_input_rows = sum(rowSums(is.na(x)) == ncol(x))),
  timing_contract = list(
    scope = "In-memory R numeric input through full original Amelia result using PyTorch EM; original R preprocessing/bootstrap/draws/postprocessing, reticulate conversion and device transfers are included.",
    excluded = "CSV parsing, initial Python environment binding/import, initial thread configuration, quality summaries and JSON writing.",
    warmup_contract = "Warmup runs call the same public amelia_torch_compat API with the same task size and settings.",
    synchronization = "Requested torch backend synchronized immediately before starting and before stopping the timer.",
    cold_process_startup_included = FALSE,
    peak_ram_measurement = "Not measured; null does not mean zero."),
  quality_contract = list(
    normalized_rmse = "For each imputation, sqrt(mean(((imputed-truth)/truth_column_sample_sd)^2)) across explicitly heldout cells; null if any heldout prediction is nonfinite.",
    pooling = "Column-mean Rubin summaries; within-imputation variance is sample variance divided by each column's nonmissing count. Between/total variance is null for m=1.",
    missing_rows = "Counts rows with at least one remaining missing value, by imputation.",
    success_gate = "Observed cells unchanged; all nonblank input rows finite; wholly missing input rows retained as NA; every heldout cell scored with finite error. Heldout cells in wholly missing rows still fail scoring."),
  environment = list(
    R = as.character(getRversion()), platform = R.version$platform,
    RNGkind = RNGkind(),
    python = py_value(reticulate::import("platform", convert = FALSE)$python_version()),
    torch = py_value(reticulate::import("builtins", convert = FALSE)$str(torch$`__version__`)),
    torch_threads = py_value(torch$get_num_threads()),
    installed_bridge_files_md5 = installed_bridge_fingerprints(),
    requested_python_matches_active = identical(
      gsub("\\", "/", reticulate::py_config()$python, fixed = TRUE),
      gsub("\\", "/", python, fixed = TRUE)),
    mps_cpu_fallback = Sys.getenv("PYTORCH_ENABLE_MPS_FALLBACK", unset = NA_character_),
    cuda_tf32_allowed = if (device == "cuda") py_value(torch$backends$cuda$matmul$allow_tf32) else NULL,
    os = as.list(Sys.info()[c("sysname", "release", "machine")]),
    BLAS = if ("BLAS" %in% names(ext)) basename(unname(ext[["BLAS"]])) else NULL,
    LAPACK = if ("LAPACK" %in% names(ext)) basename(unname(ext[["LAPACK"]])) else NULL,
    packages = list(Amelia = version_of("Amelia"), Rcpp = version_of("Rcpp"),
                    RcppArmadillo = version_of("RcppArmadillo"), jsonlite = version_of("jsonlite"),
                    reticulate = version_of("reticulate"), ameliatorch = version_of("ameliatorch")),
    thread_environment = as.list(Sys.getenv(c("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS",
                                               "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"),
                                           unset = NA_character_))),
  runs = list()
)
dir.create(dirname(config$output_json), recursive = TRUE, showWarnings = FALSE)
save_report <- function() {
  temporary <- paste0(config$output_json, ".tmp")
  jsonlite::write_json(report, temporary, auto_unbox = TRUE, pretty = TRUE,
                      digits = NA, na = "null", null = "null", matrix = "rowmajor")
  if (!file.rename(temporary, config$output_json)) stop("Cannot replace output report")
}
summarize_quality <- function(fit) {
  if (is.null(fit) || !is.list(fit$imputations)) return(list(quality_status = "no_result", quality_passed = FALSE))
  valid <- vapply(fit$imputations, function(value) {
    (is.matrix(value) || is.data.frame(value)) && identical(dim(value), dim(x))
  }, logical(1))
  if (!all(valid) || length(valid) != m) return(list(quality_status = "invalid_or_incomplete_imputations", quality_passed = FALSE))
  imputations <- lapply(fit$imputations, as.matrix)
  kept <- vapply(imputations, function(imp) identical(as.numeric(imp[observed]),
                                                     as.numeric(x[observed])), logical(1))
  missing_cells <- vapply(imputations, function(imp) sum(is.na(imp)), numeric(1))
  missing_rows <- vapply(imputations, function(imp) sum(rowSums(is.na(imp)) > 0), numeric(1))
  nonfinite_cells <- vapply(imputations, function(imp) sum(!is.finite(imp)), numeric(1))
  unexpected_nonfinite <- vapply(imputations, function(imp) {
    sum(!is.finite(imp[!wholly_missing_input_rows, , drop = FALSE]))
  }, numeric(1))
  blank_rows_preserved <- vapply(imputations, function(imp) {
    all(is.na(imp[wholly_missing_input_rows, , drop = FALSE]))
  }, logical(1))
  unscored_heldout <- vapply(imputations, function(imp) {
    residual <- sweep(imp - truth, 2, truth_scale, "/")
    sum(mask & !is.finite(residual))
  }, numeric(1))
  rmses <- vapply(imputations, function(imp) {
    if (!any(mask) || any(!is.finite(imp[mask]))) return(NA_real_)
    residual <- sweep(imp - truth, 2, truth_scale, "/")
    sqrt(mean(residual[mask]^2))
  }, numeric(1))
  means <- do.call(rbind, lapply(imputations, function(imp) colMeans(imp, na.rm = TRUE)))
  within <- do.call(rbind, lapply(imputations, function(imp) {
    apply(imp, 2, var, na.rm = TRUE) / colSums(!is.na(imp))
  }))
  between <- if (m > 1) apply(means, 2, var) else rep(NA_real_, ncol(x))
  average_within <- colMeans(within)
  covariance <- lapply(imputations, function(imp) {
    if (sum(complete.cases(imp)) < 2) return(matrix(NA_real_, ncol(x), ncol(x)))
    cov(imp, use = "complete.obs")
  })
  quality_passed <- all(kept) && all(unexpected_nonfinite == 0) &&
    all(blank_rows_preserved) && all(unscored_heldout == 0) &&
    (!any(mask) || all(is.finite(rmses)))
  list(quality_status = if (quality_passed) "computed" else "failed",
       quality_passed = quality_passed, observed_values_unchanged = kept,
       unexpected_nonfinite_cells = unexpected_nonfinite,
       wholly_missing_rows_preserved = blank_rows_preserved,
       unscored_heldout_cells_per_imputation = unscored_heldout,
       remaining_missing_cells = missing_cells, remaining_missing_rows = missing_rows,
       nonfinite_cells = nonfinite_cells, normalized_heldout_rmse = rmses,
       pooled_column_means = colMeans(means),
       pooled_mean_within_variance = average_within,
       pooled_mean_between_variance = between,
       pooled_mean_variance = average_within + (1 + 1 / m) * between,
       mean_covariance = Reduce("+", covariance) / m)
}
run_one <- function(seed, phase, repeat_index) {
  warning_messages <- character()
  error_message <- NULL
  set.seed(seed)
  if (device == "cuda") torch$cuda$reset_peak_memory_stats(torch_device)
  synchronize()
  start_time <- proc.time()[["elapsed"]]
  fit <- tryCatch(withCallingHandlers(
    ameliatorch::amelia_torch_compat(
      x, m = m, p2s = 0, parallel = parallel_mode, ncpus = ncpus,
      empri = empri, autopri = autopri, tolerance = tolerance,
      emburn = emburn, startvals = startvals, boot.type = boot_type,
      device = device, dtype = dtype),
    warning = function(w) {
      warning_messages <<- c(warning_messages, conditionMessage(w))
      invokeRestart("muffleWarning")
    }), error = function(e) {
      error_message <<- conditionMessage(e)
      NULL
    })
  # Synchronize failed calls too, so asynchronous work is not silently omitted.
  tryCatch(synchronize(), error = function(e) {
    error_message <<- paste(c(error_message, paste("Synchronization failed:", conditionMessage(e))), collapse = "; ")
  })
  elapsed <- unname(proc.time()[["elapsed"]] - start_time)
  backend <- attr(fit, "amelia_torch_backend", exact = TRUE)
  iteration_counts <- NULL
  convergence <- NULL
  if (!is.null(fit$iterHist)) {
    iteration_counts <- vapply(fit$iterHist, function(hist) {
      if (is.matrix(hist)) nrow(hist) else 0L
    }, integer(1))
    convergence <- vapply(fit$iterHist, function(hist) {
      if (is.matrix(hist) && nrow(hist)) tail(hist[, 1], 1) == 0 else TRUE
    }, logical(1))
  }
  quality <- tryCatch(summarize_quality(fit), error = function(e) {
    list(quality_status = "summary_error", quality_passed = FALSE,
         quality_error = conditionMessage(e))
  })
  valid_code <- !is.null(fit) && length(fit$code) == 1L && isTRUE(fit$code == 1)
  valid_backend <- is.list(backend) &&
    identical(backend$engine, "r-amelia-torch-em") &&
    identical(backend$call_engine, "r-amelia-torch-em") &&
    identical(backend$device, device) && identical(backend$dtype, dtype) &&
    length(backend$fits) == m
  valid_convergence <- length(convergence) == m && !anyNA(convergence) &&
    all(convergence) && isTRUE(backend$converged)
  status <- if (!is.null(error_message) || !valid_code) {
    "error"
  } else if (!valid_backend) {
    "backend_contract_failed"
  } else if (!valid_convergence) {
    "not_converged"
  } else if (!isTRUE(quality$quality_passed)) {
    "quality_failed"
  } else {
    "ok"
  }
  c(list(phase = phase, repeat_index = repeat_index, seed = seed, status = status,
         wall_seconds = elapsed, code = if (is.null(fit)) NULL else fit$code,
         iterations = iteration_counts, converged_by_tolerance = convergence,
         warnings = warning_messages, error = error_message, peak_ram_bytes = NULL,
         backend_contract_passed = valid_backend, backend = backend,
         peak_cuda_allocated_bytes = if (device == "cuda") {
           py_value(torch$cuda$max_memory_allocated(torch_device))
         } else NULL), quality)
}
save_report()
for (i in seq_len(warmups)) {
  report$runs[[length(report$runs) + 1L]] <- run_one(warmup_seeds[i],
                                                   "warmup", i)
  save_report()
}
for (i in seq_along(seeds)) {
  report$runs[[length(report$runs) + 1L]] <- run_one(seeds[i], "measured", i)
  save_report()
}
measured <- Filter(function(run) identical(run$phase, "measured"), report$runs)
measured_ok <- vapply(measured, function(run) identical(run$status, "ok"), logical(1))
all_runs_ok <- vapply(report$runs, function(run) identical(run$status, "ok"), logical(1))
measured_complete <- length(measured) == length(seeds) && all(measured_ok)
all_complete <- length(report$runs) == warmups + length(seeds) && all(all_runs_ok)
# Do not summarize a favorable subset when requested measured calls failed.
measured_times <- if (measured_complete) {
  vapply(measured, function(run) run$wall_seconds, numeric(1))
} else numeric()
report$summary <- list(
  requested_measured_runs = length(seeds),
  completed_measured_runs = length(measured),
  successful_measured_runs = sum(measured_ok),
  failed_measured_runs = sum(!measured_ok),
  all_measured_runs_succeeded = measured_complete,
  all_requested_runs_succeeded = all_complete,
  median_seconds = if (length(measured_times)) median(measured_times) else NULL,
  iqr_seconds = if (length(measured_times)) {
    unname(quantile(measured_times, probs = c(0.25, 0.75)))
  } else NULL,
  status_counts = as.list(table(vapply(report$runs, function(run) run$status, character(1))))
)
report$completed_utc <- format(Sys.time(), tz = "UTC", usetz = TRUE)
save_report()
cat("Completed", length(report$runs), "hybrid R/PyTorch runs;", sum(measured_ok),
    "successful measured calls; failures retained in report.\n")
quit(status = if (all_complete) 0L else 1L)
