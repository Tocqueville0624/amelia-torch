source_directory <- Sys.getenv("AMELIATORCH_R_SOURCE", unset = "")
if (nzchar(source_directory)) {
  # Optional local source validation; installed-package checks are the default.
  source(file.path(source_directory, "R", "environment.R"))
  source(file.path(source_directory, "R", "amelia.R"))
} else {
  library(ameliatorch)
}

expect_error <- function(expression, pattern) {
  caught <- tryCatch({ force(expression); NULL }, error = identity)
  stopifnot(inherits(caught, "error"), grepl(pattern, conditionMessage(caught), fixed = TRUE))
}

# Loading the package alone must not initialize or download Python.
stopifnot(!reticulate::py_available(initialize = FALSE))
configured_python <- Sys.getenv("RETICULATE_PYTHON", unset = "")
Sys.unsetenv("RETICULATE_PYTHON")
expect_error(check_environment(), "Select Python first")
expect_error(use_amelia_python(), "exactly one")
expect_error(check_environment("mps", "float64"), "MPS does not support float64")
expect_error(amelia_torch(data.frame(category = factor(c("a", "b")))), "plain numeric")
expect_error(amelia_torch(matrix(1:12, 6), boot.type = "none", boot_type = "none"),
             "more than once")
expect_error(amelia_torch(matrix(1:12, 6), max.resample = 10, max_resample = 10),
             "more than once")
for (bad_m in list(0, -1L, 1.5, Inf, NA_real_, TRUE, "2")) {
  expect_error(amelia_torch(matrix(1:12, 6), m = bad_m), "positive integer")
}

if (nzchar(configured_python)) {
  use_amelia_python(python = file.path(dirname(configured_python), ".",
                                      basename(configured_python)))
  stopifnot(!reticulate::py_available(initialize = FALSE))
  report <- check_environment("cpu", "float64")
  stopifnot(identical(report$device, "cpu"), identical(report$dtype, "float64"))
  # Reticulate may clean ./ in a path; the second call must still match the venv.
  report_again <- check_environment("cpu", "float64")
  stopifnot(identical(report_again$device, "cpu"))

  set.seed(29)
  x <- data.frame(a = rnorm(240), b = rnorm(240), c = rnorm(240))
  rownames(x) <- paste0("row_", seq_len(nrow(x)))
  x$b <- 0.5 * x$a + x$b
  x$c[seq(5, 235, 10)] <- NA_real_
  observed <- !is.na(x)
  # R numeric (double) counts must be converted to Python integers.
  completed <- amelia_torch(x, m = 2, seed = 29, boot.type = "none")
  stopifnot(inherits(completed, "ameliatorch_result"), length(completed$imputations) == 2L)
  stopifnot(is.list(completed$diagnostics), isTRUE(completed$diagnostics$converged),
            identical(completed$diagnostics$device, "cpu"),
            identical(completed$diagnostics$dtype, "float64"),
            identical(dim(completed$theta), c(4L, 4L, 2L)),
            identical(dim(completed$mu), c(3L, 2L)),
            identical(dim(completed$covMatrices), c(3L, 3L, 2L)))
  for (draw in completed$imputations) {
    stopifnot(is.data.frame(draw), identical(dimnames(draw), dimnames(x)),
              all(is.finite(as.matrix(draw))),
              all(as.matrix(draw)[observed] == as.matrix(x)[observed]))
  }
  matrix_x <- as.matrix(x)
  matrix_completed <- amelia_torch(matrix_x, m = 1L, seed = 29, boot_type = "none")
  stopifnot(is.matrix(matrix_completed$imputations[[1L]]),
            identical(dimnames(matrix_completed$imputations[[1L]]), dimnames(matrix_x)))
  stopifnot(identical(as.matrix(completed$imputations[[1L]]),
                     matrix_completed$imputations[[1L]]))
  all_missing_x <- rbind(matrix_x, retained_missing_row = c(NA_real_, NaN, NA_real_))
  retained <- amelia_torch(all_missing_x, m = 1, seed = 29, boot_type = "none")
  retained_draw <- retained$imputations[[1L]]
  stopifnot(all(is.finite(retained_draw[seq_len(nrow(matrix_x)), ])),
            identical(unname(retained_draw[nrow(retained_draw), ]), c(NA_real_, NaN, NA_real_)),
            retained$diagnostics$wholly_missing_rows_retained == 1L)
  float32 <- amelia_torch(x, m = 1, dtype = "float32", seed = 29, boot_type = "none")
  stopifnot(all(as.matrix(float32$imputations[[1L]])[observed] == as.matrix(x)[observed]))
  large_seed <- 2^40 + 7
  bootstrap_a <- amelia_torch(x, m = 2, seed = large_seed)
  bootstrap_b <- amelia_torch(x, m = 2, seed = large_seed)
  stopifnot(identical(bootstrap_a$imputations, bootstrap_b$imputations),
            !identical(bootstrap_a$imputations[[1L]], bootstrap_a$imputations[[2L]]),
            bootstrap_a$diagnostics$seed == large_seed)
  expect_error(amelia_torch(x, unknown_option = TRUE), "unknown_option")
  expect_error(amelia_torch(x, max.resample = 10), "max_resample")
  expect_error(amelia_torch(x, 1, NULL), "device must be")
  expect_error(amelia_torch(transform(x, c = NA_real_)), "at least two observed")
  cat("R -> Python CPU imputation and interface contract checks passed.\n")
} else {
  cat("Python bridge checks skipped: explicitly set RETICULATE_PYTHON to enable them.\n")
}
