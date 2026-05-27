import json
import os
import re
import uuid
from datetime import datetime
from typing import Optional, TypedDict

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph

from tools import get_file_detail, list_files_tool, read_file_tool, write_file_tool


load_dotenv()

API_KEY = os.getenv("OPENAI_API_KEY")
BASE_URL = os.getenv("OPENAI_BASE_URL")
MODEL_NAME = os.getenv("MODEL_NAME", "deepseek-chat")

MEMORY_DIR = "memory"
os.makedirs(MEMORY_DIR, exist_ok=True)

MEMORY_FILE = os.path.join(MEMORY_DIR, "session_state.json")
HISTORY_FILE = os.path.join(MEMORY_DIR, "history.jsonl")
SUMMARY_TEMPLATES = {
    "general",
    "meeting",
    "paper",
    "contract",
    "resume",
    "project_readme"
}


class AgentState(TypedDict):
    user_input: str

    # Agent 规划出的动作
    tool_action: str
    tool_file_name: str
    target_file_name: str
    tool_content: str
    plan_reason: str
    summary_template: str
    history_id: str
    generated_file_name: str

    # 工具执行结果
    tool_result: str

    # 错误处理状态
    error_type: str
    error_message: str
    recovery_suggestion: str

    # 审查结果
    review_passed: bool
    review_result: str

    # 最终回答
    final_answer: str

    # 写文件确认机制
    need_confirmation: bool
    pending_file_name: str
    pending_content: str


def save_state(state: AgentState) -> None:
    """
    保存当前 Agent 状态，方便观察 Agent Loop 的执行过程。
    """
    data = {
        "saved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "state": state
    }

    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_state() -> Optional[dict]:
    """
    读取上一次保存的 Agent 状态。
    """
    if not os.path.exists(MEMORY_FILE):
        return None

    with open(MEMORY_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def clear_state() -> None:
    """
    删除最近一次保存的 Agent 状态记录。
    """
    if os.path.exists(MEMORY_FILE):
        os.remove(MEMORY_FILE)


def append_history(state: AgentState) -> None:
    """
    追加一次 Agent 运行历史记录。
    """
    history_record = {
        "history_id": state["history_id"],
        "saved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "user_input": state["user_input"],
        "tool_action": state["tool_action"],
        "tool_file_name": state["tool_file_name"],
        "target_file_name": state["target_file_name"],
        "summary_template": state["summary_template"],
        "generated_file_name": state["generated_file_name"],
        "error_type": state["error_type"],
        "review_passed": state["review_passed"],
        "review_result": state["review_result"],
        "need_confirmation": state["need_confirmation"],
        "final_answer": state["final_answer"]
    }

    with open(HISTORY_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(history_record, ensure_ascii=False) + "\n")


def load_history(limit: int = 20) -> list:
    """
    读取最近的 Agent 运行历史记录。
    """
    if not os.path.exists(HISTORY_FILE):
        return []

    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]

    records = []
    for line in lines[-limit:]:
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue

    return list(reversed(records))


def clear_history() -> None:
    """
    清空 Agent 运行历史记录。
    """
    if os.path.exists(HISTORY_FILE):
        os.remove(HISTORY_FILE)


def get_pending_task() -> Optional[dict]:
    """
    读取上一次保存的状态，返回仍在等待确认的写入任务。
    """
    saved_state = load_state()
    if not saved_state:
        return None

    state = saved_state.get("state", {})

    if (
        state.get("need_confirmation") is True
        and state.get("pending_file_name")
        and state.get("pending_content")
    ):
        return state

    return None


def get_llm():
    """
    获取大模型客户端。
    """
    if not API_KEY:
        raise ValueError("未检测到 OPENAI_API_KEY，请先在 .env 文件中配置。")

    return ChatOpenAI(
        api_key=API_KEY,
        base_url=BASE_URL,
        model=MODEL_NAME,
        temperature=0
    )


