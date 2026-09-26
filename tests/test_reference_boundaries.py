"""Bounded G3 Python/R type, dependency and session boundaries.

No graphical session is opened. The frontend test blocks all subprocess launches
so a missing rejection cannot accidentally start Tcl/Tk. Dependency probes only
alter temporary package copies or a child process, never installed libraries.
"""

import json
import os
import shutil
import subprocess
import sys
import sysconfig
from pathlib import Path

import numpy as np
import pytest

from amelia_torch import amelia_reference, amelia_torch_compat, read_reference_rds
from amelia_torch.reference import (
    AmeliaReferenceError,
    AmeliaReferenceResult,
    RDSValue,
    _runtime_environment,
)

ROOT = Path(__file__).resolve().parents[1]
requires_r = pytest.mark.skipif(shutil.which("Rscript") is None, reason="Requires installed R")


def _numeric_data():
    data = np.random.default_rng(901).normal(size=(72, 3))
    data[::8, 0] = np.nan
    data[::11, 2] = np.nan
    return data


def _run_r(tmp_path, code, *arguments, r_library=None):
    executable, environment = _runtime_environment(None, r_library)
    environment.pop("R_TESTS", None)
    script = tmp_path / "fixture.R"
    script.write_text(code, encoding="utf-8")
    return subprocess.run(
        [executable, "--vanilla", str(script), *map(str, arguments)],
        env=environment, check=True, capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=30,
    )


def _copy_installed_r_package(tmp_path, package, library):
    discovered = _run_r(
        tmp_path,
        'cat(jsonlite::toJSON(find.package(commandArgs(trailingOnly=TRUE)[[1]]), '
        'auto_unbox=TRUE))\n',
        package,
    )
    source = Path(json.loads(discovered.stdout))
    library.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, library / package)
    return library / package


def _library_search(tmp_path, first):
    # Explicit r_library replaces checkout convenience. Retain the original
    # visible libraries after the fault-injected/path-probe package copy.
    discovered = _run_r(tmp_path, 'cat(jsonlite::toJSON(.libPaths()))\n')
    return [str(first), *json.loads(discovered.stdout)]


