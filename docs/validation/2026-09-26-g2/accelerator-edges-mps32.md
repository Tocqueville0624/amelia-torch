# G2 新增公开边界：本机 MPS float32

2026-09-26，在 `33220cfeee0ffc262b523adac1bff64dc5a624dc` 的已安装 Python/R 包上运行固定 [accelerator edge 脚本](../../../scripts/validate_r_accelerator_edges.R)。八个预定案例的断言全部通过，进程 exit 0；没有修改核心、脚本或门槛。完整[原始 JSON](r-accelerator-edges-mps32.json)、[输出日志](r-accelerator-edges-mps32.log)及[独立审计](r-accelerator-edges-mps32-audit.json)单独保存，旧 CPU64 记录保持不变。

这是七个初值/迭代边界案例加一个病态诊断案例的有限验证，不是 33 个 CPU 案例全部在 GPU 重跑，也不是统计推断质量、性能或 CUDA 验收。

## 冻结门槛与普通边界结果

实际环境：macOS arm64，R 4.5.3、Amelia 1.8.3、ameliatorch 0.0.0.9000、reticulate 1.47.0、Python 3.12.13、Torch 2.14.0。每份公共 hybrid EM 的实际 device/dtype 都为 MPS/float32；fallback=0。特征值检查仍明确使用 CPU，原版 R 的预处理、bootstrap、随机补值及后处理也在 CPU，不声称全部计算在 GPU。

沿用 GPU 执行前固定的 float32 门槛：EM tolerance=1e-5，theta 与按观察值标准差缩放的输出分别要求 `abs(actual-reference) <= 1e-5 + 1e-4*abs(reference)`。两引擎接收独立深拷贝，不让原版 double theta 原位修改污染另一引擎。

| 案例 | m | 原版与 MPS 的迭代数 | 实际结果 |
|---|---:|---|---|
| startvals=1，boot.none | 2 | 8 / 8 | 通过 |
| startvals=1，ordinary | 2 | 8 / 9 | 通过 |
| double 显式 theta，boot.none | 2 | 8 / 1 | 最后 theta 回写，第二份复用；通过 |
| double 显式 theta，ordinary | 2 | 8 / 7 | caller/归档原位更新；通过 |
| integer 显式 theta，boot.none | 2 | 8 / 8 | 初值不回写；通过 |
| emburn 下限 35 | 1 | 35 | 达到指定下限；通过 |
| emburn 上限 2 | 1 | 2 | 明确未收敛、warning/metadata 正确；预期异常断言通过 |

七个案例的完整 iterHist 此次均与原版一致。theta 最大绝对差为 `1.383e-7`，标准化输出最大绝对差为 `2.370e-7`；最大逐格输出误差只占对应预定门槛的约 1.01%。这些是实际有限样例误差，不是新的放宽门槛或所有数据的误差上界。

观察值精确保留、应补值有限、原版 class/缺失位置、每引擎独立 alias 语义、R 可见 `.Random.seed` 和随后 `runif(6)`/`rnorm(6)` 均通过。2 轮上限案例虽然原版仍输出 code 1，hybrid 正确记录 `converged=false` 并发出 `Amelia EM reached emburn maximum before convergence`，不能将其误报为正常收敛。

## 病态 autopri：保留差异与失败

沿用 seed 7 的 200×5 精确共线输入、40% 缺失，拟合 seed 102，boot.none、empri=0、autopri=.05、tolerance=1e-15、emburn=(300,300)。原版与 MPS 均在 300 轮后仍未收敛，最终 code 2，不给出有效插补：

| 引擎 | empri 更新轮次 | 最终 empri | 最小协方差特征值 |
|---|---|---:|---:|
| 原版 R | 216、217、219、293、296 | 5 | −1.6042e-15 |
| MPS float32 hybrid | 103、221、257 | 3 | −4.6052e-8 |

MPS 报告 423 次伪逆使用、31 个拟合缺失模式，明确未收敛 warning；这些诊断全部保留。两个引擎都实际触发了 autopri，但更新时点与次数不同。测试按各自最终 theta 验证原版状态规则、NA 输出和自身 empri/convergence 诊断，**不要求病态轨迹数值等价，也不把这个失败样本算作统计质量成功**。

全部公共调用产生 13 次 hybrid MPS EM，其中 11 次收敛；另外两次分别为预定的 2 轮截止和病态案例。`all_checks_passed=true` 表示预先规定的正常及失败行为检查均通过，绝不表示所有拟合收敛。

## 单列 CPU oracle 与复现边界

脚本附带的内部 allthetas/alias oracle 始终为 **CPU float64**。它此次也通过了初始列保持、最终 alias 和历史比较，但不计入 GPU 覆盖；allthetas 也没有被当成新增公共 amelia 参数。

脚本与四个关键 R/C/Python 源文件的 SHA-256 在运行前后、结果 JSON 和 `33220cf` Git blob 间一致；检查期间没有源码改动。该 fingerprint 描述 checkout，不伪装成对已安装二进制文件的重新哈希。实际 alias/RNG 回归使用了已安装的注册 C helper。

```sh
R_LIBS_USER="$PWD/.R-library" RETICULATE_PYTHON="$PWD/.venv/bin/python" \
  PYTORCH_ENABLE_MPS_FALLBACK=0 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 \
  MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 \
  Rscript scripts/validate_r_accelerator_edges.R mps float32 \
  results/local/g2-mps-edges-20260926.json
```

本次使用可访问 Apple GPU 的普通本机执行权限。复现时选择新的输出文件，保留失败，不覆盖历史报告。没有计时、峰值 RAM/VRAM 测量或模型推断等价声明；这些分别由性能记录与 G5 验收处理。新增文件的[SHA-256 清单](accelerator-edges-mps32-sha256.json)与 CPU 旧清单分开。
