import streamlit as st

from agent import (
    clear_state,
    clear_history,
    confirm_write_file,
    get_pending_task,
    load_history,
    load_state,
    run_agent,
)
from tools import save_uploaded_file_to_workspace


st.set_page_config(
    page_title="Tool Agent Assistant",
    page_icon="🛠️",
    layout="wide"
 )

st.title("🛠️ 基于 LangGraph 的文档工作流多 Agent 助手 3.2")

st.write(
    "这是一个用于学习 Agent Loop、Tool Calling、工具失败处理、用户确认、状态保存和评测的实验项目。"
    "Tool Agent 3.2 在 3.0 文档工作流基础上新增文件名智能匹配和写入后摘要预览下载能力。"
 )


st.sidebar.title("📌 项目目标")
st.sidebar.markdown(
    """
    本项目用于学习工具调用型 Agent 的核心工程能力：

    - Agent Loop
    - Tool Calling
    - 工具失败处理
    - 写入前用户确认
    - 状态保存
    - 后续评测
    """
)

st.sidebar.title("🧩 当前工具")
st.sidebar.markdown(
    """
    - list_files：查看 workspace 文件
    - read_file：读取 txt / md / pdf / docx 文件
    - write_file：写入 txt / md 文件，需要用户确认
    - summarize_file：按模板生成摘要
    - file_detail：查看文件详情
    """
)

st.sidebar.title("📄 文档能力")
st.sidebar.markdown(
    """
    - 上传文件到 workspace
    - 读取 txt / md / pdf / docx
    - 自动摘要模板
    - 文件名智能匹配
    - 写入后摘要预览与下载
    - 历史任务记录
    - 自动化评测脚本
    """
)

st.sidebar.title("🧪 评测集")
st.sidebar.markdown(
    """
    - eval_cases.md：手动评测集
    - 覆盖正常任务、写入确认、失败处理、状态恢复和边界测试
    - 用于记录预期工具动作、错误类型、确认状态和实际测试结果
    """
)

st.sidebar.title("🔄 多 Agent 工作流")
st.sidebar.markdown(
    """
    - Planner Agent：任务规划
    - Tool Executor Agent：工具执行
    - Reviewer Agent：结果审查
    - Final Answer Agent：最终回复
    """
)

st.sidebar.title("📂 工作目录")
st.sidebar.code("workspace/")

pending_task = get_pending_task()

if pending_task and "pending_file_name" not in st.session_state:
    st.warning("检测到上一次有未完成的写入确认任务。")
    st.write(f"待写入文件：{pending_task['pending_file_name']}")

    with st.expander("查看待写入内容"):
        st.text_area(
            "待写入内容：",
            pending_task["pending_content"],
            height=200,
            disabled=True,
            key="pending_task_preview"
        )

    restore_col, clear_col = st.columns(2)

    with restore_col:
        if st.button("恢复未完成任务"):
            st.session_state["pending_file_name"] = pending_task["pending_file_name"]
            st.session_state["pending_content"] = pending_task["pending_content"]
            st.success("已恢复未完成任务，请在下方确认是否写入。")
            st.rerun()

    with clear_col:
        if st.button("清空未完成任务"):
            clear_state()
            st.success("已清空上一次未完成任务。")
            st.rerun()

st.subheader("📤 上传文档")

uploaded_file = st.file_uploader(
    "上传 .txt / .md / .pdf / .docx 文件到 workspace：",
    type=["txt", "md", "pdf", "docx"]
)

if uploaded_file is not None:
    upload_result = save_uploaded_file_to_workspace(
        uploaded_file.name,
        uploaded_file.getvalue()
    )

    if "已上传" in upload_result:
        st.success(upload_result)
        st.write(f"文件名：{uploaded_file.name}")
        st.write(f"文件大小：{uploaded_file.size} 字节")
        st.info(f"你可以在任务输入中使用文件名：{uploaded_file.name}")
    else:
        st.error(upload_result)

st.subheader("🧾 摘要模板")

summary_template = st.selectbox(
    "选择摘要模板：",
    options=[
        "general",
        "meeting",
        "paper",
        "contract",
        "resume",
        "project_readme"
    ],
    format_func=lambda value: {
        "general": "general：通用摘要",
        "meeting": "meeting：会议纪要",
        "paper": "paper：论文摘要",
        "contract": "contract：合同摘要",
        "resume": "resume：简历分析",
        "project_readme": "project_readme：项目 README 摘要"
    }[value]
)

