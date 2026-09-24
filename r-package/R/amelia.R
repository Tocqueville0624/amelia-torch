.normalize_options <- function(options) {
  if (!length(options)) return(options)
  nms <- names(options)
  if (is.null(nms) || anyNA(nms) || any(!nzchar(nms))) {
    stop("All additional Amelia options must be named.", call. = FALSE)
  }
  aliases <- c("boot.type" = "boot_type", "max.resample" = "max_resample")
  matched <- nms %in% names(aliases)
  nms[matched] <- unname(aliases[nms[matched]])
  if (anyDuplicated(nms)) {
    stop("An option was supplied more than once, including R/Python aliases.", call. = FALSE)
  }
  names(options) <- nms
  options
}

#' Call the native Python implementation for supported continuous numeric inputs.
amelia_torch <- function(x, m = 5L, device = "cpu", dtype = "float64", seed = NULL, ...) {
  .validate_device(device, dtype)
  if (!is.numeric(m) || length(m) != 1L || is.na(m) || !is.finite(m) ||
      m < 1 || m != floor(m) || m > .Machine$integer.max) {
    stop("m must be a positive integer.", call. = FALSE)
  }
  if (!is.null(seed) && (!is.numeric(seed) || length(seed) != 1L || is.na(seed) ||
                        !is.finite(seed) || seed < 0 || seed != floor(seed) || seed > 2^53 - 1)) {
    stop("seed must be NULL or an exactly represented non-negative integer below 2^53.",
         call. = FALSE)
  }
  is_frame <- is.data.frame(x)
  if (is_frame) {
    if (!all(vapply(x, function(column) is.numeric(column) && !is.object(column), logical(1)))) {
      stop("The native prototype currently accepts only plain numeric data-frame columns.",
           call. = FALSE)
    }
    numeric_x <- as.matrix(x)
  } else {
    if (!is.matrix(x) || !is.numeric(x) || is.object(x)) {
      stop("x must be a plain numeric matrix or numeric data frame.", call. = FALSE)
    }
    numeric_x <- x
  }
  storage.mode(numeric_x) <- "double"
  options <- .normalize_options(list(...))
  .require_amelia_python()
  module <- reticulate::import("amelia_torch", convert = FALSE)
  if (!reticulate::py_has_attr(module, "amelia")) {
    stop(paste("This Python installation has no amelia() imputation implementation.",
               "Install a matching development version; environment probes alone do not implement imputation."),
         call. = FALSE)
  }
  numeric_seed <- seed
  if (!is.null(seed)) {
    # R doubles up to 2^53 - 1 are exact integers, but Python needs an integer object.
    seed <- reticulate::import_builtins(convert = FALSE)$int(sprintf("%.0f", seed))
  }
  python_result <- do.call(module$amelia,
                          c(list(x = numeric_x, m = as.integer(m), device = device,
                                 dtype = dtype, seed = seed), options))
  result <- reticulate::py_to_r(python_result)
  if (!is.list(result) || !all(c("imputations", "diagnostics") %in% names(result)) ||
      !is.list(result$imputations) || length(result$imputations) != m ||
      !is.list(result$diagnostics)) {
    stop("The Python result does not satisfy the R interface contract.", call. = FALSE)
  }
  if (!is.null(numeric_seed) && "seed" %in% names(result$diagnostics)) {
    # reticulate may truncate a Python int to R's 32-bit integer during dict
    # conversion. Preserve the exact numeric seed promised by this interface.
    reported_seed <- as.numeric(reticulate::py_to_r(
      reticulate::import_builtins(convert = FALSE)$str(python_result$diagnostics$seed)))
    if (length(reported_seed) != 1L || is.na(reported_seed) || reported_seed != numeric_seed) {
      stop("Python reported a seed different from the requested seed.", call. = FALSE)
    }
    result$diagnostics$seed <- reported_seed
  }
  observed <- !is.na(numeric_x)
  wholly_missing <- rowSums(observed) == 0L
  result$imputations <- lapply(result$imputations, function(completed) {
    if (!is.matrix(completed) || !identical(dim(completed), dim(numeric_x))) {
      stop("Python returned an imputation with an unexpected shape.", call. = FALSE)
    }
    if (anyNA(completed[observed]) || !all(completed[observed] == numeric_x[observed])) {
      stop("Python changed observed values; the imputation was rejected.", call. = FALSE)
    }
    if (any(!is.finite(completed[!wholly_missing, , drop = FALSE]))) {
      stop("Python left missing or non-finite values in an analyzed row.", call. = FALSE)
    }
    if (any(!is.na(completed[wholly_missing, , drop = FALSE]))) {
      stop("Python filled a wholly missing row, contrary to Amelia's retained-row behavior.",
           call. = FALSE)
    }
    # Preserve R's NA versus NaN representation for rows excluded from analysis.
    completed[wholly_missing, ] <- numeric_x[wholly_missing, , drop = FALSE]
    dimnames(completed) <- dimnames(numeric_x)
    if (is_frame) {
      completed <- as.data.frame(completed, optional = TRUE, stringsAsFactors = FALSE)
      names(completed) <- names(x)
      rownames(completed) <- rownames(x)
    }
    completed
  })
  class(result) <- c("ameliatorch_result", "list")
  result
}

print.ameliatorch_result <- function(x, ...) {
  cat("Amelia Torch development result:", length(x$imputations), "imputations\n")
  cat("Inspect $diagnostics for convergence and backend details.\n")
  invisible(x)
}