def parse_json_from_llm(text: str) -> dict:
    """
    尽量从模型输出中解析 JSON。
    避免模型偶尔包上 ```json 代码块导致 json.loads 失败。
    """
    text = text.strip()

    if text.startswith("```json"):
        text = text.replace("```json", "", 1).strip()

    if text.startswith("```"):
        text = text.replace("```", "", 1).strip()

    if text.endswith("```"):
        text = text[:-3].strip()

    try:
        return json.loads(text)
    except Exception:
        return {}


def detect_tool_error(tool_result: str) -> tuple[str, str, str]:
    """
    根据工具执行结果识别错误类型、错误原因和恢复建议。
    """
    if "文件不存在" in tool_result:
        return (
            "file_not_found",
            tool_result,
            "请检查文件名是否正确，或先使用“查看 workspace 里有哪些文件”。"
        )

    if "非法文件路径" in tool_result:
        return (
            "invalid_path",
            tool_result,
            "出于安全限制，Agent 只能访问 workspace 目录内的文件，请使用 workspace 内的相对文件名。"
        )

    if "暂时只支持" in tool_result:
        return (
            "unsupported_format",
            tool_result,
            "请使用 .txt、.md、.pdf 或 .docx 文件进行测试。"
        )

    if "文档内容为空或无法提取文本" in tool_result:
        return (
            "empty_document",
            tool_result,
            "该文档可能是扫描件、图片型 PDF，或没有可提取文本。请换用可复制文本的文档。"
        )

    if "读取 PDF 文件失败" in tool_result or "读取 DOCX 文件失败" in tool_result:
        return (
            "document_read_error",
            tool_result,
            "请确认文档未损坏，并使用 .pdf 或 .docx 文件进行测试。"
        )

    if "文件名不能为空" in tool_result:
        return (
            "empty_file_name",
            tool_result,
            "请输入明确的文件名，例如 notes.md 或 summary.md。"
        )

    return ("none", "", "")


def apply_error_state(state: AgentState, tool_result: str) -> AgentState:
    """
    将工具错误识别结果写入 AgentState。
    """
    error_type, error_message, recovery_suggestion = detect_tool_error(tool_result)

    state["error_type"] = error_type
    state["error_message"] = error_message
    state["recovery_suggestion"] = recovery_suggestion

    if error_type != "none":
        state["need_confirmation"] = False
        state["pending_file_name"] = ""
        state["pending_content"] = ""

    return state


