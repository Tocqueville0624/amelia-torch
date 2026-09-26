# Bounded public R/PyTorch boundary checks, not a benchmark or equivalence proof.
# Run only after concurrent timing jobs finish. Every engine gets fresh data and
# a serialized deep copy of theta: upstream emcore mutates double-matrix aliases.
# Usage: Rscript scripts/validate_r_accelerator_edges.R DEVICE DTYPE OUTPUT.json
# DEVICE is cpu (smoke), cuda, or mps. MPS requires explicit float32.
cli <- commandArgs(trailingOnly = TRUE)
if (length(cli) != 3L) stop(paste(
  "Usage: Rscript scripts/validate_r_accelerator_edges.R DEVICE DTYPE OUTPUT.json"))
device <- cli[[1]]
dtype <- cli[[2]]
output_file <- cli[[3]]
if (!device %in% c("cpu", "cuda", "mps") || !dtype %in% c("float32", "float64")) {
  stop("Choose device cpu/cuda/mps and dtype float32/float64 explicitly.")
}
if (device == "mps" && dtype != "float32") stop("MPS cannot execute float64; choose float32 explicitly.")
if (device == "mps") Sys.setenv(PYTORCH_ENABLE_MPS_FALLBACK = "0")
.libPaths(c(file.path(getwd(), ".R-library"), .libPaths()))
if (!requireNamespace("jsonlite", quietly = TRUE)) stop("Install jsonlite before this validation.")
copy_value <- function(x) unserialize(serialize(x, NULL))
sanitize <- function(x) {
  for (path in unique(c(getwd(), path.expand("~"), tempdir()))) {
    if (nzchar(path) && nchar(path) > 1) x <- gsub(path, "<local-path>", x, fixed = TRUE)
  }
  x
}
# Locked BEFORE execution. Do not tune these from observed GPU differences.
gates <- if (dtype == "float32") {
  list(em_tolerance = 1e-5, theta_atol = 1e-5, theta_rtol = 1e-4,
       standardized_output_atol = 1e-5, standardized_output_rtol = 1e-4)
} else {
  list(em_tolerance = 1e-6, theta_atol = 1e-7, theta_rtol = 1e-7,
       standardized_output_atol = 1e-6, standardized_output_rtol = 1e-7)
}
report <- list(
  schema_version = 1L, scope = paste(
    "Eight fixed public boundary cases against fresh original Amelia 1.8.3,",
    "plus a separately labeled CPU64 allthetas/alias oracle. No timing or",
    "statistical-equivalence claim; near-singular trajectories need not match."),
  device = device, dtype = dtype, gates = gates,
  rng_kind = c("Mersenne-Twister", "Inversion", "Rejection"),
  fallback = if (device == "mps") Sys.getenv("PYTORCH_ENABLE_MPS_FALLBACK") else NULL,
  cases = list(), setup_error = NULL, all_checks_passed = FALSE,
  limits = c("No full dataset or Monte Carlo quality check",
             "No GPU allthetas oracle; that extra check is explicitly CPU64",
             "A missing autopri trigger is reported, not fabricated",
             "CPU preprocessing, draws, postprocessing and diagnostics remain explicit")
)
write_report <- function() {
  dir.create(dirname(output_file), recursive = TRUE, showWarnings = FALSE)
  jsonlite::write_json(report, output_file, pretty = TRUE, auto_unbox = TRUE,
                       digits = NA, null = "null", na = "null")
}

close_numeric <- function(actual, expected, atol, rtol) {
  same_shape <- identical(dim(actual), dim(expected)) && length(actual) == length(expected)
  if (!same_shape) return(list(passed = FALSE, same_shape = FALSE))
  same_na <- identical(is.na(actual), is.na(expected))
  finite <- is.finite(actual) & is.finite(expected)
  no_infinity <- !any(is.infinite(actual) | is.infinite(expected))
  error <- abs(actual[finite] - expected[finite])
  threshold <- atol + rtol * abs(expected[finite])
  list(passed = same_na && no_infinity && all(error <= threshold),
       same_shape = TRUE, same_missingness = same_na, no_infinity = no_infinity,
       compared_values = sum(finite), max_abs_error = if (length(error)) max(error) else 0,
       max_threshold_ratio = if (length(error)) max(error / threshold) else 0)
}
iterations <- function(fit) lapply(fit$iterHist, function(h) {
  if (is.matrix(h)) nrow(h) else 0L
})
history_converged <- function(fit) {
  is.list(fit$iterHist) && length(fit$iterHist) > 0L &&
    all(vapply(fit$iterHist, function(h) {
      is.matrix(h) && nrow(h) > 0L && utils::tail(h[, 1], 1) == 0
    }, logical(1)))
}

