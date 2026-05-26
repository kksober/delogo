#!/usr/bin/env python3
"""
豆包生成图片 → 自动提取原图 → 去水印
依赖: OpenCLI Browser Bridge + Chrome 登录豆包

用法: ~/.venv/bin/python3 doubao_gen.py "绘画提示词"
"""

import subprocess
import sys
import time
import json
import re
from pathlib import Path

SESSION = "doubao"
OUT_DIR = Path.home() / "Sandbox"

def run(cmd, capture=True):
    print(f"  $ {cmd}")
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"  ⚠️  exit: {r.returncode}")
    return r.stdout.strip() if capture else r

def gen_and_clean(prompt):
    # 1. 打开豆包
    print("\n1️⃣  打开豆包...")
    run(f'opencli browser {SESSION} open "https://www.doubao.com/chat"')
    time.sleep(5)

    # 2. 让用户手动输入提示词、生成图片
    print("\n2️⃣  请在浏览器中操作:")
    print(f"   输入绘画提示词: \"{prompt}\"")
    print("   点击发送/生成，等待图片生成完毕")
    input("   完成后按回车继续...")

    # 3. 尝试提取页面中的图片 URL
    print("\n3️⃣  提取原图...")

    # 先试几种常见的图片选择器
    img_selectors = [
        'img.generated-image',         # 常见 class
        'img[class*="image"]',          # 含 image 的 class
        'img[class*="result"]',         # 含 result 的 class
        'main img',                     # 主区域里的 img
        'img[src*="blob:"]',           # blob URL
        'img[src*="data:image"]',      # base64
        'div[class*="image"] img',     # 图片容器里的 img
    ]

    found_urls = []
    for sel in img_selectors:
        js = f"""
        (() => {{
            const imgs = document.querySelectorAll('{sel}');
            return Array.from(imgs).slice(0, 5).map(i => ({{
                src: i.src || i.getAttribute('data-src') || '',
                alt: i.alt || '',
                cls: i.className,
                rect: i.getBoundingClientRect()
            }}));
        }})()
        """
        out = run(f'opencli browser {SESSION} eval \'{js}\'')
        try:
            data = json.loads(out)
            if isinstance(data, list) and len(data) > 0:
                for item in data:
                    src = item.get('src', '')
                    if src and len(src) > 50:
                        found_urls.append(item)
        except:
            pass

    # 4. 如果找到了图片 URL，下载
    if found_urls:
        print(f"\n   找到 {len(found_urls)} 个图片，下载最大的...")
        # 按面积排序取最大的
        found_urls.sort(key=lambda x: x.get('rect', {}).get('width', 0) * x.get('rect', {}).get('height', 0), reverse=True)
        best = found_urls[0]
        url = best['src']

        ts = time.strftime("%Y%m%d_%H%M%S")
        out_path = OUT_DIR / f"doubao_{ts}.png"

        # 下载
        r = subprocess.run(['curl', '-s', '-o', str(out_path), url], capture_output=True)
        if r.returncode == 0 and out_path.stat().st_size > 1000:
            print(f"   已下载原图: {out_path} ({out_path.stat().st_size // 1024} KB)")
            # 去水印
            print("\n4️⃣  去水印...")
            subprocess.run([
                str(Path.home() / ".venv/bin/python3"),
                str(Path.home() / "Sandbox/tools/delogo/delogo.py"),
                str(out_path)
            ])
            return

    # 5. 如果提取失败，回退到截图
    print("   未找到图片 URL，回退到截图方案...")
    ts = time.strftime("%Y%m%d_%H%M%S")
    out = OUT_DIR / f"doubao_{ts}.png"
    run(f'opencli browser {SESSION} screenshot "{out}"')

    if out.exists():
        print(f"\n4️⃣  去水印...")
        subprocess.run([
            str(Path.home() / ".venv/bin/python3"),
            str(Path.home() / "Sandbox/tools/delogo/delogo.py"),
            str(out)
        ])

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python3 doubao_gen.py <你的绘画提示词>")
        print("示例: python3 doubao_gen.py '一只坐在云上的猫，水墨风格'")
        sys.exit(1)
    gen_and_clean(" ".join(sys.argv[1:]))
