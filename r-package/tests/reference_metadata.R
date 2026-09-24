# Pure metadata checks: this file never invokes Amelia or Python fitting.
source_directory <- Sys.getenv("AMELIATORCH_R_SOURCE", unset = "")
if (nzchar(source_directory)) {
  source(file.path(source_directory, "R", "compatibility.R"))
  backend_metadata <- .reference_backend_metadata
} else {
  backend_metadata <- getFromNamespace(".reference_backend_metadata", "ameliatorch")
}

result <- structure(list(m = 3L), class = "amelia")
fresh <- backend_metadata(matrix(0, 2, 2), result, "1.8.3")
stopifnot(identical(fresh$engine, "reference"), identical(fresh$device, "cpu"),
          identical(fresh$gpu_used, FALSE), identical(fresh$torch_used, FALSE),
          identical(fresh$current_call_torch_used, FALSE),
          fresh$historical_m == 0, fresh$new_m == 3)

old <- structure(list(m = 2L), class = "amelia")
unknown <- backend_metadata(old, result, "1.8.3")
stopifnot(identical(unknown$engine, "appended"),
          identical(unknown$old_backend$engine, "unknown"), is.na(unknown$gpu_used),
          is.na(unknown$torch_used),
          unknown$historical_m == 2, unknown$new_m == 1, unknown$total_m == 3,
          identical(unknown$current_call_engine, "reference"),
          identical(unknown$current_call_device, "cpu"),
          identical(unknown$current_call_gpu_used, FALSE))

prior_gpu <- list(engine = "R-Amelia-pipeline-with-PyTorch-EM", device = "mps")
attr(old, "amelia_torch_backend") <- prior_gpu
mixed <- backend_metadata(old, result, "1.8.3")
stopifnot(identical(mixed$old_backend, prior_gpu), identical(mixed$gpu_used, TRUE),
          !identical(mixed$device, "cpu"), identical(mixed$current_call_gpu_used, FALSE),
          is.na(mixed$torch_used), identical(mixed$current_call_torch_used, FALSE))
prior_gpu$torch_used <- TRUE
attr(old, "amelia_torch_backend") <- prior_gpu
known_torch <- backend_metadata(old, result, "1.8.3")
stopifnot(identical(known_torch$torch_used, TRUE),
          identical(known_torch$current_call_torch_used, FALSE))

attr(old, "amelia_torch_backend") <- NULL
legacy <- list(engine = "reference", device = "cpu", gpu_used = FALSE, torch_used = FALSE)
attr(old, "ameliatorch_backend") <- legacy
compatible <- backend_metadata(old, result, "1.8.3")
stopifnot(identical(compatible$old_backend, legacy), identical(compatible$gpu_used, FALSE),
          identical(compatible$torch_used, FALSE), identical(compatible$engine, "appended"))
cat("Reference provenance metadata checks passed; no fitting was invoked.\n")
