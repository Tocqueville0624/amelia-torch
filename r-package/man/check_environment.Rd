\name{check_environment}
\alias{check_environment}
\title{Probe an Explicitly Selected Numerical Backend}
\usage{check_environment(device = "cpu", dtype = "float64")}
\arguments{
  \item{device}{One of \code{"cpu"}, \code{"cuda"}, or \code{"mps"}.}
  \item{dtype}{One of \code{"float64"} or \code{"float32"}. MPS requires float32.}
}
\description{Runs the Python package's small operator checks on the requested device.
This is an environment check, not an imputation correctness or speed benchmark.}
\details{First select Python with \code{use_amelia_python} or \code{RETICULATE_PYTHON}.
Unavailable backends and failed operations raise errors; no fallback is selected.}
\value{A named list describing the requested device, precision, and operator results.}
