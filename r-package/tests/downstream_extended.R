# Bounded G1 public-method regressions against unchanged Amelia 1.8.3.
# These diagnostics, transformations, model analyses and exports run in R.
library(ameliatorch)
stopifnot(requireNamespace("Amelia", quietly = TRUE),
          as.character(utils::packageVersion("Amelia")) == "1.8.3")
use_amelia_python(python = Sys.getenv("RETICULATE_PYTHON"))

equal_value <- function(actual, expected, tolerance = 1e-6) {
  difference <- all.equal(actual, expected, tolerance = tolerance)
  if (!isTRUE(difference)) stop(paste(difference, collapse = "; "), call. = FALSE)
}
equal_fit <- function(actual, expected) {
  stopifnot(actual$code == 1L, expected$code == 1L,
            identical(actual$m, expected$m),
            identical(actual$arguments, expected$arguments),
            identical(actual$missMatrix, expected$missMatrix),
            identical(actual$transform.calls, expected$transform.calls))
  equal_value(actual$theta, expected$theta, 1e-7)
  equal_value(actual$imputations, expected$imputations)
}
error_message <- function(operation) {
  caught <- tryCatch({operation(); NULL}, error = conditionMessage)
  stopifnot(is.character(caught), length(caught) == 1L)
  caught
}
fit_pair <- function(data, seed, m = 2L, ...) {
  options <- c(list(x = data, m = m, p2s = 0, tolerance = 1e-6,
                   boot.type = "none"), list(...))
  set.seed(seed)
  original <- do.call(Amelia::amelia, options, envir = parent.frame())
  set.seed(seed)
  hybrid <- do.call(amelia_torch_compat, options, envir = parent.frame())
  equal_fit(hybrid, original)
  list(original = original, hybrid = hybrid)
}
with_pdf <- function(operation) {
  destination <- tempfile(fileext = ".pdf")
  on.exit(unlink(destination), add = TRUE)
  before <- grDevices::dev.list()
  grDevices::pdf(destination)
  device <- grDevices::dev.cur()
  on.exit(if (device %in% grDevices::dev.list()) grDevices::dev.off(device), add = TRUE)
  value <- operation()
  grDevices::dev.off(device)
  stopifnot(identical(grDevices::dev.list(), before),
            file.info(destination)$size > 1000,
            identical(readChar(destination, 4L, useBytes = TRUE), "%PDF"))
  value
}

