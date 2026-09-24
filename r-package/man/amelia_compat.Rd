\name{amelia_compat}
\alias{amelia_compat}
\title{Delegate to Official Amelia on the CPU}
\usage{amelia_compat(x, ..., engine = "reference")}
\arguments{
  \item{x}{An input accepted by the official Amelia 1.8.3 \code{Amelia::amelia}
  S3 generic, including an existing Amelia result when its method supports it.}
  \item{...}{Arguments passed unchanged to \code{Amelia::amelia}. Use the
  original R argument names, such as \code{boot.type} and \code{max.resample}.}
  \item{engine}{Currently only \code{"reference"} is implemented. It calls
  the official R package on the CPU, without using the Torch implementation.}
}
\description{Provides a clearly labeled reference entry point with no custom
preprocessing, model changes, Python initialization, or GPU computation. The
installed official R Amelia package performs the entire call.}
\details{The wrapper preserves the original input class and forwards all
arguments to the public S3 generic. Official Amelia handles transformations,
categorical variables, time structure, priors, bounds, existing-result extension,
validation, and random draws. Use \code{set.seed()} to control the original R
random stream. The wrapper does not replace or modify upstream functions.

Exactly Amelia 1.8.3 must already be installed in the selected R library. Missing
or different versions raise a clear error without automatic installation. This
version pin preserves the project's declared reference; future versions are not
assumed equivalent. The result records the verified reference version.
This entry point is a CPU reference route, not an accelerated compatibility engine.}
\value{The official Amelia result with its original fields and class, plus an
\code{amelia_torch_backend} attribute describing the current reference CPU call
and the verified Amelia version. When appending, the metadata records the old
backend, historical and new imputation counts, and the current call separately.
Unknown or GPU history is not relabeled as pure CPU output. The legacy
\code{ameliatorch_backend} input attribute is also recognized. Official return
classes are retained because the output handling was performed by the official
package. Errors and messages originate upstream.}
\examples{
\dontrun{
set.seed(2026)
fit <- amelia_compat(my_data, m = 5, logs = "income", noms = "region")
attr(fit, "ameliatorch_backend")
}}
