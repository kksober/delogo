#!/usr/bin/env python3
"""
豆包 AI 图片去水印工具
"""

import cv2
import numpy as np
import sys
from pathlib import Path


def _build_watermark_mask(img):
    h, w = img.shape[:2]
    rx, ry = max(0, w - 260), max(0, h - 90)
    roi = img[ry:h, rx:w]
    rh, rw = roi.shape[:2]

    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    masks = []

    # A: Laplacian
    lap = cv2.Laplacian(gray, cv2.CV_16S, ksize=5)
    lap_abs = cv2.convertScaleAbs(lap)
    _, m1 = cv2.threshold(lap_abs, 12, 255, cv2.THRESH_BINARY)
    m1 = cv2.dilate(m1, np.ones((2, 3), np.uint8), iterations=2)
    masks.append(m1)

    # B: Sobel
    sobelx = cv2.Sobel(gray, cv2.CV_16S, 1, 0, ksize=3)
    sobely = cv2.Sobel(gray, cv2.CV_16S, 0, 1, ksize=3)
    mag = cv2.convertScaleAbs(cv2.magnitude(sobelx.astype(float), sobely.astype(float)))
    _, m2 = cv2.threshold(mag, 20, 255, cv2.THRESH_BINARY)
    m2 = cv2.dilate(m2, np.ones((2, 2), np.uint8), iterations=2)
    masks.append(m2)

    # C: 亮度差分 (OTSU 自适应)
    blurred = cv2.GaussianBlur(gray, (15, 15), 0)
    diff = cv2.subtract(gray, blurred)
    _, m3 = cv2.threshold(diff, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    m3 = cv2.morphologyEx(m3, cv2.MORPH_CLOSE, np.ones((2, 2), np.uint8))
    masks.append(m3)

    # D: 白色像素
    rgb = roi.astype(np.float32)
    r, g, b = rgb[:,:,2], rgb[:,:,1], rgb[:,:,0]
    brightness = (r + g + b) / 3
    color_std = np.std(rgb, axis=2)
    white_score = brightness - color_std
    _, m4 = cv2.threshold(white_score.astype(np.uint8), 200, 255, cv2.THRESH_BINARY)
    masks.append(m4)

    # 融合: ≥2 种同意
    combined = np.zeros((rh, rw), dtype=np.uint8)
    for m in masks:
        combined += (m > 0).astype(np.uint8)
    final = (combined >= 2).astype(np.uint8) * 255

    # 清理
    kernel = np.ones((3, 3), np.uint8)
    final = cv2.morphologyEx(final, cv2.MORPH_CLOSE, kernel)
    final = cv2.morphologyEx(final, cv2.MORPH_OPEN, kernel)

    # 去小噪点 (面积 < 30)
    n, labels, stats, _ = cv2.connectedComponentsWithStats(final, 8)
    for i in range(1, n):
        if stats[i, cv2.CC_STAT_AREA] < 30:
            final[labels == i] = 0

    # 放入全尺寸 + 羽化
    full = np.zeros((h, w), dtype=np.uint8)
    full[ry:ry+rh, rx:rx+rw] = final
    full = cv2.GaussianBlur(full.astype(float), (0, 0), 3)
    full = cv2.normalize(full, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)

    return full


def remove_doubao_watermark(input_path, output_path=None):
    img = cv2.imread(str(input_path))
    if img is None:
        print(f"❌ 无法读取图片: {input_path}")
        return False

    mask = _build_watermark_mask(img)
    px = cv2.countNonZero(mask)

    if px < 20:
        print(f"⚠️  未检测到明显水印 ({px} px)")
        if output_path is None:
            stem = Path(input_path).stem
            ext = Path(input_path).suffix
            output_path = Path(input_path).parent / f"{stem}_nologo{ext}"
        cv2.imwrite(str(output_path), img)
        return True

    result = cv2.inpaint(img, mask, inpaintRadius=5, flags=cv2.INPAINT_TELEA)

    if output_path is None:
        stem = Path(input_path).stem
        ext = Path(input_path).suffix
        output_path = Path(input_path).parent / f"{stem}_nologo{ext}"

    cv2.imwrite(str(output_path), result)
    print(f"✅ 去水印完成: {output_path} ({px} px)")
    return True


def batch_remove(pattern="*.png"):
    files = sorted(Path().glob(pattern))
    ok = 0
    for f in files:
        if remove_doubao_watermark(f):
            ok += 1
    print(f"\n批量完成: {ok}/{len(files)} 成功")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: delogo <图片路径> 或 delogo --batch '*.png'")
        sys.exit(1)
    if sys.argv[1] == "--batch" and len(sys.argv) >= 3:
        batch_remove(sys.argv[2])
    else:
        remove_doubao_watermark(sys.argv[1])
