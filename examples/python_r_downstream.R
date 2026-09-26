# Companion for python_r_downstream.py. Uses official methods on an actual
# Amelia-class object; none of these downstream steps is a Python/GPU rewrite.
args <- commandArgs(trailingOnly = TRUE)
stopifnot(length(args) == 1L,
          requireNamespace("Amelia", quietly = TRUE),
          as.character(utils::packageVersion("Amelia")) == "1.8.3")
directory <- args[[1L]]
fit <- readRDS(file.path(directory, "python-imputations.rds"))
transformed <- transform(fit, interaction = a * b)
set.seed(814)
extended <- ameliatorch::amelia_compat(transformed, m = 1, p2s = 0)
stopifnot(extended$m == 3L,
          identical(extended$imputations[[1L]], transformed$imputations[[1L]]))
saveRDS(extended, file.path(directory, "r-transformed-extended.rds"))

grDevices::pdf(file.path(directory, "diagnostic.pdf"))
tryCatch(plot(extended, which.vars = 3L, ask = FALSE), finally = grDevices::dev.off())
Amelia::write.amelia(extended, separate = FALSE,
                     file.stem = file.path(directory, "completed-data"),
                     format = "csv", orig.data = FALSE, impvar = "draw_id", row.names = FALSE)
models <- with(extended, stats::lm(y ~ a + b))
if (requireNamespace("broom", quietly = TRUE)) {
  # conf.int=FALSE avoids presenting the known reversed interval endpoints in
  # upstream Amelia 1.8.3 as a recommended inferential output. The pooling call
  # itself remains unchanged, including upstream's signed-tail p-value behavior.
  pooled <- Amelia::mi.combine(models, conf.int = FALSE)
  utils::write.csv(pooled, file.path(directory, "pooled-original-amelia.csv"), row.names = FALSE)
  cat("Wrote unchanged official mi.combine output; see the documented 1.8.3 caveats.\n")
} else {
  cat("Optional broom is missing; skipped mi.combine. Install broom to enable pooling.\n")
}
cat("Official R transform, reference append, PDF diagnostic and CSV export completed.\n")
