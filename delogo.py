#!/usr/bin/env python3
"""豆包 AI 图片去水印工具 - CLI"""

import sys
from pathlib import Path
from watermark import remove_watermark


def batch_remove(pattern="*.png"):
    files = sorted(Path().glob(pattern))
    ok, total = 0, len(files)
    for i, f in enumerate(files):
        success, msg = remove_watermark(f)
        print(f"[{i+1}/{total}] {msg}")
        if success:
            ok += 1
    print(f"\n批量完成: {ok}/{total} 成功")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: delogo <图片路径>  或  delogo --batch '*.png'")
        sys.exit(1)
    if sys.argv[1] == "--batch" and len(sys.argv) >= 3:
        batch_remove(sys.argv[2])
    else:
        success, msg = remove_watermark(sys.argv[1])
        print(msg)