def planner_agent_node(state: AgentState) -> AgentState:
    """
    Planner Agent：
    理解用户任务，判断应该调用哪类工具，并说明规划原因。
    """
    user_input = state["user_input"]

    prompt = f"""
你是一个工具调用型 Agent 助手。

你可以使用以下工具动作：

1. list_files
用于查看 workspace 目录有哪些文件。

2. read_file
用于读取 workspace 目录下的 txt / md 文件。

3. write_file
用于直接写入 txt / md 文件。写入前必须用户确认。

4. read_then_write
用于“根据某个已有文件生成另一个新文件”的复合任务。
例如：
- 根据 notes.md 生成 summary.md
- 读取 report.md 并生成 summary.md
- 根据 meeting.md 的内容写一份 result.md

5. chat
不需要工具，直接回答用户。

6. summarize_file
用于读取指定文档，并根据摘要模板生成 Markdown 摘要。

7. file_detail
用于查看 workspace 中文件的详细信息。

摘要模板 summary_template 可选值：
- general
- meeting
- paper
- contract
- resume
- project_readme

请根据用户输入判断应该使用哪个工具动作。

用户输入：
{user_input}

请只返回 JSON，不要输出多余解释。

JSON 格式如下：
{{
  "tool_action": "list_files / read_file / write_file / read_then_write / chat",
  "tool_file_name": "源文件名，如果没有则为空字符串",
  "target_file_name": "目标文件名，如果没有则为空字符串",
  "tool_content": "需要直接写入的内容，如果没有则为空字符串",
  "plan_reason": "简要说明为什么选择这个工具动作",
  "summary_template": "general / meeting / paper / contract / resume / project_readme"
}}

判断规则：
- 如果用户想查看有哪些文件，使用 list_files。
- 如果用户只想读取某个文件，使用 read_file。
- 如果用户想把一段明确内容保存到某个文件，使用 write_file。
- 如果用户想根据 A 文件生成 B 文件，必须使用 read_then_write。
- 如果用户想总结、摘要、提炼某个文件，使用 summarize_file。
- 如果用户想查看文件信息、文件详情、文件大小、修改时间，使用 file_detail。
- 如果只是普通聊天或普通问题，使用 chat。
- 文件名通常以 .txt、.md、.pdf 或 .docx 结尾。
"""

    llm = get_llm()
    response = llm.invoke(prompt)

    plan = parse_json_from_llm(response.content)

    tool_action = plan.get("tool_action", "chat")
    tool_file_name = plan.get("tool_file_name", "")
    target_file_name = plan.get("target_file_name", "")
    tool_content = plan.get("tool_content", "")
    plan_reason = plan.get("plan_reason", "")
    summary_template = plan.get("summary_template", "general")

    allowed_actions = {
        "list_files",
        "read_file",
        "write_file",
        "read_then_write",
        "summarize_file",
        "file_detail",
        "chat"
    }

    rule_plan = infer_plan_from_user_input(user_input)
    if rule_plan:
        tool_action = rule_plan.get("tool_action", tool_action)
        tool_file_name = rule_plan.get("tool_file_name", tool_file_name)
        target_file_name = rule_plan.get("target_file_name", target_file_name)
        tool_content = rule_plan.get("tool_content", tool_content)
        summary_template = rule_plan.get("summary_template", summary_template)
        plan_reason = rule_plan.get("plan_reason", plan_reason)

    if tool_action not in allowed_actions:
        tool_action = "chat"
        plan_reason = "无法识别为文件工具任务，因此转为普通对话。"

    if summary_template not in SUMMARY_TEMPLATES:
        summary_template = "general"

    if not plan_reason:
        reason_map = {
            "list_files": "用户想查看 workspace 中有哪些文件，因此需要列出文件列表。",
            "read_file": "用户想读取指定文件内容，因此需要调用读取文件工具。",
            "write_file": "用户想写入文件，因此需要进入写入前确认流程。",
            "read_then_write": "用户希望根据已有文件生成新文件，因此需要先读取源文件再生成目标文件内容。",
            "summarize_file": "用户想对文档进行摘要，因此需要先读取文件内容，再按摘要模板生成 Markdown 摘要。",
            "file_detail": "用户想查看文件信息，因此需要读取文件详情。",
            "chat": "用户输入更适合普通对话，因此不需要调用文件工具。"
        }
        plan_reason = reason_map.get(tool_action, "已根据用户任务选择基础工具动作。")

    state["tool_action"] = tool_action
    state["tool_file_name"] = tool_file_name
    state["target_file_name"] = target_file_name
    state["tool_content"] = tool_content
    state["plan_reason"] = plan_reason
    state["summary_template"] = summary_template

    return state


