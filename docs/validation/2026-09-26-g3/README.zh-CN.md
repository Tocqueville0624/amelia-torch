# G3 类型与会话

[English](README.md) · [文档目录](../../README.zh-CN.md)

2026-09-26，Mac arm64/Python 3.12.13/R 4.5.3/Amelia 1.8.3/Torch 2.14.0，新增 29 项、原 reference 17 和 hybrid 7 项共 53 通过，无跳过，29.11 秒。逐文件哈希固定工作源码，含 fa08a52 之后 frontend 变更。

reference/hybrid 分别执行数值和 noms 模型，含 nullable 空 integer/string ID、Unicode名称/类别和重复Python index；以独立原版 R 及Python读 RDS。同次调用保留重复 index，RDS 读回不伪造Python元数据。外部 Date/自定义数值 ID 在Python为普通字符串/数值，权威 RDS 仍保留 R 类/属性。

datetime、complex、混合 object、sparse 明确拒绝，Arrow 无通用承诺。缺 Rscript、错误 Amelia、缺 hybrid DLL/Torch、CUDA不可见明确失败，不切换设备。临时副本/import 注入不改安装库。中文/空格 venv 及 R 库路径实际完成 hybrid CPU64，依赖通过PYTHONPATH复用，不是干净依赖安装。

修复问题是 frontend=True 可进入缺共享 R/Tcl/Tk 状态的子进程；_invoke 现于启动 R 前拒绝省略/布尔 False 之外的值，含 extend/RDS/arglist。测试拦截进程启动，未打开 GUI；正常 False/默认不变。

独立 R 确认空 integer ID 提升 double，特定 noms 案例空 character ID 返回字符串 1，全空分析行仍 NA。这些是上游结果，不是桥接修正。summary 保留发现过程 9 通过/6 失败、25/2、25/4 及最终 53 通过，区分真实 frontend 缺陷与错误测试假设/库设置。随后独立 10 项 guard 通过，不再因无 R 跳过。本机记录不自动认证后续 hosted 代码，后续 CI 另列。

## 记录

本报告仅描述上述日期和测量源码对应的运行。后续项目状态见[证据摘要](../2026-09-27-evidence-summary.zh-CN.md)。

[summary.json](summary.json) · [pytest.txt](pytest.txt)

```sh
python -m pytest -q tests/test_reference_boundaries.py tests/test_reference.py tests/test_hybrid_reference.py
ruff check src/amelia_torch/reference.py tests/test_reference_boundaries.py
```
