# 代码文档生成 Agent Workflow

SE2026 Homework 2 · 2412190310 李文宇

一个由 **3 个 Agent** 协作的文档生成工作流：读取一个小型 Python 命令行项目，产出带源码证据的 README，并由审核 Agent 独立核对。整个项目只使用 Python 标准库，不需要安装任何第三方包。

## 1. 项目目标

给定一个只读的 Python 项目目录，工作流自动完成：

```text
扫描源码 → 分析事实 → 撰写文档 → 独立审核 → 机械校验
                                      │
                    ┌─────────────────┼─────────────────┐
                    ▼                 ▼                 ▼
                 通过发布         返工一次后复核      保存失败状态
```

- **分析 Agent**：通过只读工具阅读源码，输出带 `file + lines` 证据的事实清单。
- **文档 Agent**：只依据事实清单撰写 README，每条功能/命令都标注事实编号 `[F#]`。
- **审核 Agent**：使用同样的只读工具独立回到源码核对，返回 `pass` 或具体问题。
- **确定性节点**：文件扫描、AST 索引、规则校验由普通程序完成，不包装成 Agent。

## 2. 作业要求对应

| PPT 要求 | 本项目的实现 |
| --- | --- |
| 至少 2 个 Agent 协作 | 3 个独立 Agent：分析、文档、审核 |
| Agent 间消息传递或状态共享 | 共享 `RunState`，下游只读约定字段；每轮交接写入 `trace.jsonl` |
| 顺序执行 | 显式 `Workflow` 节点表 + 边 |
| 条件分支（推荐） | 审核/规则结果决定 `finalize_pass`、`revise` 或 `finalize_fail` |
| 循环（推荐） | 最多返工一次，返工后必须重新审核和校验 |
| 执行日志/状态追踪 | `trace.jsonl`、`state.json`、`review.json`、`drafts/` |
| 错误处理（推荐） | JSON 校验、HTTP/空响应重试、工具轮数上限、可读失败状态 |
| 可扩展性 | 新增节点/Agent/模型适配器不需要重写编排逻辑 |
| 文档 | 本文件 + [DESIGN.md](DESIGN.md) |

## 3. 环境与运行

- Python **3.12.8** 已验证；代码需要 3.11+（使用标准库 `tomllib`）。
- 无第三方依赖，不需要 `pip install`。
- 平台：Windows / Linux / macOS 均可。

### 3.1 Mock 演示（不调用模型，先验证编排）

```bash
cd docgen-workflow

# 一次通过
python -m docgen run --input examples/todo_cli --model mock --scenario pass --out runs/mock-pass

# 首审有问题 → 返工一次 → 通过
python -m docgen run --input examples/todo_cli --model mock --scenario rework --out runs/mock-rework

# 返工后仍失败 → needs_manual_review
python -m docgen run --input examples/todo_cli --model mock --scenario fail --out runs/mock-fail
```

### 3.2 真实模型

复制 `.env.example` 为 `.env`，填写 OpenAI 兼容接口：

```ini
LLM_BASE_URL=https://api.deepseek.com
LLM_API_KEY=你的密钥
LLM_MODEL=deepseek-flash
```

```bash
python -m docgen check-api
python -m docgen run --input examples/todo_cli --model api --out runs/real
```

`.env` 已被 `.gitignore` 忽略，不会提交。密钥只由模型适配器读取，不写入日志或运行产物。

### 3.3 测试

```bash
python -m unittest discover -s tests -v
```

当前 **25 个测试全部通过**，覆盖通过、返工、失败三条路径，以及沙箱、AST、JSON 解析、Agent 输出校验、审核证据落点和模型空响应重试。

## 4. 运行产物

每次运行在 `--out` 目录下生成：

| 文件 | 内容 |
| --- | --- |
| `README.generated.md` | 审核通过后发布的文档 |
| `README.rejected.md` | 未通过时的最后一版草稿（不会冒充成功产物） |
| `analysis.json` | 事实清单、未知项、输入摘要 |
| `review.json` | 审核结论、问题列表、每一轮的审核/规则结果 |
| `state.json` | 完整共享状态快照 |
| `trace.jsonl` | 节点、模型调用、工具调用、路由的逐条日志 |
| `drafts/draft-vN.md` | 每一版草稿，返工过程可直接对比 |
| `manifest.json` | 输入文件清单（大小、行数、sha256） |

## 5. 真实运行结果

`demo/real-deepseek/` 是最终代码的真实端到端运行（DeepSeek `deepseek-flash`）：

- 最终状态：`passed`
- 分析 Agent：16 条带源码证据的事实；调用 7 次只读工具
- 文档 Agent：2 版草稿（首版 → 按审核意见返工）
- 审核 Agent：首轮提出 2 条问题，第二轮独立复核后 `pass`；共 8 次只读工具调用
- 全过程：20 次模型调用、15 次工具调用，`trace.jsonl` 中有逐条记录
- 运行产物：`demo/real-deepseek/README.generated.md`、`analysis.json`、`review.json`、`state.json`、`trace.jsonl`、`drafts/draft-v1.md`、`drafts/draft-v2.md`

