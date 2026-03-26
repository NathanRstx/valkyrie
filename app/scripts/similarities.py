# scripts/similarities.py
import argparse
from pathlib import Path
from typing import List
import json

import numpy as np
import cv2


DEFAULT_BAND_TO_FILE = {
    "ndre": "NDRE.npy",
    "ndvi": "NDVI.npy",
    "nir": "NIR_aligned.npy",
    "rededge": "RE_aligned.npy",
}


def load_manifest(indir: Path):
    p = indir / "bands_manifest.json"
    if p.exists():
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def resolve_band_file(indir: Path, band: str) -> Path:
    band = band.strip().lower()
    manifest = load_manifest(indir)
    if manifest is not None:
        bands = manifest.get("bands", {})
        if band in bands:
            p = indir / bands[band]["file"]
            if p.exists():
                return p

    fname = DEFAULT_BAND_TO_FILE.get(band)
    if fname is None:
        raise ValueError(f"Bande inconnue: {band}. Possibles: {sorted(DEFAULT_BAND_TO_FILE.keys())}")
    p = indir / fname
    if not p.exists():
        raise FileNotFoundError(p)
    return p


def extract_patch(arr: np.ndarray, x: int, y: int, r: int) -> np.ndarray:
    return arr[y - r : y + r + 1, x - r : x + r + 1]


