import argparse
from pathlib import Path
import numpy as np
import cv2

def load_index(path):
    x = np.load(path).astype(np.float32)
    return x

def extract_patch(arr, x, y, r):
    h, w = arr.shape
    x0, x1 = max(0, x - r), min(w, x + r + 1)
    y0, y1 = max(0, y - r), min(h, y + r + 1)
    patch = arr[y0:y1, x0:x1]
    return patch

def pad_to(patch, shape):
    out = np.zeros(shape, dtype=np.float32)
    h, w = patch.shape
    out[:h, :w] = patch
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ndvi", required=True)
    ap.add_argument("--ndre", required=True)
    ap.add_argument("--x", type=int, required=True)
    ap.add_argument("--y", type=int, required=True)
    ap.add_argument("--radius", type=int, default=7)
    ap.add_argument("--topk", type=int, default=20)
    ap.add_argument("--out", default="results/similarity")
    args = ap.parse_args()

    ndvi = load_index(args.ndvi)
    ndre = load_index(args.ndre)

    h, w = ndvi.shape
    r = args.radius
    patch_shape = (2*r+1, 2*r+1)

    # Patch de référence
    ref_ndvi = pad_to(extract_patch(ndvi, args.x, args.y, r), patch_shape)
    ref_ndre = pad_to(extract_patch(ndre, args.x, args.y, r), patch_shape)
    ref = np.stack([ref_ndvi, ref_ndre], axis=0).reshape(-1)

    scores = []

    for yy in range(r, h - r):
        for xx in range(r, w - r):
            p_ndvi = ndvi[yy-r:yy+r+1, xx-r:xx+r+1]
            p_ndre = ndre[yy-r:yy+r+1, xx-r:xx+r+1]
            p = np.stack([p_ndvi, p_ndre], axis=0).reshape(-1)

            d = np.linalg.norm(p - ref)  # distance euclidienne
            scores.append((d, xx, yy))

    scores.sort(key=lambda x: x[0])
    best = scores[:args.topk]

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    # Sauvegarde texte
    with open(out / "matches.txt", "w") as f:
        for d, x, y in best:
            f.write(f"{x} {y} {d:.6f}\n")

    # Carte de similarité (optionnel)
    sim_map = np.full((h, w), np.nan, dtype=np.float32)
    for d, x, y in scores[:5000]:
        sim_map[y, x] = d

    np.save(out / "similarity_map.npy", sim_map)

    print(f"OK: {len(best)} zones similaires sauvegardées dans {out}")

if __name__ == "__main__":
    main()
