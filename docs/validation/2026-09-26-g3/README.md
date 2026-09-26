# G3：Python/R 类型、依赖和会话边界

2026-09-26 在本机 macOS arm64、Python 3.12.13、R 4.5.3、Amelia 1.8.3、PyTorch 2.14.0 下完成 CPU 小例。新增 `tests/test_reference_boundaries.py` 共 **29 项**；与现有 reference 17 项、hybrid 7 项一起运行，**53 passed，0 failed，0 skipped，29.11 秒**。代码版本以 [summary.json](summary.json) 内逐文件 SHA-256 为准，含提交 `fa08a52` 之后未提交的 frontend 修复。

## 实际覆盖

| 边界 | 实测与结果 |
|---|---|
| 全缺失 nullable integer/string ID、非 ASCII 列名/类别、重复 Python index | reference/hybrid 各测纯数值及含 `noms` 两种模型，共 4 例。保存 RDS 后以 R 读取并运行独立原版 Amelia 对照；Python 重新读取同一 RDS。列顺序、类别、观察值与全缺失分析行规则通过。 |
| index 与 RDS 的表示范围 | 同次 Python 返回保留重复 index；RDS 使用唯一的 R 行名，重新读取不伪造 Python 的重复 index 或扩展 dtype。 |
| 不支持的输入 | datetime DataFrame、complex ndarray、混合 object、SciPy sparse 各一例明确报错。Arrow 未单独验收，没有承诺通用 Arrow/扩展类型支持。 |
| 外部 R 类 | 实际原版拟合的 Date ID 与 `custom_measure` 数值 ID：Python view 分别为字符串和普通数值，未声称保留对应 Python 扩展 dtype；`save_rds` 后 R 对完整对象检查 `identical`，原 R 类及属性仍在。 |
| 依赖/设备失败 | 不存在的 Rscript、临时包副本的错误 Amelia 版本、临时 ameliatorch 副本缺少 DLL、子进程缺 Torch、CUDA 不可见均明确失败，无静默设备切换。未更改安装库。 |
| 路径 | 实际建立带中文和空格的 Python venv，并从带中文/空格的 R 库副本加载 Amelia，完成一次 hybrid CPU64 拟合。该 venv 通过 PYTHONPATH 复用现有依赖，不冒称一次干净依赖安装。 |
| GUI 路由 | reference/hybrid 的 True、numpy True、列表、整数、字符串及 opaque RDS frontend 值，在启动 R 前拒绝；`extend`、RDS 输入及 arglist 路径也检查。测试拦截全部子进程启动，因此没有启动 GUI。 |
| 正常 headless 调用 | 显式 `frontend=False` 与省略该参数的结果一致；原版 `amelia_prep` 不从归档 arglist 读取 frontend，带这个无效额外字段也不会创建 GUI 状态。 |

## 发现与修复

真实问题是 Python 入口原来允许 `frontend=True` 到达 R 子进程，而原版前端期待同一 R/Tcl/Tk 会话的 GUI 状态。现在在共同入口 `_invoke` 最前面拒绝非布尔 False 的 frontend，说明需使用原版交互式 `AmeliaView`。此修复只约束会话路由，不修改模型、EM、随机流或抽样。普通 reference、hybrid 和追加的现有回归同时通过。

测试也独立确认了两个原版类型特例：被排除的全 NA integer ID 返回时变成 double；全 NA character ID 在纯数值案例保持 NA，但在本次含 nominal 类别的案例返回整列字符串 `"1"`。这些输出在直接调用未改动的 R Amelia 时相同，没有为了符合测试预期而改写桥接结果。全缺失分析行继续保留 NA。

保留发现过程：[summary.json](summary.json) 记载初次 9 passed/6 failed、修复后 25 passed/2 failed、增加独立 oracle 后 25 passed/4 failed，以及最终 53 passed。前两项真实失败暴露 frontend 路由问题；其他失败分别来自测试遗漏正常 R 依赖库、误认为原版会保留 integer dtype/空字符 ID，以及忽略全缺失分析行。原始失败日志包含本机路径和环境，故不公开；这里只保留原因、计数和最终逐项结果。

最终移除纯 frontend guard 测试不必要的 R 可用性 skip 后，又单独运行全部 10 项：10 passed，19 deselected，0.16 秒。这样即便没有安装 R，GUI 拒绝规则也能被测试。静态检查通过，见 [pytest.txt](pytest.txt)。

## 复现与边界

已安装开发包、R 依赖及 ameliatorch 后，在项目根目录执行：

```sh
python -m pytest -q tests/test_reference_boundaries.py tests/test_reference.py tests/test_hybrid_reference.py
ruff check src/amelia_torch/reference.py tests/test_reference_boundaries.py
```

缺少 Torch 的测试是临时子进程 import 故障注入；独立真实无 Torch 安装证据仍见 [G1 packaging](../2026-09-26-g1/packaging.md)。没有打开或视觉检查 GUI，没有新增 GPU、Windows、Linux 或 Intel Mac 的 G3 实测。先前 [fa08a52 三平台 CI](../2026-09-26-ci/README.md) 不包含这里的后续代码与测试；这份报告不能作为该新修复已跨平台通过的证明，也不代表全部首版验收。
