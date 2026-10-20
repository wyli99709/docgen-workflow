# 演示运行产物

这些目录是从实际运行中保留下来的证据，不需要联网即可查看。

**先看可视化报告**：打开 [index.html](index.html)，或直接打开：

- [real-deepseek/report.html](real-deepseek/report.html)：返工后通过的真实运行
- [real-deepseek-json/report.html](real-deepseek-json/report.html)：首轮通过的真实运行
- [mock-fail/report.html](mock-fail/report.html)：返工后仍失败

报告页展示执行路径、审核问题、事实证据、工具调用和原始产物链接。它是从 JSON/JSONL 生成的静态查看页，不是工作流的一部分，也不能用来重新运行流程。

测试样例在 [`../examples/todo_cli/`](../examples/todo_cli)：5 个 Python 文件加 `pyproject.toml`，入口为 `todo_cli/cli.py`。

| 目录 | 类型 | 结果 | 关键证据 |
| --- | --- | --- | --- |
| `real-deepseek/` | 真实模型（最终代码） | passed，16 条事实，1 次返工 | `drafts/draft-v1.md` 与 `draft-v2.md`；`review.json` 的两轮 review/rules；`trace.jsonl` 中 20 次模型调用、15 次工具调用 |
| `real-deepseek-json/` | 真实模型（最终代码） | passed，15 条事实，0 次返工 | `drafts/draft-v1.md`；18 次模型调用、13 次工具调用 |
| `mock-pass/` | 离线 Mock | passed，0 次返工 | 三条路径的基准 |
| `mock-rework/` | 离线 Mock | passed，1 次返工 | `drafts/draft-v1.md` 与 `draft-v2.md` 可对比 |
| `mock-fail/` | 离线 Mock | needs_manual_review | `README.rejected.md`、`review.json` 中的两轮问题 |

说明：

- `real-deepseek/` 包含 `drafts/draft-v1.md` 和 `draft-v2.md`，可直接对比返工前后。
- 真实运行的 `state.json` 中 `input_dir` / `output_dir` 已改写为仓库相对路径，避免提交个人电脑的绝对路径。
- `.env`、密钥和模型推理原文不在产物中；`trace.jsonl` 只记录耗时、字符数和 token usage。

查看某次运行的摘要：

```bash
python - <<'PY'
import json
from pathlib import Path
p = Path('demo/real-deepseek')
state = json.loads((p / 'state.json').read_text(encoding='utf-8'))
print(state['status'], len(state['facts']), state['revision_count'])
print(json.loads((p / 'review.json').read_text(encoding='utf-8'))['rounds'])
PY
```