def main():
    ap = argparse.ArgumentParser(description="Patch similarity search (POINT or ZONE) + outputs like debug.")
    ap.add_argument("--indir", required=True, help="Dossier contenant les .npy (ex: results/float_indices)")
    ap.add_argument("--bands", default="ndre,ndvi", help="Ex: ndre,ndvi  ou  nir,rededge")
    ap.add_argument("--x", type=int, required=True, help="x du point OU coin haut-gauche de la zone")
    ap.add_argument("--y", type=int, required=True, help="y du point OU coin haut-gauche de la zone")
    ap.add_argument("--w", type=int, default=None, help="Largeur de la zone (si fournie => mode zone)")
    ap.add_argument("--h", type=int, default=None, help="Hauteur de la zone (si fournie => mode zone)")
    ap.add_argument("--radius", type=int, default=7, help="Patch radius r (patch=(2r+1)x(2r+1))")
    ap.add_argument("--topk", type=int, default=20, help="Nombre de meilleurs matches")
    ap.add_argument("--stride", type=int, default=1, help="Stride pour accélérer (1,2,4...)")
    ap.add_argument("--map_topn", type=int, default=5000, help="Nombre de points à écrire dans similarity_map (style debug)")
    ap.add_argument("--invert", action="store_true", help="Si présent: blanc = plus similaire (debug-friendly)")
    ap.add_argument("--out", default="results/similarity", help="Dossier de sortie")
    args = ap.parse_args()

    indir = Path(args.indir)
    band_list: List[str] = [b.strip().lower() for b in args.bands.split(",") if b.strip()]
    if not band_list:
        raise ValueError("Aucune bande dans --bands")

    arrays = [np.load(resolve_band_file(indir, b)).astype(np.float32) for b in band_list]

    h_img, w_img = arrays[0].shape
    for a in arrays[1:]:
        if a.shape != (h_img, w_img):
            raise ValueError(f"Bandes de tailles différentes: {(h_img, w_img)} vs {a.shape}")

    r = int(args.radius)
    stride = max(1, int(args.stride))
    is_zone_mode = (args.w is not None and args.h is not None)

    # ---------- MODE POINT OU ZONE ----------
    if args.w is None or args.h is None:
        # Mode point
        if not (r <= args.x < w_img - r and r <= args.y < h_img - r):
            raise ValueError(f"Point (x={args.x}, y={args.y}) trop proche du bord pour radius={r}")
        ref_parts = [extract_patch(a, args.x, args.y, r).reshape(-1) for a in arrays]
        ref = np.concatenate(ref_parts, axis=0)
        print("Mode: POINT")
    else:
        # Mode zone (x,y) = coin haut-gauche
        x0, y0 = int(args.x), int(args.y)
        x1 = min(w_img, x0 + int(args.w))
        y1 = min(h_img, y0 + int(args.h))

        vectors = []
        for yy in range(y0 + r, y1 - r):
            for xx in range(x0 + r, x1 - r):
                parts = [extract_patch(a, xx, yy, r).reshape(-1) for a in arrays]
                vectors.append(np.concatenate(parts, axis=0))

        if not vectors:
            raise ValueError("Zone trop petite pour le radius choisi (ou trop proche du bord).")

        ref = np.mean(np.stack(vectors, axis=0), axis=0)
        print("Mode: ZONE")

    # ---------- SCAN GLOBAL ----------
    scores = []
    for yy in range(r, h_img - r, stride):
        for xx in range(r, w_img - r, stride):
            parts = [extract_patch(a, xx, yy, r).reshape(-1) for a in arrays]
            v = np.concatenate(parts, axis=0)
            d = float(np.linalg.norm(v - ref))
            scores.append((d, xx, yy))

    scores.sort(key=lambda t: t[0])
    best = scores[: int(args.topk)]

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    # ---------- Save matches ----------
    with open(out / "matches.txt", "w", encoding="utf-8") as f:
        f.write("rank\tx\ty\tdistance\n")
        for k, (d, x, y) in enumerate(best, start=1):
            f.write(f"{k}\t{x}\t{y}\t{d:.6f}\n")

    # ---------- Build similarity_map (DEBUG STYLE: sparse top-N) ----------
    sim_map = np.full((h_img, w_img), np.nan, dtype=np.float32)
    topn = max(1, int(args.map_topn))
    for d, xx, yy in scores[:topn]:
        sim_map[yy, xx] = d

    np.save(out / "similarity_map.npy", sim_map)

    # ---------- Save similarity_map preview (.png) ----------
    # Normalisation sur les valeurs valides uniquement (dans les top-N)
    vmin = np.nanpercentile(sim_map, 1)
    vmax = np.nanpercentile(sim_map, 99)
    sim01 = (sim_map - vmin) / (vmax - vmin + 1e-6)
    sim01 = np.clip(sim01, 0, 1)

    # Option: blanc = plus similaire
    if args.invert:
        sim01 = 1.0 - sim01

    sim_img = (sim01 * 255).astype(np.uint8)
    cv2.imwrite(str(out / "similarity_map.png"), sim_img)

    # ---------- Overlay rectangles on base image ----------
    base = arrays[0].copy()
    if base.min() < 0:
        base = np.clip((base + 1) * 0.5, 0, 1)
    else:
        base = np.clip(base, 0, 1)

    base_u8 = (base * 255).astype(np.uint8)
    overlay = cv2.cvtColor(base_u8, cv2.COLOR_GRAY2BGR)

    for k, (d, x, y) in enumerate(best, start=1):
        # In zone mode, highlight rank #1 (reference-like zone) with a dedicated color.
        color = (0, 255, 255) if (is_zone_mode and k == 1) else (0, 0, 255)
        cv2.rectangle(overlay, (x - r, y - r), (x + r, y + r), color, 2)
        cv2.putText(
            overlay,
            str(k),
            (x - r, max(0, y - r - 5)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            color,
            2,
        )

    cv2.imwrite(str(out / "candidates.png"), overlay)

    print(f"OK: {len(best)} matches sauvegardés dans {out}")
    print(f"Outputs: {out}/matches.txt, {out}/similarity_map.npy, {out}/similarity_map.png, {out}/candidates.png")
    print(f"Bands used: {band_list}")
    print(f"similarity_map style: topN={topn}, stride={stride}, invert={'yes' if args.invert else 'no'}")


if __name__ == "__main__":
    main()
