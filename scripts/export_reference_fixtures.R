# Export small, redistributable synthetic fixtures from unmodified Amelia 1.8.3.
# Run from the repository root: Rscript scripts/export_reference_fixtures.R
# This is an oracle harness, not a replacement implementation of Amelia.
.libPaths(c(file.path(getwd(), ".R-library"), .libPaths()))
stopifnot(as.character(packageVersion("Amelia")) == "1.8.3")
stopifnot(requireNamespace("jsonlite", quietly = TRUE))
output_dir <- "tests/fixtures/reference_amelia"
dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)
ns <- asNamespace("Amelia")
reference <- function(name) get(name, envir = ns, inherits = FALSE)
# emcore uses an Armadillo view into its theta SEXP and mutates that allocation.
# R assignment alone does not deep-copy it; isolate every oracle call explicitly.
deep_copy <- function(value) unserialize(serialize(value, NULL))
write_fixture <- function(value, filename) {
  jsonlite::write_json(value, file.path(output_dir, filename),
                      auto_unbox = TRUE, pretty = TRUE, digits = NA,
                      na = "null", null = "null", matrix = "rowmajor")
}

# Synthetic public test data: the full numeric input is exported below, so parity
# does not depend on reproducing this R random-number stream in another language.
set.seed(21831)
raw <- matrix(rnorm(48 * 4), nrow = 48, ncol = 4)
raw[, 2] <- 0.4 * raw[, 1] + raw[, 2]
raw[, 3] <- -0.25 * raw[, 1] + 0.5 * raw[, 2] + raw[, 3]
raw[, 4] <- 0.35 * raw[, 3] + raw[, 4]
raw[25:30, 1] <- NA_real_
raw[31:36, c(2, 3)] <- NA_real_
raw[37:42, c(1, 4)] <- NA_real_
raw[43:48, c(2, 3, 4)] <- NA_real_
scaled <- reference("scalecenter")(raw)
stacked <- reference("amstack")(scaled$x, colorder = FALSE)
x <- stacked$x
p <- ncol(x)
theta0 <- diag(p + 1)
theta0[1, 1] <- -1
theta0[1, -1] <- theta0[-1, 1] <- c(0.1, -0.15, 0.05, 0.12)
theta0[-1, -1] <- matrix(c(1.2, 0.2, -0.1, 0.0,
                            0.2, 0.9, 0.15, 0.05,
                           -0.1, 0.15, 1.1, 0.3,
                            0.0, 0.05, 0.3, 1.3), 4, 4)

# Recover Rcpp::rnorm input by replaying the R stream, then export the normal
# values explicitly. The Python implementation must consume these values, NOT
# assume that torch.manual_seed(seed) and set.seed(seed) produce equal streams.
# Draws are allocated by contiguous missingness group, n_group * p values,
# reshaped in R/Armadillo column-major order; complete groups consume no draws.
capture_draws <- function(x, theta, priors, seed) {
  set.seed(seed)
  expected <- reference("amelia_impute")(deep_copy(x), deep_copy(theta),
                                         priors = deep_copy(priors))
  set.seed(seed)
  draws <- matrix(0, nrow(x), ncol(x))
  predicted <- x
  conditional_mean <- x
  row_covariances <- vector("list", nrow(x))
  patterns <- reference("indxs")(x)
  for (g in seq_len(nrow(patterns$m))) {
    rows <- seq.int(patterns$ivector[g], patterns$ivector[g + 1] - 1)
    missing <- which(patterns$m[g, ])
    observed <- which(!patterns$m[g, ])
    if (!length(missing)) {
      for (r in rows) row_covariances[[r]] <- matrix(0, p, p)
      next
    }
    mu <- theta[-1, 1]
    sigma <- theta[-1, -1]
    cond_cov <- sigma[missing, missing, drop = FALSE]
    cond_mean <- matrix(mu[missing], nrow = length(rows),
                        ncol = length(missing), byrow = TRUE)
    if (length(observed)) {
      beta <- solve(sigma[observed, observed, drop = FALSE],
                    sigma[observed, missing, drop = FALSE])
      centered <- sweep(x[rows, observed, drop = FALSE], 2, mu[observed])
      cond_mean <- cond_mean + centered %*% beta
      cond_cov <- cond_cov - sigma[missing, observed, drop = FALSE] %*% beta
    }
    z <- matrix(rnorm(length(rows) * p), nrow = length(rows), ncol = p)
    draws[rows, ] <- z
    for (j in seq_along(rows)) {
      r <- rows[j]
      v <- cond_cov
      a <- cond_mean[j, ]
      if (!is.null(priors)) {
        row_priors <- priors[priors[, 1] == r, , drop = FALSE]
        if (nrow(row_priors)) {
          precision <- numeric(length(missing))
          weighted_mean <- numeric(length(missing))
          pos <- match(row_priors[, 2], missing)
          precision[pos] <- 1 / row_priors[, 4]
          weighted_mean[pos] <- row_priors[, 3] / row_priors[, 4]
          inv_v <- solve(v)
          v <- solve(inv_v + diag(precision, length(missing)))
          a <- drop(v %*% (inv_v %*% a + weighted_mean))
        }
      }
      conditional_mean[r, missing] <- a
      whole_cov <- matrix(0, p, p)
      whole_cov[missing, missing] <- v
      row_covariances[[r]] <- whole_cov
      predicted[r, missing] <- a + drop(z[j, missing, drop = FALSE] %*% chol(v))
    }
  }
  difference <- max(abs(predicted - expected))
  stopifnot(difference < 1e-11)
  list(standard_normals = draws, expected_imputation = expected,
       conditional_means = conditional_mean,
       conditional_covariances = row_covariances,
       replay_max_absolute_error = difference)
}

