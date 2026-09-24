# Source-test or installed-package test of the unchanged R pipeline / torch EM.
source_root <- Sys.getenv("AMELIATORCH_R_SOURCE", unset = "")
if (nzchar(source_root)) {
  source(file.path(source_root, "R", "environment.R"))
  source(file.path(source_root, "R", "torch_compat.R"))
} else library(ameliatorch)
stopifnot(requireNamespace("Amelia", quietly = TRUE))
use_amelia_python(python = Sys.getenv("RETICULATE_PYTHON"))
set.seed(97)
x <- data.frame(id = seq_len(180), a = rnorm(180), b = rnorm(180),
                positive = exp(rnorm(180)), fraction = runif(180, .1, .9),
                category = factor(sample(c("red", "green", "blue"), 180, TRUE)),
                ordered = ordered(sample(1:4, 180, TRUE)),
                flag = sample(c(TRUE, FALSE), 180, TRUE))
x$b <- x$b + x$a * .4
for (column in 2:ncol(x)) x[seq(column, 180, 11), column] <- NA
compare <- function(data, arguments) {
  common <- c(list(x = data, m = 2, p2s = 0, tolerance = 1e-6), arguments)
  set.seed(871)
  expected <- do.call(Amelia::amelia, common)
  set.seed(871)
  actual <- do.call(amelia_torch_compat, c(common, list(device = "cpu", dtype = "float64")))
  stopifnot(expected$code == 1, actual$code == expected$code,
            identical(class(expected), class(actual)),
            isTRUE(all.equal(actual$theta, expected$theta, tolerance = 1e-7)),
            isTRUE(all.equal(actual$imputations, expected$imputations, tolerance = 1e-6)),
            identical(actual$missMatrix, expected$missMatrix),
            identical(actual$arguments, expected$arguments),
            isTRUE(attr(actual, "amelia_torch_backend")$converged))
  invisible(actual)
}
plain <- x[, c("id", "a", "b", "positive", "fraction")]
compare(plain, list(idvars = "id", logs = "positive", lgstc = "fraction"))
compare(x, list(idvars = "id", noms = "category", ords = "ordered", logs = "positive"))
priors <- rbind(c(2, 2, 0, 1), c(3, 3, 0, 1))
compare(plain, list(idvars = "id", priors = priors,
                   bounds = matrix(c(2, -4, 4), nrow = 1), max.resample = 20))
cat("Basic R original-pipeline / PyTorch CPU EM comparisons passed.\n")

# The same source pipeline covers square-root/logit transforms, overimputation,
# global/cell confidence priors, and panel structure without porting them here.
compare(plain, list(idvars = "id", sqrts = "positive", lgstc = "fraction",
                   overimp = matrix(c(3, 2), nrow = 1)))
confidence_priors <- rbind(c(0, 2, -1, 1, .95), c(2, 2, -.1, .1, .9))
compare(plain, list(idvars = "id", priors = confidence_priors))
set.seed(831)
panel <- data.frame(id = seq_len(240), unit = rep(letters[1:8], each = 30),
                    time = rep(seq_len(30), 8), y = rnorm(240),
                    x = rnorm(240), z = exp(rnorm(240)))
panel$y <- panel$y + .2 * panel$x + panel$time / 30
panel$y[seq(5, 240, 13)] <- NA
panel$x[seq(7, 240, 17)] <- NA
panel$z[seq(3, 240, 19)] <- NA
compare(panel, list(idvars = "id", cs = "unit", ts = "time", polytime = 2,
                    intercs = TRUE, lags = "y", leads = "x", logs = "z", empri = 5))
compare(panel, list(idvars = "id", cs = "unit", ts = "time", splinetime = 3,
                    intercs = FALSE, logs = "z", empri = 5))
stopifnot(identical(environment(getFromNamespace("amelia.default", "Amelia")),
                    asNamespace("Amelia")))
cat("Additional transformation/prior/panel comparisons passed.\n")
