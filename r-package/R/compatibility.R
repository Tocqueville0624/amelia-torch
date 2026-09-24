.reference_backend_metadata <- function(x, result, reference_version) {
  appended <- inherits(x, "amelia")
  count <- function(object) {
    if (is.list(object) && is.numeric(object$m) && length(object$m) == 1L &&
        !is.na(object$m) && is.finite(object$m)) object$m else NA_real_
  }
  historical_m <- if (appended) count(x) else 0L
  total_m <- count(result)
  metadata <- list(
    engine = if (appended) "appended" else "reference",
    implementation = "Amelia::amelia",
    amelia_version = reference_version,
    device = if (appended) "mixed-or-unknown" else "cpu",
    gpu_used = if (appended) NA else FALSE,
    torch_used = if (appended) NA else FALSE,
    em_kernel = if (appended) "mixed-or-unknown" else "official_Amelia",
    current_call_engine = "reference",
    current_call_device = "cpu",
    current_call_gpu_used = FALSE,
    current_call_torch_used = FALSE,
    current_call_em_kernel = "official_Amelia",
    historical_m = historical_m,
    new_m = total_m - historical_m,
    total_m = total_m,
    delegation = "Unmodified public S3 generic of the installed official R package"
  )
  if (appended) {
    previous <- attr(x, "amelia_torch_backend", exact = TRUE)
    if (is.null(previous)) previous <- attr(x, "ameliatorch_backend", exact = TRUE)
    if (!is.list(previous)) {
      previous <- list(engine = "unknown", device = "unknown", gpu_used = NA, torch_used = NA,
                       reason = "Input result has no recognized recorded backend provenance")
    }
    metadata$old_backend <- previous
    if (isTRUE(previous$gpu_used) ||
        (is.character(previous$device) && length(previous$device) == 1L &&
         previous$device %in% c("cuda", "mps"))) {
      metadata$gpu_used <- TRUE
    } else if (identical(previous$gpu_used, FALSE)) {
      metadata$gpu_used <- FALSE
    }
    if (isTRUE(previous$torch_used)) {
      metadata$torch_used <- TRUE
    } else if (identical(previous$torch_used, FALSE)) {
      metadata$torch_used <- FALSE
    }
  }
  metadata
}

#' Delegate to the installed official Amelia implementation without preprocessing.
amelia_compat <- function(x, ..., engine = "reference") {
  if (!is.character(engine) || length(engine) != 1L || is.na(engine) ||
      !identical(engine, "reference")) {
    stop(paste("Only engine = 'reference' is implemented by amelia_compat().",
               "Use amelia_torch_compat() for the experimental hybrid engine."),
         call. = FALSE)
  }
  if (!requireNamespace("Amelia", quietly = TRUE)) {
    stop(paste("amelia_compat(engine = 'reference') requires the R package Amelia.",
               "Install Amelia in your selected R library; this wrapper does not install it automatically."),
         call. = FALSE)
  }
  reference_version <- as.character(utils::packageVersion("Amelia"))
  if (!identical(reference_version, "1.8.3")) {
    stop(paste("amelia_compat() requires exactly Amelia 1.8.3 for reproducibility; found",
               reference_version,
               ". Install the pinned reference version in your selected R library."),
         call. = FALSE)
  }
  # Call the public S3 generic directly. Do not coerce x, reinterpret ..., clone
  # an upstream method, replace its environment, or alter the R random stream.
  # Preserve the caller's frame: amelia.molist evaluates its saved data
  # expression there. An extra wrapper frame would break local moPrep inputs.
  result <- do.call(Amelia::amelia, c(list(x = x), list(...)), envir = parent.frame())
  attr(result, "amelia_torch_backend") <- .reference_backend_metadata(x, result, reference_version)
  result
}
