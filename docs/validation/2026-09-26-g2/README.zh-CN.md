# G2 公共 CPU64 边界

[English](README.md) · [文档目录](../../README.zh-CN.md)

2026-09-26，Apple Silicon/R 4.5.3/Python 3.12.13/Torch 2.14.0/Amelia 1.8.3：33 个公共边界、七个 R 文件及 26 项Python reference/public/hybrid 通过。仅有界正确性，不是 GPU 性能/推断。

## 初值语义

原版 startval 直接返回合法 theta，C++无复制访问 double 内存并回写终值。此前混合只返回新 theta，未更新调用者/归档/后续副本状态。注册 C helper 现保留该行为，先存allthetas初列；integer 保留原整数 buffer，完整 bootstrap 忽略且不改 theta。原生Python仍不改输入，无 RNG 或 EM 公式变化。

80×3、seed 77、tolerance 1e−6、autopri 0、m2 时，原版/混合轮数一致：double/none 为 10,1；integer/none 10,10；double/ordinary 10,9；integer/ordinary 9,11。默认/identity、别名、arglist/追加及后续 runif/rnorm 也匹配。

## 其他边界

最少 35/最多 2 轮 history 一致；即使原版 code 1，截止元数据/警告明确未收敛。24×2 固定 bootstrap 实际抽成完整样本（样本 cov、NA history、不回写）；另一例实际拒绝空列后接受第二次 draw。私有记录器不额外耗 RNG、不改 namespace，与未插桩调用一致。

全空行保持 NA；完整输入默认 code 39 及关闭检查后的特例、空列/常量/样本量 code 4/43/34、窄 bounds [100,100.001]实际九格夹值、max.resample 0 为 code 52 均匹配。incheck=False、collect=True、p2s=1/2 保留统计行为，进度标明 Torch，保留原版校验消耗 RNG。

## 病态 autopri

独立 seed 7、200×5 精确共线、40%缺失，移除空行后 n197。boot.none、startvals 1、empri 0、autopri=0.05、tolerance 1e−15、emburn 300/300：原版在 216/217/219/293/296 轮更新至 5，混合 216/217/219 至 3。八次同引擎单步重放以<1e−10验证固定初始 hold 0，与错误的当前 empri ridge 公式至少相差约.00488。

原版最终 code 2，混合 code 1 但正确记录/警告未收敛，不是插补质量等价。其他BLAS可能未触发，须记部分覆盖。后续 MPS 边界另列，新增CUDA脚本未执行。历史 downstream 测试哈希早于 R_TESTS 修订，实际修订版见 G1 打包记录。

## 记录

本报告仅描述上述日期和测量源码对应的运行。后续项目状态见[证据摘要](../2026-09-27-evidence-summary.zh-CN.md)。

[public-edge-cases.R](../../../r-package/tests/public-edge-cases.R) · [public-edge-cases.json](public-edge-cases.json) · [r-tests.json](r-tests.json) · [summary.json](summary.json) · [autopri-boundary.R](../../../r-package/tests/autopri-boundary.R) · [public-autopri.json](public-autopri.json)

```sh
R_LIBS_USER="$PWD/.R-library" R CMD INSTALL --clean --library=.R-library r-package
R_LIBS_USER="$PWD/.R-library" RETICULATE_PYTHON="$PWD/.venv/bin/python" \
  OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 \
  Rscript r-package/tests/public-edge-cases.R
.venv/bin/python -m pytest -q tests/test_hybrid_reference.py tests/test_reference.py tests/test_public_reference.py
```
