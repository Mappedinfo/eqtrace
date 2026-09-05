# EqTrace: Executable Equation Contracts for Paper-Code Consistency

作者：Shiqi Wang · 日期：2026-09-05 · 语言：en

论文 + 代码一体模板。核心管线：

```text
code/ 实验代码 -> experiments/results/results.csv
  -> scripts/plot_results.py -> paper/figures/*.pdf -> paper/main.tex
```

## 常用命令

```bash
make all      # 跑实验 -> 生成图 -> 编译论文（xelatex）
make test     # 代码测试
```

## 结构

- `paper/` — LaTeX 论文（Libertinus + Noto CJK 字体基线，`sections/` 分章）
- `code/` — Python 包（src layout，uv 管理，`uv sync && uv run pytest`）
- `experiments/` — 实验产物（results.csv 是论文数字的唯一来源）
- `scripts/` — 管线脚本（跑实验、生成图）

## 铁律

- 论文里的数字不许手填：必须来自 `experiments/results/`；
- 图必须代码根据真实数据绘制；流程图可模型生成（TikZ）；
- 评估器/评测脚本改动走版本记录，论文中注明版本。