def infer_plan_from_user_input(user_input: str) -> Optional[dict]:
    """
    对常见教学用例做轻量规则增强，降低评测时对模型输出格式的依赖。
    """
    file_names = re.findall(r"(?:\.\.[/\\])?[\w\u4e00-\u9fff./\\-]+\.(?:txt|md|pdf|docx)", user_input)
    first_file = file_names[0] if file_names else ""
    second_file = file_names[1] if len(file_names) > 1 else ""
    summary_template = detect_summary_template(user_input)

    if "workspace" in user_input and ("哪些文件" in user_input or "文件列表" in user_input):
        return {
            "tool_action": "list_files",
            "tool_file_name": "",
            "target_file_name": "",
            "tool_content": "",
            "summary_template": summary_template,
            "plan_reason": "用户想查看 workspace 中有哪些文件，因此需要列出文件列表。"
        }

    if first_file and any(keyword in user_input for keyword in ["文件信息", "文件详情", "文件大小", "修改时间"]):
        return {
            "tool_action": "file_detail",
            "tool_file_name": first_file,
            "target_file_name": "",
            "tool_content": "",
            "summary_template": summary_template,
            "plan_reason": "用户想查看文件详情，因此需要调用文件详情工具。"
        }

    if first_file and any(keyword in user_input for keyword in ["总结", "摘要", "概括", "提炼"]):
        return {
            "tool_action": "summarize_file",
            "tool_file_name": first_file,
            "target_file_name": "",
            "tool_content": "",
            "summary_template": summary_template,
            "plan_reason": "用户想对文档进行摘要，因此需要读取文件并按模板生成摘要。"
        }

    if len(file_names) >= 2 and any(keyword in user_input for keyword in ["生成", "写一份", "生成一份"]):
        return {
            "tool_action": "read_then_write",
            "tool_file_name": first_file,
            "target_file_name": second_file,
            "tool_content": "",
            "summary_template": summary_template,
            "plan_reason": "用户希望根据已有文件生成新文件，因此需要先读取源文件再生成目标文件内容。"
        }

    if first_file and any(keyword in user_input for keyword in ["读取", "查看", "打开"]):
        return {
            "tool_action": "read_file",
            "tool_file_name": first_file,
            "target_file_name": "",
            "tool_content": "",
            "summary_template": summary_template,
            "plan_reason": "用户想读取指定文件内容，因此需要调用读取文件工具。"
        }

    return None


def detect_summary_template(user_input: str) -> str:
    """
    从用户输入中识别摘要模板。
    """
    template_keywords = {
        "meeting": ["meeting", "会议", "会议纪要"],
        "paper": ["paper", "论文", "研究"],
        "contract": ["contract", "合同", "协议"],
        "resume": ["resume", "简历"],
        "project_readme": ["project_readme", "README", "readme", "项目 README", "项目说明"],
        "general": ["general", "通用"]
    }

    for template, keywords in template_keywords.items():
        if any(keyword in user_input for keyword in keywords):
            return template

    return "general"


def generate_content_from_file(source_file_name: str, source_content: str, target_file_name: str) -> str:
    """
    根据源文件内容生成目标文件内容。
    例如：根据 notes.md 生成 summary.md。
    """
    prompt = f"""
你是一个严谨的文档整理助手。

现在需要根据源文件内容生成一个新的 Markdown 文档。

源文件名：
{source_file_name}

目标文件名：
{target_file_name}

源文件内容：
{source_content}

请根据源文件内容生成目标文件的 Markdown 内容。

要求：
1. 不要编造源文件中没有的信息。
2. 内容要结构清晰。
3. 如果是 summary.md，请生成一份简洁总结。
4. 使用中文。
5. 只输出目标文件内容，不要解释。
"""

    llm = get_llm()
    response = llm.invoke(prompt)

    return response.content


