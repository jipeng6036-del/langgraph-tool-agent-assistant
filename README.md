# Tool Agent Assistant

一个基于 LangGraph 的工具调用型 Agent 助手项目，用于学习和实践 Agent Loop、Tool Calling、工具失败处理、用户确认、状态保存和后续评测等核心工程能力。

本项目不以 RAG 检索为核心，而是重点关注 Agent 如何根据用户任务选择工具、执行工具、处理文件读写，并在涉及写入操作时进行用户确认。

---

## 一、项目简介

Tool Agent Assistant 是一个面向 Agent 工程学习的实验项目。

系统基于 LangGraph 构建单智能体工作流，通过 Streamlit 提供可视化页面，支持用户输入自然语言任务，由 Agent 自动判断任务类型，并调用对应工具完成操作。

当前版本已支持：

- 查看 `workspace` 目录文件
- 读取 `.txt` / `.md` 文件
- 根据已有文件生成新 Markdown 文件
- 写文件前要求用户确认
- 用户确认后才真正写入文件
- 保存最近一次 Agent 执行状态

---

## 二、项目目标

本项目主要用于学习以下 Agent 工程能力：

- Agent Loop：理解 Agent 如何从用户输入到规划、执行、反馈
- Tool Calling：让 Agent 根据任务调用不同工具
- 工具失败处理：对文件不存在、路径非法、格式不支持等情况进行处理
- 用户确认：写文件等高风险操作必须经过用户确认
- 状态保存：将最近一次执行状态保存到本地 JSON 文件
- 后续评测：为后续构建 Agent 评测集打基础

---

## 三、当前版本

当前项目版本：

```text
Tool Agent 1.1
```

版本能力：

```text
Tool Agent 1.0：文件查看、文件读取、基础写入确认、状态保存
Tool Agent 1.1：新增 read_then_write 复合流程，支持根据源文件生成目标文件，并在写入前等待用户确认
```

---

## 四、功能特性

### 1. 查看工作目录文件

用户可以输入：

```text
查看 workspace 里有哪些文件
```

Agent 会调用：

```text
list_files_tool
```

并返回 `workspace` 目录下的文件列表。

---

### 2. 读取文件内容

用户可以输入：

```text
读取 notes.md
```

Agent 会调用：

```text
read_file_tool
```

读取 `workspace/notes.md` 文件内容，并生成简洁回答。

---

### 3. 根据文件生成新文件

用户可以输入：

```text
请根据 notes.md 的内容生成 summary.md
```

Agent 会执行复合流程：

```text
读取 notes.md
↓
根据 notes.md 内容生成 summary.md 内容
↓
进入待确认写入状态
↓
用户点击确认后写入 summary.md
```

该流程对应：

```text
read_then_write
```

---

### 4. 写文件前用户确认

当 Agent 判断任务涉及写文件时，不会直接写入，而是先生成待写入内容，并在页面中展示：

```text
待确认写入操作
文件名
待写入内容预览
确认写入文件按钮
```

用户点击确认后，系统才会真正调用：

```text
write_file_tool
```

完成文件写入。

---

### 5. 状态保存

每次 Agent 执行后，系统会将最近一次状态保存到：

```text
memory/session_state.json
```

状态内容包括：

```text
user_input
tool_action
tool_file_name
target_file_name
tool_result
final_answer
need_confirmation
pending_file_name
pending_content
```

这样可以观察 Agent Loop 的执行过程，也方便后续做会话恢复和评测分析。

---

## 五、技术栈

- Python
- Streamlit
- LangGraph
- LangChain
- langchain-openai
- DeepSeek API
- python-dotenv
- JSON 状态保存

---

## 六、系统流程

```text
用户输入任务
↓
planning_node 解析任务意图
↓
判断工具动作
↓
tool_node 执行工具
↓
如需写入文件，则进入用户确认流程
↓
answer_node 生成最终回答
↓
保存 Agent 状态
↓
页面展示结果
```

---

## 七、Agent 工作流

当前 LangGraph 工作流由三个核心节点组成：

```text
planning_node
↓
tool_node
↓
answer_node
↓
END
```

### planning_node

负责根据用户输入判断需要执行的工具动作。

支持的动作包括：

```text
list_files
read_file
write_file
read_then_write
chat
```

### tool_node

负责执行工具调用。

例如：

- `list_files`：查看文件列表
- `read_file`：读取文件
- `write_file`：进入待确认写入流程
- `read_then_write`：先读源文件，再生成目标文件内容，并等待用户确认

### answer_node

负责根据工具结果生成用户可读回答，并保存当前 Agent 状态。

---

## 八、工具列表

当前工具定义在：

```text
tools.py
```

### list_files_tool

功能：

```text
列出 workspace 目录下的文件
```

### read_file_tool

功能：