run_extended <- function() {
  workspace <- tempfile("amelia-downstream-")
  dir.create(workspace)
  on.exit(unlink(workspace, recursive = TRUE), add = TRUE)
  set.seed(681)
  data <- data.frame(id = seq_len(72),
                     label = factor(rep(c("group A", "group B", "group C"), 24)),
                     a = rnorm(72), b = rnorm(72), y = rnorm(72))
  data$y <- data$y + .5 * data$a - .3 * data$b
  data$a[seq(3, 72, 10)] <- NA_real_
  data$y[seq(5, 72, 9)] <- NA_real_
  first <- fit_pair(data, 682, idvars = c("id", "label"))
  second <- fit_pair(data, 683, idvars = c("id", "label"))

  # Direct bind preserves every draw, but upstream creates a fresh object and
  # does not copy our backend attribute. Unknown history must remain unknown.
  bound <- lapply(c("original", "hybrid"), function(engine) {
    Amelia::ameliabind(first[[engine]], second[[engine]])
  })
  names(bound) <- c("original", "hybrid")
  equal_fit(bound$hybrid, bound$original)
  stopifnot(bound$hybrid$m == 4L,
            is.null(attr(bound$hybrid, "amelia_torch_backend")))
  for (i in 1:2) {
    stopifnot(identical(bound$hybrid$imputations[[i]], first$hybrid$imputations[[i]]),
              identical(bound$hybrid$imputations[[i + 2L]], second$hybrid$imputations[[i]]))
  }
  changed_data <- data
  changed_data$a[1] <- NA_real_
  different_missing <- fit_pair(changed_data, 684, idvars = c("id", "label"))
  different_model <- fit_pair(data, 685, idvars = c("id", "label"), empri = 1)
  for (case in list(list(fit = different_missing, message = "Non-compatible datasets."),
                    list(fit = different_model, message = "Non-compatible amelia arguments"))) {
    for (engine in c("original", "hybrid")) {
      message <- error_message(function() Amelia::ameliabind(first[[engine]], case$fit[[engine]]))
      stopifnot(identical(message, case$message))
    }
  }
  cat("PASS direct ameliabind, draw retention and incompatible input errors\n")

  # Use one helper expression so stored transformation calls are exactly equal.
  add_derived <- function(fit) transform(fit, interaction = a * b)
  transformed <- lapply(first, add_derived)
  equal_fit(transformed$hybrid, transformed$original)
  stopifnot(length(transformed$hybrid$transform.calls) == 1L,
            identical(transformed$hybrid$missMatrix[, "interaction"],
                      is.na(data$a * data$b)))
  set.seed(686)
  original_extended <- Amelia::amelia(transformed$original, m = 1, p2s = 0)
  set.seed(686)
  hybrid_extended <- amelia_torch_compat(transformed$hybrid, m = 1, p2s = 0)
  equal_fit(hybrid_extended, original_extended)
  stopifnot(hybrid_extended$m == 3L,
            identical(hybrid_extended$transform.calls, transformed$hybrid$transform.calls))
  for (i in seq_len(hybrid_extended$m)) {
    draw <- hybrid_extended$imputations[[i]]
    equal_value(draw$interaction, draw$a * draw$b, 0)
    if (i <= 2L) stopifnot(identical(draw, transformed$hybrid$imputations[[i]]))
  }
  cat("PASS transform, stored calls, missingness and appended derived columns\n")

  original_models <- with(bound$original, stats::lm(y ~ a + b))
  hybrid_models <- with(bound$hybrid, stats::lm(y ~ a + b))
  stopifnot(inherits(original_models, "amest"), inherits(hybrid_models, "amest"))
  equal_value(lapply(hybrid_models, stats::coef), lapply(original_models, stats::coef))
  if (requireNamespace("broom", quietly = TRUE)) {
    for (interval in c(FALSE, TRUE)) {
      original_pool <- Amelia::mi.combine(original_models, conf.int = interval, conf.level = .90)
      hybrid_pool <- Amelia::mi.combine(hybrid_models, conf.int = interval, conf.level = .90)
      equal_value(hybrid_pool, original_pool)
      stopifnot(all(is.finite(hybrid_pool$estimate)), all(hybrid_pool$std.error > 0),
                all(hybrid_pool$df > 0))
      if (interval) {
        # Version 1.8.3 uses the upper-tail .95 quantile, a negative critical
        # value. Check faithful reproduction; do not silently repair upstream.
        stopifnot(all(original_pool$conf.low > original_pool$conf.high))
      }
    }
    cat("PASS with -> mi.combine, including unchanged 1.8.3 interval ordering\n")
  } else {
    stopifnot(grepl("broom.*required", error_message(function() Amelia::mi.combine(hybrid_models))))
    cat("SKIP available-broom pooling branch: optional broom is not installed\n")
  }
  # Exercise the absent dependency branch with a private closure. No installed
  # namespace is patched, unloaded or replaced, and no pooling formula changes.
  without_broom <- Amelia::mi.combine
  environment(without_broom) <- list2env(list(requireNamespace = function(package, ...) {
    if (identical(package, "broom")) FALSE else base::requireNamespace(package, ...)
  }), parent = environment(without_broom))
  stopifnot(grepl("broom.*required", error_message(function() without_broom(hybrid_models))))
  cat("PASS explicit missing-broom dependency error (private dependency probe)\n")

  original_text <- capture.output(original_summary <- summary(first$original$imputations))
  hybrid_text <- capture.output(hybrid_summary <- summary(first$hybrid$imputations))
  stopifnot(identical(hybrid_text, original_text))
  equal_value(hybrid_summary, original_summary)
  for (engine in c("original", "hybrid")) {
    with_pdf(function() plot(first[[engine]], which.vars = 5, ask = FALSE))
    set.seed(687)
    with_pdf(function() plot(first[[engine]], which.vars = 5, compare = FALSE,
                             overimpute = TRUE, ask = FALSE))
  }
  cat("PASS summary.mi and both plot.amelia PDF branches with device cleanup\n")

  # write.amelia evaluates write.dta in its caller, so bind that official writer
  # explicitly instead of relying on the user's attached search path.
  write.dta <- foreign::write.dta
  exports <- list()
  for (engine in c("original", "hybrid")) {
    fit <- first[[engine]]
    table_stem <- file.path(workspace, paste0(engine, "-table-"))
    # Explicit separate prevents R's partial argument matching from treating
    # write.table's sep argument as write.amelia's separate argument.
    Amelia::write.amelia(fit, separate = TRUE, file.stem = table_stem, format = "table", extension = ".txt",
                         row.names = FALSE, sep = "\t")
    table_values <- lapply(seq_len(fit$m), function(i) {
      utils::read.table(paste0(table_stem, i, ".txt"), header = TRUE, sep = "\t",
                        stringsAsFactors = FALSE, check.names = FALSE)
    })
    for (i in seq_len(fit$m)) {
      expected <- fit$imputations[[i]]
      expected$label <- as.character(expected$label)
      equal_value(table_values[[i]], expected, 1e-12)
    }
    dta_stem <- file.path(workspace, paste0(engine, "-combined"))
    Amelia::write.amelia(fit, separate = FALSE, file.stem = dta_stem,
                         format = "dta", orig.data = FALSE, impvar = "draw_id")
    dta_values <- foreign::read.dta(paste0(dta_stem, ".dta"))
    stopifnot(nrow(dta_values) == nrow(data) * fit$m,
              identical(sort(unique(dta_values$draw_id)), as.numeric(1:fit$m)),
              is.factor(dta_values$label),
              identical(levels(dta_values$label), levels(data$label)))
    for (i in seq_len(fit$m)) {
      rows <- dta_values$draw_id == i
      equal_value(unname(as.matrix(dta_values[rows, c("a", "b", "y")])),
                  unname(as.matrix(fit$imputations[[i]][, c("a", "b", "y")])), 1e-12)
      stopifnot(identical(as.character(dta_values$label[rows]), as.character(data$label)))
    }
    exports[[engine]] <- list(table = table_values,
                              dta = dta_values[, names(fit$imputations[[1]])])
  }
  equal_value(exports$hybrid, exports$original)
  cat("PASS table and combined DTA readback, factor labels and custom draw_id\n")

  # Four documented moPrep branches; compare priors to their published formulas
  # and use precisely the same prepared object for original/reference/hybrid.
  set.seed(688)
  measurement <- data.frame(id = 1:60, a = rnorm(60), b = rnorm(60), y = rnorm(60))
  measurement$a[1:30] <- measurement$a[1:30] * 3
  measurement$proxy <- .2 * measurement$a + rnorm(60, sd = .2)
  measurement$y[seq(4, 60, 9)] <- NA_real_
  proportion <- Amelia::moPrep(measurement, a ~ a, error.proportion = .1)
  gold <- Amelia::moPrep(measurement, a ~ a, subset = id <= 30, gold.standard = TRUE)
  proxy <- Amelia::moPrep(measurement, a ~ a | proxy)
  moPrep <- Amelia::moPrep
  added <- moPrep(proportion, b ~ b, error.proportion = .2)
  equal_value(proportion$priors[, 4], rep(sqrt(stats::var(measurement$a) * .1), 60), 1e-14)
  equal_value(gold$priors[, 4], rep(sqrt(stats::var(measurement$a[1:30]) -
                                         stats::var(measurement$a[31:60])), 30), 1e-14)
  equal_value(proxy$priors[, 4], rep(sqrt(stats::var(measurement$a) -
                                          stats::cov(measurement$a, measurement$proxy)), 60), 1e-14)
  stopifnot(identical(added$priors[1:60, ], proportion$priors),
            identical(added$overimp[1:60, ], proportion$overimp),
            nrow(added$priors) == 120L, nrow(added$overimp) == 120L)
  prepared_cases <- list(proportion = proportion, gold = gold, proxy = proxy, added = added)
  for (name in names(prepared_cases)) {
    prepared <- prepared_cases[[name]]
    prepared$data <- measurement  # A self-contained RDS can cross processes.
    prepared_path <- file.path(workspace, paste0("molist-", name, ".rds"))
    saveRDS(prepared, prepared_path)
    stopifnot(identical(readRDS(prepared_path), prepared))
    pair <- fit_pair(prepared, 689, m = 1, idvars = "id")
    set.seed(689)
    reference <- amelia_compat(prepared, m = 1, p2s = 0, tolerance = 1e-6,
                                boot.type = "none", idvars = "id")
    equal_fit(reference, pair$original)
  }
  cat("PASS moPrep proportion, gold-standard subset, proxy and added molist priors\n")

  # Actual Python -> saved official RDS -> original R methods -> Python view.
  # Temporary scripts keep this test runnable from R CMD check's directory.
  python <- Sys.getenv("RETICULATE_PYTHON")
  stopifnot(nzchar(python), file.exists(python))
  run_python <- function(lines, arguments) {
    # R CMD check sets R_TESTS to its own startup file. A nested Rscript runs
    # in the Python bridge's temporary directory, where that file is absent.
    # Keep this test-harness setting out of children and restore the caller.
    previous_tests <- Sys.getenv("R_TESTS", unset = NA_character_)
    Sys.unsetenv("R_TESTS")
    on.exit(if (is.na(previous_tests)) Sys.unsetenv("R_TESTS") else
      Sys.setenv(R_TESTS = previous_tests), add = TRUE)
    script <- tempfile(tmpdir = workspace, fileext = ".py")
    writeLines(lines, script)
    output <- system2(python, shQuote(c(script, arguments)), stdout = TRUE, stderr = TRUE)
    status <- attr(output, "status")
    if (!is.null(status) && status != 0L) stop(paste(output, collapse = "\n"), call. = FALSE)
  }
  from_python <- file.path(workspace, "from-python.rds")
  run_python(c(
    "import sys",
    "import numpy as np",
    "import pandas as pd",
    "from amelia_torch import amelia_torch_compat",
    "rng = np.random.default_rng(690)",
    "data = pd.DataFrame(rng.normal(size=(60, 3)), columns=['a', 'b', 'y'])",
    "data.loc[::7, 'a'] = np.nan",
    "data.loc[::9, 'y'] = np.nan",
    "fit = amelia_torch_compat(data, m=2, seed=691, p2s=0, **{'boot.type': 'none'})",
    "fit.save_rds(sys.argv[1])"
  ), from_python)
  imported <- readRDS(from_python)
  stopifnot(inherits(imported, "amelia"), imported$m == 2L,
            isTRUE(attr(imported, "amelia_torch_backend")$torch_used))
  imported_transformed <- add_derived(imported)
  set.seed(692)
  returned <- amelia_compat(imported_transformed, m = 1, p2s = 0)
  stopifnot(returned$m == 3L,
            identical(returned$imputations[[1]], imported_transformed$imputations[[1]]),
            identical(returned$transform.calls, imported_transformed$transform.calls))
  with_pdf(function() plot(returned, which.vars = 3, ask = FALSE))
  to_python <- file.path(workspace, "back-to-python.rds")
  bound_path <- file.path(workspace, "bound-unknown-history.rds")
  saveRDS(returned, to_python)
  saveRDS(bound$hybrid, bound_path)
  run_python(c(
    "import sys",
    "import numpy as np",
    "from amelia_torch import read_reference_rds",
    "result = read_reference_rds(sys.argv[1])",
    "assert result.m == 3",
    "assert result.metadata['torch_used'] is True",
    "for draw in result.imputations:",
    "    np.testing.assert_allclose(draw['interaction'], draw['a'] * draw['b'], atol=0, rtol=0)",
    "extended = result.extend(m=1, seed=693, p2s=0)",
    "assert extended.m == 4 and extended.metadata['call_torch_used'] is False",
    "for draw in extended.imputations:",
    "    np.testing.assert_allclose(draw['interaction'], draw['a'] * draw['b'], atol=0, rtol=0)",
    "bound = read_reference_rds(sys.argv[2])",
    "assert bound.engine == 'unknown'",
    "assert bound.metadata['torch_used'] is None and bound.metadata['gpu_used'] is None",
    "assert bound.metadata['provenance']['source'] == 'external_RDS_without_backend_record'"
  ), c(to_python, bound_path))
  cat("PASS Python/RDS/R transform/append/plot/Python roundtrip and unknown bind provenance\n")
}

run_extended()
cat("Extended downstream G1 checks completed.\n")
