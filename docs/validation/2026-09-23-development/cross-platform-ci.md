# Hosted CPU CI verification

All three jobs in [GitHub Actions run 35952792428](https://github.com/Tocqueville0624/amelia-torch/actions/runs/35952792428)
passed at commit [`6d707a3`](https://github.com/Tocqueville0624/amelia-torch/commit/6d707a329239777a7bebed8375e702b5e77ddb72).
The configured versions were Python 3.12, R 4.5.3, and Amelia 1.8.3.
The run completed on September 24 UTC / September 23 Pacific time, 2026.

| Hosted runner | Python tests | Python lint | R source package installation | Five R test files |
|---|---|---|---|---|
| Windows | 133 passed | Passed | Passed | Passed |
| macOS | 133 passed | Passed | Passed | Passed |
| Ubuntu Linux | 133 passed | Passed | Passed | Passed |

The R tests cover the native Python bridge, official CPU reference delegation,
hybrid CPU EM, backend provenance, and downstream workflows/random-stream
regressions. The complete portable status, exact commit, job links, and checked
test filenames are recorded in [cross-platform-ci.json](cross-platform-ci.json).

This is actual hosted CPU execution evidence. It does not validate CUDA, MPS,
the user's physical RTX 3080 machine, every operating-system version, or full
Amelia compatibility. These CI runs are not performance benchmarks.

The [first run](https://github.com/Tocqueville0624/amelia-torch/actions/runs/35952331765)
passed on macOS and Ubuntu. Windows passed 132 Python tests and failed one
path-resolution test because its placeholder executable lacked a Windows
executable suffix. The fixture now uses `.exe` on Windows and is only looked up,
never executed. No statistical algorithm, numerical tolerance, or reference
version changed. The corrected run also completed the five Windows R tests that
the initial failed run had not reached.