```text
读取 workspace 目录下的 .txt / .md 文件
```

限制：

```text
只能读取 workspace 目录内的文件
只支持 .txt 和 .md 文件
```

### write_file_tool

功能：

```text
写入 .txt / .md 文件到 workspace 目录
```

限制：

```text
只能写入 workspace 目录内的文件
只支持 .txt 和 .md 文件
写入前必须经过用户确认
```

---

## 九、安全设计

为了避免 Agent 误读写系统文件，项目中加入了路径限制：

```text
所有文件操作只能发生在 workspace 目录内
```

如果用户尝试访问上级目录或系统路径，系统会拒绝操作。

这体现了 Agent 工具调用中的一个重要原则：

```text
工具能力必须有边界，不能让模型随意操作系统文件
```

---

## 十、项目结构

```text
tool_agent_assistant
├── app.py                 # Streamlit 页面入口
├── agent.py               # LangGraph Agent 工作流
├── tools.py               # 本地文件工具函数
├── README.md              # 项目说明
├── requirements.txt       # Python 依赖
├── .env.example           # 环境变量示例
├── .gitignore             # Git 忽略配置
├── workspace/             # Agent 可操作的工作目录
│   ├── notes.md
│   └── summary.md
└── memory/                # 状态保存目录
    └── session_state.json
```

---

## 十一、环境变量配置

项目根目录新建 `.env` 文件：

```env
OPENAI_API_KEY=your_api_key_here
OPENAI_BASE_URL=https://api.deepseek.com
MODEL_NAME=deepseek-chat
```

说明：

```text
.env 文件包含 API Key，不应提交到 GitHub
.env.example 用于展示配置格式，可以提交
```

---

## 十二、运行方式

### 1. 创建虚拟环境

```bash
python -m venv .venv
```

### 2. 激活虚拟环境

Windows PowerShell：

```bash
.\.venv\Scripts\Activate.ps1
```

如果遇到执行策略限制：

```bash
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.\.venv\Scripts\Activate.ps1
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 启动项目

```bash
streamlit run app.py --server.port 8502
```

浏览器访问：

```text
http://localhost:8502
```

---

## 十三、测试示例

### 测试 1：查看文件

输入：

```text
查看 workspace 里有哪些文件
```

预期：

```text
Agent 调用 list_files_tool，并返回 notes.md、summary.md 等文件
```

---

### 测试 2：读取文件

输入：

```text
读取 notes.md
```

预期：

```text
Agent 调用 read_file_tool，读取 notes.md 内容并回答
```

---

### 测试 3：根据文件生成新文件

输入：

```text
请根据 notes.md 的内容生成 summary.md
```

预期：

```text
Agent 调用 read_then_write
读取 notes.md
生成 summary.md 内容
进入待确认写入状态
```

点击：

```text
确认写入文件
```

预期：

```text
workspace 目录生成或更新 summary.md
状态更新为 write_file_confirmed
need_confirmation 为 false
```

---

## 十四、当前已实现能力

```text
✅ Agent Loop
✅ Tool Calling
✅ 文件列表查看
✅ 文件读取
✅ 根据源文件生成目标文件
✅ 写文件前用户确认
✅ 用户确认后写入文件
✅ 状态保存
✅ 确认写入后的状态更新
✅ workspace 文件操作安全边界
```

---

## 十五、后续优化方向

### Tool Agent 1.2：工具失败处理增强

计划增加：

```text
文件不存在时给出可选文件建议
不支持格式时给出明确提示
工具执行失败时记录失败原因
```

### Tool Agent 1.3：状态恢复

计划增加：

```text
读取上一次 pending 状态
页面支持继续上一次未完成任务
支持清空状态
```

### Tool Agent 1.4：评测集

计划增加：

```text
eval_cases.md
记录测试问题、预期工具、实际工具、是否通过
```

### Tool Agent 2.0：多 Agent 协作

计划探索：

```text
Planner Agent
Tool Executor Agent
Reviewer Agent
```

---

## 十六、项目定位

本项目不是普通聊天机器人，而是一个用于学习 Agent 工程机制的工具调用型 Agent 项目。

它重点体现：

```text
模型不只是生成文本，而是能够根据任务选择工具、调用工具、处理结果，并在高风险操作前等待用户确认。
```

与 RAG 知识库项目相比，本项目更关注：

```text
工具调用
执行流程
状态管理
用户确认
失败处理
评测设计
```

---

## 十七、简历描述参考

```text
基于 LangGraph 构建工具调用型 Agent 助手，实现 Agent Loop、Tool Calling、文件读取与写入、写入前用户确认和状态保存机制。系统支持根据用户自然语言任务自动选择 list_files、read_file、write_file、read_then_write 等工具，并将最近一次执行状态保存为 JSON，用于观察 Agent 执行过程和后续评测优化。
```