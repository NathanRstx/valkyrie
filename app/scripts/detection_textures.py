# scripts/detection_texture.py
import argparse
from pathlib import Path
from typing import Tuple, List

import numpy as np
import cv2


# ---------- IO ----------

def read_index(path: Path) -> np.ndarray:
    if path.suffix.lower() == ".npy":
        return np.load(path).astype(np.float32)

    img = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    if img is None:
        raise FileNotFoundError(f"Cannot read {path}")
    if img.ndim == 3:
        img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    orig_dtype = img.dtype
    img = img.astype(np.float32)
    if np.issubdtype(orig_dtype, np.integer):
        img /= float(np.iinfo(orig_dtype).max)
    return img


def save_u8(path: Path, x01: np.ndarray):
    x01 = np.clip(x01, 0, 1)
    cv2.imwrite(str(path), (x01 * 255).astype(np.uint8))


# ---------- Texture detection core ----------

def detect_texture_anomalies(
    idx: np.ndarray,
    win: int = 31,
    top_pct: float = 5.0,
    min_area: int = 100
) -> Tuple[np.ndarray, np.ndarray, List[Tuple]]:

    win = win if win % 2 == 1 else win + 1
    # Lissage léger pour limiter la sensibilité au bruit avant le calcul du gradient.
    idx_smooth = cv2.GaussianBlur(idx, (5, 5), 0)

    # Calcul du gradient (texture locale)
    gx = cv2.Sobel(idx_smooth, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(idx_smooth, cv2.CV_32F, 0, 1, ksize=3)
    grad = np.sqrt(gx**2 + gy**2)

    # Énergie locale du gradient
    texture_map = cv2.blur(grad, (win, win))

    print(f"[DEBUG] texture min/max: {texture_map.min():.4f} / {texture_map.max():.4f}")

    # Normalisation pour visualisation
    texture01 = (texture_map - texture_map.min()) / (
        texture_map.max() - texture_map.min() + 1e-6
    )

    # Seuillage par percentile
    pct = min(max(top_pct, 0.1), 50.0)
    thr = np.percentile(texture_map, 100.0 - pct)
    mask = (texture_map >= thr).astype(np.uint8) * 255

    print(f"[DEBUG] threshold (top {pct}%) = {thr:.4f}")

    # Nettoyage morphologique
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)

    # Extraction des composantes connexes
    num, labels, stats, centroids = cv2.connectedComponentsWithStats(mask, connectivity=8)

    candidates = []
    for i in range(1, num):
        x, y, w, h, area = stats[i]
        if area >= min_area:
            cx, cy = centroids[i]
            candidates.append((area, x, y, w, h, cx, cy))

    candidates.sort(reverse=True)

    return texture01, mask, candidates


# ---------- Main ----------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--index", required=True, help="Chemin vers NDVI/NDRE (.npy ou image)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--win", type=int, default=31)
    ap.add_argument("--top_pct", type=float, default=5.0)
    ap.add_argument("--min_area", type=int, default=100)
    args = ap.parse_args()

    idx = read_index(Path(args.index))

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    texture01, mask, candidates = detect_texture_anomalies(
        idx,
        win=args.win,
        top_pct=args.top_pct,
        min_area=args.min_area,
    )

    save_u8(out / "texture_map.png", texture01)
    cv2.imwrite(str(out / "mask.png"), mask)

    # overlay
    base = idx.copy()
    if base.min() < 0:
        base = np.clip((base + 1) * 0.5, 0, 1)
    else:
        base = np.clip(base, 0, 1)

    base_u8 = (base * 255).astype(np.uint8)
    overlay = cv2.cvtColor(base_u8, cv2.COLOR_GRAY2BGR)

    for k, (area, x, y, w, h, cx, cy) in enumerate(candidates[:30], start=1):
        cv2.rectangle(overlay, (x, y), (x + w, y + h), (0, 0, 255), 2)
        cv2.putText(overlay, str(k), (x, max(0, y - 6)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

    cv2.imwrite(str(out / "candidates.png"), overlay)

    # Save candidates to txt
    with open(out / "candidates.txt", "w") as f:
        for k, (area, x, y, w, h, cx, cy) in enumerate(candidates, start=1):
            f.write(f"{k}: area={area}, x={x}, y={y}, w={w}, h={h}, cx={cx:.1f}, cy={cy:.1f}\n")

    print(f"OK: {len(candidates)} zones candidates détectées")
    print(f"Outputs: {out}")


if __name__ == "__main__":
    main()

