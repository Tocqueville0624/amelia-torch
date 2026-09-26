# One persistent R process per G5 route. Not a timing benchmark.
.libPaths(c(file.path(getwd(), ".R-library"), .libPaths()))
Sys.setenv(R_LIBS_USER = paste(.libPaths(), collapse = .Platform$path.sep))
args <- commandArgs(trailingOnly = TRUE)
if (length(args) != 1L) stop("Supply a G5 configuration JSON")
config <- jsonlite::read_json(args[[1]], simplifyVector = FALSE)
stopifnot(as.character(packageVersion("Amelia")) == "1.8.3")
RNGkind("L'Ecuyer-CMRG", "Inversion", "Rejection")
hybrid <- !identical(config$route, "r-reference")
backend <- torch <- NULL
if (hybrid) {
  ameliatorch::use_amelia_python(python = Sys.getenv("RETICULATE_PYTHON"))
  torch <- reticulate::import("torch", convert = FALSE)
  torch$set_num_threads(as.integer(config$threads))
  torch$backends$cuda$matmul$allow_tf32 <- FALSE
  torch$backends$cudnn$allow_tf32 <- FALSE
  backend <- reticulate::import("amelia_torch.backends", convert = FALSE)
  invisible(backend$resolve_backend(config$device, config$dtype))
}
installed_md5 <- function(package) {
  base <- system.file(package = package)
  paths <- list.files(base, pattern = "\\.(so|dll|dylib|rdb|rdx)$|^DESCRIPTION$|^NAMESPACE$",
                     recursive = TRUE, full.names = TRUE)
  value <- as.list(unname(tools::md5sum(paths)))
  names(value) <- substring(paths, nchar(base) + 2L)
  value
}
report <- list(route = config$route, environment = list(
  R = as.character(getRversion()), Amelia = as.character(packageVersion("Amelia")),
  RNGkind = as.list(RNGkind()),
  installed_Amelia_md5 = installed_md5("Amelia"),
  installed_ameliatorch_md5 = if (hybrid) installed_md5("ameliatorch") else NULL,
  ameliatorch = if (hybrid) as.character(packageVersion("ameliatorch")) else NULL,
  torch = if (hybrid) reticulate::py_to_r(reticulate::import("builtins", convert = FALSE)$str(torch$`__version__`)) else NULL,
  requested_python_matches_active = if (hybrid) identical(
    gsub("\\", "/", reticulate::py_config()$python, fixed = TRUE),
    gsub("\\", "/", Sys.getenv("RETICULATE_PYTHON"), fixed = TRUE)) else NULL,
  cuda_tf32_allowed = if (hybrid && config$device == "cuda") reticulate::py_to_r(torch$backends$cuda$matmul$allow_tf32) else NULL
), records = list(), completed = FALSE)
if (hybrid && !isTRUE(report$environment$requested_python_matches_active)) {
  stop("Requested Python interpreter did not bind to the hybrid runtime")
}
write_report <- function() {
  temporary <- paste0(config$output_json, ".tmp")
  jsonlite::write_json(report, temporary, auto_unbox = TRUE, pretty = TRUE,
                      digits = NA, null = "null", na = "null", matrix = "rowmajor")
  if (!file.rename(temporary, config$output_json)) stop("Cannot checkpoint G5 report")
}
run_one <- function(item) {
  warnings <- character()
  fit <- NULL
  record <- list(id = item$id, scenario = item$scenario, replicate = item$replicate,
                 r_imputation_seed = item$r_imputation_seed,
                 input_sha256 = item$input_sha256, input_md5_verified = FALSE,
                 status = "failed", warnings = list(), quality_passed = FALSE)
  tryCatch(withCallingHandlers({
    if (!identical(unname(tools::md5sum(item$input_file)), item$input_md5)) {
      stop("Input digest mismatch")
    }
    record$input_md5_verified <- TRUE
    values <- readBin(item$input_file, "double", n = config$n * 3L, size = 8L, endian = "little")
    stopifnot(length(values) == config$n * 3L)
    x <- matrix(values, ncol = 3L, byrow = TRUE)
    observed <- !is.na(x)
    set.seed(as.integer(item$r_imputation_seed))
    call_args <- list(x = x, m = as.integer(config$m), p2s = 0, parallel = "no",
                      ncpus = 1L, tolerance = 1e-4, autopri = .05, empri = NULL,
                      emburn = c(0, 500), boot.type = "ordinary")
    if (hybrid) {
      call_args$device <- config$device
      call_args$dtype <- config$dtype
    }
    fit <- do.call(if (hybrid) ameliatorch::amelia_torch_compat else Amelia::amelia, call_args)
    record$code <- fit$code
    record$message <- fit$message
    record$iter_histories <- fit$iterHist
    record$backend <- attr(fit, "amelia_torch_backend", exact = TRUE)
    histories <- fit$iterHist
    converged <- if (is.list(histories)) vapply(histories, function(h) {
      # Original complete-bootstrap shortcut returns a scalar NA history.
      if (is.matrix(h) && nrow(h)) isTRUE(tail(h[, 1], 1) == 0)
      else identical(h, NA)
    }, logical(1)) else logical()
    record$imputation_fits_returned <- length(histories)
    record$imputation_fits_converged <- sum(converged)
    record$imputation_fits_nonconverged <- sum(!converged)
    record$em_iterations <- as.list(vapply(histories, function(h) if (is.matrix(h)) nrow(h) else 0L, integer(1)))
    record$empri_final <- if (hybrid) lapply(record$backend$fits, `[[`, "empri_final") else NULL
    record$pseudoinverse_uses <- if (hybrid) sum(vapply(record$backend$fits, `[[`, numeric(1), "pseudoinverse_uses")) else NULL
    record$original_r_internal_diagnostics <- if (!hybrid) "Final empri and pseudoinverse counts not exposed by public Amelia result; raw iterHist and warnings retained." else NULL
    valid_shapes <- is.list(fit$imputations) && length(fit$imputations) == config$m &&
      all(vapply(fit$imputations, function(imp) (is.matrix(imp) || is.data.frame(imp)) && identical(dim(imp), dim(x)), logical(1)))
    record$observed_preserved <- valid_shapes && all(vapply(fit$imputations, function(imp) {
      identical(as.numeric(as.matrix(imp)[observed]), as.numeric(x[observed]))
    }, logical(1)))
    record$all_completed_values_finite <- valid_shapes && all(vapply(fit$imputations, function(imp) all(is.finite(as.matrix(imp))), logical(1)))
    record$quality_passed <- valid_shapes && record$observed_preserved && record$all_completed_values_finite
    meta <- record$backend
    record$backend_contract_passed <- !hybrid || (is.list(meta) &&
      identical(meta$engine, "r-amelia-torch-em") && identical(meta$call_engine, "r-amelia-torch-em") &&
      identical(meta$device, config$device) && identical(meta$dtype, config$dtype) &&
      length(meta$fits) == config$m && isTRUE(meta$converged) &&
      isTRUE(meta$current_call_torch_used) &&
      identical(meta$current_call_gpu_used, config$device != "cpu") &&
      all(vapply(meta$fits, function(value) isTRUE(value$converged) &&
        identical(value$device, config$device) && identical(value$dtype, config$dtype), logical(1))))
    if (!isTRUE(fit$code == 1)) record$status <- "failed"
    else if (length(converged) != config$m || !all(converged)) record$status <- "nonconverged"
    else if (!record$backend_contract_passed) record$status <- "backend_failed"
    else if (!record$quality_passed) record$status <- "quality_failed"
    else {
      record$regression <- unname(lapply(fit$imputations, function(imp) {
        frame <- as.data.frame(imp)
        names(frame) <- c("y", "x1", "x2")
        model <- stats::lm(y ~ x1 + x2, data = frame)
        list(estimate = unname(coef(model)[["x1"]]),
             variance = unname(stats::vcov(model)["x1", "x1"]))
      }))
      record$status <- "success"
    }
  }, warning = function(w) {
    warnings <<- c(warnings, conditionMessage(w))
    invokeRestart("muffleWarning")
  }), error = function(e) {
    record$status <<- if (grepl("out of memory", conditionMessage(e), ignore.case = TRUE)) "oom" else "failed"
    record$error_type <<- class(e)[[1]]
    record$error <<- conditionMessage(e)
  })
  record$warnings <- as.list(warnings)
  record
}
write_report()
started <- proc.time()[["elapsed"]]
for (item in config$datasets) {
  if (proc.time()[["elapsed"]] - started >= config$time_budget_seconds) break
  report$records[[length(report$records) + 1L]] <- run_one(item)
  write_report()
}
report$completed <- length(report$records) == length(config$datasets)
write_report()
cat("G5 batch", config$route, ":", length(report$records), "datasets retained\n")
quit(status = if (report$completed) 0L else 2L)
