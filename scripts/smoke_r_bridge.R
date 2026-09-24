# Open Amelia_Project.Rproj first, or run Rscript from the project root.
.libPaths(c(file.path(getwd(), ".R-library"), .libPaths()))
python <- file.path(getwd(), ".venv", if (.Platform$OS.type == "windows") "Scripts/python.exe" else "bin/python")
stopifnot(file.exists(python))
# Do not normalizePath(python): resolving the venv symlink loses its environment.
Sys.setenv(RETICULATE_PYTHON = python, PYTORCH_ENABLE_MPS_FALLBACK = "0")
reticulate::use_python(python, required = TRUE)
probe <- reticulate::import("amelia_torch.diagnostics")
report <- probe$environment_report()
dir.create("results/local", recursive = TRUE, showWarnings = FALSE)
jsonlite::write_json(report, "results/local/r_bridge.json", auto_unbox = TRUE, pretty = TRUE)
cat("R -> reticulate -> Python -> PyTorch bridge succeeded.\n")
cat("Python:", report$python, "PyTorch:", report$torch, "MPS:", report$mps_available, "CUDA:", report$cuda_available, "\n")
for (device_probe in report$probes) {
  if (!all(vapply(device_probe$operations, function(x) isTRUE(x$ok), logical(1)))) {
    stop(paste("Operator probe failed on", device_probe$device))
  }
}
