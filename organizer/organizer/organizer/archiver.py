"""需求 3：按类别把文件归档到子文件夹。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .scanner import FileInfo
from .utils import resolve_conflict

ARCHIVE_MODES = ("ext", "year", "month")


@dataclass
class ArchiveAction:
    src: Path
    dst: Path | None
    status: str  # "ok" | "skip"
    reason: str = ""
    conflict: bool = False

    @property
    def ok(self) -> bool:
        return self.status == "ok" and self.dst is not None


def target_folder(info: FileInfo, mode: str) -> str:
    """算出这个文件该进哪个子文件夹。"""
    if mode == "ext":
        return info.ext or "no_ext"
    if mode == "year":
        return f"{info.mtime.year}"
    if mode == "month":
        return f"{info.mtime.year}-{info.mtime.month:02d}"
    raise ValueError(f"未知的归档方式：{mode}")


def build_archive_plan(
    files: list[FileInfo],
    root: str | Path,
    mode: str = "ext",
) -> list[ArchiveAction]:
    """生成归档计划。这一步不碰磁盘。"""
    if mode not in ARCHIVE_MODES:
        raise ValueError(f"未知的归档方式：{mode}")

    root = Path(root)
    taken: set[str] = set()
    actions: list[ArchiveAction] = []

    for info in files:
        dst_dir = root / target_folder(info, mode)

        if info.path.parent == dst_dir:
            actions.append(ArchiveAction(info.path, None, "skip", "已在目标目录"))
            continue

        dst, conflicted = resolve_conflict(dst_dir / info.name, taken)
        taken.add(str(dst).lower())

        reason = f"目标已存在，自动改名为 {dst.name}" if conflicted else ""
        actions.append(ArchiveAction(info.path, dst, "ok", reason, conflict=conflicted))

    return actions


def apply_archive_plan(actions: list[ArchiveAction]) -> list[tuple[Path, Path]]:
    """真正执行移动。返回成功的 [(src, dst)]。"""
    done: list[tuple[Path, Path]] = []

    for action in actions:
        if not action.ok or action.dst is None:
            continue
        try:
            action.dst.parent.mkdir(parents=True, exist_ok=True)
            action.src.rename(action.dst)
        except OSError as exc:
            action.status = "skip"
            action.reason = f"移动失败：{exc}"
            continue
        done.append((action.src, action.dst))

    return done
