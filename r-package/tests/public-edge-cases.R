# Small public-pipeline regression tests against unmodified Amelia 1.8.3.
# No timing claims. Optional edge_report is left in this script's environment
# so a validation harness can serialize evidence without adding a dependency.
source_root <- Sys.getenv("AMELIATORCH_R_SOURCE", unset = "")
if (nzchar(source_root)) {
  source(file.path(source_root, "R", "environment.R"))
  source(file.path(source_root, "R", "torch_compat.R"))
  make_context <- .torch_em_context
} else {
  library(ameliatorch)
  make_context <- getFromNamespace(".torch_em_context", "ameliatorch")
}
stopifnot(as.character(utils::packageVersion("Amelia")) == "1.8.3")
use_amelia_python(python = Sys.getenv("RETICULATE_PYTHON"))
reticulate::import("torch")$set_num_threads(1L)
upstream <- asNamespace("Amelia")
copy_value <- function(x) unserialize(serialize(x, NULL))
same <- function(actual, expected, tolerance = 1e-7) {
  result <- all.equal(actual, expected, tolerance = tolerance)
  if (!isTRUE(result)) stop(paste(result, collapse = "; "), call. = FALSE)
}
edge_report <- list(
  schema_version = 1L, scope = "Bounded public hybrid CPU64 edge cases; no GPU or timing claim",
  R = as.character(getRversion()), Amelia = as.character(utils::packageVersion("Amelia")),
  cases = list(), instrumentation = list(),
  not_covered = c("GPU precision variants", "public autopri-update trigger and fixed-hold audit")
)

evaluate <- function(fn, arguments, seed, python_warnings = FALSE, inspect_rng = FALSE) {
  # Python's RuntimeWarning is not an R warning condition. Record it separately,
  # with the warnings context entered before the reference R seed is selected.
  if (python_warnings) {
    warnings_module <- reticulate::import("warnings", convert = FALSE)
    context <- warnings_module$catch_warnings(record = TRUE)
    records <- context$`__enter__`()
    on.exit(context$`__exit__`(NULL, NULL, NULL), add = TRUE)
    warnings_module$simplefilter("always")
  }
  r_warnings <- character()
  supplied_arguments <- copy_value(arguments)
  initial_startvals <- copy_value(supplied_arguments$startvals)
  set.seed(seed)
  output <- capture.output(value <- withCallingHandlers(
    do.call(fn, supplied_arguments), warning = function(warning) {
      r_warnings <<- c(r_warnings, conditionMessage(warning))
      invokeRestart("muffleWarning")
    }
  ))
  # Read both observable RNG layers before crossing any further Python boundary.
  rng <- if (inspect_rng) list(visible_seed = copy_value(.Random.seed),
                               next_uniforms = stats::runif(6),
                               next_normals = stats::rnorm(6)) else NULL
  py_warnings <- character()
  if (python_warnings && reticulate::py_len(records)) {
    py_warnings <- vapply(seq_len(reticulate::py_len(records)), function(i) {
      reticulate::py_str(records$`__getitem__`(as.integer(i - 1L))$message)
    }, character(1))
  }
  list(value = value, output = output, r_warnings = r_warnings,
       python_warnings = py_warnings, rng = rng,
       initial_startvals = initial_startvals,
       supplied_startvals = supplied_arguments$startvals)
}

