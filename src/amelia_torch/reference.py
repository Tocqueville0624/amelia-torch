"""Typed Python access to original and hybrid Amelia 1.8.3 R pipelines.

``amelia_reference`` never invokes PyTorch, CUDA, or MPS. The experimental
``amelia_torch_compat`` substitutes only EM, retaining the R workflow around it.
Neither path implies GPU acceleration. The saved RDS remains authoritative.
Imported results retain recorded provenance; an external RDS without a backend
record has unknown origins even though this bridge's new fits use the CPU.
"""

from __future__ import annotations

import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path
from typing import Any

import numpy as np

_INT_NA = -(2**31)


def _write_binary_column(values, rtype, work, filename):
    """Write one R atomic column with an explicit, endian-independent schema."""
    if rtype == "double":
        array = np.asarray(values, dtype="<f8")
        dtype, size, missing = "float64", 8, "ieee754_nan"
    else:
        cleaned = [_INT_NA if value is None else int(value) for value in values]
        if any(value < _INT_NA or value > 2**31 - 1 for value in cleaned):
            raise ValueError("An integer transport value exceeds the R int32 range")
        array = np.asarray(cleaned, dtype="<i4")
        dtype, size, missing = "int32", 4, "int32_min"
        if rtype == "logical" and not np.isin(array, [0, 1, _INT_NA]).all():
            raise ValueError("Logical transport codes must be 0, 1, or the NA sentinel")
    array.tofile(work / filename)
    return {"format": "binary-column-v1", "filename": filename,
            "dtype": dtype, "byte_order": "little", "itemsize": size,
            "count": len(array), "missing_encoding": missing,
            "missing_sentinel": _INT_NA if dtype == "int32" else None}


def _read_binary_column(column, count, work):
    storage = column["storage"]
    expected = ("float64", 8, "ieee754_nan") if column["type"] == "double" else (
        "int32", 4, "int32_min"
    )
    if (storage.get("format"), storage.get("byte_order")) != ("binary-column-v1", "little"):
        raise AmeliaReferenceError("Unsupported binary-column format or byte order")
    if (storage.get("dtype"), storage.get("itemsize"), storage.get("missing_encoding")) != expected:
        raise AmeliaReferenceError("Binary-column dtype or missing-value encoding mismatch")
    if storage.get("count") != count or (expected[0] == "int32" and storage.get("missing_sentinel") != _INT_NA):
        raise AmeliaReferenceError("Binary-column count or NA sentinel mismatch")
    filename = storage.get("filename")
    if not isinstance(filename, str) or Path(filename).name != filename or filename in {".", ".."}:
        raise AmeliaReferenceError("Binary-column filename must be a local basename")
    path = work / filename
    if not path.is_file() or path.stat().st_size != count * expected[1]:
        raise AmeliaReferenceError("Binary-column byte length does not match its schema")
    array = np.fromfile(path, dtype="<f8" if expected[0] == "float64" else "<i4", count=count)
    if column["type"] == "logical" and not np.isin(array, [0, 1, _INT_NA]).all():
        raise AmeliaReferenceError("Invalid logical code in binary-column result")
    return array


@dataclass(frozen=True)
class RDSValue:
    """Pass an existing R object as an option, e.g. an ``ameliaArgs`` arglist.

    The file is copied into the private temporary call directory. Live R
    connections, PSOCK clusters, and external pointers cannot be transported.
    """

    path: str | os.PathLike[str]


class AmeliaReferenceError(RuntimeError):
    """The R reference engine failed, with its official code when available."""

    def __init__(self, message, *, code=None, details=None, partial_rds=None):
        super().__init__(message)
        self.code = code
        self.details = details or {}
        self.partial_rds = partial_rds


def _write_bytes(path, content, overwrite):
    destination = Path(path).expanduser()
    with destination.open("wb" if overwrite else "xb") as stream:
        stream.write(content)
    return destination


