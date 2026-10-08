"""命令行入口。"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .scanner import scan_files
from .utils import human_size


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

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args) or 0
