# G2 MPS32公共边界

[English](accelerator-edges-mps32.md) · [文档目录](../../README.zh-CN.md)

2026-09-26，在 `33220cfeee0ffc262b523adac1bff64dc5a624dc` 的 Mac 已安装Python/R 包执行，八项预设断言通过、exit 0，脚本/阈值未改。七个普通/迭代边界加一个病态案例，不是 33 个 CPU 案例全量复测或CUDA/推断/性能验收。

环境 Mac arm64、R 4.5.3/Amelia 1.8.3/reticulate 1.47.0、Python 3.12.13/Torch 2.14.0。EM 为 MPS32、fallback 0；特征值检查及原版 R 流程仍 CPU。普通 EM 容差 1e−5，theta 和 SD 缩放输出界限 1e−5+1e−4×abs(reference)。

普通 history 一致：identity none 8/8、ordinary 8/9；double none 8/1、ordinary 8/7；integer none 8/8；最少 35、最多 2。最大 theta 差 1.383e−7，缩放输出 2.370e−7（约占对应界限 1.01%）。观察值/掩码/类/别名、可见 seed 及后续 runif/rnorm 通过。两轮例虽原版 code 1，混合正确警告未收敛。

精确共线压力两引擎 300 轮未收敛、code 2。原版 216/217/219/293/296 更新，最终 empri 5、最小特征值−1.6042e−15；MPS103/221/257 更新，empri 3、最小特征值−4.6052e−8、423 次伪逆、31 个拟合模式。轨迹差异保留，不算质量成功。

13 份混合 EM 中 11 收敛，截止/病态两份未收敛；all_checks_passed=true 包含正确失败处理。allthetas oracle 仍 CPU64。checkout 源码前后及 commit 指纹一致，不代表重哈希已安装二进制。未测峰值内存/性能。

## 记录

本报告仅描述上述日期和测量源码对应的运行。后续项目状态见[证据摘要](../2026-09-27-evidence-summary.zh-CN.md)。

[validate_r_accelerator_edges.R](../../../scripts/validate_r_accelerator_edges.R) · [r-accelerator-edges-mps32.json](r-accelerator-edges-mps32.json) · [r-accelerator-edges-mps32.log](r-accelerator-edges-mps32.log) · [r-accelerator-edges-mps32-audit.json](r-accelerator-edges-mps32-audit.json) · [accelerator-edges-mps32-sha256.json](accelerator-edges-mps32-sha256.json)

```sh
R_LIBS_USER="$PWD/.R-library" RETICULATE_PYTHON="$PWD/.venv/bin/python" \
  PYTORCH_ENABLE_MPS_FALLBACK=0 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 \
  MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 \
  Rscript scripts/validate_r_accelerator_edges.R mps float32 \
  results/local/g2-mps-edges-20260926.json
```
