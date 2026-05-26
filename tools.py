from pathlib import Path


WORKSPACE_DIR = Path("workspace")
WORKSPACE_DIR.mkdir(exist_ok=True)


def get_available_files() -> list[str]:
    """
    返回 workspace 目录下的所有文件名。
    """
    files = []

    for file in WORKSPACE_DIR.glob("*"):
        if file.is_file():
            files.append(file.name)

    return files


def format_available_files_suggestion() -> str:
    """
    当文件不存在时，给出 workspace 中可用文件建议。
    """
    files = get_available_files()

    if not files:
        return "当前 workspace 目录中没有可用文件。"

    suggestion = "当前 workspace 中可用文件：\n"

    for file_name in files:
        suggestion += f"- {file_name}\n"

    suggestion += "\n请检查文件名是否输入正确。"

    return suggestion


def safe_path(file_name: str) -> Path:
    """
    限制所有文件操作只能发生在 workspace 目录内，避免误读写系统文件。
    """
    if not file_name or not file_name.strip():
        raise ValueError("文件名不能为空。")

    # 禁止绝对路径，例如 C:\\Users\\xxx\\file.md
    input_path = Path(file_name)

    if input_path.is_absolute():
        raise ValueError("非法文件路径：只能访问 workspace 目录内的文件。")

    target_path = (WORKSPACE_DIR / file_name).resolve()
    workspace_path = WORKSPACE_DIR.resolve()

    try:
        target_path.relative_to(workspace_path)
    except ValueError:
        raise ValueError("非法文件路径：只能访问 workspace 目录内的文件。")

    return target_path


def list_files_tool() -> str:
    """
    列出 workspace 目录下的文件。
    """
    files = get_available_files()

    if not files:
        return "workspace 目录当前没有文件。"

    result = "workspace 目录文件：\n"

    for file_name in files:
        result += f"- {file_name}\n"

    return result


def read_file_tool(file_name: str) -> str:
    """
    读取 workspace 目录下的 txt / md 文件。
    """
    try:
        file_path = safe_path(file_name)
    except ValueError as e:
        return str(e)

    if not file_path.exists():
        return (
            f"文件不存在：{file_name}\n\n"
            f"{format_available_files_suggestion()}"
        )

    if file_path.suffix.lower() not in [".txt", ".md"]:
        return (
            f"暂时只支持读取 .txt 和 .md 文件，"
            f"当前文件格式不支持：{file_path.name}"
        )

    return file_path.read_text(encoding="utf-8-sig")


def write_file_tool(file_name: str, content: str) -> str:
    """
    写入 txt / md 文件到 workspace 目录。
    """
    try:
        file_path = safe_path(file_name)
    except ValueError as e:
        return str(e)

    if file_path.suffix.lower() not in [".txt", ".md"]:
        return (
            f"暂时只支持写入 .txt 和 .md 文件，"
            f"当前文件格式不支持：{file_path.name}"
        )

    file_path.write_text(content, encoding="utf-8-sig")

    return f"文件已写入：{file_name}"