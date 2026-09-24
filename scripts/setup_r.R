# Run from the project root. Install only into this project's library.
lib <- file.path(getwd(), ".R-library")
dir.create(lib, recursive = TRUE, showWarnings = FALSE)
.libPaths(c(lib, .libPaths()))
packages <- c("Amelia", "reticulate", "jsonlite")
missing <- packages[!vapply(packages, requireNamespace, logical(1), quietly = TRUE)]
if (length(missing)) {
  type <- if (Sys.info()[["sysname"]] == "Darwin" || .Platform$OS.type == "windows") "binary" else "source"
  install.packages(missing, repos = "https://cloud.r-project.org", lib = lib, type = type)
}
stopifnot(all(vapply(packages, requireNamespace, logical(1), quietly = TRUE)))
if (as.character(packageVersion("Amelia")) != "1.8.3") {
  stop("The reference contract requires Amelia 1.8.3. Install that archived version into .R-library before continuing.")
}
for (p in packages) cat(p, as.character(packageVersion(p)), "\n")