def generate_summary_with_template(content: str, template: str, source_file_name: str) -> str:
    """
    根据摘要模板生成 Markdown 摘要。
    """
    headings = {
        "general": "# 文档摘要\n## 核心内容\n## 关键要点\n## 总结",
        "meeting": "# 会议纪要\n## 会议主题\n## 讨论内容\n## 决策事项\n## 待办事项\n## 下一步计划",
        "paper": "# 论文摘要\n## 研究背景\n## 研究方法\n## 核心结论\n## 创新点\n## 局限性",
        "contract": "# 合同摘要\n## 合同主体\n## 核心条款\n## 权利义务\n## 风险点\n## 注意事项",
        "resume": "# 简历分析\n## 基本概况\n## 技能亮点\n## 项目经验\n## 优化建议",
        "project_readme": "# 项目 README 摘要\n## 项目定位\n## 核心功能\n## 技术栈\n## 运行方式\n## 后续优化方向"
    }
    selected_template = template if template in headings else "general"
    outline = headings[selected_template]
    clipped_content = content[:12000]

    prompt = f"""
你是一个严谨的文档工作流助手。

请根据指定模板，为源文件生成 Markdown 摘要。

源文件名：
{source_file_name}

摘要模板：
{selected_template}

必须使用以下 Markdown 结构：
{outline}

源文件内容：
{clipped_content}

要求：
1. 不要编造源文件中没有的信息。
2. 如果某个小节没有明确内容，请写“原文未明确提及”。
3. 输出必须是 Markdown。
4. 使用中文。
5. 只输出摘要正文，不要额外解释。
"""

    llm = get_llm()
    response = llm.invoke(prompt)

    return response.content


def build_summary_file_name(source_file_name: str) -> str:
    """
    根据源文件名生成默认摘要文件名。
    """
    base_name = os.path.splitext(os.path.basename(source_file_name))[0]
    if not base_name:
        base_name = "document"
    return f"{base_name}_summary.md"


def tool_executor_agent_node(state: AgentState) -> AgentState:
    """
    Tool Executor Agent：
    根据 Planner Agent 的规划结果执行本地工具。
    """
    action = state["tool_action"]
    file_name = state["tool_file_name"]
    target_file_name = state["target_file_name"]
    content = state["tool_content"]
    summary_template = state["summary_template"]

    # 默认状态
    state["need_confirmation"] = False
    state["pending_file_name"] = ""
    state["pending_content"] = ""
    state["generated_file_name"] = ""
    state["error_type"] = "none"
    state["error_message"] = ""
    state["recovery_suggestion"] = ""

    if action == "list_files":
        state["tool_result"] = list_files_tool()
        state = apply_error_state(state, state["tool_result"])

    elif action == "read_file":
        state["tool_result"] = read_file_tool(file_name)
        state = apply_error_state(state, state["tool_result"])

    elif action == "file_detail":
        state["tool_result"] = get_file_detail(file_name)
        state = apply_error_state(state, state["tool_result"])

    elif action == "write_file":
        if not target_file_name:
            target_file_name = file_name

        # write_file 本身是高风险操作，先不真正写入
        if not target_file_name:
            state["tool_result"] = "文件名不能为空。"
            state = apply_error_state(state, state["tool_result"])
            return state

        state["need_confirmation"] = True
        state["pending_file_name"] = target_file_name
        state["pending_content"] = content
        state["tool_result"] = (
            f"检测到写文件操作，需要用户确认后才能写入：{target_file_name}"
        )

    elif action == "read_then_write":
        if not file_name:
            state["tool_result"] = "文件名不能为空。"
            state = apply_error_state(state, state["tool_result"])
            return state

        if not target_file_name:
            target_file_name = "summary.md"

        source_content = read_file_tool(file_name)

        error_type, error_message, recovery_suggestion = detect_tool_error(source_content)

        if error_type != "none":
            state["tool_result"] = source_content
            state["error_type"] = error_type
            state["error_message"] = error_message
            state["recovery_suggestion"] = recovery_suggestion
            state["need_confirmation"] = False
            state["pending_file_name"] = ""
            state["pending_content"] = ""
            return state

        generated_content = generate_content_from_file(
            source_file_name=file_name,
            source_content=source_content,
            target_file_name=target_file_name
        )

        state["need_confirmation"] = True
        state["pending_file_name"] = target_file_name
        state["generated_file_name"] = target_file_name
        state["pending_content"] = generated_content
        state["tool_result"] = (
            f"已读取源文件：{file_name}\n"
            f"已生成目标文件内容：{target_file_name}\n"
            f"当前尚未真正写入文件，等待用户确认。"
        )

    elif action == "summarize_file":
        if not file_name:
            state["tool_result"] = "文件名不能为空。"
            state = apply_error_state(state, state["tool_result"])
            return state

        source_content = read_file_tool(file_name)
        error_type, error_message, recovery_suggestion = detect_tool_error(source_content)

        if error_type != "none":
            state["tool_result"] = source_content
            state["error_type"] = error_type
            state["error_message"] = error_message
            state["recovery_suggestion"] = recovery_suggestion
            state["need_confirmation"] = False
            state["pending_file_name"] = ""
            state["pending_content"] = ""
            state["generated_file_name"] = ""
            return state

        generated_content = generate_summary_with_template(
            content=source_content,
            template=summary_template,
            source_file_name=file_name
        )
        generated_file_name = build_summary_file_name(file_name)

        state["need_confirmation"] = True
        state["pending_file_name"] = generated_file_name
        state["pending_content"] = generated_content
        state["generated_file_name"] = generated_file_name
        state["target_file_name"] = generated_file_name
        state["tool_result"] = (
            f"已读取源文件：{file_name}\n"
            f"已使用摘要模板：{summary_template}\n"
            f"已生成摘要文件内容：{generated_file_name}\n"
            f"当前尚未真正写入文件，等待用户确认。"
        )

    elif action == "chat":
        state["tool_result"] = "未调用工具。"
        state = apply_error_state(state, state["tool_result"])

    else:
        state["tool_result"] = "未调用工具。"
        state = apply_error_state(state, state["tool_result"])

    return state