st.subheader("💬 输入任务")

user_input = st.text_area(
    "请输入你希望 Agent 完成的任务：",
    placeholder="例如：查看 workspace 里有哪些文件；读取 notes.md；生成一份 summary.md",
    height=120
)

if st.button("运行 Agent"):
    if user_input.strip():
        agent_input = user_input
        if summary_template != "general":
            agent_input = f"使用 {summary_template} 模板。用户任务：{user_input}"

        with st.spinner("Agent 正在规划并调用工具..."):
            result = run_agent(agent_input)

        st.subheader("🤖 Agent 回答")
        st.write(result["final_answer"])

        st.subheader("🧭 Agent 状态")

        st.json({
            "tool_action": result["tool_action"],
            "tool_file_name": result["tool_file_name"],
            "target_file_name": result["target_file_name"],
            "plan_reason": result["plan_reason"],
            "summary_template": result["summary_template"],
            "generated_file_name": result["generated_file_name"],
            "history_id": result["history_id"],
            "need_confirmation": result["need_confirmation"],
            "pending_file_name": result["pending_file_name"],
            "error_type": result["error_type"],
            "error_message": result["error_message"],
            "recovery_suggestion": result["recovery_suggestion"],
            "review_passed": result["review_passed"],
            "review_result": result["review_result"],
            "tool_result": result["tool_result"]
        })

        if result["error_type"] != "none":
            st.error("工具执行失败")
            st.write("**错误原因：**")
            st.write(result["error_message"])
            st.info(f"恢复建议：{result['recovery_suggestion']}")

        if result["need_confirmation"]:
            st.warning("检测到写文件操作，需要你确认后才会真正写入文件。")
            st.session_state["pending_file_name"] = result["pending_file_name"]
            st.session_state["pending_content"] = result["pending_content"]

    else:
        st.warning("请输入任务内容。")

if "pending_file_name" in st.session_state:
    st.subheader("✅ 待确认写入操作")

    st.write(f"文件名：{st.session_state['pending_file_name']}")
    st.text_area(
        "待写入内容预览：",
        st.session_state["pending_content"],
        height=200
    )

    if st.button("确认写入文件"):
        pending_file_name = st.session_state["pending_file_name"]
        pending_content = st.session_state["pending_content"]
        write_result = confirm_write_file(
            pending_file_name,
            pending_content
        )

        st.success(write_result)

        if "文件已写入" in write_result:
            st.session_state["last_written_file"] = pending_file_name
            st.session_state["last_written_content"] = pending_content
            st.session_state["last_write_result"] = write_result

        del st.session_state["pending_file_name"]
        del st.session_state["pending_content"]
        st.rerun()

st.subheader("📄 最近生成内容预览")

if "last_written_file" in st.session_state and "last_written_content" in st.session_state:
    last_written_file = st.session_state["last_written_file"]
    last_written_content = st.session_state["last_written_content"]

    if "last_write_result" in st.session_state:
        st.success(st.session_state["last_write_result"])

    st.write(f"文件名：{last_written_file}")
    st.markdown(last_written_content)
    st.download_button(
        label="下载生成文件",
        data=last_written_content,
        file_name=last_written_file,
        mime="text/markdown"
    )

    if st.button("清空最近生成预览"):
        del st.session_state["last_written_file"]
        del st.session_state["last_written_content"]
        if "last_write_result" in st.session_state:
            del st.session_state["last_write_result"]
        st.rerun()
else:
    st.info("暂无最近生成内容。")

st.subheader("💾 最近一次状态保存")

saved_state = load_state()

if saved_state:
    st.json(saved_state)

    if st.button("清空状态记录"):
        clear_state()
        st.success("状态记录已清空。")
        st.rerun()
else:
    st.info("暂无状态记录。")

st.subheader("📚 历史任务列表")

history_records = load_history(limit=20)

if history_records:
    st.dataframe(
        [
            {
                "时间": record.get("saved_at", ""),
                "用户输入": record.get("user_input", ""),
                "tool_action": record.get("tool_action", ""),
                "error_type": record.get("error_type", ""),
                "review_passed": record.get("review_passed", False),
                "generated_file_name": record.get("generated_file_name", "")
            }
            for record in history_records
        ],
        use_container_width=True
    )

    if st.button("清空历史记录"):
        clear_history()
        st.success("历史任务记录已清空。")
        st.rerun()
else:
    st.info("暂无历史任务记录。")
