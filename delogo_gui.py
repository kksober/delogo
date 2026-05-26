#!/usr/bin/env python3
"""
豆包去水印工具 - 桌面版
支持: 拖拽单张图片 / 拖拽文件夹批量处理
"""

import cv2
import numpy as np
import os
import sys
import threading
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, ttk


def remove_watermark(img_path, output_path=None):
    """核心去水印逻辑"""
    img = cv2.imread(str(img_path))
    if img is None:
        return False

    h, w = img.shape[:2]
    rx, ry = max(0, w - 260), max(0, h - 90)
    roi = img[ry:h, rx:w]
    rh, rw = roi.shape[:2]
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)

    masks = []
    # Laplacian
    lap = cv2.Laplacian(gray, cv2.CV_16S, ksize=5)
    _, m1 = cv2.threshold(cv2.convertScaleAbs(lap), 12, 255, cv2.THRESH_BINARY)
    m1 = cv2.dilate(m1, np.ones((2, 3), np.uint8), iterations=2)
    masks.append(m1)
    # Sobel
    sx = cv2.Sobel(gray, cv2.CV_16S, 1, 0, ksize=3)
    sy = cv2.Sobel(gray, cv2.CV_16S, 0, 1, ksize=3)
    mag = cv2.convertScaleAbs(cv2.magnitude(sx.astype(float), sy.astype(float)))
    _, m2 = cv2.threshold(mag, 20, 255, cv2.THRESH_BINARY)
    m2 = cv2.dilate(m2, np.ones((2, 2), np.uint8), iterations=2)
    masks.append(m2)
    # 亮度差分
    _, m3 = cv2.threshold(cv2.subtract(gray, cv2.GaussianBlur(gray, (15, 15), 0)),
                          0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    m3 = cv2.morphologyEx(m3, cv2.MORPH_CLOSE, np.ones((2, 2), np.uint8))
    masks.append(m3)
    # 白色像素
    rgb_f = roi.astype(float)
    ws = rgb_f.mean(axis=2) - rgb_f.std(axis=2)
    _, m4 = cv2.threshold(ws.astype(np.uint8), 200, 255, cv2.THRESH_BINARY)
    masks.append(m4)

    combined = sum((m > 0).astype(np.uint8) for m in masks)
    final = (combined >= 2).astype(np.uint8) * 255
    final = cv2.morphologyEx(final, cv2.MORPH_CLOSE, np.ones((3, 3)))
    final = cv2.morphologyEx(final, cv2.MORPH_OPEN, np.ones((2, 2)))
    n, labels, stats, _ = cv2.connectedComponentsWithStats(final, 8)
    for i in range(1, n):
        if stats[i, cv2.CC_STAT_AREA] < 30:
            final[labels == i] = 0

    mask = np.zeros((h, w), dtype=np.uint8)
    mask[ry:ry+rh, rx:rx+rw] = final
    mask = cv2.GaussianBlur(mask.astype(float), (0, 0), 3)
    mask = cv2.normalize(mask, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)

    result = cv2.inpaint(img, mask, inpaintRadius=5, flags=cv2.INPAINT_TELEA)

    if output_path is None:
        stem = Path(img_path).stem
        ext = Path(img_path).suffix
        output_path = Path(img_path).parent / f"{stem}_nologo{ext}"
    cv2.imwrite(str(output_path), result)
    return True


class DelogoApp:
    def __init__(self):
        self.win = tk.Tk()
        self.win.title("豆包去水印工具")
        self.win.geometry("520x400")
        self.win.configure(bg="#f0f0f0")

        # 图标
        try:
            self.win.iconbitmap(default="")
        except:
            pass

        title = tk.Label(self.win, text="豆包去水印工具", font=("Microsoft YaHei", 16, "bold"),
                         bg="#f0f0f0", fg="#333")
        title.pack(pady=(20, 5))

        desc = tk.Label(self.win, text="拖拽图片或文件夹到窗口，或点击下方按钮选择",
                        font=("Microsoft YaHei", 10), bg="#f0f0f0", fg="#666")
        desc.pack(pady=(0, 15))

        # 拖拽区域
        self.drop_frame = tk.Frame(self.win, bg="white", highlightbackground="#ccc",
                                   highlightthickness=2, bd=0, relief="solid")
        self.drop_frame.pack(padx=30, pady=5, fill=tk.BOTH, expand=True)

        self.drop_label = tk.Label(self.drop_frame,
                                   text="📂 拖拽图片或文件夹到这里\n\n支持格式: PNG / JPG / JPEG / WEBP",
                                   font=("Microsoft YaHei", 11), bg="white", fg="#999")
        self.drop_label.pack(expand=True)

        # 按钮区
        btn_frame = tk.Frame(self.win, bg="#f0f0f0")
        btn_frame.pack(pady=(10, 5))

        self.btn_file = tk.Button(btn_frame, text="选择单张图片", command=self.select_file,
                                  font=("Microsoft YaHei", 10), bg="#4a90d9", fg="white",
                                  relief="flat", padx=15, pady=5, cursor="hand2")
        self.btn_file.pack(side=tk.LEFT, padx=5)

        self.btn_folder = tk.Button(btn_frame, text="选择文件夹（批量）", command=self.select_folder,
                                    font=("Microsoft YaHei", 10), bg="#50b86c", fg="white",
                                    relief="flat", padx=15, pady=5, cursor="hand2")
        self.btn_folder.pack(side=tk.LEFT, padx=5)

        # 进度条
        self.progress = ttk.Progressbar(self.win, mode='determinate')
        self.progress.pack(padx=30, pady=(5, 0), fill=tk.X)

        # 状态
        self.status = tk.Label(self.win, text="就绪", font=("Microsoft YaHei", 9),
                               bg="#f0f0f0", fg="#888", anchor="w")
        self.status.pack(padx=30, pady=(5, 15), fill=tk.X)

        # 绑定拖拽
        self.drop_frame.bind("<Enter>", lambda e: self.drop_frame.configure(highlightbackground="#4a90d9"))
        self.drop_frame.bind("<Leave>", lambda e: self.drop_frame.configure(highlightbackground="#ccc"))
        self.win.drop_target_register = None

        # macOS 不支持 tkinter 原生拖拽，但 Windows 可以用 tkinterdnd2
        # 这里手动处理：加提示让用户用按钮
        if sys.platform == "darwin":
            self.drop_label.config(text="📂 点击下方按钮选择图片或文件夹\n\n支持格式: PNG / JPG / JPEG / WEBP")

    def log(self, msg):
        self.status.config(text=msg)
        self.win.update()

    def run_single(self, path):
        self.log(f"处理中: {Path(path).name}")
        ok = remove_watermark(path)
        if ok:
            self.log(f"✅ 完成: {Path(path).stem}_nologo{Path(path).suffix}")
        else:
            self.log(f"❌ 失败: 无法读取图片")
        self.progress["value"] = 0

    def run_batch(self, folder):
        exts = (".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff")
        files = [f for f in sorted(Path(folder).iterdir())
                 if f.suffix.lower() in exts and f.is_file()]
        if not files:
            self.log("❌ 该文件夹中没有图片文件")
            self.progress["value"] = 0
            return

        self.progress["maximum"] = len(files)
        ok = 0
        for i, f in enumerate(files):
            self.log(f"[{i+1}/{len(files)}] {f.name}")
            self.progress["value"] = i + 1
            self.win.update()
            if remove_watermark(str(f)):
                ok += 1

        self.log(f"✅ 批量完成: {ok}/{len(files)} 成功")
        self.progress["value"] = 0

    def select_file(self):
        path = filedialog.askopenfilename(
            title="选择图片",
            filetypes=[("图片文件", "*.png *.jpg *.jpeg *.webp *.bmp *.tiff")]
        )
        if not path:
            return
        threading.Thread(target=self.run_single, args=(path,), daemon=True).start()

    def select_folder(self):
        folder = filedialog.askdirectory(title="选择文件夹")
        if not folder:
            return
        threading.Thread(target=self.run_batch, args=(folder,), daemon=True).start()

    def run(self):
        self.win.mainloop()


if __name__ == "__main__":
    # 支持命令行参数: 拖拽文件到 exe 图标上
    if len(sys.argv) > 1:
        path = sys.argv[1]
        if os.path.isdir(path):
            exts = (".png", ".jpg", ".jpeg", ".webp")
            files = [f for f in Path(path).iterdir() if f.suffix.lower() in exts]
            for i, f in enumerate(files):
                print(f"[{i+1}/{len(files)}] {f.name}")
                remove_watermark(str(f))
            print(f"完成: {len(files)} 张图片")
        else:
            if remove_watermark(path):
                print(f"✅ 完成")
            else:
                print(f"❌ 失败")
        input("按回车退出...")
    else:
        app = DelogoApp()
        app.run()