@requires_r
@pytest.mark.parametrize("implementation", [amelia_reference, amelia_torch_compat])
@pytest.mark.parametrize("nominal", [False, True])
def test_nullable_empty_ids_unicode_and_duplicate_index_actual_rds_roundtrip(
    tmp_path, implementation, nominal
):
    pd = pytest.importorskip("pandas")
    n = 90
    rng = np.random.default_rng(902)
    data = pd.DataFrame({
        "空整数ID": pd.array([None] * n, dtype="Int64"),
        "空文本ID": pd.array([None] * n, dtype="string"),
        "数值甲": rng.normal(size=n),
        "结果": rng.normal(size=n),
        "类别": pd.Categorical(np.tile(["北方", "南方", "東方"], n // 3)),
    })
    data.loc[::7, "数值甲"] = np.nan
    data.loc[::9, "结果"] = np.nan
    data.loc[::11, "类别"] = np.nan
    if not nominal:
        data = data.drop(columns="类别")
    data.index = pd.Index([f"重复{i // 2}" for i in range(n)], name="样本")
    result = implementation(
        data, m=1, seed=903, p2s=0, idvars=["空整数ID", "空文本ID"],
        timeout=30, **({"noms": ["类别"]} if nominal else {}),
    )
    completed = result.imputations[0]
    pd.testing.assert_index_equal(completed.index, data.index)
    pd.testing.assert_index_equal(completed.columns, data.columns)
    # Original Amelia converts even excluded integer IDs to double. Preserve
    # that returned R type instead of claiming the input Int64 dtype survived.
    assert str(completed["空整数ID"].dtype) == "float64"
    assert completed["空整数ID"].isna().all()
    if nominal:
        # An independent official R call below verifies this upstream quirk:
        # with noms, an all-NA excluded character column becomes string "1".
        assert (completed["空文本ID"] == "1").all()
        pd.testing.assert_index_equal(completed["类别"].cat.categories, data["类别"].cat.categories)
    else:
        assert completed["空文本ID"].isna().all()
    analytical_columns = ["数值甲", "结果"] + (["类别"] if nominal else [])
    blank_rows = data[analytical_columns].isna().all(axis=1).to_numpy()
    np.testing.assert_array_equal(
        completed[analytical_columns].isna().to_numpy(),
        np.repeat(blank_rows[:, None], len(analytical_columns), axis=1),
    )
    for name in analytical_columns:
        observed = data[name].notna().to_numpy()
        pd.testing.assert_series_equal(completed[name].iloc[observed], data[name].iloc[observed])
    saved = result.save_rds(tmp_path / "类型 往返.rds")
    checked = _run_r(tmp_path, r'''
args <- commandArgs(trailingOnly=TRUE)
fit <- readRDS(args[[1]])
x <- fit$imputations[[1]]
nominal <- identical(args[[2]], "TRUE")
stopifnot(typeof(x[[1]]) == "double", typeof(x[[2]]) == "character",
          all(is.na(x[[1]])),
          !anyDuplicated(rownames(x)))
if (nominal) stopifnot(all(x[[2]] == "1"), is.factor(x[[5]])) else
  stopifnot(all(is.na(x[[2]])))
# Recover the original input, including its original integer ID type, and
# independently rerun unmodified Amelia rather than assuming these quirks.
raw <- x
is.na(raw) <- fit$missMatrix
raw[[1]] <- rep(NA_integer_, nrow(raw))
set.seed(903)
original <- Amelia::amelia(raw, m=1, p2s=0, idvars=names(raw)[1:2],
                            noms=if (nominal) names(raw)[5] else NULL)
stopifnot(isTRUE(all.equal(original$imputations, fit$imputations, tolerance=1e-6)))
cat("R ID atomic types, factors and unique row names verified\n")
''', saved, "TRUE" if nominal else "FALSE")
    assert "verified" in checked.stdout
    restored = read_reference_rds(saved, timeout=30)
    # The in-memory Python index is preserved, but duplicate Python labels do
    # not become duplicate R row.names or persist as Python metadata in RDS.
    assert restored.imputations[0].index.is_unique
    assert list(restored.imputations[0].index) == [str(i + 1) for i in range(n)]
    pd.testing.assert_frame_equal(
        restored.imputations[0].reset_index(drop=True), completed.reset_index(drop=True)
    )


@requires_r
@pytest.mark.parametrize("kind", ["datetime", "complex", "mixed_object", "scipy_sparse"])
def test_out_of_contract_input_types_are_rejected_explicitly(kind):
    pd = pytest.importorskip("pandas")
    if kind == "datetime":
        data = pd.DataFrame({"date": pd.date_range("2020-01-01", periods=3), "a": [1, 2, 3]})
        message = "Datetime.*explicit"
    elif kind == "complex":
        data = np.array([[1 + 2j, 2], [3, 4]])
        message = "two-dimensional numeric ndarray"
    elif kind == "mixed_object":
        data = pd.DataFrame({"mixed": [1, "two", {"nested": 3}], "a": [1, 2, 3]})
        message = "common numeric, logical, or string"
    else:
        from scipy import sparse

        data = sparse.csr_matrix(np.eye(3))
        message = "two-dimensional numeric ndarray"
    with pytest.raises(TypeError, match=message):
        amelia_reference(data, m=1, p2s=0, timeout=10)


@requires_r
def test_external_date_and_custom_r_classes_keep_authoritative_rds_not_python_dtype(tmp_path):
    pd = pytest.importorskip("pandas")
    source = tmp_path / "external-classed.rds"
    _run_r(tmp_path, r'''
args <- commandArgs(trailingOnly=TRUE)
set.seed(904)
data <- data.frame(date=as.Date("2020-01-01") + 0:59,
                   custom=structure(seq_len(60) / 10, class="custom_measure"),
                   a=rnorm(60), b=rnorm(60), y=rnorm(60))
data$y[seq(3, 60, 8)] <- NA_real_
fit <- Amelia::amelia(data, m=1, idvars=c("date", "custom"), p2s=0)
stopifnot(inherits(fit$imputations[[1]]$date, "Date"),
          inherits(fit$imputations[[1]]$custom, "custom_measure"))
saveRDS(fit, args[[1]])
''', source)
    loaded = read_reference_rds(source, timeout=30)
    view = loaded.imputations[0]
    assert not pd.api.types.is_datetime64_any_dtype(view["date"].dtype)
    assert view["date"].iloc[0] == "2020-01-01"
    assert pd.api.types.is_float_dtype(view["custom"].dtype)
    np.testing.assert_allclose(view["custom"], np.arange(1, 61) / 10, rtol=0, atol=0)
    copied = loaded.save_rds(tmp_path / "preserved.rds")
    _run_r(tmp_path, r'''
args <- commandArgs(trailingOnly=TRUE)
original <- readRDS(args[[1]])
returned <- readRDS(args[[2]])
stopifnot(identical(original, returned),
          inherits(returned$imputations[[1]]$date, "Date"),
          inherits(returned$imputations[[1]]$custom, "custom_measure"))
''', source, copied)


def test_missing_rscript_explains_install_or_explicit_path(tmp_path):
    with pytest.raises(AmeliaReferenceError, match="install R or supply rscript"):
        amelia_reference(_numeric_data(), m=1, rscript=tmp_path / "missing-Rscript")


@requires_r
def test_wrong_amelia_version_in_temporary_library_is_rejected(tmp_path):
    library = tmp_path / "wrong-version-library"
    copied = _copy_installed_r_package(tmp_path, "Amelia", library)
    _run_r(tmp_path, r'''
args <- commandArgs(trailingOnly=TRUE)
metadata <- file.path(args[[1]], "Meta", "package.rds")
value <- readRDS(metadata)
value$DESCRIPTION["Version"] <- "0.0.0"
saveRDS(value, metadata)
description <- read.dcf(file.path(args[[1]], "DESCRIPTION"))
description[1, "Version"] <- "0.0.0"
write.dcf(description, file.path(args[[1]], "DESCRIPTION"))
''', copied)
    with pytest.raises(AmeliaReferenceError, match="requires Amelia 1.8.3 exactly; found 0.0.0"):
        amelia_reference(_numeric_data(), m=1, p2s=0,
                         r_library=_library_search(tmp_path, library), timeout=15)


@requires_r
def test_missing_hybrid_dll_in_temporary_copy_reports_install_requirement(tmp_path):
    library = tmp_path / "broken-dll-library"
    copied = _copy_installed_r_package(tmp_path, "ameliatorch", library)
    native_libraries = [p for p in (copied / "libs").rglob("*")
                        if p.suffix in {".so", ".dll", ".dylib"}]
    assert native_libraries
    for path in native_libraries:
        path.rename(path.with_suffix(path.suffix + ".disabled"))
    with pytest.raises(AmeliaReferenceError, match="requires the installed ameliatorch R package"):
        amelia_torch_compat(_numeric_data(), m=1, p2s=0,
                           r_library=_library_search(tmp_path, library), timeout=15)


@requires_r
def test_unavailable_cuda_is_explicit_and_does_not_fallback(monkeypatch):
    # A fresh R/reticulate process sees no CUDA devices, including on CUDA CI.
    monkeypatch.setenv("CUDA_VISIBLE_DEVICES", "")
    with pytest.raises(AmeliaReferenceError, match="CUDA is not available"):
        amelia_torch_compat(_numeric_data(), m=1, p2s=0, device="cuda", timeout=30)


@requires_r
def test_missing_torch_in_child_reports_module_requirement(tmp_path, monkeypatch):
    # Fault injection is scoped to child imports, not a claimed clean machine
    # without Torch. A separate reference-only wheel environment is documented.
    blocker = tmp_path / "dependency-probe"
    blocker.mkdir()
    (blocker / "torch.py").write_text("raise ModuleNotFoundError(\"No module named 'torch'\")\n")
    previous = os.environ.get("PYTHONPATH", "")
    monkeypatch.setenv("PYTHONPATH", os.pathsep.join([str(blocker), previous]))
    with pytest.raises(AmeliaReferenceError, match="No module named 'torch'"):
        amelia_torch_compat(_numeric_data(), m=1, p2s=0, timeout=30)


@requires_r
def test_unicode_space_python_and_r_library_paths_execute_actual_hybrid(tmp_path):
    library = tmp_path / "R library 空格"
    _copy_installed_r_package(tmp_path, "Amelia", library)
    environment_root = tmp_path / "Python 环境 with spaces"
    subprocess.run(
        [sys.executable, "-m", "venv", "--without-pip", str(environment_root)],
        check=True, capture_output=True, text=True, timeout=30,
    )
    executable = environment_root / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    environment = os.environ.copy()
    # Reuse installed test dependencies without downloading or claiming this
    # path-handling test is a clean dependency installation.
    environment["PYTHONPATH"] = os.pathsep.join([str(ROOT / "src"), sysconfig.get_path("purelib")])
    program = tmp_path / "run-hybrid.py"
    program.write_text(
        "import sys,json\n"
        "import numpy as np\n"
        "from amelia_torch import amelia_torch_compat\n"
        "assert 'Python 环境 with spaces' in sys.executable\n"
        "data=np.random.default_rng(905).normal(size=(60,3))\n"
        "data[::7,0]=np.nan\n"
        "fit=amelia_torch_compat(data,m=1,seed=906,p2s=0,r_library=json.loads(sys.argv[1]),timeout=30)\n"
        "assert fit.metadata['call_device']=='cpu' and fit.metadata['call_torch_used'] is True\n"
        "assert np.isfinite(fit.imputations[0]).all()\n"
        "print('Unicode and space interpreter/library paths verified')\n",
        encoding="utf-8",
    )
    completed = subprocess.run(
        [str(executable), str(program), json.dumps(_library_search(tmp_path, library))],
        env=environment,
        check=True, capture_output=True, text=True, encoding="utf-8", timeout=45,
    )
    assert "paths verified" in completed.stdout


@pytest.mark.parametrize("implementation", [amelia_reference, amelia_torch_compat])
@pytest.mark.parametrize("frontend", [True, np.bool_(True), [True], 1, "TRUE"])
def test_frontend_true_rejected_before_starting_any_r_process(
    monkeypatch, implementation, frontend
):
    def no_process_allowed(*args, **kwargs):
        pytest.fail("frontend=True reached subprocess launch; GUI session boundary is not rejected")

    monkeypatch.setattr(subprocess, "run", no_process_allowed)
    with pytest.raises((ValueError, AmeliaReferenceError), match="frontend|GUI|interactive"):
        implementation(_numeric_data(), m=1, p2s=0, frontend=frontend, timeout=1)


@pytest.mark.parametrize("engine", ["reference", "torch-compat"])
def test_frontend_rejection_applies_to_result_extend_and_saved_rds(monkeypatch, tmp_path, engine):
    def no_process_allowed(*args, **kwargs):
        pytest.fail("GUI frontend must be rejected before starting a subprocess")

    monkeypatch.setattr(subprocess, "run", no_process_allowed)
    result = AmeliaReferenceResult(
        imputations=(), metadata={"m": 1}, warnings=(), _rds=b"not read for rejection",
        _container="numpy", _runtime={"engine": engine},
    )
    with pytest.raises(ValueError, match="interactive R/Tcl/Tk"):
        result.extend(m=1, frontend=True)
    implementation = amelia_torch_compat if engine == "torch-compat" else amelia_reference
    with pytest.raises(ValueError, match="interactive R/Tcl/Tk"):
        implementation(input_rds=tmp_path / "not-read.rds", frontend=True)
    with pytest.raises(ValueError, match="interactive R/Tcl/Tk"):
        implementation(_numeric_data(), arglist=RDSValue(tmp_path / "not-read.rds"), frontend=True)
    # Opaque RDS values cannot smuggle the GUI flag past the scalar front door.
    with pytest.raises(ValueError, match="interactive R/Tcl/Tk"):
        implementation(_numeric_data(), frontend=RDSValue(tmp_path / "not-read.rds"))


@requires_r
@pytest.mark.parametrize("implementation", [amelia_reference, amelia_torch_compat])
def test_frontend_false_preserves_original_flow_and_archived_arglist_is_not_gui_state(
    tmp_path, implementation
):
    data = _numeric_data()
    options = {"m": 1, "seed": 907, "p2s": 0, "timeout": 30}
    ordinary = implementation(data, **options)
    explicit = implementation(data, frontend=False, **options)
    np.testing.assert_array_equal(explicit.imputations[0], ordinary.imputations[0])
    saved = ordinary.save_rds(tmp_path / "headless.rds")
    arglist = tmp_path / "arguments.rds"
    _run_r(tmp_path, r'''
args <- commandArgs(trailingOnly=TRUE)
archive <- readRDS(args[[1]])$arguments
# This extra archive field is ignored by original amelia_prep, which never
# imports frontend from ameliaArgs. It cannot attach to an R GUI session.
archive$frontend <- TRUE
saveRDS(archive, args[[2]])
''', saved, arglist)
    reused = implementation(data, arglist=RDSValue(arglist), frontend=False, **options)
    np.testing.assert_array_equal(reused.imputations[0], ordinary.imputations[0])