compare_pair <- function(name, data, options = list(), seed = 77L, expected_code = 1L,
                         reference = Amelia::amelia, hybrid = amelia_torch_compat,
                         inspect_rng = FALSE) {
  arguments <- utils::modifyList(list(x = data, m = 1, p2s = 0, boot.type = "none",
                                      autopri = 0, tolerance = 1e-6), options)
  original <- evaluate(reference, arguments, seed, inspect_rng = inspect_rng)
  actual <- evaluate(hybrid, arguments, seed, python_warnings = TRUE,
                      inspect_rng = inspect_rng)
  stopifnot(original$value$code == expected_code, actual$value$code == expected_code,
            identical(actual$value$message, original$value$message),
            identical(actual$r_warnings, original$r_warnings))
  if (inspect_rng) stopifnot(identical(actual$rng, original$rng))
  meta <- attr(actual$value, "amelia_torch_backend", exact = TRUE)
  stopifnot(meta$device == "cpu", meta$dtype == "float64", !isTRUE(meta$gpu_used))
  if (expected_code == 1L) {
    stopifnot(identical(class(actual$value), class(original$value)),
              identical(actual$value$missMatrix, original$value$missMatrix))
    actual_arguments <- actual$value$arguments
    original_arguments <- original$value$arguments
    # Explicit double startvals are overwritten in place by upstream emcore,
    # including the archive alias. Final values allow only numerical tolerance;
    # all other archived options still require exact equality.
    same(actual_arguments$startvals, original_arguments$startvals)
    stopifnot(identical(typeof(actual_arguments$startvals),
                        typeof(original_arguments$startvals)))
    actual_arguments$startvals <- original_arguments$startvals <- NULL
    stopifnot(identical(actual_arguments, original_arguments))
    same(actual$value$theta, original$value$theta)
    same(actual$value$imputations, original$value$imputations, 1e-6)
    same(actual$value$iterHist, original$value$iterHist, 0)
    observed <- !is.na(data)
    stopifnot(all(vapply(actual$value$imputations, function(draw) {
      identical(as.matrix(draw)[observed], as.matrix(data)[observed])
    }, logical(1))))
  } else {
    stopifnot(!isTRUE(meta$converged), !isTRUE(meta$current_call_torch_used),
              identical(meta$fits, list()))
  }
  histories <- original$value$iterHist
  edge_report$cases[[name]] <<- list(
    seed = seed, input_dimensions = dim(data), code = actual$value$code,
    reference_message = original$value$message,
    reference_iterations = lapply(histories, function(x) if (is.matrix(x)) nrow(x) else 0L),
    hybrid_converged = meta$converged, hybrid_torch_used = meta$current_call_torch_used,
    reference_r_warnings = original$r_warnings, hybrid_r_warnings = actual$r_warnings,
    hybrid_python_warnings = actual$python_warnings,
    rng_seed_and_followup_checked = inspect_rng,
    matching_outputs_and_history = expected_code == 1L,
    error_contract_matched = expected_code != 1L, passed = TRUE
  )
  cat("Public edge case passed:", name, "(code", expected_code, ")\n")
  list(original = original, actual = actual)
}

