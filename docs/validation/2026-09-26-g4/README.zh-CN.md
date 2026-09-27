# G4 原版并行

[English](README.md) · [文档目录](../../README.zh-CN.md)

2026-09-26，Mac/R 4.5.3/Amelia 1.8.3，实际小进程检查保留原版 CPU 统计实现，不改核心、不测 GPU 调度或速度。

Python snow2使用 96×3、m3、seed 9127、L'Ecuyer-CMRG，通过显式 r_library、项目默认发现、继承 R_LIBS_USER 三路线（继承例关闭自动发现）。三次逐值一致、观察值保留、输出有限且收敛，插补副本并非重复。incheck=False 下非法长度二 boot.type 实际触发 worker bootx 错误，传播AmeliaReferenceError，不伪造成功 RDS。

R 调用者持有两 worker PSOCK cluster，与原版完整结果及后续 runif(6)一致，worker 身份和存活保持，最终由 caller 关闭。Unix multicore 2、m3 与原版一致；Windows 明确跳过 fork、用 snow/serial，混合仍串行、不静默切引擎。

Python两项 1.86 秒通过，只是测试时长。初始受限环境在执行前阻止 localhost socket，允许 socket 的环境随后实际运行。本页为本机记录，后续三平台 CI 另有证据。

## 记录

本报告仅描述上述日期和测量源码对应的运行。后续项目状态见[证据摘要](../2026-09-27-evidence-summary.zh-CN.md)。

[test_reference_parallel.py](../../../tests/test_reference_parallel.py) · [reference-parallel.R](../../../r-package/tests/reference-parallel.R) · [r-parallel.json](r-parallel.json) · [summary.json](summary.json)

```sh
.venv/bin/python -m pytest -q tests/test_reference_parallel.py
R_LIBS_USER="$PWD/.R-library" Rscript r-package/tests/reference-parallel.R
```
