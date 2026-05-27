import re
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


def normalize_text(text: str) -> str:
    """
    标准化文件名匹配文本：转小写、去掉常见分隔符，只保留中文、英文和数字。
    """
    if not text:
        return ""

    return "".join(re.findall(r"[\u4e00-\u9fffA-Za-z0-9]+", text.lower()))


def get_supported_workspace_files() -> list[str]:
    """
    返回 workspace 下支持读取的文件列表。
    """
    files = []

    for file in WORKSPACE_DIR.glob("*"):
        if file.is_file() and file.suffix.lower() in SUPPORTED_READ_EXTENSIONS:
            files.append(file.name)

    return files


def clean_file_query(query: str) -> str:
    """
    去掉任务动词，保留更像文件名或关键词的部分。
    """
    cleaned = query.strip()
    stop_words = [
        "使用",
        "用户任务",
        "模板",
        "总结",
        "摘要",
        "概括",
        "提炼",
        "读取",
        "查看",
        "打开",
        "文件信息",
        "文件详情",
        "文件大小",
        "修改时间",
        "文件",
        "内容",
        "信息",
        "请",
        "一下",
        "根据",
        "生成",
        "的",
        "general",
        "meeting",
        "paper",
        "contract",
        "resume",
        "project_readme",
    ]

    for word in stop_words:
        cleaned = cleaned.replace(word, "")

    return cleaned.strip(" ：:，,。.!！?？")


def build_match_message(query: str, status: str, candidates: list[str]) -> str:
    if status == "multiple":
        message = f"匹配到多个候选文件：{query}\n\n候选文件列表：\n"
        for file_name in candidates:
            message += f"- {file_name}\n"
        message += "\n请用户输入更明确的文件名。"
        return message

    message = f"文件不存在：{query}\n\n{format_available_files_suggestion()}"
    return message


def prefer_source_document(candidates: list[str], query: str) -> list[str]:
    """
    关键词没有明确指向 summary 时，优先把已生成的摘要文件排除在候选外。
    """
    normalized_query = normalize_text(query)
    if "summary" in normalized_query or "摘要" in normalized_query:
        return candidates

    source_candidates = [
        file_name
        for file_name in candidates
        if not normalize_text(Path(file_name).stem).endswith("summary")
    ]

    return source_candidates or candidates


