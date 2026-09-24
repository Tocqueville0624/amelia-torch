# Lightweight regression checks for actual device opening and safe publication.
# Rscript tests/test_plot_devices.R; no benchmark/imputation is executed.
expressions <- parse(file = "scripts/plot_benchmarks.R")
for (expression in expressions) {
  if (is.call(expression) && identical(expression[[1L]], as.name("<-")) &&
      is.symbol(expression[[2L]]) &&
      as.character(expression[[2L]]) %in% c("validate_file", "render_file")) {
    eval(expression)
  }
}
scratch <- tempfile("plot-devices-")
dir.create(scratch)
original <- getwd()
setwd(scratch)
prefix <- file.path(scratch, "checked")
draw <- function() plot(1, 1, xlab = "Fixture x", ylab = "Fixture y")
expect_error <- function(code, message) {
  error <- tryCatch({ force(code); NULL }, error = identity)
  stopifnot(inherits(error, "error"), grepl(message, conditionMessage(error), fixed = TRUE))
}
tryCatch({
  before <- dev.list()
  expect_error(render_file("pdf", "fake-silent-device", function(path) NULL),
               "did not actually open")
  stopifnot(identical(before, dev.list()), !file.exists("Rplots.pdf"),
            !file.exists(paste0(prefix, ".pdf")))
  expect_error(render_file("pdf", "fake-warning-device", function(path) warning("mock DLL")),
               "mock DLL")
  stopifnot(identical(before, dev.list()), !file.exists("Rplots.pdf"))
  expect_error(render_file("pdf", "fake-partial-device", function(path) {
    pdf(path); stop("mock failure after opening")
  }), "mock failure after opening")
  stopifnot(identical(before, dev.list()), !file.exists(paste0(prefix, ".pdf")))
  valid <- render_file("pdf", "base-R-pdf", function(path) pdf(path))
  stopifnot(valid$format == "pdf", valid$bytes > 100, file.exists(paste0(prefix, ".pdf")))
  original_md5 <- tools::md5sum(paste0(prefix, ".pdf"))
  expect_error(render_file("pdf", "base-R-pdf", function(path) pdf(path)), "overwriting")
  stopifnot(identical(original_md5, tools::md5sum(paste0(prefix, ".pdf"))),
            identical(before, dev.list()), !file.exists("Rplots.pdf"))
  writeBin(charToRaw(paste(rep("not an image", 20), collapse = "")), "bad.png")
  expect_error(validate_file("bad.png", "png"), "declared graphics format")
  stopifnot(!length(list.files(scratch, pattern = "^\\.benchmark-plot-", all.files = TRUE)))
  cat("Plot device regression checks: PASS\n")
}, finally = {
  setwd(original)
  unlink(scratch, recursive = TRUE)
})