cells <- which(is.na(x), arr.ind = TRUE)
prior_rows <- unique(cells[, 1])
selected <- cells[cells[, 1] %in% prior_rows[c(2, 8)], , drop = FALSE]
priors <- cbind(selected, mean = seq(-0.25, 0.25, length.out = nrow(selected)),
                variance = rep(0.35, nrow(selected)))
cases <- list(
  no_prior = list(empri = 0, priors = NULL),
  empirical_prior = list(empri = 3.75, priors = NULL),
  cell_prior = list(empri = 0, priors = priors)
)
no_complete <- x
complete_rows <- which(complete.cases(no_complete))
no_complete[cbind(complete_rows, (seq_along(complete_rows) - 1L) %% p + 1L)] <- NA
no_complete <- reference("amstack")(no_complete, colorder = FALSE)$x
cases$no_complete_rows <- list(empri = 0, priors = NULL, x = no_complete,
                               initial_theta = reference("startval")(no_complete, 0))
cases$minimum_iterations <- list(empri = 0, priors = NULL,
                                 tolerance = 0.01, emburn = c(35, 80))
cases$maximum_iterations <- list(empri = 0, priors = NULL, emburn = c(0, 2))
provenance <- list(
  package = "Amelia", version = "1.8.3",
  source_url = "https://cran.r-project.org/src/contrib/Amelia_1.8.3.tar.gz",
  source_sha256 = "7699455ca3e9dabd60ad0ec69185ece3f24a597ef8da18033ea0b7a32356967f",
  package_license = "GPL (>= 2)", R_version = as.character(getRversion()),
  input_origin = "Synthetic numeric data generated by this repository; no private data.",
  coordinate_system = "Already standardized, row-stacked numeric EM coordinates",
  indexing = "R one-based rows and columns for priors and permutations",
  internal_prior_columns = c("row", "column", "mean", "variance"),
  random_contract = "Consume exported standard_normals; seeds are R-only provenance."
)
for (case_name in names(cases)) {
  case <- cases[[case_name]]
  case_x <- if (is.null(case$x)) x else case$x
  case_theta <- if (is.null(case$initial_theta)) theta0 else case$initial_theta
  case_tolerance <- if (is.null(case$tolerance)) 1e-9 else case$tolerance
  case_emburn <- if (is.null(case$emburn)) c(0, 1000) else case$emburn
  one <- reference("emarch")(deep_copy(case_x), p2s = 0, thetaold = deep_copy(case_theta),
                              priors = deep_copy(case$priors), empri = case$empri,
                              autopri = 0, tolerance = case_tolerance, emburn = c(1, 1))
  fit <- reference("emarch")(deep_copy(case_x), p2s = 0, thetaold = deep_copy(case_theta),
                              priors = deep_copy(case$priors), empri = case$empri,
                              autopri = 0, tolerance = case_tolerance, emburn = case_emburn)
  converged <- tail(fit$iter.hist[, 1], 1) == 0
  stopifnot(converged || case_name == "maximum_iterations")
  draw <- capture_draws(case_x, fit$thetanew, case$priors, seed = 4201L)
  result <- c(list(schema_version = 1L, case = case_name, provenance = provenance,
                  x = case_x, initial_theta = case_theta,
                  priors = case$priors, empri = case$empri,
                  effective_integer_empri = as.integer(case$empri),
                  autopri = 0, tolerance = case_tolerance, emburn = case_emburn,
                  expected_one_step_theta = one$thetanew,
                  expected_one_step_history = one$iter.hist,
                  expected_theta = fit$thetanew,
                  expected_history = fit$iter.hist,
                  expected_iterations = nrow(fit$iter.hist),
                  expected_converged = converged), draw)
  write_fixture(result, paste0(case_name, ".json"))
  cat(case_name, ":", nrow(fit$iter.hist), "iterations; explicit-noise replay verified\n")
}

