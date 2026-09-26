# Plot the independently audited MCAR intervals, without altering any gates.
# Rscript scripts/plot_inference_summary.R SUMMARY.json OUTPUT_DIRECTORY
args <- commandArgs(trailingOnly = TRUE)
stopifnot(length(args) == 2L)
.libPaths(c(file.path(getwd(), ".R-library"), .libPaths()))
report <- jsonlite::read_json(args[[1]], simplifyVector = FALSE)
stopifnot(isTRUE(report$audit_passed))
rows <- lapply(report$routes, function(x) x$scenarios$mcar)
stopifnot(all(vapply(rows, function(x) !is.null(x$coverage), logical(1))))
labels <- gsub("-", " ", names(rows), fixed = TRUE)
labels[names(rows) == "r-reference"] <- "Original R"
color <- function(passed) if (isTRUE(passed)) "#226955" else "#b64b36"
draw <- function() {
  old <- par(mfrow = c(1, 2), mar = c(5, 8, 5, 1), oma = c(4, 0, 3, 0))
  on.exit(par(old))
  for (paired in c(FALSE, TRUE)) {
    limits <- if (paired) c(-6, 6) else c(89, 100)
    bounds <- if (paired) c(-5, 5) else c(90, 99)
    plot(NA_real_, NA_real_, xlim = limits, ylim = c(length(rows) + .4, .35),
         xlab = if (paired) "Difference (percentage points)" else "Coverage of Rubin 95% intervals (%)",
         ylab = "", yaxt = "n", bty = "l")
    rect(bounds[1], 0, bounds[2], length(rows) + 1, col = "#e8f0ec", border = NA)
    abline(v = if (paired) 0 else 95, col = "#7a828a", lty = 3)
    axis(2, at = seq_along(rows), labels = labels, las = 1, tick = FALSE, cex.axis = .85)
    title(main = if (paired) "Paired difference from original R\nRequired interval inside [-5, +5] pp"
          else "Absolute coverage\nRequired interval inside [90%, 99%]", cex.main = .92)
    for (i in seq_along(rows)) {
      if (paired && names(rows)[i] == "r-reference") {
        text(0, i, "Reference", col = "#7a828a", cex = .9)
        next
      }
      row <- rows[[i]]
      value <- if (paired) row$paired_vs_reference$coverage_difference else row$coverage
      passed <- row$checks[[if (paired) "paired_coverage_difference" else "absolute_coverage"]]
      interval <- unlist(value$interval) * 100
      center <- value$mean * 100
      arrows(interval[1], i, interval[2], i, angle = 90, code = 3, length = .04,
             col = color(passed), lwd = 2)
      points(center, i, pch = 19, col = color(passed), cex = 1.1)
      text(center, i - .18, if (paired) sprintf("%+.1f pp", center) else sprintf("%.1f%%", center),
           cex = .85)
    }
  }
  mtext("MCAR inference validation: retain the prespecified boundary misses", outer = TRUE,
        side = 3, line = .7, cex = 1.2, font = 2)
  mtext("Bars: marginal 90% Monte Carlo intervals. Shading: fixed acceptance bounds.",
        outer = TRUE, side = 1, line = 1, cex = .85)
  mtext("Green/red: this coverage criterion passed/failed. Exact endpoints and other criteria are in the JSON.",
        outer = TRUE, side = 1, line = 2.2, cex = .8)
}
dir.create(args[[2]], recursive = TRUE, showWarnings = FALSE)
grDevices::png(file.path(args[[2]], "mcar-coverage.png"), width = 1800, height = 900, res = 150)
draw()
invisible(grDevices::dev.off())
grDevices::pdf(file.path(args[[2]], "mcar-coverage.pdf"), width = 12, height = 6)
draw()
invisible(grDevices::dev.off())
