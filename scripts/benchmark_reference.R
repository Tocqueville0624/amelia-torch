# R reference runner. Invoke from the repository root:
# Rscript scripts/benchmark_reference.R path/to/config.json
# Numeric input/truth/mask CSVs have headers and no row-name column.
# Input parsing and quality summaries are outside the timed interval.
.libPaths(c(file.path(getwd(), ".R-library"), .libPaths()))
# Local PSOCK children start fresh R sessions. Export library discovery only to
# this process and its children; do not modify the user's R startup files.
Sys.setenv(R_LIBS_USER = paste(.libPaths(), collapse = .Platform$path.sep))
RNGkind("L'Ecuyer-CMRG")
stopifnot(requireNamespace("jsonlite", quietly = TRUE))
stopifnot(as.character(packageVersion("Amelia")) == "1.8.3")
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
if (!(parallel_mode %in% c("no", "snow"))) stop("parallel must be no or snow")
if (m < 1 || warmups < 0 || ncpus < 1) stop("m/ncpus must be positive and warmups nonnegative")
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
report <- list(
  schema_version = 1L, implementation = "R Amelia", version = "1.8.3",
  config = list(n = nrow(x), p = ncol(x), m = m, seeds = seeds,
                warmups = warmups, warmup_seeds = warmup_seeds,
                ncpus = ncpus, parallel = parallel_mode,
                empri = empri, autopri = autopri, tolerance = tolerance,
                emburn = emburn, startvals = startvals, boot.type = boot_type,
                missing_cells = sum(is.na(x)), heldout_cells = sum(mask),
                completely_missing_input_rows = sum(rowSums(is.na(x)) == ncol(x))),
  timing_contract = list(
    scope = "In-memory numeric input through full Amelia result; includes internal PSOCK cluster creation and teardown.",
    excluded = "CSV parsing, quality summaries and JSON writing.",
    warmup_contract = "Warmup runs call the same public API; snow starts a fresh internal cluster on every call.",
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
    os = as.list(Sys.info()[c("sysname", "release", "machine")]),
    BLAS = if ("BLAS" %in% names(ext)) basename(unname(ext[["BLAS"]])) else NULL,
    LAPACK = if ("LAPACK" %in% names(ext)) basename(unname(ext[["LAPACK"]])) else NULL,
    packages = list(Amelia = version_of("Amelia"), Rcpp = version_of("Rcpp"),
                    RcppArmadillo = version_of("RcppArmadillo"), jsonlite = version_of("jsonlite")),
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
  start_time <- proc.time()[["elapsed"]]
  fit <- tryCatch(withCallingHandlers(
    Amelia::amelia(x, m = m, p2s = 0, parallel = parallel_mode, ncpus = ncpus,
                   empri = empri, autopri = autopri, tolerance = tolerance,
                   emburn = emburn, startvals = startvals, boot.type = boot_type),
    warning = function(w) {
      warning_messages <<- c(warning_messages, conditionMessage(w))
      invokeRestart("muffleWarning")
    }), error = function(e) {
      error_message <<- conditionMessage(e)
      NULL
    })
  elapsed <- unname(proc.time()[["elapsed"]] - start_time)
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
  valid_convergence <- length(convergence) == m && !anyNA(convergence) && all(convergence)
  status <- if (!is.null(error_message) || !valid_code) {
    "error"
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
         warnings = warning_messages, error = error_message, peak_ram_bytes = NULL), quality)
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
cat("Completed", length(report$runs), "R reference runs;", sum(measured_ok),
    "successful measured calls; failures retained in report.\n")
quit(status = if (all_complete) 0L else 1L)
