#!/usr/bin/env python3
"""
豆包去水印工具 - 桌面版
支持: 单张图片 / 文件夹批量处理
"""

import os
import sys
import threading
from pathlib import Path

import tkinter as tk
from tkinter import filedialog, ttk

from watermark import remove_watermark


class DelogoApp:
    def __init__(self):
        self.win = tk.Tk()
        self.win.title("豆包去水印工具")
        self.win.geometry("520x400")
        self.win.configure(bg="#f0f0f0")

        try:
            self.win.iconbitmap(default="")
        except Exception:
            pass

        title = tk.Label(self.win, text="豆包去水印工具", font=("Microsoft YaHei", 16, "bold"),
                         bg="#f0f0f0", fg="#333")
        title.pack(pady=(20, 5))

        desc_text = ("📂 点击下方按钮选择图片或文件夹\n\n支持格式: PNG / JPG / JPEG / WEBP"
                     if sys.platform == "darwin" else
                     "📂 拖拽图片或文件夹到这里\n\n支持格式: PNG / JPG / JPEG / WEBP")
        desc = tk.Label(self.win, text=desc_text,
                        font=("Microsoft YaHei", 10), bg="#f0f0f0", fg="#666")
        desc.pack(pady=(0, 15))

        # 拖拽区域
        self.drop_frame = tk.Frame(self.win, bg="white", highlightbackground="#ccc",
                                   highlightthickness=2, bd=0, relief="solid")
        self.drop_frame.pack(padx=30, pady=5, fill=tk.BOTH, expand=True)

        self.drop_label = tk.Label(self.drop_frame,
                                   text=desc_text,
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

        # 拖拽效果
        self.drop_frame.bind("<Enter>", lambda e: self.drop_frame.configure(highlightbackground="#4a90d9"))
        self.drop_frame.bind("<Leave>", lambda e: self.drop_frame.configure(highlightbackground="#ccc"))

    def log(self, msg):
        self.status.config(text=msg)
        self.win.update()

    def run_single(self, path):
        self.log(f"处理中: {Path(path).name}")
        success, msg = remove_watermark(path)
        self.log(f"{'✅' if success else '❌'} {msg}")
        self.progress["value"] = 0

    def run_batch(self, folder):
        exts = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff"}
        files = [f for f in sorted(Path(folder).iterdir())
                 if f.suffix.lower() in exts and f.is_file()]
        if not files:
            self.log("没有找到图片文件")
            self.progress["value"] = 0
            return

        self.progress["maximum"] = len(files)
        ok, total = 0, len(files)
        for i, f in enumerate(files):
            self.log(f"[{i+1}/{total}] {f.name}")
            self.progress["value"] = i + 1
            self.win.update()
            success, msg = remove_watermark(str(f))
            if success:
                ok += 1

        self.log(f"批量完成: {ok}/{total} 成功")
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
    # 命令行参数: 拖拽文件到 exe 图标
    if len(sys.argv) > 1:
        path = sys.argv[1]
        if os.path.isdir(path):
            exts = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff"}
            files = [f for f in sorted(Path(path).iterdir()) if f.suffix.lower() in exts]
            total = len(files)
            for i, f in enumerate(files):
                success, msg = remove_watermark(str(f))
                print(f"[{i+1}/{total}] {msg}")
        else:
            success, msg = remove_watermark(path)
            print(msg)
        input("按回车退出...")
    else:
        app = DelogoApp()
        app.run()
