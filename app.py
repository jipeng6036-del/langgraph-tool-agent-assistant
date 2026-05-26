import streamlit as st

from agent import (
    clear_state,
    confirm_write_file,
    get_pending_task,
    load_state,
    run_agent,
)


st.set_page_config(
    page_title="Tool Agent Assistant",
    page_icon="🛠️",
    layout="wide"
)

st.title("🛠️ 基于 LangGraph 的工具调用型 Agent 助手 1.3")

st.write(
    "这是一个用于学习 Agent Loop、Tool Calling、工具失败处理、用户确认、状态保存和评测的实验项目。"
    "当前 1.3 版本新增了状态恢复与任务继续能力。"
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
    - read_file：读取 txt / md 文件
    - write_file：写入 txt / md 文件，需要用户确认
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

st.subheader("💬 输入任务")

user_input = st.text_area(
    "请输入你希望 Agent 完成的任务：",
    placeholder="例如：查看 workspace 里有哪些文件；读取 notes.md；生成一份 summary.md",
    height=120
)

if st.button("运行 Agent"):
    if user_input.strip():
        with st.spinner("Agent 正在规划并调用工具..."):
            result = run_agent(user_input)

        st.subheader("🤖 Agent 回答")
        st.write(result["final_answer"])

        st.subheader("🧭 Agent 状态")

        st.json({
            "tool_action": result["tool_action"],
            "tool_file_name": result["tool_file_name"],
            "target_file_name": result["target_file_name"],
            "need_confirmation": result["need_confirmation"],
            "pending_file_name": result["pending_file_name"],
            "error_type": result["error_type"],
            "error_message": result["error_message"],
            "recovery_suggestion": result["recovery_suggestion"],
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
        write_result = confirm_write_file(
            st.session_state["pending_file_name"],
            st.session_state["pending_content"]
        )

        st.success(write_result)

        del st.session_state["pending_file_name"]
        del st.session_state["pending_content"]

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
