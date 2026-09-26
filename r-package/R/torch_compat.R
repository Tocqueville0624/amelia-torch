# Original Amelia 1.8.3 closures run in a private lookup environment. No package
# namespace is modified. Only emarch is replaced; preprocessing, R RNG/bootstrap,
# conditional draws, category conversion, transformations and output stay upstream.

.torch_em_context <- function(device, dtype) {
  if (!requireNamespace("Amelia", quietly = TRUE) ||
      as.character(utils::packageVersion("Amelia")) != "1.8.3") {
    stop("This compatibility engine requires exactly Amelia 1.8.3.", call. = FALSE)
  }
  .validate_device(device, dtype)
  # Source-mode tests also require this package's installed, compiled helpers.
  own_namespace <- asNamespace("ameliatorch")
  snapshot_rng <- get("C_amelia_rng_snapshot", envir = own_namespace, inherits = FALSE)
  restore_rng <- get("C_amelia_rng_restore", envir = own_namespace, inherits = FALSE)
  writeback_theta <- get("C_amelia_theta_writeback", envir = own_namespace, inherits = FALSE)
  # Preserve C RNG state as well as .Random.seed, which the upstream C++ imputer
  # can leave stale. An R-vector-only snapshot is insufficient across reticulate.
  initial_rng <- .Call(snapshot_rng)
  on.exit(.Call(restore_rng, initial_rng), add = TRUE)
  .require_amelia_python()
  module <- reticulate::import("amelia_torch.em", convert = TRUE)
  # Fail before invoking any R bootstrap if the requested accelerator is absent.
  backends <- reticulate::import("amelia_torch.backends", convert = FALSE)
  backends$resolve_backend(device, dtype)
  upstream <- asNamespace("Amelia")
  context <- new.env(parent = upstream)
  tracking <- new.env(parent = emptyenv())
  tracking$fits <- list()
  context$emarch <- function(x, p2s = TRUE, thetaold = NULL, startvals = 0,
                            tolerance = 0.0001, priors = NULL, empri = NULL,
                            frontend = FALSE, collect = FALSE, allthetas = FALSE,
                            autopri = 0.05, emburn = c(0, 0)) {
    # Keep upstream startval semantics and finite complete-case decisions.
    initial <- if (all(stats::complete.cases(x))) NULL else {
      if (is.null(thetaold)) get("startval", upstream)(x, startvals, priors) else thetaold
    }
    em_rng <- .Call(snapshot_rng)
    on.exit(.Call(restore_rng, em_rng), add = TRUE)
    fit <- module$em_fit(x, thetaold = initial, tolerance = tolerance,
                         priors = priors, empri = empri, autopri = autopri,
                         emburn = as.numeric(emburn), allthetas = allthetas,
                         device = device, dtype = dtype)
    tracking$fits[[length(tracking$fits) + 1L]] <- fit$diagnostics
    history <- if (isTRUE(fit$diagnostics$complete_sample)) NA else fit$iter_hist
    parameters <- fit$theta
    if (allthetas && !isTRUE(fit$diagnostics$complete_sample)) {
      upper <- upper.tri(initial, diag = TRUE)
      upper[1, 1] <- FALSE
      parameters <- do.call(cbind, lapply(c(list(initial), fit$theta_history),
                                         function(theta) theta[upper]))
    }
    if (!isTRUE(fit$diagnostics$complete_sample)) {
      # Preserve upstream's double-matrix alias side effect after recording the
      # initial allthetas column. Integer starts are coerced by Rcpp and stay
      # unchanged; the C helper mirrors that distinction without R copy-on-write.
      .Call(writeback_theta, initial, fit$theta)
    }
    if (isTRUE(p2s > 0)) {
      cat("PyTorch EM:", fit$diagnostics$iterations, "iterations on", device, dtype, "\n")
    }
    list(thetanew = parameters, iter.hist = history)
  }
  for (name in c("amelia.default", "amelia.amelia")) {
    fn <- get(name, envir = upstream)
    environment(fn) <- context
    assign(name, fn, envir = context)
  }
  list(environment = context, tracking = tracking)
}

#' Run the original Amelia pipeline with a PyTorch EM kernel (experimental).
amelia_torch_compat <- function(x, ..., device = "cpu", dtype = "float64") {
  arguments <- list(...)
  historical_m <- if (inherits(x, "amelia")) x$m else 0L
  previous_backend <- if (inherits(x, "amelia")) {
    value <- attr(x, "amelia_torch_backend", exact = TRUE)
    if (is.null(value)) value <- attr(x, "ameliatorch_backend", exact = TRUE)
    if (is.null(value)) list(origin = "unknown") else value
  } else NULL
  parallel_mode <- if (is.null(arguments$parallel)) {
    getOption("amelia.parallel", "no")
  } else arguments$parallel
  ncpus <- if (is.null(arguments$ncpus)) getOption("amelia.ncpus", 1L) else arguments$ncpus
  if (!identical(parallel_mode, "no") && ncpus > 1L) {
    stop(paste("The experimental PyTorch compatibility engine currently requires serial",
               "replicate scheduling. Use parallel='no', or amelia_compat for the",
               "original R parallel implementation."), call. = FALSE)
  }
  if (!is.null(arguments$cl)) {
    stop("A cluster cannot be passed to the serial PyTorch compatibility engine.",
         call. = FALSE)
  }
  bridge <- .torch_em_context(device, dtype)
  if (inherits(x, "molist")) {
    # Same argument replacement as Amelia 1.8.3's amelia.molist S3 method.
    arguments$priors <- x$priors
    arguments$overimp <- x$overimp
    # moPrep stores a caller expression, not the evaluated data frame.
    x <- eval(x$data, envir = parent.frame())
  }
  method <- if (inherits(x, "amelia")) "amelia.amelia" else "amelia.default"
  result <- do.call(method, c(list(x = x), arguments), envir = bridge$environment)
  new_torch_used <- length(bridge$tracking$fits) > 0L
  new_gpu_used <- new_torch_used && device != "cpu"
  known_history <- function(name, current) {
    if (historical_m == 0L) return(current)
    previous <- previous_backend[[name]]
    if (isTRUE(previous) || current) TRUE else if (identical(previous, FALSE)) FALSE else NA
  }
  converged <- is.list(result$iterHist) && length(result$iterHist) > 0L &&
    all(vapply(result$iterHist, function(history) {
      if (is.matrix(history) && nrow(history)) utils::tail(history[, 1], 1) == 0 else TRUE
    }, logical(1)))
  total_m <- result[["m"]]
  if (!is.numeric(total_m) || length(total_m) != 1L || !is.finite(total_m)) total_m <- 0L
  attr(result, "amelia_torch_backend") <- list(
    engine = if (historical_m > 0L) "mixed-history" else "r-amelia-torch-em",
    call_engine = "r-amelia-torch-em", reference_version = "1.8.3",
    device = device, dtype = dtype, experimental = TRUE,
    torch_used = known_history("torch_used", new_torch_used),
    gpu_used = known_history("gpu_used", new_gpu_used),
    current_call_torch_used = new_torch_used, current_call_gpu_used = new_gpu_used,
    historical_m = historical_m, previous_backend = previous_backend,
    new_m = max(0, total_m - historical_m), total_m = total_m,
    r_cpu_work = c("preprocessing", "bootstrap and RNG", "conditional draws", "postprocessing"),
    fits = bridge$tracking$fits, converged = converged
  )
  result
}
