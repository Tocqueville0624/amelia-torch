# Data-only subprocess adapter to version-pinned official and hybrid R pipelines.
# No user-supplied R expressions are parsed/evaluated. Model validation and every
# statistical transformation remains upstream; the explicit hybrid replaces EM.
arguments <- commandArgs(trailingOnly = TRUE)
if (length(arguments) != 3L) stop("Expected request, response and RDS file arguments")
if (!requireNamespace("jsonlite", quietly = TRUE)) {
  stop("The R reference bridge requires jsonlite; install.packages('jsonlite')")
}
request_file <- arguments[[1]]
response_file <- arguments[[2]]
result_file <- arguments[[3]]
warnings_seen <- character()
work_directory <- dirname(request_file)
write_response <- function(value) {
  jsonlite::write_json(value, response_file, auto_unbox = TRUE, pretty = FALSE,
                       digits = NA, na = "null", null = "null")
}
decode_vector <- function(values, type) {
  if (is.null(values)) values <- list()
  if (type == "character") {
    return(vapply(values, function(value) if (is.null(value)) NA_character_ else as.character(value), character(1)))
  }
  if (type == "logical") {
    return(vapply(values, function(value) if (is.null(value)) NA else as.logical(value), logical(1)))
  }
  numbers <- vapply(values, function(value) if (is.null(value)) NA_real_ else as.numeric(value), numeric(1))
  if (type == "integer") as.integer(numbers) else numbers
}
read_binary_column <- function(column, count) {
  storage <- column$storage
  numeric_type <- identical(column$type, "double")
  expected_dtype <- if (numeric_type) "float64" else "int32"
  expected_size <- if (numeric_type) 8L else 4L
  expected_missing <- if (numeric_type) "ieee754_nan" else "int32_min"
  if (!identical(storage$format, "binary-column-v1") ||
      !identical(storage$byte_order, "little") ||
      !identical(storage$dtype, expected_dtype) ||
      storage$itemsize != expected_size || storage$count != count ||
      !identical(storage$missing_encoding, expected_missing)) {
    stop("Invalid binary-column schema, byte order or count")
  }
  if (!numeric_type && storage$missing_sentinel != -2147483648) stop("Invalid integer NA sentinel")
  if (length(count) != 1L || !is.finite(count) || count < 0 || count != floor(count)) {
    stop("Invalid binary-column row count")
  }
  if (basename(storage$filename) != storage$filename || storage$filename %in% c(".", "..")) {
    stop("Binary-column filename must be a local basename")
  }
  path <- file.path(work_directory, storage$filename)
  if (!file.exists(path) || file.info(path)$size != count * expected_size) {
    stop("Binary-column byte length does not match its schema")
  }
  result <- readBin(path, what = if (numeric_type) "double" else "integer",
                    n = count, size = expected_size, signed = TRUE, endian = "little")
  if (length(result) != count) stop("Binary-column read was truncated")
  if (column$type == "logical") {
    if (any(!is.na(result) & !(result %in% c(0L, 1L)))) stop("Invalid logical code")
    result <- as.logical(result)
  }
  result
}
write_binary_column <- function(column, type, filename) {
  numeric_type <- identical(type, "double")
  path <- file.path(work_directory, filename)
  values <- if (numeric_type) as.double(column) else as.integer(column)
  size <- if (numeric_type) 8L else 4L
  writeBin(values, path, size = size, endian = "little")
  if (file.info(path)$size != length(column) * size) stop("Binary-column write was truncated")
  list(format = "binary-column-v1", filename = filename,
       dtype = if (numeric_type) "float64" else "int32", byte_order = "little",
       itemsize = size, count = length(column),
       missing_encoding = if (numeric_type) "ieee754_nan" else "int32_min",
       missing_sentinel = if (numeric_type) NULL else -2147483648)
}
decode_data <- function(value) {
  columns <- lapply(value$columns, function(column) {
    values <- if (column$type == "character") decode_vector(column$values, "character") else {
      read_binary_column(column, value$nrow)
    }
    if (column$type == "factor") {
      levels <- unlist(column$levels, use.names = FALSE)
      if (any(!is.na(values) & (values < 1L | values > length(levels)))) stop("Invalid factor code")
      factor(values, levels = seq_along(levels), labels = levels, ordered = isTRUE(column$ordered))
    } else values
  })
  if (!length(columns)) stop("Input must contain at least one column")
  if (any(vapply(columns, length, integer(1)) != value$nrow)) stop("Invalid column lengths")
  if (value$container == "matrix") {
    result <- do.call(cbind, columns)
    dimnames(result) <- NULL
    return(result)
  }
  result <- as.data.frame(columns, optional = TRUE, stringsAsFactors = FALSE)
  names(result) <- vapply(value$columns, function(column) column$name, character(1))
  if (!is.null(value$row_names)) rownames(result) <- unlist(value$row_names, use.names = FALSE)
  result
}
decode_option <- function(value) {
  if (value$kind == "null") return(NULL)
  if (value$kind == "rds") {
    if (basename(value$filename) != value$filename) stop("RDS option must use a local filename")
    return(readRDS(file.path(dirname(request_file), value$filename)))
  }
  if (value$kind == "list") return(lapply(value$items, decode_option))
  decoded <- decode_vector(value$values, value$type)
  if (value$kind == "matrix") return(matrix(decoded, nrow = value$nrow, ncol = value$ncol, byrow = TRUE))
  if (!(value$kind %in% c("scalar", "vector"))) stop("Unknown option encoding")
  decoded
}
encode_column <- function(column, name, filename) {
  if (is.factor(column)) {
    return(list(name = name, type = "factor", storage = write_binary_column(column, "factor", filename),
                levels = unname(as.list(levels(column))), ordered = is.ordered(column)))
  }
  type <- if (is.logical(column)) "logical" else if (is.integer(column)) "integer" else if (is.numeric(column)) "double" else "character"
  if (type == "character") return(list(name = name, type = type, values = unname(as.list(as.character(column)))))
  list(name = name, type = type, storage = write_binary_column(column, type, filename))
}
encode_data <- function(data, imputation_index) {
  if (!(is.matrix(data) || is.data.frame(data))) stop("An official imputation is not tabular")
  names <- colnames(data)
  if (is.null(names)) names <- paste0("V", seq_len(ncol(data)))
  columns <- lapply(seq_len(ncol(data)), function(i) {
    encode_column(data[, i], names[i], sprintf("output-%06d-column-%06d.bin", imputation_index, i))
  })
  list(container = if (is.data.frame(data)) "data_frame" else "matrix",
       nrow = nrow(data), columns = columns,
       row_names = if (is.null(rownames(data))) NULL else unname(as.list(rownames(data))))
}
historical_provenance <- function(x, request) {
  previous <- request$historical_metadata
  if (!is.null(previous) && identical(as.integer(previous$m), as.integer(x$m))) {
    return(list(source = "previous_python_result", m = x$m, metadata = previous,
                torch_used = previous$torch_used, gpu_used = previous$gpu_used,
                engine = previous$engine))
  }
  backend <- attr(x, "amelia_torch_backend")
  if (is.null(backend)) backend <- attr(x, "ameliatorch_backend")
  if (!is.null(backend)) {
    return(list(source = "recorded_R_backend_attribute", m = x$m, recorded_backend = backend,
                torch_used = backend$torch_used, gpu_used = backend$gpu_used,
                engine = if (is.null(backend$engine)) "unknown" else backend$engine))
  }
  list(source = "external_RDS_without_backend_record", m = x$m, engine = "unknown",
       torch_used = NULL, gpu_used = NULL)
}
execute <- function() {
  request <- jsonlite::read_json(request_file, simplifyVector = FALSE)
  if (!identical(as.integer(request$schema_version), 2L)) stop("Unknown bridge schema")
  if (!(request$engine %in% c("reference", "torch-compat"))) stop("Unknown bridge engine")
  hybrid <- identical(request$engine, "torch-compat")
  call_engine <- if (hybrid) "r-amelia-torch-em" else "r-amelia-reference"
  compatibility_version <- NULL
  if (!requireNamespace("Amelia", quietly = TRUE)) {
    stop("Amelia 1.8.3 is not installed in the selected R libraries")
  }
  version <- as.character(utils::packageVersion("Amelia"))
  if (!identical(version, "1.8.3") || !identical(request$required_version, "1.8.3")) {
    stop(paste0("This reference bridge requires Amelia 1.8.3 exactly; found ", version))
  }
  # Namespace loading (including reticulate's initialization hooks) can consume
  # R randomness. Load dependencies before applying the caller's explicit seed.
  if (hybrid) {
    if (!requireNamespace("ameliatorch", quietly = TRUE)) {
      stop("The hybrid engine requires the installed ameliatorch R package")
    }
    compatibility_version <- as.character(utils::packageVersion("ameliatorch"))
  }
  if (!is.null(request$rng_kind)) do.call(RNGkind, as.list(unlist(request$rng_kind)))
  if (!is.null(request$seed)) set.seed(as.integer(request$seed))
  if (!is.null(request$input_rds)) {
    if (basename(request$input_rds) != request$input_rds) stop("Input RDS must use a local filename")
    x <- readRDS(file.path(dirname(request_file), request$input_rds))
  } else x <- decode_data(request$data)
  previous <- if (inherits(x, "amelia")) historical_provenance(x, request) else NULL
  options <- lapply(request$options, decode_option)
  supported <- setdiff(names(formals(get("amelia.default", envir = asNamespace("Amelia")))),
                       c("x", "m", "..."))
  unknown <- setdiff(names(options), supported)
  if (length(unknown)) {
    stop(paste0("Unknown Amelia 1.8.3 option(s): ", paste(unknown, collapse = ", "),
                ". Use original R option names; for example 'boot.type', not 'boot_type'."))
  }
  if (request$operation == "inspect") {
    if (!inherits(x, "amelia")) stop("The saved RDS is not an official Amelia result")
    fit <- x
  } else {
    if (!identical(request$operation, "fit")) stop("Unknown reference operation")
    if (inherits(x, "amelia") && any(!names(options) %in% c("p2s", "frontend"))) {
      stop("Official Amelia append reuses saved arguments; new model options would be ignored")
    }
    if (is.matrix(options$priors) && nrow(options$priors) == 1L) {
      warnings_seen <<- c(warnings_seen,
        "Amelia 1.8.3 has a verified single-row priors indexing quirk in impfill that can change unrelated observed cells. This bridge preserves the original result; see the Python reference bridge documentation.")
    }
    if (hybrid) {
      fit <- do.call(ameliatorch::amelia_torch_compat,
                     c(list(x = x, m = as.integer(request$m), device = request$device,
                            dtype = request$dtype), options))
    } else {
      fit <- do.call(Amelia::amelia, c(list(x = x, m = as.integer(request$m)), options))
    }
  }
  # The full original object is saved without changing its classes or slots.
  if (inherits(fit, "amelia")) saveRDS(fit, result_file)
  if (is.null(fit$code) || length(fit$code) != 1L || fit$code != 1) {
    write_response(list(ok = FALSE, error = list(kind = "AmeliaResultError", code = fit$code,
                                                message = if (is.null(fit$message)) "Official Amelia returned an unsuccessful result" else fit$message),
                         warnings = as.list(warnings_seen)))
    return(FALSE)
  }
  iterations <- lapply(fit$iterHist, function(history) if (is.matrix(history)) nrow(history) else 0L)
  converged <- lapply(fit$iterHist, function(history) {
    if (is.matrix(history) && nrow(history)) tail(history[, 1], 1) == 0 else TRUE
  })
  if (!all(unlist(converged))) {
    warnings_seen <<- c(warnings_seen, "Original Amelia returned a result before every EM chain satisfied tolerance; inspect iterHist in the saved RDS.")
  }
  inspected <- identical(request$operation, "inspect")
  backend <- if (hybrid && !inspected) attr(fit, "amelia_torch_backend") else NULL
  if (hybrid && !inspected &&
      (!is.list(backend) || !is.logical(backend$current_call_torch_used) ||
       length(backend$current_call_torch_used) != 1L ||
       !is.logical(backend$current_call_gpu_used) || length(backend$current_call_gpu_used) != 1L)) {
    stop("The installed hybrid R package did not return the required execution provenance")
  }
  current_torch <- if (hybrid && !inspected) isTRUE(backend$current_call_torch_used) else FALSE
  current_gpu <- if (hybrid && !inspected) isTRUE(backend$current_call_gpu_used) else FALSE
  current <- list(engine = call_engine, device = if (hybrid) request$device else "cpu",
                  dtype = if (hybrid) request$dtype else "R double",
                  torch_used = current_torch, gpu_used = current_gpu,
                  r_backend_record = backend)
  provenance <- if (inspected) previous else if (!is.null(previous)) {
    list(source = "appended_result", historical_m = previous$m, historical = previous,
         new_m = fit$m - previous$m,
         current_call = current)
  } else c(list(source = "executed_in_this_call", m = fit$m), current)
  result_engine <- if (inspected) previous$engine else if (!is.null(previous)) {
    "appended-history"
  } else call_engine
  combine_usage <- function(name, current) {
    if (is.null(previous)) return(current)
    old <- previous[[name]]
    if (isTRUE(old) || isTRUE(current)) TRUE else if (identical(old, FALSE)) FALSE else NULL
  }
  result_torch <- combine_usage("torch_used", current_torch)
  result_gpu <- combine_usage("gpu_used", current_gpu)
  current_compute <- if (hybrid) "mixed-r-cpu-and-torch" else "cpu"
  write_response(list(
    ok = TRUE,
    metadata = list(engine = result_engine,
                    compute_backend = if (is.null(previous)) current_compute else "historical-or-unknown",
                    torch_used = result_torch, gpu_used = result_gpu,
                    operation = request$operation,
                    call_engine = if (inspected) "rds-inspection" else call_engine,
                    call_compute_backend = if (inspected) NULL else current_compute,
                    call_device = if (inspected) NULL else current$device,
                    call_dtype = if (inspected) NULL else current$dtype,
                    call_torch_used = current_torch, call_gpu_used = current_gpu,
                    compatibility_package_version = compatibility_version,
                    hybrid_backend = backend,
                    provenance = provenance, reference_version = version,
                    reference_version_scope = "R package loaded by this call; not proof of an external RDS creation version",
                    R_version = as.character(getRversion()), call_rng_kind = as.list(RNGkind()),
                    transport = list(schema_version = 2L, numeric = "binary-column-v1",
                                     byte_order = "little", double_bytes = 8L, integer_bytes = 4L,
                                     factor_codes = "R 1-based int32", character = "JSON",
                                     integer_na = -2147483648, double_na = "IEEE754 NaN"),
                    code = fit$code, message = fit$message, m = fit$m,
                    iterations = iterations, converged_by_tolerance = converged,
                    authoritative_result = "Amelia-class R object in RDS; provenance identifies its execution engine"),
    warnings = as.list(warnings_seen), imputations = unname(lapply(seq_along(fit$imputations), function(i) {
      encode_data(fit$imputations[[i]], i)
    }))
  ))
  TRUE
}
success <- tryCatch(withCallingHandlers(execute(), warning = function(condition) {
  warnings_seen <<- c(warnings_seen, conditionMessage(condition))
  invokeRestart("muffleWarning")
}), error = function(condition) {
  write_response(list(ok = FALSE,
                      error = list(kind = "RExecutionError", message = conditionMessage(condition)),
                      warnings = as.list(warnings_seen)))
  FALSE
})
quit(status = if (isTRUE(success)) 0L else 1L)