@dataclass
class AmeliaReferenceResult:
    """A Python view of an Amelia-class R result, plus the complete RDS.

    ``imputations`` are NumPy arrays or pandas DataFrames. Altering these Python
    views does not alter the original R object or subsequent ``extend`` calls.
    """

    imputations: tuple[Any, ...]
    metadata: dict[str, Any]
    warnings: tuple[str, ...]
    _rds: bytes = field(repr=False)
    _container: str = field(repr=False)
    _python_schema: dict | None = field(default=None, repr=False)
    _runtime: dict = field(default_factory=dict, repr=False)

    @property
    def engine(self):
        return self.metadata["engine"]

    @property
    def m(self):
        return int(self.metadata["m"])

    def save_rds(self, path, *, overwrite=False):
        """Save the actual Amelia object for ``readRDS`` and official R methods."""
        return _write_bytes(path, self._rds, overwrite)

    def extend(self, m=5, *, seed=None, r_rng_kind=None, timeout=None, **options):
        """Append imputations through the official ``amelia.amelia`` S3 method.

        R 1.8.3 reuses the saved arguments; it does not apply arbitrary new model
        options through ``...``. Only p2s/frontend are accepted here, so changed
        model options cannot appear to work while upstream ignores them.
        """
        unsupported = set(options) - {"p2s", "frontend"}
        if unsupported:
            raise ValueError(
                "Official Amelia append reuses the saved model; new options are not applied: "
                + ", ".join(sorted(unsupported))
            )
        runtime = self._runtime.copy()
        engine = runtime.pop("engine", "reference")
        implementation = amelia_torch_compat if engine == "torch-compat" else amelia_reference
        return implementation(
            self,
            m=m,
            seed=seed,
            r_rng_kind=r_rng_kind,
            timeout=timeout,
            **runtime,
            **options,
        )


def _pandas():
    try:
        import pandas as pd
    except ImportError as error:
        raise ImportError(
            "pandas is required for typed DataFrame/factor results; install amelia-torch[reference]"
        ) from error
    return pd


def _numeric_value(value):
    if value is None:
        return None
    if isinstance(value, (np.integer, int)) and not isinstance(value, (bool, np.bool_)):
        integer = int(value)
        if abs(integer) > 2**53:
            raise ValueError("R numeric transport cannot exactly represent integers beyond 2**53")
        return integer
    number = float(value)
    if math.isnan(number):
        return None
    if math.isinf(number):
        return "Inf" if number > 0 else "-Inf"
    return number


def _vector_type(values):
    present = [value for value in values if value is not None]
    if not present:
        return "double"
    if all(isinstance(value, (bool, np.bool_)) for value in present):
        return "logical"
    if all(isinstance(value, (str, np.str_)) for value in present):
        return "character"
    if all(isinstance(value, (int, np.integer, float, np.floating)) for value in present):
        integers = all(isinstance(value, (int, np.integer)) for value in present)
        if integers and all(-(2**31) < int(value) < 2**31 for value in present):
            return "integer"
        return "double"
    raise TypeError("R atomic vectors must have a common numeric, logical, or string type")


def _vector_values(values, rtype):
    if rtype in {"integer", "double"}:
        return [_numeric_value(value) for value in values]
    if rtype == "logical":
        return [None if value is None else bool(value) for value in values]
    return [None if value is None else str(value) for value in values]