saved_rng_kind <- RNGkind()
tryCatch({
  RNGkind("Mersenne-Twister", "Inversion", "Rejection")
  set.seed(6101)
  complete <- data.frame(a = rnorm(80), b = rnorm(80), c = rnorm(80))
  complete$c <- complete$c + .3 * complete$a
  data <- complete
  data$a[seq(3, 80, 9)] <- NA_real_
  data$b[seq(5, 80, 11)] <- NA_real_
  default <- compare_pair("default_startvals", data)
  compare_pair("identity_startvals_1", data, list(startvals = 1))
  initial <- diag(4)
  initial[1, 1] <- -1
  initial[-1, 1] <- initial[1, -1] <- c(.1, -.2, .15)
  initial[2, 3] <- initial[3, 2] <- .2
  initial_copy <- copy_value(initial)
  compare_pair("explicit_startvals", data, list(startvals = initial))
  stopifnot(identical(initial, initial_copy))

  # emcore's double NumericMatrix/Armadillo alias is observable through the
  # caller's matrix, each archived argument list, and the next imputation's
  # initial theta. Integer starts are coerced to a fresh double buffer instead.
  typed_pairs <- list()
  for (boot in c("none", "ordinary")) {
    for (mode in c("default", "identity", "double", "integer")) {
      start <- switch(mode, default = 0, identity = 1, double = copy_value(initial),
                      integer = { value <- diag(4); value[1, 1] <- -1
                                  storage.mode(value) <- "integer"; value })
      name <- paste("startvals_m2", boot, mode, sep = "_")
      pair <- compare_pair(name, data, list(m = 2, boot.type = boot, startvals = start),
                            inspect_rng = TRUE)
      for (fit in pair) {
        if (mode == "double") {
          stopifnot(!identical(fit$supplied_startvals, fit$initial_startvals),
                    identical(fit$supplied_startvals, fit$value$arguments$startvals))
          same(unname(fit$supplied_startvals), unname(fit$value$theta[, , 2]), 0)
        } else {
          stopifnot(identical(fit$supplied_startvals, fit$initial_startvals),
                    identical(fit$value$arguments$startvals, fit$initial_startvals))
        }
      }
      if (boot == "none") {
        iterations <- vapply(pair$actual$value$iterHist, nrow, integer(1))
        if (mode == "double") stopifnot(iterations[2] == 1L)
        else stopifnot(iterations[1] == iterations[2], iterations[2] > 1L)
      }
      edge_report$cases[[name]]$caller_and_archive_alias_matched <- TRUE
      edge_report$cases[[name]]$startvals_storage_type <- typeof(start)
      edge_report$cases[[name]]$startvals_mutated <- mode == "double"
      typed_pairs[[paste(boot, mode, sep = "_")]] <- pair
    }
  }

  # The archive may itself be reused or persisted and appended. Each engine
  # receives its own independent original object so shared aliases cannot mask
  # a mismatch, including any upstream quirks in arglist replay.
  for (operation in c("arglist", "append")) {
    results <- list()
    for (engine in c("original", "actual")) {
      old <- copy_value(typed_pairs$ordinary_double[[engine]]$value)
      fn <- if (engine == "original") Amelia::amelia else amelia_torch_compat
      arguments <- if (operation == "arglist") {
        list(x = data, m = 2, p2s = 0, arglist = old$arguments)
      } else list(x = old, m = 1, p2s = 0)
      results[[engine]] <- evaluate(fn, arguments, 918L,
                                    python_warnings = engine == "actual", inspect_rng = TRUE)
    }
    original <- results$original$value
    actual <- results$actual$value
    stopifnot(original$code == 1L, actual$code == 1L,
              identical(results$original$rng, results$actual$rng))
    same(actual$theta, original$theta)
    same(actual$imputations, original$imputations, 1e-6)
    same(actual$iterHist, original$iterHist, 0)
    same(actual$arguments, original$arguments)
    if (operation == "append") stopifnot(actual$m == 3L)
    edge_report$cases[[paste0("explicit_archive_", operation)]] <- list(
      seed = 918L, code = actual$code, imputations = actual$m,
      rng_seed_and_followup_checked = TRUE, matching_outputs_and_history = TRUE,
      archived_arguments_matched = TRUE, passed = TRUE
    )
    cat("Explicit archive", operation, "passed.\n")
  }

  # The allthetas initial column must be captured BEFORE alias writeback.
  stacked <- get("amstack", upstream)(as.matrix(data), colorder = FALSE)$x
  starts <- lapply(1:2, function(i) copy_value(initial))
  reference_history <- get("emarch", upstream)(stacked, thetaold = starts[[1]],
                      p2s = 0, tolerance = 1e-6, autopri = 0, allthetas = TRUE)
  hybrid_history <- make_context("cpu", "float64")$environment$emarch(
    stacked, thetaold = starts[[2]], p2s = 0, tolerance = 1e-6, autopri = 0, allthetas = TRUE)
  same(hybrid_history, reference_history)
  same(starts[[2]], starts[[1]])
  upper <- upper.tri(initial, diag = TRUE); upper[1, 1] <- FALSE
  same(hybrid_history$thetanew[, 1], initial[upper], 0)
  edge_report$cases$allthetas_explicit_alias <- list(
    initial_column_preserved = TRUE, caller_final_theta_matched = TRUE, passed = TRUE)

  minimum <- compare_pair("emburn_minimum_35", data, list(emburn = c(35, 45)))
  stopifnot(nrow(default$original$value$iterHist[[1]]) < 35L,
            nrow(minimum$actual$value$iterHist[[1]]) == 35L,
            isTRUE(attr(minimum$actual$value, "amelia_torch_backend")$converged))
  cutoff <- compare_pair("emburn_maximum_2", data, list(emburn = c(0, 2)))
  stopifnot(nrow(cutoff$actual$value$iterHist[[1]]) == 2L,
            tail(cutoff$actual$value$iterHist[[1]][, 1], 1) > 0L,
            identical(attr(cutoff$actual$value, "amelia_torch_backend")$converged, FALSE),
            any(grepl("emburn maximum before convergence", cutoff$actual$python_warnings,
                      fixed = TRUE)), length(cutoff$original$r_warnings) == 0L)

  blank <- data
  blank[1, ] <- NA_real_
  blank_pair <- compare_pair("all_missing_analysis_row", blank, list(p2s = 1))
  stopifnot(all(is.na(blank_pair$actual$value$imputations[[1]][1, ])),
            sum(is.na(blank_pair$actual$value$imputations[[1]])) == ncol(blank),
            any(grepl("will remain unimputed", blank_pair$original$output, fixed = TRUE)),
            any(grepl("will remain unimputed", blank_pair$actual$output, fixed = TRUE)))
  compare_pair("no_missing_checked_input", complete, expected_code = 39L)
  no_check <- compare_pair("no_missing_incheck_false", complete, list(incheck = FALSE))
  stopifnot(identical(no_check$actual$value$imputations[[1]], complete),
            all(is.na(no_check$actual$value$iterHist[[1]])),
            isTRUE(attr(no_check$actual$value, "amelia_torch_backend")$fits[[1]]$complete_sample))
  bad <- data; bad$a <- NA_real_
  compare_pair("all_missing_column", bad, expected_code = 4L)
  bad <- data; bad$a <- 3
  compare_pair("constant_column", bad, expected_code = 43L)
  compare_pair("too_few_rows", data[1:5, ], expected_code = 34L)

  bounds <- matrix(c(1, 100, 100.001), nrow = 1)
  compare_pair("max_resample_zero_rejected", data,
               list(bounds = bounds, max.resample = 0), expected_code = 52L)
  bounded <- compare_pair("bounds_resampling_exhausted", data,
                          list(bounds = bounds, max.resample = 1))
  values <- bounded$actual$value$imputations[[1]]$a[is.na(data$a)]
  stopifnot(length(values) == 9L, all(abs(values - 100) < 1e-12))
  edge_report$cases$bounds_resampling_exhausted$boundary_clamped_cells <- length(values)
  edge_report$cases$bounds_resampling_exhausted$evidence <-
    "All nine missing a values equal the remote lower bound after one allowed resample."

  compare_pair("incheck_false_missing_input", data, list(incheck = FALSE))
  collected <- compare_pair("collect_true", data, list(collect = TRUE))
  same(collected$actual$value$theta, default$actual$value$theta, 0)
  same(collected$actual$value$imputations, default$actual$value$imputations, 0)
  for (verbosity in 1:2) {
    verbose <- compare_pair(paste0("p2s_", verbosity), data, list(p2s = verbosity))
    same(verbose$actual$value$imputations, default$actual$value$imputations, 0)
    stopifnot(any(grepl("PyTorch EM:", verbose$actual$output, fixed = TRUE)),
              length(verbose$original$output) > 0L)
  }

  # Instrument private function copies only. Each runif delegates unchanged to
  # stats::runif and records its actual row indices, without extra RNG draws.
  # Uninstrumented public calls are also compared to the observed calls below.
  boot_observer <- function(record) {
    sampler <- get("bootx", envir = upstream)
    scope <- new.env(parent = environment(sampler))
    scope$runif <- function(n, min = 0, max = 1) {
      result <- stats::runif(n, min, max)
      record$orders[[length(record$orders) + 1L]] <- trunc(result)
      result
    }
    environment(sampler) <- scope
    function(x, priors = NULL, boot.type = "np") {
      record$input <- copy_value(x)
      result <- sampler(x, priors, boot.type)
      record$accepted_sample <- copy_value(result$x)
      result
    }
  }
  observed_reference <- function(record) {
    scope <- new.env(parent = upstream)
    scope$bootx <- boot_observer(record)
    fn <- get("amelia.default", envir = upstream)
    environment(fn) <- scope
    fn
  }
  observed_hybrid <- function(record) {
    fn <- amelia_torch_compat
    scope <- new.env(parent = environment(fn))
    scope$.torch_em_context <- function(device, dtype) {
      bridge <- make_context(device, dtype)
      bridge$environment$bootx <- boot_observer(record)
      bridge
    }
    environment(fn) <- scope
    fn
  }
  set.seed(153)
  bootstrap_data <- data.frame(a = rnorm(24), b = rnorm(24))
  for (branch in c("complete", "redraw")) {
    sample <- bootstrap_data
    sample$a[if (branch == "complete") 24L else 3:24] <- NA_real_
    seed <- if (branch == "complete") 1L else 5L
    options <- list(boot.type = "ordinary", empri = 5)
    baseline <- compare_pair(paste0("bootstrap_", branch), sample, options, seed)
    r_trace <- new.env(parent = emptyenv()); r_trace$orders <- list()
    h_trace <- new.env(parent = emptyenv()); h_trace$orders <- list()
    observed <- compare_pair(paste0("bootstrap_", branch, "_instrumented"), sample,
                              options, seed, reference = observed_reference(r_trace),
                              hybrid = observed_hybrid(h_trace))
    same(observed$original$value, baseline$original$value, 0)
    same(observed$actual$value, baseline$actual$value, 0)
    stopifnot(identical(r_trace$orders, h_trace$orders),
              identical(r_trace$accepted_sample, h_trace$accepted_sample))
    observed_counts <- lapply(r_trace$orders, function(rows) {
      colSums(!is.na(r_trace$input[rows, , drop = FALSE]))
    })
    if (branch == "complete") {
      stopifnot(length(r_trace$orders) == 1L, !anyNA(r_trace$accepted_sample),
                all(is.na(baseline$actual$value$iterHist[[1]])))
      same(unname(baseline$actual$value$theta[-1, -1, 1]),
           unname(stats::cov(r_trace$accepted_sample)), 1e-12)
      stopifnot(isTRUE(attr(baseline$actual$value, "amelia_torch_backend")$fits[[1]]$complete_sample))
      complete_start <- diag(3); complete_start[1, 1] <- -1
      complete_alias <- compare_pair("bootstrap_complete_explicit_startvals", sample,
                    c(options, list(startvals = complete_start)), seed, inspect_rng = TRUE)
      for (fit in complete_alias) {
        stopifnot(identical(fit$supplied_startvals, fit$initial_startvals),
                  identical(fit$value$arguments$startvals, fit$initial_startvals),
                  all(is.na(fit$value$iterHist[[1]])))
      }
      edge_report$cases$bootstrap_complete_explicit_startvals$caller_and_archive_unchanged <- TRUE
    } else {
      stopifnot(length(r_trace$orders) == 2L, any(observed_counts[[1]] == 0L),
                all(observed_counts[[2]] > 0L), anyNA(r_trace$accepted_sample))
    }
    edge_report$instrumentation[[branch]] <- list(
      seed = seed, actual_orders = r_trace$orders, observed_column_counts = observed_counts,
      public_uninstrumented_outputs_identical = TRUE,
      original_hybrid_orders_identical = TRUE,
      accepted_complete = !anyNA(r_trace$accepted_sample)
    )
  }
  stopifnot(identical(environment(get("amelia.default", envir = upstream)), upstream),
            identical(environment(get("bootx", envir = upstream)), upstream))
}, finally = do.call(RNGkind, as.list(saved_rng_kind)))
edge_report$all_passed <- TRUE
cat("Public hybrid CPU64 edge checks passed:", length(edge_report$cases), "cases.\n")
