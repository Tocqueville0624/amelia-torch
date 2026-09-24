# Hosted CPU CI verification

All three jobs in [GitHub Actions run 35953184726](https://github.com/Tocqueville0624/amelia-torch/actions/runs/35953184726)
passed at commit [`620213e`](https://github.com/Tocqueville0624/amelia-torch/commit/620213e56866bf83c9f16207a1b8e79654ede03c).
The configured versions were Python 3.12, R 4.5.3, and Amelia 1.8.3.
The run completed on September 24 UTC / September 23 Pacific time, 2026.

| Hosted runner | Python tests | Python lint | R source package installation | Five R test files |
|---|---|---|---|---|
| Windows | 149 passed | Passed | Passed | Passed |
| macOS | 149 passed | Passed | Passed | Passed |
| Ubuntu Linux | 149 passed | Passed | Passed | Passed |

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
version changed. The first [corrected run](https://github.com/Tocqueville0624/amelia-torch/actions/runs/35952792428)
passed 133 Python tests on each platform and completed the five Windows R tests
that the initial failed run had not reached. The latest run above includes the
expanded 149-test suite and retains all five passing R test files per platform.
