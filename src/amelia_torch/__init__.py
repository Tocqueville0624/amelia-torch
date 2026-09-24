"""Amelia compatibility interfaces and experimental PyTorch numerical kernels.

PyTorch is loaded only when a native function is requested. The original-R
compatibility path can therefore run on platforms without a supported torch wheel.
"""

from importlib import import_module

__version__ = "0.0.1.dev0"
_EXPORTS = {
    "AmeliaInputError": (".api", "AmeliaInputError"),
    "amelia": (".api", "amelia"),
    "em_fit": (".em", "em_fit"),
    "resolve_backend": (".backends", "resolve_backend"),
    "amelia_reference": (".reference", "amelia_reference"),
    "amelia_torch_compat": (".reference", "amelia_torch_compat"),
    "AmeliaReferenceResult": (".reference", "AmeliaReferenceResult"),
    "AmeliaReferenceError": (".reference", "AmeliaReferenceError"),
    "RDSValue": (".reference", "RDSValue"),
    "read_reference_rds": (".reference", "read_reference_rds"),
}
__all__ = list(_EXPORTS)


def __getattr__(name):
    if name not in _EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, attribute = _EXPORTS[name]
    try:
        result = getattr(import_module(module_name, __name__), attribute)
    except ModuleNotFoundError as error:
        if error.name == "torch":
            raise ImportError(
                "This function requires PyTorch. Install a wheel suitable for your platform "
                "using the official PyTorch selector, or use amelia_reference with R."
            ) from error
        raise
    globals()[name] = result
    return result
