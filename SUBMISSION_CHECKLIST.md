# SE2026 Homework 2 提交清单

> 课程：SE2026 · Homework 2  
> 学号姓名：2412190310 李文宇  
> 截止时间：2026-10-25 24:00

## 1. PPT 要求对照

| PPT 要求 | 本项目实现 | 可检查证据 |
| --- | --- | --- |
| 至少 2 个 Agent 协作 | 3 个：分析、文档、审核 | `docgen/agents/`、`prompts/` |
| Agent 间消息传递/状态共享 | 共享 `RunState`，每轮写入 JSON | `state.json`、`analysis.json`、`trace.jsonl` |
| 支持顺序执行 | 固定节点表和边 | `docgen/orchestrator.py`、`docgen/pipeline.py` |
| 条件分支/循环（推荐） | 审核/规则结果决定发布、返工、失败 | `review.json` 的 `rounds`；`demo/mock-rework/` |
| 执行日志/状态追踪（推荐） | JSONL 逐条记录节点、模型、工具、路由 | `trace.jsonl`、`state.json` |
| 错误处理（推荐） | HTTP/空响应重试、JSON 校验、轮数上限、失败关闭 | `docgen/llm/`、`docgen/agents/base.py`、`tests/` |
| 可扩展性 | 节点、Agent、模型适配器分离 | `DESIGN.md` 第 12 节 |
| 文档 | README、设计文档、演示产物 | `README.md`、`DESIGN.md`、`Desgin.md`、`demo/` |

对应评分：流程完整性 40%、Agent 协作 30%、可扩展性 20%、文档 10%。

## 2. 提交物

| 提交物 | 位置 | 说明 |
| --- | --- | --- |
| 源代码仓库 | 本目录 `docgen-workflow/` | 已初始化本地 Git，`main` 分支，可推送到 GitHub/Gitee |
| 项目说明 | `README.md` | 安装、配置、运行、产物、演示和限制 |
| 设计文档 | `DESIGN.md` | 流程图、State、Agent 契约、错误路径、测试、扩展方式 |
| 设计文档入口 | `Desgin.md` | 对应 PPT 中的拼写，指向 `DESIGN.md` |
| 备份压缩包 | `../2412190310李文宇.zip` | 小于 200 MB，提交到课程平台 `002Homework2` |
| 演示视频（可选） | 未录制 | 可用第 5 节的 1 分钟脚本自行录制 |

## 3. 推送到 GitHub/Gitee

在 `docgen-workflow` 目录执行：

```bash
cd "C:\Users\liwen\Desktop\Homework 2\docgen-workflow"

git status
git remote add origin <你的仓库地址>
git push -u origin main
```

注意：

- `.env` 已被 `.gitignore` 忽略，**不要** `git add -f .env`。
- 仓库中不应出现 API 密钥。
- 推送前可执行 `git status --short` 确认工作区干净。
- 提交历史可用 `git log --oneline` 查看；至少包含基础工作流、重试/审核加固、静态报告三次提交。

## 4. 课程平台提交

把以下文件上传到 `002Homework2`：

```text
C:\Users\liwen\Desktop\Homework 2\2412190310李文宇.zip
```

压缩包已排除 `.env`、`.git`、`runs/` 和缓存文件，包含源码、测试、文档和 `demo/` 演示产物。如果平台只接受 `.rar`，用压缩工具重新打包时保持同样的排除规则即可。

## 5. 可选：1 分钟演示视频脚本

| 时间 | 画面与讲解 |
| --- | --- |
| 0:00–0:10 | 打开 `README.md`，说明这是 3 个 Agent 的文档生成 Workflow |
| 0:10–0:25 | 运行 `python -m docgen run --input examples/todo_cli --model mock --scenario rework --out runs/demo` |
| 0:25–0:40 | 打开 `demo/real-deepseek/report.html`，展示执行路径和审核问题 |
| 0:40–0:52 | 打开 `review.json` 或报告页，说明“首轮问题 → 返工 → 第二轮通过” |
| 0:52–1:00 | 运行 `python -m unittest discover -s tests`，说明 25 个测试通过 |

## 6. 提交前检查

- [x] `python -m unittest discover -s tests` 通过（25 个测试）
- [x] `demo/real-deepseek/` 是最终代码的真实运行，状态 `passed`
- [x] `demo/mock-pass/rework/fail` 覆盖三条路径
- [x] `README.md`、`DESIGN.md`、`Desgin.md` 可打开
- [x] `.env` 未进入 Git，未进入压缩包
- [x] 压缩包小于 200 MB
- [ ] 推送到 GitHub/Gitee（由你完成）
- [ ] 上传备份包到 `002Homework2`（由你完成）
- [ ] 可选视频（由你决定是否录制）