def _encode_data(data, work):
    schema = None
    if type(data).__module__.split(".")[0] == "pandas":
        pd = _pandas()
        if not isinstance(data, pd.DataFrame):
            raise TypeError("Pass a pandas DataFrame, not a Series")
        names = list(map(str, data.columns))
        if len(set(names)) != len(names):
            raise ValueError("DataFrame column names must remain unique when converted to R strings")
        encoded_columns = []
        schema = {"index": data.index.copy(), "columns": data.columns.copy(), "categories": {}}
        for position in range(data.shape[1]):
            column = data.iloc[:, position]
            name = names[position]
            missing = column.isna().to_numpy()
            if isinstance(column.dtype, pd.CategoricalDtype):
                categories = list(column.cat.categories)
                levels = list(map(str, categories))
                if len(set(levels)) != len(levels):
                    raise ValueError("Distinct category labels cannot map to the same R factor level")
                codes = column.cat.codes.to_numpy(dtype=np.int32).copy() + 1
                codes[missing] = _INT_NA
                encoded = {
                    "name": name, "type": "factor",
                    "storage": _write_binary_column(codes, "factor", work,
                                                     f"input-column-{position:06d}.bin"),
                    "levels": levels, "ordered": bool(column.cat.ordered),
                }
                schema["categories"][position] = categories
            else:
                values = [None if absent else value for value, absent in zip(column, missing)]
                if pd.api.types.is_bool_dtype(column.dtype):
                    rtype = "logical"
                elif pd.api.types.is_integer_dtype(column.dtype):
                    rtype = _vector_type(values) if any(value is not None for value in values) else "integer"
                elif pd.api.types.is_float_dtype(column.dtype):
                    rtype = "double"
                elif isinstance(column.dtype, pd.StringDtype):
                    rtype = "character"
                elif pd.api.types.is_datetime64_any_dtype(column.dtype):
                    raise TypeError("Datetime columns need explicit numeric/string conversion for Amelia")
                else:
                    rtype = _vector_type(values)
                encoded = {"name": name, "type": rtype}
                if rtype == "character":
                    encoded["values"] = _vector_values(values, rtype)
                else:
                    encoded["storage"] = _write_binary_column(
                        _vector_values(values, rtype), rtype, work,
                        f"input-column-{position:06d}.bin",
                    )
            encoded_columns.append(encoded)
        row_names = list(map(str, data.index))
        # R requires unique row names; local Python index metadata restores even
        # duplicate/MultiIndex labels without introducing them as model columns.
        if len(set(row_names)) != len(row_names):
            row_names = None
        payload = {
            "container": "data_frame", "nrow": len(data),
            "columns": encoded_columns, "row_names": row_names,
        }
        return payload, "pandas", schema
    array = np.asarray(data)
    if array.ndim != 2 or array.dtype.kind not in "biuf":
        raise TypeError("Pass a two-dimensional numeric ndarray or a pandas DataFrame")
    columns = []
    for position in range(array.shape[1]):
        values = array[:, position].tolist()
        rtype = _vector_type(values)
        columns.append({"name": None, "type": rtype, "storage": _write_binary_column(
            _vector_values(values, rtype), rtype, work, f"input-column-{position:06d}.bin",
        )})
    return {"container": "matrix", "nrow": len(array), "columns": columns,
            "row_names": None}, "numpy", None


def _encode_option(value, work, counter):
    if isinstance(value, RDSValue):
        source = Path(value.path).expanduser()
        if not source.is_file():
            raise FileNotFoundError("The RDS option file does not exist")
        target = work / f"option-{counter[0]}.rds"
        counter[0] += 1
        shutil.copyfile(source, target)
        return {"kind": "rds", "filename": target.name}
    if value is None:
        return {"kind": "null"}
    if isinstance(value, dict):
        if not all(isinstance(key, str) for key in value):
            raise TypeError("R named-list keys must be strings")
        return {"kind": "list", "items": {
            key: _encode_option(item, work, counter) for key, item in value.items()
        }}
    if isinstance(value, np.ndarray):
        if value.ndim == 0:
            value = value.item()
        elif value.ndim > 2:
            raise TypeError("Use an RDSValue for an R array with more than two dimensions")
        else:
            value = value.tolist()
    if isinstance(value, (tuple, list)):
        if value and all(isinstance(row, (tuple, list)) for row in value):
            widths = {len(row) for row in value}
            if len(widths) == 1:
                flat = [item for row in value for item in row]
                rtype = _vector_type(flat)
                return {"kind": "matrix", "type": rtype,
                        "nrow": len(value), "ncol": widths.pop(),
                        "values": _vector_values(flat, rtype)}
        rtype = _vector_type(value)
        return {"kind": "vector", "type": rtype, "values": _vector_values(value, rtype)}
    rtype = _vector_type([value])
    return {"kind": "scalar", "type": rtype, "values": _vector_values([value], rtype)}


