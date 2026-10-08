"""命令行入口。"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

from .renamer import apply_rename_plan, build_rename_plan
from .scanner import scan_files
from .utils import confirm, human_size

REPORT_NAME = "organizer_report.txt"


def _write_report(root: Path, lines: list[str]) -> None:
    path = Path(root) / REPORT_NAME
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\n报告已写入：{path}")


def cmd_scan(args: argparse.Namespace) -> int:
    try:
        files = scan_files(args.dir, args.ext, recursive=not args.no_recursive)
    except (FileNotFoundError, NotADirectoryError) as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 1

    if not files:
        print("没有找到匹配的文件。")
        return 0

    print(f"{'文件名':<44}{'大小':>10}  {'修改时间':<20}")
    print("-" * 78)
    for info in files:
        name = info.name if len(info.name) <= 42 else info.name[:39] + "..."
        print(f"{name:<44}{human_size(info.size):>10}  {info.mtime:%Y-%m-%d %H:%M:%S}")
    print(f"\n共 {len(files)} 个文件。")
    return 0


def cmd_rename(args: argparse.Namespace) -> int:
    root = Path(args.dir)
    try:
        files = scan_files(root, args.ext)
    except (FileNotFoundError, NotADirectoryError) as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 1

    if not files:
        print("没有找到匹配的文件。")
        return 0

    plan = build_rename_plan(files, args.from_template, args.to_template)
    ok = [a for a in plan if a.ok]
    skipped = [a for a in plan if not a.ok]

    # ---------- 预览 ----------
    print("将要执行的改名：")
    if ok:
        for action in ok:
            mark = " *" if action.conflict else "  "
            print(f"{mark} {action.src.name}  ->  {action.dst.name}")
            if action.reason:
                print(f"      ! {action.reason}")
    else:
        print("  （没有可改名的文件）")

    if skipped:
        print("\n跳过：")
        for action in skipped:
            print(f"  - {action.src.name}：{action.reason}")

    print(f"\n合计：可改 {len(ok)} 个，跳过 {len(skipped)} 个。")

    # ---------- 确认 ----------
    if not args.apply:
        print("\n当前是预览模式，未修改任何文件。确认无误后加 --apply 执行。")
        return 0

    if not ok:
        print("没有需要执行的操作。")
        return 0

    if not args.yes and not confirm("\n确认执行以上改名？[y/N] "):
        print("已取消，未修改任何文件。")
        return 0

    # ---------- 执行 ----------
    done = apply_rename_plan(plan)
    print(f"\n已完成改名 {len(done)} 个文件。")

    done_pairs = {(str(src), str(dst)) for src, dst in done}
    lines = [
        "操作：批量改名（rename）",
        f"时间：{datetime.now():%Y-%m-%d %H:%M:%S}",
        f"目录：{root}",
        f"模板：{args.from_template}  ->  {args.to_template}",
        "",
        f"处理 {len(done)} 个，跳过 {len(plan) - len(done)} 个。",
        "",
    ]
    for action in plan:
        if action.dst is not None and (str(action.src), str(action.dst)) in done_pairs:
            lines.append(f"[OK]   {action.src.name} -> {action.dst.name}")
        else:
            lines.append(f"[SKIP] {action.src.name}：{action.reason or '未知原因'}")

    _write_report(root, lines)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="organizer",
        description="批量整理作业文件的小工具（扫描 / 改名 / 归档 / 撤销）",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_scan = sub.add_parser("scan", help="扫描并列出文件")
    p_scan.add_argument("dir", nargs="?", default=".", help="要扫描的目录，默认当前目录")
    p_scan.add_argument(
        "--ext",
        action="append",
        metavar="EXT",
        help="只看这些扩展名，可重复，也可用逗号分隔，例如 --ext docx,pdf",
    )
    p_scan.add_argument("--no-recursive", action="store_true", help="不递归子目录")
    p_scan.set_defaults(func=cmd_scan)

    p_rename = sub.add_parser("rename", help="按模板批量改名（默认只预览）")
    p_rename.add_argument("dir", nargs="?", default=".")
    p_rename.add_argument(
        "--from",
        dest="from_template",
        required=True,
        metavar="模板",
        help="原文件名模板，例如 '{学号}_{姓名}_{作业名}.{ext}'",
    )
    p_rename.add_argument(
        "--to",
        dest="to_template",
        required=True,
        metavar="模板",
        help="新文件名模板，例如 '{作业名}_{学号}.{ext}'",
    )
    p_rename.add_argument("--ext", action="append", metavar="EXT", help="只看这些扩展名")
    p_rename.add_argument("--apply", action="store_true", help="真正执行（默认只预览）")
    p_rename.add_argument("--yes", action="store_true", help="跳过交互确认")
    p_rename.set_defaults(func=cmd_rename)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args) or 0
