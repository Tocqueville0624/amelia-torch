# G4：原版 CPU 并行过渡路径

2026-09-26，在本机 macOS / R 4.5.3 / Amelia 1.8.3 完成小型真实进程测试。全部沿用官方 R CPU 统计实现；没有修改核心，也没有验证 GPU 多副本调度或测量速度。

- [Python snow2 测试](../../../tests/test_reference_parallel.py)：固定 96×3 数值数据、m=3、seed 9127、`L'Ecuyer-CMRG`，分别通过显式 `r_library`、开发目录默认解析、正常 `R_LIBS_USER` 环境继承调用真实 PSOCK workers。三次插补逐值一致，每份观察值不变、输出有限、EM 收敛，三份插补并非重复同一随机样本。环境继承测试关闭项目库自动发现，没有复制或改写用户 R 安装。
- 同一个 Python 文件用 `incheck=FALSE` 及非法的长度二 `boot.type`，让错误真实发生在 worker 的 `bootx` 内。父进程收到 `nodes produced errors`，Python 抛出 `AmeliaReferenceError`、没有成功结果或伪造 RDS。这不是模拟 subprocess 失败。
- [R supplied-cl 测试](../../../r-package/tests/reference-parallel.R)：调用者创建 2 个 PSOCK worker，确认它们都载入 Amelia 1.8.3，以同样显式 worker stream seed 对照官方 `amelia` 与 `amelia_compat`。完整结果与 worker 随后的 `runif(6)` 逐值一致；前后 worker 身份相同且仍响应，最后由测试调用者关闭 cluster。
- 同一 R 文件在本机 Unix `multicore` 路径使用 2 个 worker、m=3；同 seed 下原版与 reference wrapper 完整结果逐值一致。Windows 分支明确跳过 Unix fork，保留 snow/serial 路线，不将 Windows 的串行回退称为多进程成功。

[R 原始记录](r-parallel.json) 和 [版本/命令/源码哈希](summary.json) 可核验本次结果。Python 两项测试通过，报告为 `2 passed in 1.86s`；时间仅为测试执行时间。初次受限环境禁止本机 server socket，测试未启动；随后获批在允许 localhost sockets 的执行环境实际运行并通过，没有用跳过断言替代通过。

复现：

```sh
.venv/bin/python -m pytest -q tests/test_reference_parallel.py
R_LIBS_USER="$PWD/.R-library" Rscript r-package/tests/reference-parallel.R
```

这些是本机验收。新增并行测试尚未实际通过 Windows/Linux 的新 CI 运行，不能借用此前五个 R 文件的 CPU CI 结果外推。Hybrid 仍明确要求串行副本调度；需要原版并行能力时选择 reference，不会静默切换引擎。