def _decode_data(encoded, container, schema, work):
    columns = encoded["columns"]
    count = encoded["nrow"]
    if not isinstance(count, int) or count < 0:
        raise AmeliaReferenceError("Invalid row count in R transport schema")
    if container == "auto":
        container = "pandas" if encoded["container"] == "data_frame" else "numpy"
    if container == "numpy":
        if any(column["type"] in {"factor", "character"} for column in columns):
            raise TypeError("Categorical/string R data require return_type='pandas'")
        arrays = []
        for column in columns:
            values = _read_binary_column(column, count, work)
            if column["type"] != "double":
                missing = values == _INT_NA
                if missing.any():
                    values = values.astype(np.float64)
                    values[missing] = np.nan
                elif column["type"] == "logical":
                    values = values.astype(bool)
            arrays.append(values)
        return np.column_stack(arrays)
    pd = _pandas()
    decoded = []
    for position, column in enumerate(columns):
        kind = column["type"]
        values = column["values"] if kind == "character" else _read_binary_column(column, count, work)
        if len(values) != count:
            raise AmeliaReferenceError("Column value count does not match the row count")
        if kind == "factor":
            categories = column["levels"]
            if schema is not None and position in schema.get("categories", {}):
                original = schema["categories"][position]
                lookup = dict(zip(map(str, original), original))
                if all(level in lookup for level in categories):
                    categories = [lookup[level] for level in categories]
            missing = values == _INT_NA
            if ((values[~missing] < 1) | (values[~missing] > len(categories))).any():
                raise AmeliaReferenceError("Factor code is outside the recorded level range")
            codes = values.astype(np.int64) - 1
            codes[missing] = -1
            decoded.append(pd.Series(pd.Categorical.from_codes(
                codes, categories=categories, ordered=column["ordered"],
            )))
        elif kind == "integer":
            missing = values == _INT_NA
            array = pd.array(values, dtype="Int64")
            array[missing] = pd.NA
            decoded.append(pd.Series(array) if missing.any() else pd.Series(values.astype(np.int64)))
        elif kind == "logical":
            missing = values == _INT_NA
            array = pd.array(values == 1, dtype="boolean")
            array[missing] = pd.NA
            decoded.append(pd.Series(array) if missing.any() else pd.Series(values.astype(bool)))
        elif kind == "double":
            decoded.append(pd.Series(np.asarray(values, dtype=np.float64)))
        else:
            decoded.append(pd.Series(values, dtype="object"))
    frame = pd.concat(decoded, axis=1)
    frame.columns = [column["name"] for column in columns]
    if encoded.get("row_names") is not None:
        frame.index = encoded["row_names"]
    if schema is not None:
        if len(schema["index"]) == len(frame):
            frame.index = schema["index"].copy()
        if len(schema["columns"]) == frame.shape[1]:
            frame.columns = schema["columns"].copy()
    return frame


def _runtime_environment(rscript, r_library):
    executable = shutil.which(os.path.expanduser(os.fspath(rscript or "Rscript")))
    if executable is None:
        raise AmeliaReferenceError("Rscript was not found; install R or supply rscript explicitly")
    # subprocess runs inside a temporary directory. Resolve an explicit relative
    # executable (or relative PATH entry) before changing that working directory.
    executable = str(Path(executable).resolve())
    environment = os.environ.copy()
    if r_library is not None:
        paths = [r_library] if isinstance(r_library, (str, os.PathLike)) else list(r_library)
    else:
        # Source-checkout convenience only. Wheels use the user's normal R
        # library unless an explicit r_library is provided.
        development = Path(__file__).resolve().parents[2] / ".R-library"
        paths = [development] if (development / "Amelia").is_dir() else []
    if paths:
        expanded = [str(Path(path).expanduser().resolve()) for path in paths]
        if not all(Path(path).is_dir() for path in expanded):
            raise AmeliaReferenceError("An explicitly configured R library directory does not exist")
        existing = environment.get("R_LIBS_USER")
        environment["R_LIBS_USER"] = os.pathsep.join(expanded + ([existing] if existing else []))
    return executable, environment


def _sanitize(message, work):
    return str(message).replace(str(work), "<temporary>").replace(str(Path.home()), "<home>")


