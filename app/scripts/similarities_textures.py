#!/usr/bin/env python3
# scripts/similarities_textures.py
import argparse
from pathlib import Path
from typing import List
import json

import numpy as np
import cv2

import detection_textures


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


def is_valid_center(x: int, y: int, width: int, height: int, radius: int) -> bool:
    return radius <= x < width - radius and radius <= y < height - radius


def main():
    ap = argparse.ArgumentParser(description="Texture-based similarity search + same outputs as similarities.py")
    ap.add_argument("--indir", required=True, help="Dossier contenant les .npy (ex: results/float_indices)")
    ap.add_argument("--bands", default="ndre,ndvi", help="Ex: ndre,ndvi  ou  nir,rededge")
    ap.add_argument("--x", type=int, required=True, help="x du point OU coin haut-gauche de la zone")
    ap.add_argument("--y", type=int, required=True, help="y du point OU coin haut-gauche de la zone")
    ap.add_argument("--w", type=int, default=None, help="Largeur de la zone (si fournie => mode zone)")
    ap.add_argument("--h", type=int, default=None, help="Hauteur de la zone (si fournie => mode zone)")
    ap.add_argument("--radius", type=int, default=7, help="Patch radius r (patch=(2r+1)x(2r+1))")
    ap.add_argument("--topk", type=int, default=20, help="Nombre de meilleurs matches")
    ap.add_argument("--stride", type=int, default=1, help="Unused (kept for compatibility)")
    ap.add_argument("--map_topn", type=int, default=5000, help="Nombre de points à écrire dans similarity_map (style debug)")
    ap.add_argument("--invert", action="store_true", help="Si présent: blanc = plus similaire (debug-friendly)")
    ap.add_argument("--out", default="results/similarity_textures", help="Dossier de sortie")
    # texture detection params
    ap.add_argument("--win", type=int, default=31, help="Window for texture detection (odd)")
    ap.add_argument("--top_pct", type=float, default=5.0, help="Top percentile for texture thresholding")
    ap.add_argument("--min_area", type=int, default=100, help="Min area for texture candidate")

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
    is_zone_mode = (args.w is not None and args.h is not None)

    # ---------- Texture detection (on first band) ----------
    base = arrays[0]
    texture01, mask, candidates = detection_textures.detect_texture_anomalies(
        base, win=args.win, top_pct=args.top_pct, min_area=args.min_area
    )
    valid_candidates = [
        candidate
        for candidate in candidates
        if is_valid_center(int(round(candidate[5])), int(round(candidate[6])), w_img, h_img, r)
    ]

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    # save texture debug outputs
    detection_textures.save_u8(out / "texture_map.png", texture01)
    cv2.imwrite(str(out / "mask.png"), mask)

    # ---------- Build reference vector based on textures ----------
    if args.w is None or args.h is None:
        # POINT mode: try to find the candidate that contains the point
        px, py = int(args.x), int(args.y)
        chosen = None
        for (area, x, y, w, h, cx, cy) in valid_candidates:
            if x <= px < x + w and y <= py < y + h:
                chosen = (int(round(cx)), int(round(cy)))
                break
        if chosen is None:
            # choose nearest candidate centroid
            if not valid_candidates:
                raise ValueError("Aucune zone texturée exploitable détectée pour établir la référence avec ce radius.")
            dmin = None
            for (area, x, y, w, h, cx, cy) in valid_candidates:
                d = (cx - px) ** 2 + (cy - py) ** 2
                if dmin is None or d < dmin[0]:
                    dmin = (d, int(round(cx)), int(round(cy)))
            chosen = (dmin[1], dmin[2])
        ref_parts = [extract_patch(a, chosen[0], chosen[1], r).reshape(-1) for a in arrays]
        ref = np.concatenate(ref_parts, axis=0)
        print("Mode: POINT (texture-driven)")
    else:
        # ZONE mode: average over candidate centroids inside the zone
        x0, y0 = int(args.x), int(args.y)
        x1 = min(w_img, x0 + int(args.w))
        y1 = min(h_img, y0 + int(args.h))

        centers = []
        for (area, x, y, w, h, cx, cy) in valid_candidates:
            if x0 <= cx < x1 and y0 <= cy < y1:
                centers.append((int(round(cx)), int(round(cy))))

        if not centers:
            raise ValueError("Aucune zone texturée exploitable trouvée dans la zone fournie pour ce radius.")

        vectors = []
        for (cx, cy) in centers:
            parts = [extract_patch(a, cx, cy, r).reshape(-1) for a in arrays]
            vectors.append(np.concatenate(parts, axis=0))

        ref = np.mean(np.stack(vectors, axis=0), axis=0)
        print("Mode: ZONE (texture-driven)")

    # ---------- SCAN: compare only detected texture candidates ----------
    scores = []
    for (area, x, y, w, h, cx, cy) in valid_candidates:
        xx, yy = int(round(cx)), int(round(cy))
        parts = [extract_patch(a, xx, yy, r).reshape(-1) for a in arrays]
        v = np.concatenate(parts, axis=0)
        d = float(np.linalg.norm(v - ref))
        scores.append((d, x, y, w, h, xx, yy))

    if not scores:
        raise ValueError("Aucun candidat texturé exploitable après filtrage des bords.")

    scores.sort(key=lambda t: t[0])
    best = scores[: int(args.topk)]

    # ---------- Save matches ----------
    with open(out / "matches.txt", "w", encoding="utf-8") as f:
        f.write("rank\tx\ty\tw\th\tcx\tcy\tdistance\n")
        for k, (d, x, y, w, h, cx, cy) in enumerate(best, start=1):
            f.write(f"{k}\t{x}\t{y}\t{w}\t{h}\t{cx}\t{cy}\t{d:.6f}\n")

    # ---------- Build similarity_map (sparse top-N) ----------
    sim_map = np.full((h_img, w_img), np.nan, dtype=np.float32)
    topn = max(1, int(args.map_topn))
    for item in scores[:topn]:
        d, x, y, w, h, cx, cy = item
        sim_map[cy, cx] = d

    np.save(out / "similarity_map.npy", sim_map)

    # ---------- Save similarity_map preview (.png) ----------
    vmin = np.nanpercentile(sim_map, 1)
    vmax = np.nanpercentile(sim_map, 99)
    sim01 = (sim_map - vmin) / (vmax - vmin + 1e-6)
    sim01 = np.clip(sim01, 0, 1)
    sim01 = np.nan_to_num(sim01, nan=0.0)

    if args.invert:
        sim01 = 1.0 - sim01

    sim_img = (sim01 * 255).astype(np.uint8)
    cv2.imwrite(str(out / "similarity_map.png"), sim_img)

    # ---------- Overlay rectangles on base image (draw candidate boxes)
    base = arrays[0].copy()
    if base.min() < 0:
        base = np.clip((base + 1) * 0.5, 0, 1)
    else:
        base = np.clip(base, 0, 1)

    base_u8 = (base * 255).astype(np.uint8)
    overlay = cv2.cvtColor(base_u8, cv2.COLOR_GRAY2BGR)

    for k, (d, x, y, w, h, cx, cy) in enumerate(best, start=1):
        # In zone mode, highlight rank #1 (reference-like zone) with a dedicated color.
        color = (0, 255, 255) if (is_zone_mode and k == 1) else (0, 0, 255)
        cv2.rectangle(overlay, (x, y), (x + w, y + h), color, 2)
        cv2.putText(overlay, str(k), (int(cx), max(0, int(cy) - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

    cv2.imwrite(str(out / "candidates.png"), overlay)

    print(f"OK: {len(best)} matches sauvegardés dans {out}")
    print(f"Outputs: {out}/matches.txt, {out}/similarity_map.npy, {out}/similarity_map.png, {out}/candidates.png, {out}/texture_map.png, {out}/mask.png")
    print(f"Bands used: {band_list}")
    print(f"Texture detection: win={args.win}, top_pct={args.top_pct}, min_area={args.min_area}")


if __name__ == "__main__":
    main()
