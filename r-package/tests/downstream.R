# Small installed-package compatibility checks, never a timing benchmark.
# Official downstream diagnostics continue to execute the upstream CPU code.
source_directory <- Sys.getenv("AMELIATORCH_R_SOURCE", unset = "")
if (nzchar(source_directory)) {
  for (name in c("environment.R", "compatibility.R", "torch_compat.R")) {
    source(file.path(source_directory, "R", name))
  }
  make_context <- .torch_em_context
} else {
  library(ameliatorch)
  make_context <- getFromNamespace(".torch_em_context", "ameliatorch")
}
stopifnot(requireNamespace("Amelia", quietly = TRUE),
          as.character(utils::packageVersion("Amelia")) == "1.8.3")
use_amelia_python(python = Sys.getenv("RETICULATE_PYTHON"))
equal_numeric <- function(actual, expected, tolerance = 1e-6) {
  difference <- all.equal(actual, expected, tolerance = tolerance)
  if (!isTRUE(difference)) stop(paste(difference, collapse = "; "), call. = FALSE)
}
equal_fit <- function(actual, expected) {
  stopifnot(actual$code == 1, expected$code == 1,
            identical(class(actual), class(expected)),
            identical(actual$arguments, expected$arguments),
            identical(actual$missMatrix, expected$missMatrix))
  equal_numeric(actual$theta, expected$theta, 1e-7)
  equal_numeric(actual$imputations, expected$imputations)
}
fit_pair <- function(data, ...) {
  options <- c(list(x = data, m = 2, p2s = 0, tolerance = 1e-6), list(...))
  set.seed(571)
  original <- do.call(Amelia::amelia, options)
  original_rng <- .Random.seed
  original_followup <- stats::runif(6)
  original_followup_normal <- stats::rnorm(6)
  set.seed(571)
  hybrid <- do.call(amelia_torch_compat, options)
  equal_fit(hybrid, original)
  stopifnot(identical(.Random.seed, original_rng))
  stopifnot(identical(stats::runif(6), original_followup))
  stopifnot(identical(stats::rnorm(6), original_followup_normal))
  list(original = original, hybrid = hybrid)
}
with_pdf <- function(operation) {
  destination <- tempfile(fileext = ".pdf")
  on.exit(unlink(destination), add = TRUE)
  grDevices::pdf(destination)
  device <- grDevices::dev.cur()
  on.exit(if (device %in% grDevices::dev.list()) grDevices::dev.off(device), add = TRUE)
  value <- operation()
  grDevices::dev.off(device)
  stopifnot(file.info(destination)$size > 1000,
            identical(readChar(destination, 4L, useBytes = TRUE), "%PDF"))
  value
}

set.seed(37)
plain <- data.frame(id = 1:90, a = rnorm(90), b = rnorm(90), y = rnorm(90))
plain$y <- plain$y + .4 * plain$a - .3 * plain$b
plain$a[seq(3, 90, 11)] <- NA_real_
plain$y[seq(5, 90, 9)] <- NA_real_
fits <- fit_pair(plain, idvars = "id")
stopifnot(identical(capture.output(print(fits$hybrid)), capture.output(print(fits$original))),
          identical(capture.output(summary(fits$hybrid)), capture.output(summary(fits$original))))
for (fit in fits) {
  with_pdf(function() Amelia::compare.density(fit, var = "y"))
  with_pdf(function() Amelia::missmap(fit))
}
set.seed(182)
original_over <- with_pdf(function() {
  Amelia::overimpute(fits$original, var = "y", draws = 10, subset = id <= 18)
})
set.seed(182)
hybrid_over <- with_pdf(function() {
  Amelia::overimpute(fits$hybrid, var = "y", draws = 10, subset = id <= 18)
})
equal_numeric(hybrid_over, original_over)
stopifnot(nrow(hybrid_over$overimps) > 0, all(is.finite(hybrid_over$overimps)))

# disperse fits a few additional chains in original Amelia, not in PyTorch.
set.seed(219)
original_disperse <- with_pdf(function() Amelia::disperse(fits$original, m = 2, dims = 1))
set.seed(219)
hybrid_disperse <- with_pdf(function() Amelia::disperse(fits$hybrid, m = 2, dims = 1))
equal_numeric(hybrid_disperse, original_disperse)
stopifnot(length(hybrid_disperse$iters) == 2L)

set.seed(59)
panel <- data.frame(unit = rep(letters[1:3], each = 30), time = rep(1:30, 3),
                    a = rnorm(90), y = rnorm(90))
panel$y <- panel$y + .3 * panel$a + .02 * panel$time
panel$y[seq(4, 90, 8)] <- NA_real_
panel_fits <- fit_pair(panel, cs = "unit", ts = "time", polytime = 1)
set.seed(310)
original_ts <- with_pdf(function() Amelia::tscsPlot(panel_fits$original, "y", cs = "a", draws = 10))
set.seed(310)
hybrid_ts <- with_pdf(function() Amelia::tscsPlot(panel_fits$hybrid, "y", cs = "a", draws = 10))
equal_numeric(hybrid_ts, original_ts)
stopifnot(all(is.finite(hybrid_ts)), ncol(hybrid_ts) == 10L)

