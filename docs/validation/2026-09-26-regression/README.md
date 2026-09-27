# Local package regression

[简体中文](README.zh-CN.md) · [Documentation](../../README.md)

2026-09-26, Apple Silicon. The full Python suite passed 235 tests and Ruff; this included three then-uncommitted G7 audit checks, so the count is not assigned to an earlier CI commit. Per-file identities are in checks.json.

A fresh R source tarball ran `R CMD check --no-manual --no-build-vignettes` in a separate temporary directory, including nine R test files: 0 errors/0 warnings/0 notes, Status: OK. Build/check logs replace local paths. Parallel checks executed in a context permitting worker sockets. This is local code/package regression, not new GPU performance, inference or RStudio visual evidence.

## Records

This report describes the dated run and measured source below. Later project status is recorded in the [evidence summary](../2026-09-27-evidence-summary.md).

[checks.json](checks.json) · [build.log](build.log) · [check.log](check.log)