def reviewer_agent_node(state: AgentState) -> AgentState:
    """
    Reviewer Agent：
    使用规则检查工具执行结果、错误状态和写入确认状态。
    """
    tool_action = state["tool_action"]
    error_type = state["error_type"]
    need_confirmation = state["need_confirmation"]
    pending_file_name = state["pending_file_name"]
    pending_content = state["pending_content"]
    tool_result = state["tool_result"]

    if error_type != "none":
        state["review_passed"] = False
        if error_type == "empty_document":
            state["review_result"] = "文档可能无法提取文本，无法生成可靠摘要。"
        elif error_type == "unsupported_format":
            state["review_result"] = "文件格式不支持，未继续执行文档工作流。"
        else:
            state["review_result"] = "工具执行失败，已记录错误原因和恢复建议。"
        return state

    if "文档内容为空或无法提取文本" in tool_result:
        state["review_passed"] = False
        state["review_result"] = "文档可能无法提取文本，无法生成可靠摘要。"
        return state

    if tool_action == "summarize_file" and need_confirmation and pending_file_name and pending_content:
        state["review_passed"] = True
        state["review_result"] = "摘要内容已生成，已进入用户确认流程，暂未实际写入文件。"
        return state

    if need_confirmation and pending_file_name and pending_content:
        state["review_passed"] = True
        state["review_result"] = "检测到写文件操作，已进入用户确认流程，暂未实际写入文件。"
        return state

    if tool_action in ["list_files", "read_file", "file_detail", "chat"] and error_type == "none":
        state["review_passed"] = True
        state["review_result"] = "工具执行成功，结果可用于最终回复。"
        return state

    if tool_action == "write_file_confirmed":
        state["review_passed"] = True
        state["review_result"] = "用户已确认写入，文件写入流程完成。"
        return state

    state["review_passed"] = True
    state["review_result"] = "已完成基础审查。"
    return state


