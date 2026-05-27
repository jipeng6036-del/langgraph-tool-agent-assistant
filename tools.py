from datetime import datetime
from pathlib import Path


WORKSPACE_DIR = Path("workspace")
WORKSPACE_DIR.mkdir(exist_ok=True)

SUPPORTED_READ_EXTENSIONS = [".txt", ".md", ".pdf", ".docx"]
SUPPORTED_UPLOAD_EXTENSIONS = SUPPORTED_READ_EXTENSIONS
SUPPORTED_WRITE_EXTENSIONS = [".txt", ".md"]


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
    读取 workspace 目录下的 txt / md / pdf / docx 文件。
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

    suffix = file_path.suffix.lower()

    if suffix not in SUPPORTED_READ_EXTENSIONS:
        return (
            f"暂时只支持读取 .txt、.md、.pdf 和 .docx 文件，"
            f"当前文件格式不支持：{file_path.name}"
        )

    if suffix in [".txt", ".md"]:
        return file_path.read_text(encoding="utf-8-sig")

    if suffix == ".pdf":
        return read_pdf_file(file_path)

    if suffix == ".docx":
        return read_docx_file(file_path)

    return (
        f"暂时只支持读取 .txt、.md、.pdf 和 .docx 文件，"
        f"当前文件格式不支持：{file_path.name}"
    )


def read_pdf_file(file_path: Path) -> str:
    """
    使用 pypdf 提取 PDF 页面文本。
    """
    try:
        from pypdf import PdfReader
    except ImportError:
        return "暂时只支持读取 .pdf 文件，但当前环境缺少 pypdf 依赖。"

    try:
        reader = PdfReader(str(file_path))
        page_texts = []

        for page in reader.pages:
            page_text = page.extract_text() or ""
            if page_text.strip():
                page_texts.append(page_text.strip())

        content = "\n\n".join(page_texts).strip()
    except Exception as e:
        return f"读取 PDF 文件失败：{file_path.name}\n原因：{e}"

    if not content:
        return f"文档内容为空或无法提取文本：{file_path.name}"

    return content


def read_docx_file(file_path: Path) -> str:
    """
    使用 python-docx 提取 DOCX 段落文本。
    """
    try:
        from docx import Document
    except ImportError:
        return "暂时只支持读取 .docx 文件，但当前环境缺少 python-docx 依赖。"

    try:
        document = Document(str(file_path))
        paragraphs = [
            paragraph.text.strip()
            for paragraph in document.paragraphs
            if paragraph.text.strip()
        ]
        content = "\n".join(paragraphs).strip()
    except Exception as e:
        return f"读取 DOCX 文件失败：{file_path.name}\n原因：{e}"

    if not content:
        return f"文档内容为空或无法提取文本：{file_path.name}"

    return content


def save_uploaded_file_to_workspace(file_name: str, file_bytes: bytes) -> str:
    """
    将上传文件保存到 workspace 目录。
    """
    try:
        file_path = safe_path(file_name)
    except ValueError as e:
        return str(e)

    if file_path.suffix.lower() not in SUPPORTED_UPLOAD_EXTENSIONS:
        return (
            f"暂时只支持上传 .txt、.md、.pdf 和 .docx 文件，"
            f"当前文件格式不支持：{file_path.name}"
        )

    file_path.write_bytes(file_bytes)

    return f"文件已上传到 workspace：{file_path.name}"


def get_file_detail(file_name: str) -> str:
    """
    返回 workspace 文件详情。
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

    if file_path.suffix.lower() not in SUPPORTED_READ_EXTENSIONS:
        return (
            f"暂时只支持查看 .txt、.md、.pdf 和 .docx 文件详情，"
            f"当前文件格式不支持：{file_path.name}"
        )

    stat = file_path.stat()
    modified_at = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")

    return (
        f"文件名：{file_path.name}\n"
        f"文件大小：{stat.st_size} 字节\n"
        f"修改时间：{modified_at}\n"
        f"文件格式：{file_path.suffix.lower()}"
    )


def write_file_tool(file_name: str, content: str) -> str:
    """
    写入 txt / md 文件到 workspace 目录。
    """
    try:
        file_path = safe_path(file_name)
    except ValueError as e:
        return str(e)

    if file_path.suffix.lower() not in SUPPORTED_WRITE_EXTENSIONS:
        return (
            f"暂时只支持写入 .txt 和 .md 文件，"
            f"当前文件格式不支持：{file_path.name}"
        )

    file_path.write_text(content, encoding="utf-8-sig")

    return f"文件已写入：{file_name}"