saved_kind <- RNGkind()
tryCatch({
  stopifnot(requireNamespace("Amelia", quietly = TRUE),
            as.character(utils::packageVersion("Amelia")) == "1.8.3",
            requireNamespace("ameliatorch", quietly = TRUE))
  ameliatorch::use_amelia_python(python = Sys.getenv("RETICULATE_PYTHON"))
  torch <- reticulate::import("torch")
  torch$set_num_threads(1L)
  reticulate::import("amelia_torch.backends")$resolve_backend(device, dtype)
  platform <- reticulate::import("platform")
  report$environment <- list(
    system = unname(Sys.info()["sysname"]), architecture = unname(Sys.info()["machine"]),
    R = as.character(getRversion()), Amelia = as.character(utils::packageVersion("Amelia")),
    ameliatorch = as.character(utils::packageVersion("ameliatorch")),
    reticulate = as.character(utils::packageVersion("reticulate")),
    python = platform$python_version(), torch = torch$`__version__`,
    cuda_runtime = torch$version$cuda,
    accelerator_name = if (device == "cuda") torch$cuda$get_device_name(0L) else device
  )
  hash <- reticulate::import("hashlib")
  paths <- reticulate::import("pathlib")
  source_files <- c("scripts/validate_r_accelerator_edges.R", "r-package/R/torch_compat.R",
                    "r-package/src/rng_state.c", "src/amelia_torch/em.py",
                    "src/amelia_torch/backends.py")
  report$source_sha256 <- as.list(stats::setNames(vapply(source_files, function(path) {
    hash$sha256(paths$Path(path)$read_bytes())$hexdigest()
  }, character(1)), source_files))
  report$source_note <- "Hashes describe checkout source; install this checkout's R and Python packages before running."
  RNGkind("Mersenne-Twister", "Inversion", "Rejection")
  set.seed(6101)
  data <- data.frame(a = rnorm(80), b = rnorm(80), c = rnorm(80))
  data$c <- data$c + .3 * data$a
  data$a[seq(3, 80, 9)] <- NA_real_
  data$b[seq(5, 80, 11)] <- NA_real_
  initial <- diag(4)
  initial[1, 1] <- -1
  initial[-1, 1] <- initial[1, -1] <- c(.1, -.2, .15)
  initial[2, 3] <- initial[3, 2] <- .2
  master_initial <- copy_value(initial)
  master_data <- copy_value(data)
  integer_start <- diag(4)
  integer_start[1, 1] <- -1
  storage.mode(integer_start) <- "integer"
  cases <- list(
    identity_none_m2 = list(startvals = 1, m = 2, boot.type = "none"),
    identity_ordinary_m2 = list(startvals = 1, m = 2, boot.type = "ordinary"),
    double_none_m2 = list(startvals = initial, m = 2, boot.type = "none"),
    double_ordinary_m2 = list(startvals = initial, m = 2, boot.type = "ordinary"),
    integer_none_m2 = list(startvals = integer_start, m = 2, boot.type = "none"),
    emburn_minimum_35 = list(startvals = 1, emburn = c(35, 45)),
    emburn_maximum_2 = list(startvals = 1, emburn = c(0, 2))
  )
  evaluate <- function(engine, arguments, seed) {
    supplied <- copy_value(arguments)
    start <- copy_value(supplied$startvals)
    original_data <- copy_value(supplied$x)
    warning_module <- reticulate::import("warnings", convert = FALSE)
    context <- warning_module$catch_warnings(record = TRUE)
    records <- context$`__enter__`()
    on.exit(context$`__exit__`(NULL, NULL, NULL), add = TRUE)
    warning_module$simplefilter("always")
    warnings <- character()
    error <- NULL
    fn <- if (engine == "reference") Amelia::amelia else ameliatorch::amelia_torch_compat
    if (engine != "reference") supplied <- c(supplied, list(device = device, dtype = dtype))
    set.seed(seed)
    invisible(capture.output(value <- tryCatch(withCallingHandlers(
      do.call(fn, supplied), warning = function(w) {
        warnings <<- c(warnings, sanitize(conditionMessage(w)))
        invokeRestart("muffleWarning")
      }), error = function(e) {
        error <<- list(class = class(e)[[1]], message = sanitize(conditionMessage(e)))
        NULL
      })))
    # Capture both visible state and subsequent C/R stream BEFORE any Python call.
    rng <- list(visible_seed = copy_value(.Random.seed),
                next_uniforms = runif(6), next_normals = rnorm(6))
    python_warnings <- if (reticulate::py_len(records)) {
      vapply(seq_len(reticulate::py_len(records)), function(i) sanitize(
        reticulate::py_str(records$`__getitem__`(as.integer(i - 1L))$message)), character(1))
    } else character()
    list(value = value, error = error, r_warnings = warnings, python_warnings = python_warnings,
         rng = rng, start_before = start, start_after = supplied$startvals,
         caller_data_unchanged = identical(supplied$x, original_data))
  }
  describe <- function(run) {
    fit <- run$value
    list(error = run$error, code = fit$code, message = fit$message,
         iterations = iterations(fit), converged_by_history = history_converged(fit),
         iter_history = fit$iterHist, r_warnings = run$r_warnings,
         python_warnings = run$python_warnings,
         caller_data_unchanged = run$caller_data_unchanged,
         start_type = typeof(run$start_after),
         start_changed = !identical(run$start_after, run$start_before),
         backend = attr(fit, "amelia_torch_backend", exact = TRUE))
  }
  for (name in names(cases)) {
    args <- utils::modifyList(list(x = data, m = 1, p2s = 0, boot.type = "none",
      tolerance = gates$em_tolerance, autopri = 0, emburn = c(0, 100)), cases[[name]])
    runs <- lapply(c("reference", "hybrid"), evaluate, arguments = args, seed = 77L)
    names(runs) <- c("reference", "hybrid")
    result <- list(name = name, seed = 77L, n = 80L, p = 3L,
                   options = args[setdiff(names(args), "x")],
                   engines = lapply(runs, describe), passed = FALSE)
    result <- tryCatch({
      stopifnot(is.null(runs$reference$error), is.null(runs$hybrid$error))
      expected <- runs$reference$value
      actual <- runs$hybrid$value
      meta <- attr(actual, "amelia_torch_backend", exact = TRUE)
      theta <- close_numeric(actual$theta, expected$theta, gates$theta_atol, gates$theta_rtol)
      scale <- vapply(data, stats::sd, numeric(1), na.rm = TRUE)
      output <- lapply(seq_along(actual$imputations), function(i) {
        close_numeric(sweep(as.matrix(actual$imputations[[i]]), 2, scale, "/"),
                      sweep(as.matrix(expected$imputations[[i]]), 2, scale, "/"),
                      gates$standardized_output_atol, gates$standardized_output_rtol)
      })
      observed <- !is.na(as.matrix(data))
      alias_checks <- vapply(runs, function(run) {
        if (is.matrix(run$start_before) && typeof(run$start_before) == "double") {
          !identical(run$start_before, run$start_after) &&
            identical(run$start_after, run$value$arguments$startvals) &&
            isTRUE(all.equal(unname(run$start_after),
                             unname(run$value$theta[, , run$value$m]), tolerance = 0))
        } else identical(run$start_before, run$start_after) &&
          identical(run$start_before, run$value$arguments$startvals)
      }, logical(1))
      expected_converged <- name != "emburn_maximum_2"
      checks <- list(
        success_codes = identical(as.integer(actual$code), 1L) && expected$code == 1L,
        original_class = identical(class(actual), class(expected)),
        same_missingness = identical(actual$missMatrix, expected$missMatrix),
        observed_exact = all(vapply(actual$imputations, function(draw) {
          identical(unname(as.matrix(draw)[observed]), unname(as.matrix(data)[observed]))
        }, logical(1))),
        all_completed_finite = all(vapply(actual$imputations, function(draw) all(is.finite(as.matrix(draw))), logical(1))),
        theta_within_gate = theta$passed,
        output_within_gate = all(vapply(output, function(x) x$passed, logical(1))),
        same_rng_and_followups = identical(runs$reference$rng, runs$hybrid$rng),
        aliases_preserved_per_engine = all(alias_checks),
        data_unchanged = all(vapply(runs, function(run) run$caller_data_unchanged, logical(1))),
        requested_backend = identical(meta$device, device) && identical(meta$dtype, dtype) &&
          isTRUE(meta$current_call_torch_used) && identical(meta$current_call_gpu_used, device != "cpu") &&
          length(meta$fits) == actual$m && all(vapply(meta$fits, function(fit) {
            identical(fit$device, device) && identical(fit$dtype, dtype)
          }, logical(1))),
        convergence_status = identical(meta$converged, expected_converged) &&
          identical(meta$converged, history_converged(actual)) &&
          identical(history_converged(expected), expected_converged)
      )
      if (name == "double_none_m2") checks$second_fit_reuses_theta <-
        nrow(actual$iterHist[[2]]) == 1L && nrow(expected$iterHist[[2]]) == 1L
      if (name == "emburn_minimum_35") checks$minimum_iterations <-
        all(unlist(iterations(actual)) == 35L) && all(unlist(iterations(expected)) == 35L)
      if (name == "emburn_maximum_2") {
        checks$maximum_iterations <- all(unlist(iterations(actual)) == 2L) &&
          all(unlist(iterations(expected)) == 2L)
        checks$cutoff_warning <- any(grepl("emburn maximum before convergence",
          runs$hybrid$python_warnings, fixed = TRUE))
      }
      result$checks <- checks
      result$theta_comparison <- theta
      result$output_comparisons <- output
      result$identical_iteration_history <- identical(actual$iterHist, expected$iterHist)
      result$passed <- all(unlist(checks))
      result
    }, error = function(e) {
      result$check_error <- sanitize(conditionMessage(e)); result
    })
    report$cases[[name]] <- result
    write_report()
    cat(name, if (isTRUE(result$passed)) "PASS" else "FAIL", "\n")
  }

  # One deliberately ill-conditioned PUBLIC call per engine. Compare legal
  # status to its own final theta; floating-point signs/trajectories can differ.
  set.seed(7)
  pathological <- matrix(rnorm(1000), 200, 5)
  pathological[, 5] <- pathological[, 1] + pathological[, 2]
  pathological[sample(length(pathological), 400)] <- NA_real_
  options <- list(x = pathological, m = 1, p2s = 0, boot.type = "none", startvals = 1,
                  empri = 0, autopri = .05, tolerance = 1e-15, emburn = c(300, 300))
  runs <- lapply(c("reference", "hybrid"), evaluate, arguments = options, seed = 102L)
  names(runs) <- c("reference", "hybrid")
  audit <- list(name = "pathological_autopri", seed = 102L, input_seed = 7L,
                n = 200L, p = 5L, options = options[setdiff(names(options), "x")],
                engines = lapply(runs, describe), passed = FALSE,
                statistical_quality_sample = FALSE,
                numerical_comparison_required = FALSE,
                reason = "Near-singular eigenvalue signs and adaptive trajectories can differ by device/precision.")
  for (engine in names(runs)) audit$engines[[engine]] <- tryCatch({
    run <- runs[[engine]]
    stopifnot(is.null(run$error))
    fit <- run$value
    history <- fit$iterHist[[1]]
    values <- eigen(fit$theta[-1, -1, 1], symmetric = TRUE, only.values = TRUE)$values
    expected_code <- if (any(values < .Machine$double.eps)) 2L else 1L
    n <- sum(rowSums(!is.na(pathological)) > 0)
    effective <- 0L
    updates <- list()
    for (i in seq_len(nrow(history))) {
      previous <- if (i > 1L) history[seq.int(max(1L, i - 20L), i - 1L), 3] else 0
      if (history[i, 2] == 1 && sum(previous) > 3 && effective < .05 * n) {
        effective <- as.integer(effective + .01 * n)
        updates[[length(updates) + 1L]] <- list(iteration = i, empri = effective)
      }
    }
    blank <- rowSums(!is.na(pathological)) == 0
    observed <- !is.na(pathological)
    valid_result <- if (fit$code == 2L) all(is.na(fit$imputations[[1]])) else {
      draw <- as.matrix(fit$imputations[[1]])
      all(is.finite(draw[!blank, ])) && all(is.na(draw[blank, ])) &&
        identical(unname(draw[observed]), unname(pathological[observed]))
    }
    checks <- list(legal_original_status = fit$code == expected_code,
                   bounded_iterations = nrow(history) == 300L,
                   output_matches_status = valid_result,
                   data_unchanged = run$caller_data_unchanged)
    if (engine == "hybrid") {
      meta <- attr(fit, "amelia_torch_backend", exact = TRUE)
      checks$autopri_diagnostic <- meta$fits[[1]]$empri_final == effective
      checks$convergence_diagnostic <- identical(meta$converged, history_converged(fit)) &&
        identical(meta$fits[[1]]$converged, history_converged(fit))
      checks$requested_backend <- identical(meta$device, device) && identical(meta$dtype, dtype) &&
        length(meta$fits) == 1L && identical(meta$fits[[1]]$device, device) &&
        identical(meta$fits[[1]]$dtype, dtype) && isTRUE(meta$current_call_torch_used) &&
        identical(meta$current_call_gpu_used, device != "cpu")
      checks$unconverged_warned <- history_converged(fit) || any(grepl(
        "emburn maximum before convergence", run$python_warnings, fixed = TRUE))
    }
    entry <- describe(run)
    entry$final_covariance_min_eigenvalue <- min(values)
    entry$expected_code_from_own_theta <- expected_code
    entry$empri_from_public_history <- effective
    entry$autopri_updates <- updates
    entry$autopri_branch_observed <- length(updates) > 0L
    entry$checks <- checks
    entry$passed <- all(unlist(checks))
    entry
  }, error = function(e) {
    entry <- describe(runs[[engine]])
    entry$check_error <- sanitize(conditionMessage(e)); entry$passed <- FALSE; entry
  })
  audit$passed <- all(vapply(audit$engines, function(x) isTRUE(x$passed), logical(1)))
  report$cases$pathological_autopri <- audit
  write_report()
  cat("pathological_autopri", if (audit$passed) "PASS (status/diagnostics only)" else "FAIL", "\n")

  # allthetas is an internal EM diagnostic, NOT an extra public amelia option.
  # This bounded oracle always uses CPU64; never label it accelerator coverage.
  report$cpu64_allthetas_alias_oracle <- tryCatch({
    upstream <- asNamespace("Amelia")
    stacked <- get("amstack", upstream)(as.matrix(data), colorder = FALSE)$x
    starts <- lapply(1:2, function(i) copy_value(initial))
    reference <- get("emarch", upstream)(copy_value(stacked), thetaold = starts[[1]],
      p2s = 0, tolerance = 1e-6, autopri = 0, allthetas = TRUE)
    context <- getFromNamespace(".torch_em_context", "ameliatorch")("cpu", "float64")
    actual <- context$environment$emarch(copy_value(stacked), thetaold = starts[[2]],
      p2s = 0, tolerance = 1e-6, autopri = 0, allthetas = TRUE)
    upper <- upper.tri(initial, diag = TRUE); upper[1, 1] <- FALSE
    checks <- list(
      same_history = isTRUE(all.equal(actual, reference, tolerance = 1e-7)),
      same_final_alias = isTRUE(all.equal(starts[[2]], starts[[1]], tolerance = 1e-7)),
      initial_column_preserved = isTRUE(all.equal(actual$thetanew[, 1], initial[upper], tolerance = 0)))
    list(device = "cpu", dtype = "float64", public_option = FALSE, checks = checks,
         passed = all(unlist(checks)))
  }, error = function(e) list(device = "cpu", dtype = "float64", passed = FALSE,
                              error = sanitize(conditionMessage(e))))
  report$master_inputs_unchanged <- identical(initial, master_initial) && identical(data, master_data)
  report$autopri_trigger_coverage <- vapply(audit$engines,
    function(x) isTRUE(x$autopri_branch_observed), logical(1))
  report$all_checks_passed <- all(vapply(report$cases, function(x) isTRUE(x$passed), logical(1))) &&
    isTRUE(report$cpu64_allthetas_alias_oracle$passed) && isTRUE(report$master_inputs_unchanged)
}, error = function(e) {
  report$setup_error <<- list(class = class(e)[[1]], message = sanitize(conditionMessage(e)))
}, finally = do.call(RNGkind, as.list(saved_kind)))
write_report()
cat("Boundary checks:", if (report$all_checks_passed) "PASS" else "FAIL", "\n")
if (!report$all_checks_passed) quit(status = 1L)
