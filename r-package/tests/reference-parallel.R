# Reference-only parallel routing. No reticulate/Python initialization, no GPU.
library(ameliatorch)
stopifnot(as.character(utils::packageVersion("Amelia")) == "1.8.3")
saved_kind <- RNGkind()
parallel_report <- list(schema_version = 1L, reference_version = "1.8.3",
                        platform_type = .Platform$OS.type, cases = list())
same_fit <- function(actual, expected) {
  attr(actual, "amelia_torch_backend") <- NULL
  stopifnot(isTRUE(all.equal(actual, expected, tolerance = 0)))
}
tryCatch({
  RNGkind("L'Ecuyer-CMRG", "Inversion", "Rejection")
  set.seed(419)
  data <- data.frame(a = rnorm(96), b = rnorm(96), c = rnorm(96))
  data$c <- data$c + .3 * data$a
  data$a[seq(1, 96, 7)] <- NA_real_
  data$b[seq(1, 96, 11)] <- NA_real_
  common <- list(x = data, m = 3, p2s = 0, ncpus = 2, tolerance = 1e-6, autopri = 0)
  cl <- parallel::makePSOCKcluster(2L)
  tryCatch({
    worker_versions <- unlist(parallel::clusterCall(cl, function() {
      as.character(utils::packageVersion("Amelia"))
    }))
    stopifnot(identical(worker_versions, rep("1.8.3", 2)))
    workers_before <- unlist(parallel::clusterCall(cl, Sys.getpid))
    parallel::clusterSetRNGStream(cl, iseed = 420L)
    set.seed(421)
    original <- do.call(Amelia::amelia, c(common, list(parallel = "snow", cl = cl)))
    reference_followup <- parallel::clusterCall(cl, stats::runif, 6)
    # Reuse the exact same caller-owned workers and explicitly restore streams.
    parallel::clusterSetRNGStream(cl, iseed = 420L)
    set.seed(421)
    actual <- do.call(amelia_compat, c(common, list(parallel = "snow", cl = cl)))
    actual_followup <- parallel::clusterCall(cl, stats::runif, 6)
    workers_after <- unlist(parallel::clusterCall(cl, Sys.getpid))
    same_fit(actual, original)
    stopifnot(original$code == 1L, actual$code == 1L,
              identical(workers_before, workers_after),
              identical(reference_followup, actual_followup),
              !attr(actual, "amelia_torch_backend")$torch_used,
              all(unlist(parallel::clusterCall(cl, function() TRUE))))
    parallel_report$cases$supplied_snow_cluster <- list(
      workers = 2L, worker_versions = worker_versions, rng_kind = RNGkind(),
      worker_stream_seed = 420L, parent_seed = 421L, m = actual$m,
      exact_original_result = TRUE, exact_worker_rng_followup = TRUE,
      caller_cluster_reused_and_still_alive = TRUE, passed = TRUE)
  }, finally = parallel::stopCluster(cl))

  if (.Platform$OS.type == "windows") {
    # Preserve official platform behavior; do not pretend Windows has Unix fork.
    parallel_report$cases$multicore <- list(
      executed = FALSE, reason = "Windows has no Unix fork backend; use snow or serial")
    cat("Unix multicore not executed on Windows; snow route was tested.\n")
  } else {
    set.seed(422)
    original <- do.call(Amelia::amelia, c(common, list(parallel = "multicore")))
    set.seed(422)
    actual <- do.call(amelia_compat, c(common, list(parallel = "multicore")))
    same_fit(actual, original)
    stopifnot(original$code == 1L, actual$code == 1L,
              !attr(actual, "amelia_torch_backend")$torch_used)
    parallel_report$cases$multicore <- list(
      executed = TRUE, workers = 2L, seed = 422L, rng_kind = RNGkind(),
      m = actual$m, exact_original_result = TRUE, passed = TRUE)
  }
}, finally = do.call(RNGkind, as.list(saved_kind)))
parallel_report$all_executed_checks_passed <- TRUE
cat("Reference parallel routing checks passed.\n")
