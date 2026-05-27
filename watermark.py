"""
豆包 AI 水印去除核心算法
"""

import cv2
import numpy as np
from pathlib import Path


def _imread(path):
    """跨平台安全的图片读取 (Windows cv2.imread 不支持中文路径)"""
    data = np.fromfile(str(path), dtype=np.uint8)
    img = cv2.imdecode(data, cv2.IMREAD_COLOR)
    return img


def _imwrite(path, img):
    """跨平台安全的图片写入"""
    ext = Path(path).suffix or ".png"
    _, buf = cv2.imencode(ext, img)
    buf.tofile(str(path))


def build_watermark_mask(img):
    h, w = img.shape[:2]
    roi_w = max(180, int(w * 0.22))
    roi_h = max(60, int(h * 0.08))
    rx, ry = max(0, w - roi_w), max(0, h - roi_h)
    roi = img[ry:h, rx:w]
    rh, rw = roi.shape[:2]

    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    masks = []

    # A: Laplacian
    lap = cv2.Laplacian(gray, cv2.CV_16S, ksize=5)
    _, m1 = cv2.threshold(cv2.convertScaleAbs(lap), 12, 255, cv2.THRESH_BINARY)
    m1 = cv2.dilate(m1, np.ones((2, 3), np.uint8), iterations=2)
    masks.append(m1)

    # B: Sobel
    sx = cv2.Sobel(gray, cv2.CV_16S, 1, 0, ksize=3)
    sy = cv2.Sobel(gray, cv2.CV_16S, 0, 1, ksize=3)
    mag = cv2.convertScaleAbs(cv2.magnitude(sx.astype(float), sy.astype(float)))
    _, m2 = cv2.threshold(mag, 20, 255, cv2.THRESH_BINARY)
    m2 = cv2.dilate(m2, np.ones((2, 2), np.uint8), iterations=2)
    masks.append(m2)

    # C: 亮度差分 + OTSU
    _, m3 = cv2.threshold(
        cv2.subtract(gray, cv2.GaussianBlur(gray, (15, 15), 0)),
        0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    m3 = cv2.morphologyEx(m3, cv2.MORPH_CLOSE, np.ones((2, 2), np.uint8))
    masks.append(m3)

    # D: 白色像素
    rgb_f = roi.astype(float)
    ws = rgb_f.mean(axis=2) - rgb_f.std(axis=2)
    _, m4 = cv2.threshold(ws.astype(np.uint8), 200, 255, cv2.THRESH_BINARY)
    masks.append(m4)

    # 融合: >=2 种方法一致
    combined = sum((m > 0).astype(np.uint8) for m in masks)
    final = (combined >= 2).astype(np.uint8) * 255

    # 形态学清理
    final = cv2.morphologyEx(final, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
    final = cv2.morphologyEx(final, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))

    # 去小噪点 (最小面积按图片尺寸缩放)
    min_area = max(20, int((w * h) / 55000))
    n, labels, stats, _ = cv2.connectedComponentsWithStats(final, 8)
    for i in range(1, n):
        if stats[i, cv2.CC_STAT_AREA] < min_area:
            final[labels == i] = 0

    # 放入全图 + 羽化
    full = np.zeros((h, w), dtype=np.uint8)
    full[ry:ry + rh, rx:rx + rw] = final
    full = cv2.GaussianBlur(full.astype(float), (0, 0), 3)
    full = cv2.normalize(full, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)

    return full


def remove_watermark(input_path, output_path=None):
    img = _imread(input_path)
    if img is None:
        return False, "无法读取图片"

    mask = build_watermark_mask(img)
    px = int(cv2.countNonZero(mask))

    if output_path is None:
        p = Path(input_path)
        output_path = p.parent / f"{p.stem}_nologo{p.suffix}"

    if px < 20:
        _imwrite(output_path, img)
        return True, f"未检测到明显水印 ({px} px), 已复制原图"

    radius = max(3, min(10, int(min(img.shape[0], img.shape[1]) / 256)))
    result = cv2.inpaint(img, mask, inpaintRadius=radius, flags=cv2.INPAINT_TELEA)
    _imwrite(output_path, result)
    return True, f"去水印完成 ({px} px)"
