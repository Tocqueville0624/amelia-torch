\name{amelia_torch_compat}
\alias{amelia_torch_compat}
\title{Experimental Original Amelia Pipeline With a PyTorch EM Kernel}
\usage{amelia_torch_compat(x, ..., device = "cpu", dtype = "float64")}
\arguments{
\item{x}{Data accepted by Amelia 1.8.3, or an existing Amelia result.}
\item{...}{Arguments passed to the original Amelia method. Parallel replicate scheduling is not currently supported by this experimental engine.}
\item{device}{Explicit \code{"cpu"}, \code{"cuda"}, or \code{"mps"}.}
\item{dtype}{\code{"float64"} by default; MPS requires explicit \code{"float32"}.}
}
\description{Runs the original Amelia 1.8.3 preprocessing, bootstrap, conditional draws and output handling, substituting the project's PyTorch EM in a private function lookup environment. The Amelia namespace is never modified.}
\details{Select an installed Python environment with \code{use_amelia_python} first. This remains experimental; equivalent floating point results require validation. R still performs substantial work, and MPS also uses CPU eigenvalue checks. For the unmodified original CPU algorithm and parallel scheduling use \code{amelia_compat}. No silent CPU fallback is selected.}
\value{The upstream Amelia result, with an \code{amelia_torch_backend} attribute recording the hybrid engine and EM diagnostics.}
\seealso{\code{amelia_compat}, \code{amelia_torch}, \code{use_amelia_python}}