def find_matching_files(query: str) -> dict:
    """
    根据用户输入或 Planner 给出的文件名关键词，在 workspace 中做智能匹配。
    """
    raw_query = (query or "").strip()
    supported_files = get_supported_workspace_files()

    if not raw_query:
        return {
            "status": "not_found",
            "matched_file": "",
            "candidates": supported_files,
            "message": "文件名不能为空。"
        }

    exact_matches = [file_name for file_name in supported_files if file_name == raw_query]
    if exact_matches:
        return {
            "status": "matched",
            "matched_file": exact_matches[0],
            "candidates": exact_matches,
            "message": f"已匹配文件：{exact_matches[0]}"
        }

    lower_matches = [
        file_name
        for file_name in supported_files
        if file_name.lower() == raw_query.lower()
    ]
    if lower_matches:
        return {
            "status": "matched",
            "matched_file": lower_matches[0],
            "candidates": lower_matches,
            "message": f"已匹配文件：{lower_matches[0]}"
        }

    normalized_query = normalize_text(raw_query)
    cleaned_query = normalize_text(clean_file_query(raw_query))
    query_terms = [
        term
        for term in {normalized_query, cleaned_query}
        if term
    ]

    normalized_exact_matches = []
    for file_name in supported_files:
        normalized_name = normalize_text(file_name)
        normalized_stem = normalize_text(Path(file_name).stem)
        if any(term in [normalized_name, normalized_stem] for term in query_terms):
            normalized_exact_matches.append(file_name)

    if len(normalized_exact_matches) == 1:
        matched_file = normalized_exact_matches[0]
        return {
            "status": "matched",
            "matched_file": matched_file,
            "candidates": normalized_exact_matches,
            "message": f"已匹配文件：{matched_file}"
        }

    if len(normalized_exact_matches) > 1:
        preferred_matches = prefer_source_document(normalized_exact_matches, raw_query)
        if len(preferred_matches) == 1:
            matched_file = preferred_matches[0]
            return {
                "status": "matched",
                "matched_file": matched_file,
                "candidates": preferred_matches,
                "message": f"已匹配文件：{matched_file}"
            }

        return {
            "status": "multiple",
            "matched_file": "",
            "candidates": normalized_exact_matches,
            "message": build_match_message(raw_query, "multiple", normalized_exact_matches)
        }

    contains_matches = []
    for file_name in supported_files:
        normalized_name = normalize_text(file_name)
        normalized_stem = normalize_text(Path(file_name).stem)

        for term in query_terms:
            if term in normalized_name or term in normalized_stem:
                contains_matches.append(file_name)
                break

    if len(contains_matches) == 1:
        matched_file = contains_matches[0]
        return {
            "status": "matched",
            "matched_file": matched_file,
            "candidates": contains_matches,
            "message": f"已匹配文件：{matched_file}"
        }

    if len(contains_matches) > 1:
        preferred_matches = prefer_source_document(contains_matches, raw_query)
        if len(preferred_matches) == 1:
            matched_file = preferred_matches[0]
            return {
                "status": "matched",
                "matched_file": matched_file,
                "candidates": preferred_matches,
                "message": f"已匹配文件：{matched_file}"
            }

        return {
            "status": "multiple",
            "matched_file": "",
            "candidates": contains_matches,
            "message": build_match_message(raw_query, "multiple", contains_matches)
        }

    return {
        "status": "not_found",
        "matched_file": "",
        "candidates": supported_files,
        "message": build_match_message(raw_query, "not_found", supported_files)
    }


def resolve_workspace_file_name(file_name_or_query: str) -> dict:
    """
    统一解析 workspace 文件名：完整文件名直接使用，关键词走智能匹配。
    """
    raw_query = (file_name_or_query or "").strip()

    if not raw_query:
        return {
            "ok": False,
            "file_name": "",
            "error_type": "empty_file_name",
            "message": "文件名不能为空。",
            "candidates": []
        }

    input_path = Path(raw_query)
    if input_path.is_absolute() or ".." in input_path.parts:
        return {
            "ok": False,
            "file_name": "",
            "error_type": "invalid_path",
            "message": "非法文件路径：只能访问 workspace 目录内的文件。",
            "candidates": []
        }

    exact_path = safe_path(raw_query)
    if exact_path.exists() and exact_path.is_file() and exact_path.suffix.lower() not in SUPPORTED_READ_EXTENSIONS:
        return {
            "ok": False,
            "file_name": "",
            "error_type": "unsupported_format",
            "message": (
                f"暂时只支持读取 .txt、.md、.pdf 和 .docx 文件，"
                f"当前文件格式不支持：{exact_path.name}"
            ),
            "candidates": get_supported_workspace_files()
        }

    match_result = find_matching_files(raw_query)
    status = match_result["status"]

    if status == "matched":
        return {
            "ok": True,
            "file_name": match_result["matched_file"],
            "error_type": "none",
            "message": match_result["message"],
            "candidates": match_result["candidates"]
        }

    if status == "multiple":
        return {
            "ok": False,
            "file_name": "",
            "error_type": "multiple_matches",
            "message": match_result["message"],
            "candidates": match_result["candidates"]
        }

    return {
        "ok": False,
        "file_name": "",
        "error_type": "file_not_found",
        "message": match_result["message"],
        "candidates": match_result["candidates"]
    }


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
    resolution = resolve_workspace_file_name(file_name)
    if not resolution["ok"]:
        return resolution["message"]

    file_name = resolution["file_name"]

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
    resolution = resolve_workspace_file_name(file_name)
    if not resolution["ok"]:
        return resolution["message"]

    file_name = resolution["file_name"]

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