# The no-missing-data internal shortcut has sample, not maximum-likelihood,
# covariance, and does not apply the empirical prior or the supplied theta.
complete <- x[complete.cases(x), , drop = FALSE]
complete_fit <- reference("emarch")(deep_copy(complete), p2s = 0, thetaold = deep_copy(theta0),
                                     empri = 99, autopri = 0)
write_fixture(list(schema_version = 1L, provenance = provenance, x = complete,
                   initial_theta = theta0, empri = 99,
                   expected_theta = complete_fit$thetanew,
                   expected_history = NULL,
                   expected_iterations = 0L), "complete_internal.json")

write_fixture(list(schema_version = 1L, provenance = provenance, raw_x = raw,
                   mean = scaled$mu, sd = scaled$sd, standardized_x = scaled$x,
                   stacked_x = x, n_order = stacked$n.order,
                   p_order = stacked$p.order,
                   expected_startvals_0 = reference("startval")(x, 0),
                   expected_startvals_1 = reference("startval")(x, 1),
                   expected_startvals_with_priors = reference("startval")(x, 0, priors)),
              "preprocessing.json")

# Exercise the real public preprocessing-to-EM path, with asymmetric missingness
# counts so column reordering is nontrivial, plus an officially retained blank
# row. Explicit initial theta is already expressed in the prepared coordinates.
# Imputed draws are deliberately excluded: R and Python RNGs are not equivalent.
public_raw <- raw
public_raw[1:3, 1] <- NA_real_
public_raw <- rbind(public_raw, rep(NA_real_, p))
public_initial <- deep_copy(theta0)
public_arguments <- list(m = 1, p2s = 0, boot.type = "none", autopri = 0,
                         empri = 0, tolerance = 1e-8, emburn = c(0, 1000))
public_prepped <- do.call(reference("amelia_prep"),
                          c(list(x = deep_copy(public_raw),
                                 startvals = deep_copy(public_initial)),
                            public_arguments))
stopifnot(is.null(public_prepped$message))
set.seed(4231L)
public_fit <- do.call(Amelia::amelia,
                      c(list(x = deep_copy(public_raw),
                             startvals = deep_copy(public_initial), parallel = "no"),
                        public_arguments))
stopifnot(public_fit$code == 1,
          tail(public_fit$iterHist[[1]][, 1], 1) == 0,
          all(is.na(tail(public_fit$imputations[[1]], 1))))
public_provenance <- provenance
public_provenance$coordinate_system <- "Raw public numeric input; expected theta is in Amelia's standardized, reordered model coordinates"
write_fixture(list(schema_version = 1L, case = "public_continuous",
                   provenance = public_provenance, raw_x = public_raw,
                   initial_theta = public_initial, m = 1L, boot_type = "none",
                   tolerance = 1e-8, empri = 0, autopri = 0, emburn = c(0, 1000),
                   expected_code = public_fit$code,
                   expected_theta = public_fit$theta[, , 1],
                   expected_history = public_fit$iterHist[[1]],
                   expected_iterations = nrow(public_fit$iterHist[[1]]),
                   expected_scale_mean = public_prepped$scaled.mu,
                   expected_scale_sd = public_prepped$scaled.sd,
                   expected_n_order = public_prepped$n.order,
                   expected_p_order = public_prepped$p.order,
                   expected_blank_rows = public_prepped$blanks,
                   expected_prepared_x = public_prepped$x),
              "public_continuous.json")

