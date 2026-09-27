# Interruption and report persistence

[简体中文](2026-09-26-interruption-records.zh-CN.md) · [Documentation](../README.md)

The 2026-09-26 change affects recording only, preserving EMB, parameters, seeds, synchronization and timing boundaries. Historical Colab measurements remain pinned to 905cc79.

Native reports use complete temporary-JSON replacement after each repeat; write failures retain the previous report. Catchable interruptions and nonserializable/nonfinite summaries become explicit records with seed, original status and cause. Main/hybrid suites save plans before child execution, retain completed tasks and use null for unknown exit codes. Warmups count in “all requested calls succeeded.” New directories are required; no automatic resume is implemented.

Seventeen new injection checks covered interruptions, write failures, bad JSON, nonfinite output and failed warmups. Related 75 checks and Ruff passed implementation/review runs. Final full-suite execution had 260 passing and two sandbox socket failures; those two passed when rerun with localhost sockets permitted. This is 262 checked cases across runs, not one failure-free run or new hosted CI.

Complete same-filesystem replacement and catchable interruptions do not guarantee preservation after SIGKILL, power/disk failure or VM loss. There is no added fsync, background compression, atomic parameter-NPZ saving or automatic recovery. External checkpoints and hash checks remain necessary.

## Records

This report describes the dated run and measured source below. Later project status is recorded in the [evidence summary](2026-09-27-evidence-summary.md).
