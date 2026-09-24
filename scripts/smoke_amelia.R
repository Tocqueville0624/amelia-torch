# This verifies the R reference installation, not a speedup or algorithm parity.
.libPaths(c(file.path(getwd(), ".R-library"), .libPaths()))
set.seed(20260923)
n <- 200L
x <- cbind(x1 = rnorm(n), x2 = rnorm(n), x3 = rnorm(n))
x[, 2] <- 0.6 * x[, 1] + x[, 2]
mask <- matrix(runif(length(x)) < 0.15, nrow = n)
# Amelia leaves wholly missing rows outside its fitted data; test that case separately.
mask[rowSums(mask) == ncol(mask), 1] <- FALSE
incomplete <- x
incomplete[mask] <- NA_real_
fit <- Amelia::amelia(incomplete, m = 2, p2s = 0, parallel = "no")
stopifnot(fit$code == 1, length(fit$imputations) == 2)
for (imp in fit$imputations) {
  stopifnot(!anyNA(imp), all(is.finite(imp)), identical(imp[!mask], incomplete[!mask]))
}
dir.create("results/local", recursive = TRUE, showWarnings = FALSE)
report <- list(kind = "R_reference_smoke_only", R = R.version.string,
               Amelia = as.character(packageVersion("Amelia")), code = fit$code,
               n = n, p = ncol(x), m = 2L, observed_values_preserved = TRUE)
jsonlite::write_json(report, "results/local/r_reference.json", auto_unbox = TRUE, pretty = TRUE)
writeLines(capture.output(sessionInfo()), "results/local/r_session.txt")
cat("Amelia reference smoke passed: 2 complete datasets; observed values preserved.\n")
