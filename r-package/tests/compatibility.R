# Prepared reference-delegation tests. Running this file performs CPU fits.
# Keep it out of an active timed benchmark session.
source_directory <- Sys.getenv("AMELIATORCH_R_SOURCE", unset = "")
if (nzchar(source_directory)) {
  source(file.path(source_directory, "R", "compatibility.R"))
} else {
  library(ameliatorch)
}

expect_error <- function(expression, pattern) {
  caught <- tryCatch({ force(expression); NULL }, error = identity)
  stopifnot(inherits(caught, "error"), grepl(pattern, conditionMessage(caught), fixed = TRUE))
}

stopifnot(!reticulate::py_available(initialize = FALSE))
expect_error(amelia_compat(NULL, engine = "torch"), "Only engine = 'reference'")

compare_official <- function(x, ..., comparison_seed = 20260923L) {
  before <- serialize(x, NULL)
  arguments <- list(...)
  set.seed(comparison_seed)
  reference <- do.call(Amelia::amelia, c(list(x = unserialize(before)), arguments))
  reference_rng <- .Random.seed
  set.seed(comparison_seed)
  wrapped <- do.call(amelia_compat, c(list(x = unserialize(before)), arguments))
  stopifnot(identical(.Random.seed, reference_rng))
  metadata <- attr(wrapped, "amelia_torch_backend")
  stopifnot(identical(metadata$engine, if (inherits(x, "amelia")) "appended" else "reference"),
            identical(metadata$implementation, "Amelia::amelia"),
            identical(metadata$current_call_device, "cpu"),
            identical(metadata$current_call_gpu_used, FALSE),
            identical(metadata$amelia_version, as.character(utils::packageVersion("Amelia"))),
            identical(class(wrapped), class(reference)),
            identical(names(wrapped), names(reference)),
            identical(serialize(x, NULL), before))
  attr(wrapped, "amelia_torch_backend") <- NULL
  stopifnot(isTRUE(all.equal(wrapped, reference, tolerance = 0, check.attributes = TRUE)))
  stopifnot(!reticulate::py_available(initialize = FALSE))
  reference
}

if (requireNamespace("Amelia", quietly = TRUE)) {
  # Both the implementation and this validation require the declared reference.
  stopifnot(as.character(utils::packageVersion("Amelia")) == "1.8.3")
  set.seed(47)
  plain <- matrix(rnorm(360), nrow = 120, ncol = 3,
                  dimnames = list(paste0("row", 1:120), c("a", "b", "c")))
  plain[seq(3, 113, 10), 2] <- NA_real_
  initial <- compare_official(plain, m = 1, p2s = 0, boot.type = "none")
  stopifnot(inherits(initial, "amelia"), identical(initial$code, 1))
  appended <- compare_official(initial, m = 2, p2s = 0)
  stopifnot(inherits(appended, "amelia"), length(appended$imputations) > length(initial$imputations))

  set.seed(48)
  advanced <- data.frame(
    record_id = paste0("record", 1:120),
    unit = factor(rep(LETTERS[1:4], each = 30)),
    time = rep(1:30, 4),
    positive = exp(rnorm(120, sd = 0.5)),
    measure = rnorm(120) + 0.3 * rep(1:30, 4),
    nominal = factor(sample(c("red", "green", "blue"), 120, replace = TRUE)),
    ordinal = ordered(sample(1:4, 120, replace = TRUE))
  )
  rownames(advanced) <- paste0("observation", 1:120)
  advanced$positive[seq(3, 113, 11)] <- NA_real_
  advanced$measure[seq(5, 109, 13)] <- NA_real_
  advanced$nominal[seq(8, 113, 15)] <- NA
  advanced$ordinal[seq(10, 112, 17)] <- NA
  rich <- compare_official(
    advanced, m = 1, p2s = 0, boot.type = "none", empri = 1,
    idvars = "record_id", logs = "positive", noms = "nominal", ords = "ordinal",
    ts = "time", cs = "unit", polytime = 1, intercs = TRUE,
    # Use two rows: Amelia 1.8.3 drops single-row prior matrix dimensions in
    # validation and impfill; the wrapper deliberately preserves that behavior.
    priors = rbind(c(18, 5, 0, 1), c(31, 5, 0, 1)),
    bounds = matrix(c(5, -8, 15), nrow = 1), max.resample = 10
  )
  stopifnot(inherits(rich, "amelia"), identical(rich$code, 1),
            identical(rich$imputations[[1]]$record_id, advanced$record_id))
  cat("Official Amelia CPU delegation, S3 extension, advanced options and R RNG checks passed.\n")
} else {
  expect_error(amelia_compat(NULL), "requires the R package Amelia")
  cat("Official reference fits skipped: optional R package Amelia is not installed.\n")
}