def _invoke(*, x, input_rds, operation, m, seed, r_rng_kind, rscript, r_library,
            timeout, return_type, options, engine="reference", device="cpu", dtype="float64"):
    if "frontend" in options and (
        not isinstance(options["frontend"], (bool, np.bool_)) or bool(options["frontend"])
    ):
        raise ValueError(
            "The Python subprocess bridge requires frontend=False; frontend=True needs "
            "the original AmeliaView GUI in an interactive R/Tcl/Tk session. "
            "This bridge cannot control or attach to that GUI session."
        )
    if return_type not in {"auto", "numpy", "pandas"}:
        raise ValueError("return_type must be auto, numpy, or pandas")
    if x is not None and input_rds is not None:
        raise ValueError("Provide either x or input_rds")
    if x is None and input_rds is None:
        raise ValueError("Provide x or an input_rds containing an official R object")
    if seed is not None and (
        isinstance(seed, bool) or int(seed) != seed or not 0 <= seed <= 2**31 - 1
    ):
        raise ValueError("R seed must be an integer between 0 and 2**31-1")
    if operation != "inspect" and (isinstance(m, bool) or int(m) != m or m < 1):
        raise ValueError("m must be a positive integer")
    executable, environment = _runtime_environment(rscript, r_library)
    if engine == "torch-compat":
        # Preserve the virtual-environment executable path; resolving its symlink
        # would select the base interpreter and lose this package installation.
        environment["RETICULATE_PYTHON"] = sys.executable
    with tempfile.TemporaryDirectory(prefix="amelia-reference-") as directory:
        work = Path(directory)
        schema, inferred = None, "auto"
        request = {"schema_version": 2, "operation": operation, "required_version": "1.8.3",
                   "engine": engine, "device": device, "dtype": dtype,
                   "m": int(m), "seed": None if seed is None else int(seed),
                   "rng_kind": [r_rng_kind] if isinstance(r_rng_kind, str) else r_rng_kind}
        if isinstance(x, AmeliaReferenceResult):
            (work / "input.rds").write_bytes(x._rds)
            request["input_rds"] = "input.rds"
            request["historical_metadata"] = x.metadata
            schema, inferred = x._python_schema, x._container
            ignored = set(options) - {"p2s", "frontend"}
            if ignored:
                raise ValueError("Appending an Amelia result reuses saved model arguments; new model options are not supported")
        elif input_rds is not None:
            source = Path(input_rds).expanduser()
            if not source.is_file():
                raise FileNotFoundError("The input RDS file does not exist")
            shutil.copyfile(source, work / "input.rds")
            request["input_rds"] = "input.rds"
        else:
            request["data"], inferred, schema = _encode_data(x, work)
        option_counter = [0]
        request["options"] = {
            name: _encode_option(value, work, option_counter)
            for name, value in options.items()
        }
        container = inferred if return_type == "auto" else return_type
        request_path = work / "request.json"
        response_path = work / "response.json"
        output_rds = work / "result.rds"
        request_path.write_text(json.dumps(request, allow_nan=False), encoding="utf-8")
        resource = resources.files("amelia_torch").joinpath("_r/reference_bridge.R")
        with resources.as_file(resource) as bridge:
            try:
                completed = subprocess.run(
                    [executable, "--vanilla", str(bridge), str(request_path),
                     str(response_path), str(output_rds)],
                    env=environment, cwd=work, capture_output=True, text=True,
                    encoding="utf-8", errors="replace", timeout=timeout, check=False,
                )
            except subprocess.TimeoutExpired as error:
                raise AmeliaReferenceError("The R Amelia call exceeded the explicit timeout") from error
        if not response_path.is_file():
            output = _sanitize(completed.stderr or completed.stdout, work).strip()
            raise AmeliaReferenceError(f"The R reference process failed before returning a result: {output}")
        response = json.loads(response_path.read_text(encoding="utf-8"))
        if not response.get("ok") or completed.returncode:
            failure = response.get("error", {})
            message = _sanitize(failure.get("message") or "R reference execution failed", work)
            raise AmeliaReferenceError(
                message, code=failure.get("code"),
                details={"engine": "r-amelia-torch-em" if engine == "torch-compat" else "r-amelia-reference",
                         "kind": failure.get("kind")},
                partial_rds=output_rds.read_bytes() if output_rds.is_file() else None,
            )
        warnings = tuple(_sanitize(message, work) for message in response.get("warnings", []))
        imputations = tuple(_decode_data(item, container, schema, work) for item in response["imputations"])
        return AmeliaReferenceResult(
            imputations=imputations, metadata=response["metadata"], warnings=warnings,
            _rds=output_rds.read_bytes(), _container=container, _python_schema=schema,
            _runtime={"rscript": rscript, "r_library": r_library,
                      **({"engine": engine, "device": device, "dtype": dtype}
                         if engine == "torch-compat" else {})},
        )