pool <- function(fit) {
  models <- lapply(fit$imputations, function(data) stats::lm(y ~ a + b, data = data))
  estimates <- do.call(rbind, lapply(models, stats::coef))
  standard_errors <- do.call(rbind, lapply(models, function(model) sqrt(diag(stats::vcov(model)))))
  pooled <- Amelia::mi.meld(estimates, standard_errors)
  equal_numeric(as.numeric(pooled$q.mi), as.numeric(colMeans(estimates)), 1e-12)
  manual_se <- sqrt(colMeans(standard_errors^2) + (1 + 1 / nrow(estimates)) *
                      apply(estimates, 2, stats::var))
  equal_numeric(as.numeric(pooled$se.mi), as.numeric(manual_se), 1e-12)
  pooled
}
equal_numeric(pool(fits$hybrid), pool(fits$original))

export_directory <- tempfile(pattern = "amelia-export-")
dir.create(export_directory)
tryCatch({
  Amelia::write.amelia(fits$hybrid, file.stem = file.path(export_directory, "draw-"),
                       format = "csv", row.names = FALSE)
  for (i in seq_len(fits$hybrid$m)) {
    exported <- utils::read.csv(file.path(export_directory, paste0("draw-", i, ".csv")))
    equal_numeric(exported, fits$hybrid$imputations[[i]], 1e-12)
  }
  Amelia::write.amelia(fits$hybrid, separate = FALSE,
                       file.stem = file.path(export_directory, "combined"),
                       format = "csv", row.names = FALSE)
  combined <- utils::read.csv(file.path(export_directory, "combined.csv"))
  stopifnot(nrow(combined) == nrow(plain) * 3L,
            identical(sort(unique(combined$imp)), 0:2))
}, finally = unlink(export_directory, recursive = TRUE))

# Saved model arguments and additional imputations remain upstream semantics.
arglist_fits <- fit_pair(plain, arglist = fits$original$arguments)
set.seed(382)
original_extended <- Amelia::amelia(fits$original, m = 1, p2s = 0)
set.seed(382)
hybrid_extended <- amelia_torch_compat(fits$hybrid, m = 1, p2s = 0)
equal_fit(hybrid_extended, original_extended)
stopifnot(hybrid_extended$m == 3,
          all(vapply(1:2, function(i) {
            identical(hybrid_extended$imputations[[i]], fits$hybrid$imputations[[i]])
          }, logical(1))),
          attr(hybrid_extended, "amelia_torch_backend")$historical_m == 2)

# moPrep stores substitute(x), not the data itself. Resolve it in the actual
# caller's local environment for both wrappers; global-only tests miss this.
local({
  scoped_data <- plain
  settings <- Amelia::moPrep(scoped_data, b ~ b, error.sd = .1)
  set.seed(415)
  original <- Amelia::amelia(settings, m = 1, p2s = 0, idvars = "id")
  set.seed(415)
  reference <- amelia_compat(settings, m = 1, p2s = 0, idvars = "id")
  set.seed(415)
  hybrid <- amelia_torch_compat(settings, m = 1, p2s = 0, idvars = "id")
  equal_fit(hybrid, original)
  attr(reference, "amelia_torch_backend") <- NULL
  equal_numeric(reference, original, 0)
})

# Internal allthetas adapter must preserve the original vectorized upper
# triangles and initial-theta column used by downstream convergence diagnostics.
stacked <- getFromNamespace("amstack", "Amelia")(as.matrix(plain[, -1]), colorder = FALSE)$x
original_history <- getFromNamespace("emarch", "Amelia")(
  stacked, p2s = 0, tolerance = 1e-7, allthetas = TRUE
)
context <- make_context("cpu", "float64")
hybrid_history <- context$environment$emarch(stacked, p2s = 0, tolerance = 1e-7,
                                            allthetas = TRUE)
equal_numeric(hybrid_history$thetanew, original_history$thetanew, 1e-7)
equal_numeric(hybrid_history$iter.hist, original_history$iter.hist, 0)
stopifnot(nrow(hybrid_history$thetanew) == 9L,
          ncol(hybrid_history$thetanew) == nrow(hybrid_history$iter.hist) + 1L)
# Check multiple nonbootstrap replicates separately: R/C random-state boundaries
# can differ from ordinary bootstrap even if the first imputation is identical.
saved_rng_kind <- RNGkind()
tryCatch({
  RNGkind(normal.kind = "Inversion")
  nonbootstrap_fits <- fit_pair(plain, idvars = "id", boot.type = "none")
  # This normal generator keeps a cached spare outside .Random.seed. Our data
  # require an odd number of normal draws per imputation, exercising that cache.
  RNGkind(normal.kind = "Box-Muller")
  box_muller_fits <- fit_pair(plain, idvars = "id", boot.type = "none")
}, finally = do.call(RNGkind, as.list(saved_rng_kind)))
cat("Downstream CPU summaries, PDF diagnostics, pooling, CSV export, saved arguments, extension, molist and allthetas checks passed.\n")
