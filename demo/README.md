# 演示运行产物

这些目录是从实际运行中保留下来的证据，不需要联网即可查看。

| 目录 | 类型 | 结果 | 关键证据 |
| --- | --- | --- | --- |
| `real-deepseek/` | 真实模型（最终代码） | passed，16 条事实，1 次返工 | `drafts/draft-v1.md` 与 `draft-v2.md`；`review.json` 的两轮 review/rules；`trace.jsonl` 中 20 次模型调用、15 次工具调用 |
| `real-deepseek-json/` | 真实模型（最终代码） | passed，15 条事实，0 次返工 | `drafts/draft-v1.md`；18 次模型调用、13 次工具调用 |
| `mock-pass/` | 离线 Mock | passed，0 次返工 | 三条路径的基准 |
| `mock-rework/` | 离线 Mock | passed，1 次返工 | `drafts/draft-v1.md` 与 `draft-v2.md` 可对比 |
| `mock-fail/` | 离线 Mock | needs_manual_review | `README.rejected.md`、`review.json` 中的两轮问题 |

说明：

- `real-deepseek/` 生成于加入草稿快照功能之前，所以没有 `drafts/` 目录；返工过程仍可从 `review.json` 的 `rounds` 和 `trace.jsonl` 的两次 `writer` 调用中看到。
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
