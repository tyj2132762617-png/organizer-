
---

## PR #2 · 批量改名

### `organizer/renamer.py`（新增）

```python
"""需求 2：按模板批量改名。默认只预览，加 --apply 才真正执行，且绝不覆盖已有文件。"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .scanner import FileInfo
from .utils import resolve_conflict, sanitize_filename

_PLACEHOLDER = re.compile(r"\{(\w+)\}")


def template_to_regex(template: str) -> str:
    """把 '{学号}_{姓名}_{作业名}.{ext}' 这样的模板编译成正则表达式。"""
    parts: list[str] = []
    cursor = 0
    for match in _PLACEHOLDER.finditer(template):
        parts.append(re.escape(template[cursor:match.start()]))
        parts.append(f"(?P<{match.group(1)}>.+?)")
        cursor = match.end()
    parts.append(re.escape(template[cursor:]))
    return "".join(parts)


def parse_filename(name: str, template: str) -> dict[str, str] | None:
    """按模板拆解文件名；拆不出来返回 None。"""
    match = re.fullmatch(template_to_regex(template), name)
    if match is None:
        return None
    return {key: value for key, value in match.groupdict().items() if value is not None}


@dataclass
class RenameAction:
    """一个待执行的改名动作。"""

    src: Path
    dst: Path | None
    status: str  # "ok" | "skip"
    reason: str = ""
    conflict: bool = False

    @property
    def ok(self) -> bool:
        return self.status == "ok" and self.dst is not None


def build_rename_plan(
    files: list[FileInfo],
    from_template: str,
    to_template: str,
) -> list[RenameAction]:
    """
    根据模板生成改名计划。这一步不碰磁盘，只是算出「打算改成什么」。
    重名冲突会在这里就地解决（加 (2)、(3) 后缀）。
    """
    taken: set[str] = set()
    actions: list[RenameAction] = []

    for info in files:
        src = info.path

        parsed = parse_filename(src.name, from_template)
        if parsed is None:
            actions.append(RenameAction(src, None, "skip", "文件名不匹配 --from 模板"))
            continue

        try:
            new_name = sanitize_filename(to_template.format(**parsed))
        except KeyError as exc:
            actions.append(
                RenameAction(src, None, "skip", f"--to 模板用到了未解析出的字段 {exc}")
            )
            continue

        dst = src.with_name(new_name)
        if dst == src:
            actions.append(RenameAction(src, None, "skip", "新旧文件名一致"))
            continue

        dst, conflicted = resolve_conflict(dst, taken)
        taken.add(str(dst).lower())

        reason = f"目标已存在，自动改名为 {dst.name}" if conflicted else ""
        actions.append(RenameAction(src, dst, "ok", reason, conflict=conflicted))

    return actions


def apply_rename_plan(actions: list[RenameAction]) -> list[tuple[Path, Path]]:
    """
    真正执行改名。单个文件失败不影响其它文件。
    返回成功改名的 [(src, dst)]。
    """
    done: list[tuple[Path, Path]] = []

    for action in actions:
        if not action.ok or action.dst is None:
            continue
        try:
            action.src.rename(action.dst)
        except OSError as exc:
            action.status = "skip"
            action.reason = f"改名失败：{exc}"
            continue
        done.append((action.src, action.dst))

    return done
