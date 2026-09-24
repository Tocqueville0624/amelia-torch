# Fixed, bounded R-user compatibility cases; never a performance benchmark.
.libPaths(c(file.path(getwd(), ".R-library"), .libPaths()))
cli <- commandArgs(trailingOnly = TRUE)
if (length(cli) != 3L) stop("Usage: Rscript scripts/validate_r_accelerator.R DEVICE DTYPE OUTPUT.json")
device <- cli[[1]]
dtype <- cli[[2]]
stopifnot(device %in% c("mps", "cuda"), dtype %in% c("float32", "float64"))
ameliatorch::use_amelia_python(python = Sys.getenv("RETICULATE_PYTHON"))
reticulate::import("torch")$set_num_threads(1L)
set.seed(97)
x <- data.frame(id = seq_len(240), a = rnorm(240), b = rnorm(240),
                positive = exp(rnorm(240)), fraction = runif(240, .1, .9),
                category = factor(sample(c("red", "green", "blue"), 240, TRUE)),
                ordered = ordered(sample(1:4, 240, TRUE)))
x$b <- x$b + x$a * .4
for (column in 2:ncol(x)) x[seq(column, 240, 11), column] <- NA
cases <- list(
  transformed = list(data = x[, 1:5], options = list(idvars = "id", logs = "positive", lgstc = "fraction")),
  categorical = list(data = x, options = list(idvars = "id", noms = "category", ords = "ordered", logs = "positive")),
  prior_bounds = list(data = x[, 1:5], options = list(idvars = "id", priors = rbind(c(2, 2, 0, 1), c(3, 3, 0, 1)), bounds = matrix(c(2, -4, 4), 1), max.resample = 20))
)
# Predeclared gates: standardized continuous output error <= .002;
# theta all.equal at tolerance .0001; discrete disagreement <= 1% of all cells.
results <- lapply(names(cases), function(name) {
  case <- cases[[name]]
  args <- c(list(x = case$data, m = 3, p2s = 0, tolerance = 1e-4, emburn = c(0, 500)), case$options)
  tryCatch({
    set.seed(871)
    expected <- do.call(Amelia::amelia, args)
    set.seed(871)
    actual <- do.call(ameliatorch::amelia_torch_compat, c(args, list(device = device, dtype = dtype)))
    stopifnot(expected$code == 1, actual$code == 1)
    meta <- attr(actual, "amelia_torch_backend")
    observed <- vapply(seq_len(ncol(case$data)), function(j) {
      # User priors intentionally overimpute their specified observed cells.
      keep <- !is.na(case$data[[j]])
      if (!is.null(case$options$priors)) keep[case$options$priors[case$options$priors[, 2] == j, 1]] <- FALSE
      all(vapply(actual$imputations, function(imp) identical(imp[[j]][keep], case$data[[j]][keep]), logical(1)))
    }, logical(1))
    errors <- c()
    different <- total <- 0
    for (i in seq_len(actual$m)) for (j in seq_len(ncol(case$data))) {
      a <- actual$imputations[[i]][[j]]
      b <- expected$imputations[[i]][[j]]
      if (is.numeric(a)) {
        scale <- stats::sd(case$data[[j]], na.rm = TRUE)
        errors <- c(errors, max(abs(a - b)) / scale)
      } else {
        different <- different + sum(a != b)
        total <- total + length(a)
      }
    }
    categorical_error <- if (total) different / total else 0
    checks <- list(original_class = identical(class(actual), class(expected)),
                   theta = isTRUE(all.equal(actual$theta, expected$theta, tolerance = 1e-4)),
                   observed = all(observed), continuous = max(errors) <= .002,
                   categorical = categorical_error <= .01, converged = isTRUE(meta$converged),
                   gpu_used = isTRUE(meta$gpu_used))
    list(case = name, passed = all(unlist(checks)), checks = checks,
         max_standardized_continuous_error = max(errors),
         discrete_disagreements = different, discrete_cells = total,
         backend = meta)
  }, error = function(e) list(case = name, passed = FALSE, error = class(e)[[1]], message = conditionMessage(e)))
})
report <- list(schema_version = 1, scope = "Three fixed public R-pipeline GPU cases against original Amelia 1.8.3, matched R seed; m=3. No timing or distributional-equivalence claim.",
               device = device, dtype = dtype, R = as.character(getRversion()),
               Amelia = as.character(packageVersion("Amelia")),
               gates = list(theta_all_equal_tolerance = 1e-4, max_standardized_continuous_error = .002, max_discrete_disagreement_fraction = .01),
               all_passed = all(vapply(results, function(x) isTRUE(x$passed), logical(1))), cases = results)
dir.create(dirname(cli[[3]]), recursive = TRUE, showWarnings = FALSE)
jsonlite::write_json(report, cli[[3]], pretty = TRUE, auto_unbox = TRUE, digits = NA, null = "null")
print(lapply(results, function(x) x[c("case", "passed", "checks", "max_standardized_continuous_error", "discrete_disagreements")]))
if (!report$all_passed) quit(status = 1)
