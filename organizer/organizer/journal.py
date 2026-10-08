"""操作日志与「撤销上次操作」。"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

JOURNAL_NAME = ".organizer_journal.json"


def journal_path(root: str | Path) -> Path:
    return Path(root) / JOURNAL_NAME


def load_journal(root: str | Path) -> list[dict]:
    path = journal_path(root)
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    return data if isinstance(data, list) else []


def save_journal(root: str | Path, records: list[dict]) -> None:
    journal_path(root).write_text(
        json.dumps(records, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _relative(path: Path, root: Path) -> str:
    """尽量存相对路径，整个目录搬走也不影响撤销。"""
    resolved = Path(path).resolve()
    try:
        return str(resolved.relative_to(root.resolve()))
    except ValueError:
        return str(resolved)


def _absolute(value: str, root: Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else root / path


def record_operation(
    root: str | Path,
    operation: str,
    entries: list[tuple[Path, Path]],
) -> dict:
    """把一次操作追加进日志；entries 是 [(src, dst)]。"""
    root = Path(root)
    payload = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "operation": operation,
        "entries": [
            {"src": _relative(src, root), "dst": _relative(dst, root)}
            for src, dst in entries
        ],
    }
    records = load_journal(root)
    records.append(payload)
    save_journal(root, records)
    return payload


@dataclass
class UndoAction:
    """一次反向操作：把 current 还原回 target。"""

    current: Path
    target: Path
    status: str  # "ok" | "skip"
    reason: str = ""

    @property
    def ok(self) -> bool:
        return self.status == "ok"


def build_undo_plan(root: str | Path) -> tuple[dict | None, list[UndoAction]]:
    """读取最近一条日志，算出反向操作。不改磁盘。"""
    root = Path(root)
    records = load_journal(root)
    if not records:
        return None, []

    last = records[-1]
    actions: list[UndoAction] = []

    # 逆序还原，先把最后改的还回去
    for entry in reversed(last.get("entries", [])):
        current = _absolute(entry["dst"], root)
        target = _absolute(entry["src"], root)

        if not current.exists():
            actions.append(UndoAction(current, target, "skip", "文件已不在原位"))
        elif target.exists():
            actions.append(UndoAction(current, target, "skip", "原位置已被占用"))
        else:
            actions.append(UndoAction(current, target, "ok"))

    return last, actions


def apply_undo_plan(root: str | Path, actions: list[UndoAction]) -> int:
    """执行反向操作，成功几个返回几个；最后把日志记录弹掉。"""
    root = Path(root)
    count = 0

    for action in actions:
        if not action.ok:
            continue
        try:
            action.target.parent.mkdir(parents=True, exist_ok=True)
            action.current.rename(action.target)
        except OSError as exc:
            action.status = "skip"
            action.reason = f"还原失败：{exc}"
            continue
        count += 1

    records = load_journal(root)
    if records:
        records.pop()
        save_journal(root, records)

    return count