# Confirm version-specific edge behavior dynamically, including the log inverse.
# These are compatibility observations, not endorsements of upstream quirks.
log_x <- matrix(c(-2, 0, 2, 4, 7, 10), ncol = 1)
log_forward <- reference("amtransform")(log_x, logs = 1, sqrts = NULL, lgstc = NULL)
log_roundtrip <- reference("untransform")(log_forward$x, logs = 1,
                                         xmin = log_forward$xmin,
                                         sqrts = NULL, lgstc = NULL)
stopifnot(max(abs(log_roundtrip - log_x - 1)) < 1e-12)
blank_x <- rbind(raw, rep(NA_real_, p))
blank_fit <- Amelia::amelia(blank_x, m = 1, p2s = 0, boot.type = "none",
                            autopri = 0, parallel = "no")
stopifnot(blank_fit$code == 1, all(is.na(tail(blank_fit$imputations[[1]], 1))))
complete_code <- Amelia::amelia(raw[complete.cases(raw), ], m = 1, p2s = 0)$code
missing_col <- raw
missing_col[, 1] <- NA_real_
missing_col_code <- Amelia::amelia(missing_col, m = 1, p2s = 0)$code
one_observed <- missing_col
one_observed[1, 1] <- 0
one_observed_code <- Amelia::amelia(one_observed, m = 1, p2s = 0)$code
constant_col <- raw
constant_col[, 1] <- 3
constant_code <- Amelia::amelia(constant_col, m = 1, p2s = 0)$code
stopifnot(complete_code == 39, missing_col_code == 4,
          one_observed_code == 4, constant_code == 43)
write_fixture(list(schema_version = 1L, provenance = provenance,
                   log_input = log_x, log_forward = log_forward$x,
                   log_xmin = log_forward$xmin, log_roundtrip = log_roundtrip,
                   log_roundtrip_difference = log_roundtrip - log_x,
                   all_missing_row_fit_code = blank_fit$code,
                   all_missing_row_output = tail(blank_fit$imputations[[1]], 1),
                   public_no_missing_input_code = complete_code,
                   public_all_missing_column_code = missing_col_code,
                   public_one_observed_value_column_code = one_observed_code,
                   public_constant_column_code = constant_code),
              "edge_contract.json")

# Numerical-boundary diagnostic: exact collinearity eventually makes the
# eigenvalue sign sensitive to BLAS and roundoff. Keep both reference runs, but
# do NOT use this history as a cross-platform pointwise acceptance criterion.
set.seed(6)
stress_x <- matrix(rnorm(1000), 200, 5)
stress_x[, 5] <- stress_x[, 1] + stress_x[, 2]
stress_x[sample(length(stress_x), 400)] <- NA_real_
stress_x <- reference("amstack")(reference("scalecenter")(stress_x)$x,
                                 colorder = FALSE)$x
stress_theta <- reference("startval")(stress_x, 1)
stress_fits <- lapply(c(0, 0.05), function(a) {
  reference("emarch")(deep_copy(stress_x), p2s = 0,
                       thetaold = deep_copy(stress_theta),
                       tolerance = 1e-15, emburn = c(0, 300), autopri = a)
})
write_fixture(list(schema_version = 1L, provenance = provenance,
                   purpose = "Diagnostic only; eigenvalue sign near zero is platform-sensitive, not a strict parity gate.",
                   x = stress_x, initial_theta = stress_theta,
                   tolerance = 1e-15, emburn = c(0, 300), empri = 0,
                   no_autopri_theta = stress_fits[[1]]$thetanew,
                   no_autopri_history = stress_fits[[1]]$iter.hist,
                   autopri = 0.05,
                   adaptive_theta = stress_fits[[2]]$thetanew,
                   adaptive_history = stress_fits[[2]]$iter.hist),
              "adaptive_stress.json")
cat("Wrote reference fixtures to", output_dir, "\n")
