# Bounded public CPU64 numerical-boundary audit. Near-zero eigenvalue signs
# depend on BLAS: compare each engine with its own actual trajectory, never
# require identical update times or a fabricated identical success/failure code.
library(ameliatorch)
stopifnot(as.character(utils::packageVersion("Amelia")) == "1.8.3")
use_amelia_python(python = Sys.getenv("RETICULATE_PYTHON"))
reticulate::import("torch")$set_num_threads(1L)
upstream <- asNamespace("Amelia")
copy_value <- function(x) unserialize(serialize(x, NULL))
make_context <- getFromNamespace(".torch_em_context", "ameliatorch")
saved_kind <- RNGkind()
autopri_report <- list(schema_version = 1L, scope = "Public CPU64 pathological boundary audit",
                       input_seed = 7L, fit_seed = 102L, engines = list())

tryCatch({
  RNGkind("Mersenne-Twister", "Inversion", "Rejection")
  set.seed(7)
  data <- matrix(rnorm(1000), 200, 5)
  data[, 5] <- data[, 1] + data[, 2]
  data[sample(length(data), 400)] <- NA_real_
  options <- list(m = 1, p2s = 0, boot.type = "none", startvals = 1,
                  empri = 0, autopri = .05, tolerance = 1e-15, emburn = c(300, 300))
  set.seed(102)
  invisible(capture.output(prepared <- suppressWarnings(do.call(
    get("amelia_prep", upstream), c(list(x = copy_value(data)), options)))))
  n <- nrow(prepared$x)
  p <- ncol(prepared$x)
  stopifnot(n == 197L, p == 5L)
  autopri_report$raw_dimensions <- dim(data)
  autopri_report$prepared_dimensions <- c(n, p)
  autopri_report$blank_rows <- which(rowSums(!is.na(data)) == 0L)
  autopri_report$options <- options
  upper <- upper.tri(matrix(0, p + 1, p + 1), diag = TRUE)
  upper[1, 1] <- FALSE
  restore_theta <- function(column) {
    result <- matrix(0, p + 1, p + 1)
    result[1, 1] <- -1
    result[upper] <- column
    result[lower.tri(result)] <- t(result)[lower.tri(result)]
    result
  }
  for (engine in c("reference", "hybrid")) {
    fn <- if (engine == "reference") Amelia::amelia else amelia_torch_compat
    warnings <- character()
    set.seed(102)
    invisible(capture.output(fit <- withCallingHandlers(
      do.call(fn, c(list(x = copy_value(data)), options)), warning = function(w) {
        warnings <<- c(warnings, conditionMessage(w))
        invokeRestart("muffleWarning")
      })))
    # boot.type='none' means this is the same standardized, ordered public EM
    # input. An independent replay supplies all iteration theta values.
    em <- if (engine == "reference") get("emarch", upstream) else
      make_context("cpu", "float64")$environment$emarch
    trace <- em(copy_value(prepared$x), p2s = 0, startvals = 1, empri = 0,
                autopri = .05, tolerance = 1e-15, emburn = c(300, 300), allthetas = TRUE)
    history <- fit$iterHist[[1]]
    stopifnot(identical(unname(trace$iter.hist), unname(history)), nrow(history) == 300L,
              isTRUE(all.equal(restore_theta(trace$thetanew[, ncol(trace$thetanew)]),
                               unname(fit$theta[, , 1]), tolerance = 0)))

    # Reconstruct the documented integer update from observed public flags.
    effective <- 0L
    updates <- list()
    for (i in seq_len(nrow(history))) {
      previous <- if (i > 1L) history[seq.int(max(1L, i - 20L), i - 1L), 3] else 0
      if (history[i, 2] == 1 && sum(previous) > 3 && effective < .05 * n) {
        effective <- as.integer(effective + .01 * n)
        updates[[length(updates) + 1L]] <- c(iteration = i, empri = effective)
      }
    }
    hold_checks <- list()
    for (update in updates) {
      i <- unname(update["iteration"])
      e <- unname(update["empri"])
      if (i == nrow(history)) next
      previous_theta <- restore_theta(trace$thetanew[, i + 1L])
      next_theta <- restore_theta(trace$thetanew[, i + 2L])
      # Independent unregularized single-step replay at the actual previous
      # theta, then apply the prior formula outside the EM implementation. Use
      # each engine's own sweep: near singularity, different factorization
      # decisions can change the raw conditional moments. With one iteration
      # and autopri=0, no update-history or adaptive hold can enter this oracle.
      raw <- em(copy_value(prepared$x), p2s = 0,
        thetaold = copy_value(previous_theta), empri = 0, autopri = 0,
        tolerance = 1e6, emburn = c(1, 1))$thetanew
      expected <- raw
      expected[-1, -1] <- raw[-1, -1] * n / (n + e + p + 2)
      wrongly_rebuilt <- expected
      wrongly_rebuilt[-1, -1] <- expected[-1, -1] + diag(e / (n + e + p + 2), p)
      fixed_error <- max(abs(next_theta - expected))
      rebuilt_error <- max(abs(next_theta - wrongly_rebuilt))
      stopifnot(fixed_error < 1e-10, rebuilt_error > e / (2 * (n + e + p + 2)))
      hold_checks[[length(hold_checks) + 1L]] <- list(
        update_iteration = i, tested_iteration = i + 1L, current_empri = e,
        initial_hold = 0, fixed_hold_max_abs_error = fixed_error,
        hypothetical_rebuilt_hold_max_abs_error = rebuilt_error)
    }

    eigenvalues <- eigen(fit$theta[-1, -1, 1], symmetric = TRUE, only.values = TRUE)$values
    expected_code <- if (any(eigenvalues < .Machine$double.eps)) 2L else 1L
    stopifnot(fit$code == expected_code, min(abs(eigenvalues)) < 1e-9)
    if (fit$code == 2L) stopifnot(all(is.na(fit$imputations[[1]]))) else {
      draw <- fit$imputations[[1]]
      observed <- !is.na(data)
      blank <- rowSums(!is.na(data)) == 0L
      stopifnot(identical(unname(as.matrix(draw)[observed]), unname(data[observed])),
                all(is.finite(as.matrix(draw)[!blank, ])), all(is.na(draw[blank, ])))
    }
    backend <- if (engine == "hybrid") attr(fit, "amelia_torch_backend") else NULL
    if (engine == "hybrid") {
      stopifnot(backend$fits[[1]]$empri_final == effective,
                identical(backend$converged, tail(history[, 1], 1L) == 0),
                identical(backend$fits[[1]]$converged, tail(history[, 1], 1L) == 0))
    }
    autopri_report$engines[[engine]] <- list(
      code = fit$code, message = fit$message, iterations = nrow(history),
      empri_initial = 0, empri_final = effective, updates = updates,
      singular_flag_count = sum(history[, 3]), final_history = unname(tail(history, 1)),
      final_covariance_min_eigenvalue = min(eigenvalues), r_warnings = warnings,
      hold_checks = hold_checks, hold_branch_observed = length(hold_checks) > 0L,
      status_matches_original_eigenvalue_rule = TRUE,
      hybrid_metadata = backend, passed = TRUE)
    cat("Public autopri boundary:", engine, "code", fit$code, "updates", length(updates),
        "final empri", effective, "fixed-hold checks", length(hold_checks), "\n")
  }
}, finally = do.call(RNGkind, as.list(saved_kind)))
autopri_report$both_engines_hold_branch_observed <- all(vapply(
  autopri_report$engines, function(value) value$hold_branch_observed, logical(1)))
autopri_report$all_executed_checks_passed <- TRUE
# A different BLAS may never cross zero on this input. Record that missing
# branch explicitly instead of fabricating an update or asserting exact flags.
if (!autopri_report$both_engines_hold_branch_observed) {
  cat("This platform did not trigger every adaptive hold branch; report partial coverage.\n")
}
