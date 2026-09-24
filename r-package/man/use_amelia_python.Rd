\name{use_amelia_python}
\alias{use_amelia_python}
\title{Select an Existing Python Environment}
\usage{use_amelia_python(python = NULL, venv = NULL)}
\arguments{
  \item{python}{Path to an installed Python interpreter.}
  \item{venv}{Path to an existing virtual environment. Supply exactly one argument.}
}
\description{Selects Python explicitly without downloading software or initializing Python.}
\details{Call this function before the first Python operation. An initialized interpreter
cannot be switched without restarting R. Virtual environment symlinks are not dereferenced.
The Python package must already be installed in the chosen environment.}
\value{The selected interpreter path, invisibly.}