另有 `demo/real-deepseek-json/`：**最终代码**的另一次全新真实运行，15 条事实、首轮审核通过、1 版草稿、18 次模型调用、13 次工具调用，`drafts/draft-v1.md` 为草稿快照。两次真实运行均为最终代码，连续运行都 `passed`，分别覆盖“返工后通过”和“首轮通过”两条路径。

复核阶段还运行过允许两次返工的版本：其中一次返工后的草稿出现自相矛盾（同时声称 id 单调增长和会被复用），审核 Agent 拒绝发布，最终状态为 `needs_manual_review`。这是预期的失败关闭行为，不会把有问题的文档标成成功。

`demo/mock-pass/`、`demo/mock-rework/`、`demo/mock-fail/` 是不调用模型的三条固定路径，用来证明条件边、返工和失败状态可重复。

### 人工核验

以下事实已回到源码逐行核对（其余事实可在 `analysis.json` 中按 `file + lines` 复查）：

| 事实 | 陈述要点 | 证据 |
| --- | --- | --- |
| F1 | `python -m todo_cli` 入口和退出码 | `todo_cli/__main__.py:1-6` |
| F7 | `add` 的 ID 生成、保存、输出和退出码 | `todo_cli/cli.py:29-30, 60-66` |
| F9 | `done` 的成功路径 | `todo_cli/cli.py:34-35, 82-86` |
| F10 | `delete` 的实现 | `todo_cli/cli.py:37-38, 88-92` |

早期真实运行曾出现证据行号偏移（工具当时不返回行号，模型只能自行数行）。修正后 `read_file` 返回带真实行号的 `numbered_text`，并在分析提示词中加入“final 前逐条复核行号”的要求；上表数据来自修正后的运行。

## 6. 目录结构

```text
docgen-workflow/
├─ docgen/
│  ├─ __main__.py        # CLI：run / check-api
│  ├─ orchestrator.py    # 节点、边、条件路由
│  ├─ pipeline.py        # 具体流程、状态写入、产物输出
│  ├─ state.py           # 共享 RunState
│  ├─ trace.py           # JSONL 日志
│  ├─ agents/            # 分析、文档、审核 Agent
│  ├─ llm/               # OpenAI 兼容适配器 + Mock 适配器
│  ├─ tools/             # 只读沙箱、文件搜索、AST 索引
│  └─ checks/rules.py    # 确定性规则校验
├─ prompts/              # 三个 Agent 的提示词
├─ examples/todo_cli/    # 演示输入项目（只读）
├─ tests/                # 25 个 unittest
├─ demo/                 # 真实运行 + Mock 三场景产物
├─ DESIGN.md             # 设计文档
├─ .env.example
└─ requirements.txt      # 无第三方依赖
```

## 7. 设计要点

- **固定外层流程，Agent 内部有限自主**：节点顺序和路由由程序控制；Agent 只能在工具调用和内容上决策。
- **事实先行**：文档 Agent 不直接读整个源码自由发挥，而是消费带证据的事实清单；无法确认的内容只能写“待确认”。
- **审核独立且可追溯**：审核 Agent 有自己的提示词和工具循环，必须至少成功调用一次 `read_file` 才能给出结论；每条问题必须引用可解析的 `文件:行号`，源码优先于事实清单措辞。
- **确定性校验独立**：路径、行号、引用编号、必需章节由规则节点检查，避免“模型自审自夸”。
- **有界返工**：默认最多返工一次；返工后仍失败则保存 `needs_manual_review`，不会把未通过文档标成成功。
- **可替换模型**：`ModelAdapter` 接口隔离模型调用；Mock 与 OpenAI 兼容适配器可互换。

更完整的架构、状态字段、Agent 契约、错误路径和扩展方式见 [DESIGN.md](DESIGN.md)。

## 8. 限制

- 输入限定为小型 Python 项目（默认最多 50 个受支持文件、单文件 200 KB），不执行目标代码。
- 只读取 `.py`、`.toml`、`.txt`、`.md`、`.cfg`、`.ini`，忽略 `.venv`、缓存和构建目录。
- 默认只有一次返工；审核标准较严时，一次运行可能以 `needs_manual_review` 结束。可以用 `--max-revisions 2` 再试，或人工修改后重跑。
- 目前不支持并行 Agent 或网页界面；这些是后续扩展点。
- 生成内容仍可能遗漏信息；发布前建议按 `analysis.json` 抽查证据，尤其是命令、参数和限制。
- 真实模型调用会产生费用；Mock 模式完全离线、无费用。
