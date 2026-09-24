.absolute_python_path <- function(path) {
  if (!is.character(path) || length(path) != 1L || is.na(path) || !nzchar(path)) {
    stop("Provide one non-empty Python or virtual environment path.", call. = FALSE)
  }
  path <- path.expand(path)
  absolute <- startsWith(path, "/") || startsWith(path, "\\\\") ||
    grepl("^[A-Za-z]:[/\\\\]", path)
  if (!absolute) path <- file.path(getwd(), path)
  path
}

.same_python_path <- function(a, b) {
  a <- gsub("\\", "/", a, fixed = TRUE)
  b <- gsub("\\", "/", b, fixed = TRUE)
  if (.Platform$OS.type == "windows") {
    a <- tolower(a)
    b <- tolower(b)
  }
  identical(a, b)
}

#' Select an already installed Python interpreter without initializing Python.
use_amelia_python <- function(python = NULL, venv = NULL) {
  if (is.null(python) == is.null(venv)) {
    stop("Supply exactly one of python or venv.", call. = FALSE)
  }
  if (!is.null(venv)) {
    venv <- .absolute_python_path(venv)
    python <- file.path(venv, if (.Platform$OS.type == "windows") {
      "Scripts/python.exe"
    } else {
      "bin/python"
    })
  }
  python <- .absolute_python_path(python)
  if (!file.exists(python) || dir.exists(python)) {
    stop("The requested Python interpreter does not exist. Install the environment first.",
         call. = FALSE)
  }
  # Resolve directory spelling (e.g. ./), never the interpreter symlink itself.
  # Resolving the final venv executable would lose its virtual environment.
  python <- file.path(normalizePath(dirname(python), winslash = "/", mustWork = TRUE),
                      basename(python))
  if (reticulate::py_available(initialize = FALSE)) {
    active <- reticulate::py_config()$python
    if (!.same_python_path(active, python)) {
      stop("Python is already initialized with another interpreter. Restart R before switching.",
           call. = FALSE)
    }
  }
  Sys.setenv(RETICULATE_PYTHON = python)
  reticulate::use_python(python, required = TRUE)
  invisible(python)
}

.require_amelia_python <- function() {
  python <- Sys.getenv("RETICULATE_PYTHON", unset = "")
  if (!nzchar(python)) {
    stop(paste("Select Python first with use_amelia_python(venv = ...) or set",
               "RETICULATE_PYTHON. The package does not install or choose environments automatically."),
         call. = FALSE)
  }
  use_amelia_python(python = python)
}

.validate_device <- function(device, dtype) {
  if (!is.character(device) || length(device) != 1L || is.na(device) ||
      !device %in% c("cpu", "cuda", "mps")) {
    stop("device must be one of cpu, cuda, or mps.", call. = FALSE)
  }
  if (!is.character(dtype) || length(dtype) != 1L || is.na(dtype) ||
      !dtype %in% c("float64", "float32")) {
    stop("dtype must be float64 or float32.", call. = FALSE)
  }
  if (device == "mps" && dtype == "float64") {
    stop("MPS does not support float64; use cpu or explicitly choose float32.", call. = FALSE)
  }
  if (device == "mps" && Sys.getenv("PYTORCH_ENABLE_MPS_FALLBACK") == "1") {
    stop("Disable PYTORCH_ENABLE_MPS_FALLBACK before starting Python; CPU fallback is not allowed.",
         call. = FALSE)
  }
}

#' Run operator probes on the explicitly requested backend.
check_environment <- function(device = "cpu", dtype = "float64") {
  .validate_device(device, dtype)
  .require_amelia_python()
  diagnostics <- reticulate::import("amelia_torch.diagnostics", convert = TRUE)
  report <- diagnostics$probe_backend(device, dtype)
  if (!all(vapply(report$operations, function(operation) isTRUE(operation$ok), logical(1)))) {
    stop("One or more requested backend operator probes failed.", call. = FALSE)
  }
  report
}