def final_answer_node(state: AgentState) -> AgentState:
    """
    Final Answer Agent：
    根据规划、工具执行和审查结果生成用户可读回答。
    """
    user_input = state["user_input"]
    tool_result = state["tool_result"]
    need_confirmation = state["need_confirmation"]
    pending_file_name = state["pending_file_name"]
    error_type = state["error_type"]
    error_message = state["error_message"]
    recovery_suggestion = state["recovery_suggestion"]
    review_result = state["review_result"]

    if error_type != "none":
        state["final_answer"] = (
            "工具执行失败。\n\n"
            f"错误类型：{error_type}\n\n"
            f"错误原因：\n{error_message}\n\n"
            f"恢复建议：\n{recovery_suggestion}\n\n"
            f"Reviewer 审查结果：\n{review_result}"
        )
        save_state(state)
        append_history(state)
        return state

    if need_confirmation:
        state["final_answer"] = (
            f"我已经根据你的任务生成了待写入内容。\n\n"
            f"{tool_result}\n\n"
            f"待写入文件：{pending_file_name}\n\n"
            f"注意：当前尚未真正写入文件。请在页面下方查看内容预览，确认无误后点击“确认写入文件”。\n\n"
            f"Reviewer 审查结果：\n{review_result}"
        )
        save_state(state)
        append_history(state)
        return state

    prompt = f"""
你是一个本地工具调用型 Agent 助手。

用户输入：
{user_input}

工具执行结果：
{tool_result}

Reviewer 审查结果：
{review_result}

请用中文给用户一个简洁、清晰的回答。
如果工具返回的是文件内容，请可以适当总结。
如果工具提示文件不存在，请明确告诉用户。
"""

    llm = get_llm()
    response = llm.invoke(prompt)

    state["final_answer"] = response.content
    save_state(state)
    append_history(state)

    return state


def build_agent_graph():
    """
    构建 LangGraph 最小多 Agent 工作流。
    """
    workflow = StateGraph(AgentState)

    workflow.add_node("planner_agent", planner_agent_node)
    workflow.add_node("tool_executor_agent", tool_executor_agent_node)
    workflow.add_node("reviewer_agent", reviewer_agent_node)
    workflow.add_node("final_answer_agent", final_answer_node)

    workflow.set_entry_point("planner_agent")
    workflow.add_edge("planner_agent", "tool_executor_agent")
    workflow.add_edge("tool_executor_agent", "reviewer_agent")
    workflow.add_edge("reviewer_agent", "final_answer_agent")
    workflow.add_edge("final_answer_agent", END)

    return workflow.compile()


agent_graph = build_agent_graph()


def run_agent(user_input: str) -> AgentState:
    """
    运行 Agent。
    """
    initial_state: AgentState = {
        "user_input": user_input,
        "tool_action": "",
        "tool_file_name": "",
        "target_file_name": "",
        "tool_content": "",
        "plan_reason": "",
        "summary_template": "general",
        "history_id": str(uuid.uuid4()),
        "generated_file_name": "",
        "tool_result": "",
        "error_type": "none",
        "error_message": "",
        "recovery_suggestion": "",
        "review_passed": False,
        "review_result": "",
        "final_answer": "",
        "need_confirmation": False,
        "pending_file_name": "",
        "pending_content": ""
    }

    result = agent_graph.invoke(initial_state)
    return result


def confirm_write_file(file_name: str, content: str) -> str:
    """
    用户确认后才真正写入文件，并更新状态保存。
    """
    result = write_file_tool(file_name, content)

    error_type, error_message, recovery_suggestion = detect_tool_error(result)

    completed_state: AgentState = {
        "user_input": f"用户已确认写入文件：{file_name}",
        "tool_action": "write_file_confirmed",
        "tool_file_name": file_name,
        "target_file_name": file_name,
        "tool_content": content,
        "plan_reason": "用户已确认写入文件。",
        "summary_template": "general",
        "history_id": str(uuid.uuid4()),
        "generated_file_name": file_name,
        "tool_result": result,
        "error_type": error_type,
        "error_message": error_message,
        "recovery_suggestion": recovery_suggestion,
        "review_passed": True,
        "review_result": "用户已确认写入，文件写入流程完成。",
        "final_answer": f"文件已确认并写入：{file_name}" if error_type == "none" else "文件写入失败。",
        "need_confirmation": False,
        "pending_file_name": "",
        "pending_content": ""
    }

    save_state(completed_state)
    append_history(completed_state)

    return result
