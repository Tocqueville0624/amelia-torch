# Source this file in an existing RStudio session, preferably into a local env:
# local({ source("scripts/rstudio_smoke.R", local = TRUE); run_rstudio_smoke(getwd()) })
# Pass the project root explicitly when RStudio's working directory is elsewhere.
# Creates only synthetic validation files under results/local/g6-rstudio.
# Never clears the user's workspace, closes source tabs or saves .RData.
run_rstudio_smoke <- function(project_root, show_data = TRUE) {
  stopifnot(interactive(), requireNamespace("rstudioapi", quietly = TRUE),
            rstudioapi::isAvailable())
  project_root <- normalizePath(project_root, mustWork = TRUE)
  previous_libraries <- .libPaths()
  on.exit(.libPaths(previous_libraries), add = TRUE)
  .libPaths(c(file.path(project_root, ".R-library"), previous_libraries))
  stopifnot(requireNamespace("ameliatorch", quietly = TRUE),
            as.character(utils::packageVersion("Amelia")) == "1.8.3")
  directory <- file.path(project_root, "results", "local", "g6-rstudio")
  dir.create(directory, recursive = TRUE, showWarnings = FALSE)
  expected_files <- file.path(directory, c("reference.rds", "hybrid.rds", "completed.csv",
                                            "input.csv", "diagnostic.png", "session.json"))
  if (any(file.exists(expected_files))) {
    stop("The G6 output files already exist. Select a fresh checkout or archive this test's outputs first.")
  }
  helper <- asNamespace("ameliatorch")
  saved_rng <- .Call(get("C_amelia_rng_snapshot", envir = helper))
  on.exit(.Call(get("C_amelia_rng_restore", envir = helper), saved_rng), add = TRUE)
  requested_python <- file.path(project_root, ".venv",
    if (.Platform$OS.type == "windows") "Scripts/python.exe" else "bin/python")
  # Keep the venv path (do not resolve the interpreter symlink).
  ameliatorch::use_amelia_python(python = requested_python)
  config <- reticulate::py_config()
  stopifnot(identical(config$python, requested_python))
  torch <- reticulate::import("torch")
  previous_threads <- torch$get_num_threads()
  torch$set_num_threads(1L)
  on.exit(torch$set_num_threads(as.integer(previous_threads)), add = TRUE)
  set.seed(20260926)
  input <- data.frame(id = seq_len(120), predictor = rnorm(120),
                      auxiliary = rnorm(120), outcome = rnorm(120))
  input$outcome <- .6 * input$predictor + .3 * input$auxiliary + input$outcome
  input$predictor[seq(4, 120, 9)] <- NA_real_
  input$outcome[seq(7, 120, 11)] <- NA_real_
  utils::write.csv(input, file.path(directory, "input.csv"), row.names = FALSE)
  set.seed(871)
  reference <- ameliatorch::amelia_compat(input, m = 3, idvars = "id", p2s = 0,
                                         tolerance = 1e-6, engine = "reference")
  set.seed(871)
  hybrid <- ameliatorch::amelia_torch_compat(input, m = 3, idvars = "id", p2s = 0,
                                           tolerance = 1e-6, device = "cpu", dtype = "float64")
  stopifnot(reference$code == 1L, hybrid$code == 1L,
            inherits(reference, "amelia"), inherits(hybrid, "amelia"),
            isTRUE(all.equal(hybrid$imputations, reference$imputations, tolerance = 1e-6)))
  observed <- !is.na(as.matrix(input))
  stopifnot(all(vapply(hybrid$imputations, function(x) {
    all(is.finite(as.matrix(x))) &&
      identical(unname(as.matrix(x)[observed]), unname(as.matrix(input)[observed]))
  }, logical(1))))
  saveRDS(reference, file.path(directory, "reference.rds"))
  saveRDS(hybrid, file.path(directory, "hybrid.rds"))
  utils::write.csv(hybrid$imputations[[1]], file.path(directory, "completed.csv"), row.names = FALSE)
  stopifnot(identical(readRDS(file.path(directory, "reference.rds")), reference),
            identical(readRDS(file.path(directory, "hybrid.rds")), hybrid),
            isTRUE(all.equal(utils::read.csv(file.path(directory, "completed.csv")),
                             hybrid$imputations[[1]], tolerance = 1e-12)))
  Amelia::compare.density(hybrid, var = "outcome", lwd = 2,
                          main = "Amelia: observed and imputed outcome",
                          xlab = "Synthetic outcome", ylab = "Density")
  graphic_device <- names(grDevices::dev.cur())
  stopifnot(identical(graphic_device, "RStudioGD"))
  grDevices::dev.copy(grDevices::png, filename = file.path(directory, "diagnostic.png"),
                      width = 1200, height = 800, res = 120)
  grDevices::dev.off()
  # RStudio masks View with its own data viewer. utils::View would bypass that
  # integration and ask macOS for the unrelated X11 data editor.
  if (show_data) View(utils::head(hybrid$imputations[[1]], 12),
                      title = "Amelia synthetic completed data")
  meta <- attr(hybrid, "amelia_torch_backend", exact = TRUE)
  stopifnot(isTRUE(meta$converged), identical(meta$device, "cpu"),
            identical(meta$dtype, "float64"), isTRUE(meta$current_call_torch_used),
            identical(meta$current_call_gpu_used, FALSE))
  report <- list(
    schema_version = 1L, interactive = interactive(), rstudio_api_available = TRUE,
    rstudio_version = as.character(rstudioapi::versionInfo()$version),
    R = as.character(getRversion()), system = unname(Sys.info()["sysname"]),
    architecture = unname(Sys.info()["machine"]),
    Amelia = as.character(utils::packageVersion("Amelia")),
    ameliatorch = as.character(utils::packageVersion("ameliatorch")),
    python = as.character(config$version), python_selected_project_venv = TRUE,
    python_display_path = ".venv/bin/python (Windows: .venv/Scripts/python.exe)",
    torch = torch$`__version__`, dimensions = dim(input), m = 3L,
    original_reference_code = reference$code, hybrid_code = hybrid$code,
    same_seed_imputations_match = TRUE, observed_values_unchanged = TRUE,
    completed_values_finite = TRUE, rds_and_csv_readback_passed = TRUE,
    on_screen_graphics_device = graphic_device,
    plot_visual_review = "Pending independent GUI screenshot review; R execution alone does not prove display.",
    output_files = basename(expected_files), backend = meta)
  jsonlite::write_json(report, file.path(directory, "session.json"),
                       auto_unbox = TRUE, pretty = TRUE, digits = NA, null = "null")
  cat("G6 RSTUDIO PASS: installed reference + hybrid CPU64, m=3, 120 rows.\n")
  cat("Python: project .venv interpreter verified; original and hybrid imputations agree.\n")
  cat("Saved and read back RDS + CSV. Diagnostic drawn in RStudio Plots.\n")
  cat("Output: results/local/g6-rstudio; user source tabs and workspace retained.\n")
  invisible(report)
}
