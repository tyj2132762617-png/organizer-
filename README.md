# organizer-
"""需求 1：扫描目录、按扩展名过滤、列出文件信息。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .utils import GENERATED_FILES


@dataclass(frozen=True)
class FileInfo:
    """一个待处理的文件。"""

    path: Path
    size: int
    mtime: datetime

    @property
    def name(self) -> str:
        return self.path.name

    @property
    def ext(self) -> str:
        """不含点的小写扩展名；没有扩展名时返回空串。"""
        return self.path.suffix.lower().lstrip(".")


def parse_extensions(raw: list[str] | None) -> set[str] | None:
    """
    把命令行传来的 ['docx,pdf'] / ['.docx'] 统一成 {'docx', 'pdf'}。
    没给过滤条件时返回 None。
    """
    if not raw:
        return None

    exts: set[str] = set()
    for item in raw:
        for part in item.split(","):
            cleaned = part.strip().lower().lstrip(".")
            if cleaned:
                exts.add(cleaned)
    return exts or None


def scan_files(
    root: str | Path,
    extensions: list[str] | None = None,
    recursive: bool = True,
) -> list[FileInfo]:
    """扫描 root 下的所有文件，可按扩展名过滤。"""
    root = Path(root)

    if not root.exists():
        raise FileNotFoundError(f"目录不存在：{root}")
    if not root.is_dir():
        raise NotADirectoryError(f"不是目录：{root}")

    exts = parse_extensions(extensions)
    iterator = root.rglob("*") if recursive else root.glob("*")

    files: list[FileInfo] = []
    for path in sorted(iterator, key=lambda p: str(p).lower()):
        if not path.is_file():
            continue
        # 跳过本工具自己生成的文件
        if path.name in GENERATED_FILES:
            continue
        if exts is not None and path.suffix.lower().lstrip(".") not in exts:
            continue

        stat = path.stat()
        files.append(
            FileInfo(
                path=path,
                size=stat.st_size,
                mtime=datetime.fromtimestamp(stat.st_mtime),
            )
        )
    return files