def amelia_reference(x=None, m=5, *, input_rds=None, seed=None, r_rng_kind=None,
                     rscript=None, r_library=None, timeout=None, return_type="auto", **options):
    """Call unmodified R Amelia 1.8.3, preserving its CPU statistical workflow.

    Model arguments (e.g. logs/noms/ords/priors/bounds/ts/cs) are passed directly
    to Amelia for validation. R row/column indices remain 1-based. Use
    ``**{"boot.type": "none"}`` for an R argument containing a dot.
    ``frontend`` may only be omitted or False: an isolated subprocess cannot
    participate in the original AmeliaView R/Tcl/Tk GUI session.

    NumPy arrays return NumPy arrays. pandas DataFrames preserve factor levels
    and orderedness, numeric/logical/string columns, labels, and missingness as
    returned by R. Integer columns may become double when Amelia imputes them.
    Set r_rng_kind="L'Ecuyer-CMRG" for R's reproducible PSOCK worker streams.
    Neither a shared seed nor this engine implies equivalence to PyTorch RNGs.
    """
    return _invoke(x=x, input_rds=input_rds, operation="fit", m=m, seed=seed,
                   r_rng_kind=r_rng_kind, rscript=rscript, r_library=r_library,
                   timeout=timeout, return_type=return_type, options=options)


def read_reference_rds(path, *, rscript=None, r_library=None, timeout=None, return_type="auto"):
    """Read an existing official Amelia RDS without fitting or changing it.

    R factors/ordered levels and row names survive RDS. Python-only index or
    label classes are not stored in the official R object; reloaded labels follow
    their R representation. Use return_type='numpy' for numeric results without
    the optional pandas dependency.
    """
    return _invoke(x=None, input_rds=path, operation="inspect", m=1, seed=None,
                   r_rng_kind=None, rscript=rscript, r_library=r_library,
                   timeout=timeout, return_type=return_type, options={})


def amelia_torch_compat(x=None, m=5, *, input_rds=None, seed=None, r_rng_kind=None,
                        device="cpu", dtype="float64", rscript=None, r_library=None,
                        timeout=None, return_type="auto", **options):
    """Run the original R pipeline with only EM delegated to PyTorch.

    This experimental hybrid requires the installed ``ameliatorch`` R package,
    Amelia 1.8.3, and PyTorch in the calling Python interpreter. Preprocessing,
    bootstrap, RNG, conditional draws and postprocessing remain on the R CPU.
    Replicate scheduling is serial. CPU float64 is the default; MPS explicitly
    requires dtype="float32". No speed advantage is implied by choosing a GPU.

    Original R option names and 1-based indices are preserved. ``extend`` keeps
    this execution engine and its explicit device/dtype configuration.
    """
    if device not in {"cpu", "cuda", "mps"}:
        raise ValueError("device must be cpu, cuda, or mps")
    if dtype not in {"float64", "float32"}:
        raise ValueError("dtype must be float64 or float32")
    if device == "mps" and dtype == "float64":
        raise ValueError("MPS does not support float64; explicitly choose float32 or use CPU")
    return _invoke(x=x, input_rds=input_rds, operation="fit", m=m, seed=seed,
                   r_rng_kind=r_rng_kind, rscript=rscript, r_library=r_library,
                   timeout=timeout, return_type=return_type, options=options,
                   engine="torch-compat", device=device, dtype=dtype)
