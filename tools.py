import os
from pathlib import Path


WORKSPACE_DIR = Path("workspace")
WORKSPACE_DIR.mkdir(exist_ok=True)


def safe_path(file_name: str) -> Path:
    """
    限制所有文件操作只能发生在 workspace 目录内，避免误读写系统文件。
    """
    target_path = (WORKSPACE_DIR / file_name).resolve()
    workspace_path = WORKSPACE_DIR.resolve()

    if not str(target_path).startswith(str(workspace_path)):
        raise ValueError("非法文件路径：只能访问 workspace 目录内的文件。")

    return target_path


def list_files_tool() -> str:
    """
    列出 workspace 目录下的文件。
    """
    files = list(WORKSPACE_DIR.glob("*"))

    if not files:
        return "workspace 目录当前没有文件。"

    result = "workspace 目录文件：\n"
    for file in files:
        if file.is_file():
            result += f"- {file.name}\n"

    return result


def read_file_tool(file_name: str) -> str:
    """
    读取 workspace 目录下的 txt / md 文件。
    """
    file_path = safe_path(file_name)

    if not file_path.exists():
        return f"文件不存在：{file_name}"

    if file_path.suffix.lower() not in [".txt", ".md"]:
        return "暂时只支持读取 .txt 和 .md 文件。"

    return file_path.read_text(encoding="utf-8")


def write_file_tool(file_name: str, content: str) -> str:
    """
    写入 txt / md 文件到 workspace 目录。
    """
    file_path = safe_path(file_name)

    if file_path.suffix.lower() not in [".txt", ".md"]:
        return "暂时只支持写入 .txt 和 .md 文件。"

    file_path.write_text(content, encoding="utf-8")

    return f"文件已写入：{file_name}"