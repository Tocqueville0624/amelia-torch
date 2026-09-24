\name{amelia_torch}
\alias{amelia_torch}
\title{Call the Native Amelia Torch Development Implementation}
\usage{amelia_torch(x, m = 5L, device = "cpu", dtype = "float64", seed = NULL, ...)}
\arguments{
  \item{x}{Plain numeric matrix or data frame. Missing values are \code{NA}.}
  \item{m}{Positive integer number of imputations.}
  \item{device}{Explicit backend: \code{"cpu"}, \code{"cuda"}, or \code{"mps"}.}
  \item{dtype}{Explicit precision: \code{"float64"} or \code{"float32"}.}
  \item{seed}{NULL or an exactly represented nonnegative integer below \code{2^53}.}
  \item{...}{Named Python Amelia options. \code{boot.type} and \code{max.resample}
  map to \code{boot_type} and \code{max_resample}; duplicate aliases raise errors.}
}
\description{Calls the matching Python implementation without modifying its algorithm.
This native prototype supports only the features explicitly implemented in Python;
unsupported options raise errors. It is not a complete replacement for official Amelia.}
\details{Python must be selected explicitly before use. R and Python seeds do not
imply identical random draws. Observed values, row names, column names, and input
matrix/data-frame shape are preserved. Data-frame outputs contain numeric columns;
categorical and other classed columns are rejected.}
\section{Wholly missing rows}{As in Amelia, rows with no observed modeled variables
remain missing and are excluded from estimation. The wrapper preserves their
original R \code{NA}/\code{NaN} representation. All other output rows must be finite.}
\value{An \code{ameliatorch_result} list with \code{imputations}, \code{diagnostics},
and any additional Python result fields. This is not the original Amelia return class.}
