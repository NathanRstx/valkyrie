# scripts/detection.py
import argparse
import json
from pathlib import Path
from typing import Dict, Optional, Tuple, List

import cv2
import numpy as np


# ---------- Band mapping helpers ----------

DEFAULT_BAND_TO_FILE = {
    "ndre": "NDRE.npy",
    "ndvi": "NDVI.npy",
    "nir": "NIR_aligned.npy",
    "rededge": "RE_aligned.npy",
    # si un jour tu ajoutes ces sorties :
    "red": "red.npy",
    "green": "green.npy",
    "blue": "blue.npy",
}

DEFAULT_WL_TO_BAND = {
    475: "blue",
    560: "green",
    668: "red",
    717: "rededge",
    840: "nir",
}


def load_manifest(indir: Path) -> Optional[Dict]:
    p = indir / "bands_manifest.json"
    if p.exists():
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def resolve_index_path(index: Optional[str], indir: Optional[str], band: Optional[str], wavelength: Optional[int]) -> Path:
    """
    Résout quel fichier d'entrée utiliser.
    Priorité:
      1) --index
      2) --band + --indir
      3) --wavelength + --indir (converti en band)
    """
    if index is not None:
        return Path(index)

    if indir is None:
        raise ValueError("Si tu n'utilises pas --index, tu dois fournir --indir <dossier>.")

    indir_p = Path(indir)
    manifest = load_manifest(indir_p)

    if wavelength is not None and band is None:
        band = DEFAULT_WL_TO_BAND.get(int(wavelength))
        if band is None:
            raise ValueError(f"Longueur d'onde inconnue: {wavelength}. Possibles: {sorted(DEFAULT_WL_TO_BAND.keys())}")

    if band is None:
        raise ValueError("Tu dois fournir soit --index, soit --band, soit --wavelength (avec --indir).")

    band_key = band.strip().lower()

    # Si on a un manifest, on l'utilise
    if manifest is not None:
        bands = manifest.get("bands", {})
        if band_key in bands:
            rel = bands[band_key]["file"]
            p = indir_p / rel
            if p.exists():
                return p

    # fallback sans manifest
    fname = DEFAULT_BAND_TO_FILE.get(band_key)
    if fname is None:
        raise ValueError(f"Bande inconnue: {band}. Possibles: {sorted(DEFAULT_BAND_TO_FILE.keys())}")
    p = indir_p / fname
    if not p.exists():
        raise FileNotFoundError(f"Introuvable: {p} (band={band_key})")
    return p


# ---------- IO ----------

def read_index(path: Path) -> np.ndarray:
    if not path.exists():
        raise FileNotFoundError(f"Introuvable: {path} (cwd={Path.cwd()})")

    if path.suffix.lower() == ".npy":
        return np.load(path).astype(np.float32)

    img = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    if img is None:
        raise FileNotFoundError(f"OpenCV ne peut pas lire: {path}")
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


# ---------- Core detection (callable later by GUI) ----------

def detect_candidates(
    idx: np.ndarray,
    win: int = 41,
    z: Optional[float] = None,
    top_pct: float = 1.0,
    min_area: int = 300,
    do_cleanup: bool = True,
) -> Tuple[np.ndarray, np.ndarray, List[Tuple]]:
    """
    Returns: (anomaly_map01, mask_u8, candidates)
    candidates elements: (area, x, y, w, h, cx, cy)
    """
    win = win if win % 2 == 1 else win + 1

    idx = cv2.GaussianBlur(idx, (5,5), 0)

    mu = cv2.blur(idx, (win, win))
    mu2 = cv2.blur(idx * idx, (win, win))
    var = np.maximum(mu2 - mu * mu, 0)
    sigma = np.sqrt(var + 1e-6)
    sigma = np.maximum(sigma, 0.01)
    zmap = (idx - mu) / (sigma + 1e-6)
    amap = np.abs(zmap)

    print(f"[DEBUG] idx  min/max: {idx.min():.4f} / {idx.max():.4f}")
    print(f"[DEBUG] amap min/max: {amap.min():.4f} / {amap.max():.4f}")
    print(f"[DEBUG] amap p99/p999: {np.percentile(amap,99):.4f} / {np.percentile(amap,99.9):.4f}")

    amap01 = (amap - amap.min()) / (amap.max() - amap.min() + 1e-6)

    if z is not None:
        thr = float(z)
        mask = (amap >= thr).astype(np.uint8) * 255
        print(f"[DEBUG] threshold mode=z, thr={thr}")
    else:
        pct = float(top_pct)
        pct = min(max(pct, 0.01), 50.0)
        thr = np.percentile(amap, 100.0 - pct)
        mask = (amap >= thr).astype(np.uint8) * 255
        print(f"[DEBUG] threshold mode=percentile, top_pct={pct} => thr={thr:.4f}")

    if do_cleanup:
        mask = cv2.medianBlur(mask, 5)
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)

    num, labels, stats, centroids = cv2.connectedComponentsWithStats(mask, connectivity=8)

    candidates = []
    for i in range(1, num):
        x, y, w, h, area = stats[i]
        if area >= min_area:
            cx, cy = centroids[i]
            candidates.append((area, x, y, w, h, cx, cy))
    candidates.sort(reverse=True)

    return amap01, mask, candidates


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--index", default=None, help="Chemin direct vers une image (.png/.tif) ou un .npy")
    ap.add_argument("--indir", default=None, help="Dossier contenant les .npy (ex: results/float_indices)")
    ap.add_argument("--band", default=None, help="Bande/indice: ndre, ndvi, nir, rededge, ...")
    ap.add_argument("--wavelength", type=int, default=None, help="Longueur d'onde (nm): 475, 560, 668, 717, 840")

    ap.add_argument("--out", required=True)
    ap.add_argument("--win", type=int, default=41)
    ap.add_argument("--z", type=float, default=None, help="Seuil z-score (ex 2.5). Si absent, utilise --top_pct.")
    ap.add_argument("--top_pct", type=float, default=1.0, help="Garder les top X%% pixels les plus anormaux (ex 1.0)")
    ap.add_argument("--min_area", type=int, default=300)
    ap.add_argument("--no_cleanup", action="store_true", help="Désactive le nettoyage morphologique (debug)")
    args = ap.parse_args()

    index_path = resolve_index_path(args.index, args.indir, args.band, args.wavelength)
    idx = read_index(index_path)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    amap01, mask, candidates = detect_candidates(
        idx,
        win=args.win,
        z=args.z,
        top_pct=args.top_pct,
        min_area=args.min_area,
        do_cleanup=(not args.no_cleanup),
    )

    save_u8(out / "anomaly.png", amap01)
    cv2.imwrite(str(out / "mask.png"), mask)

    # overlay (pour l’instant on affiche l’index en gris [0..1] si possible)
    base = idx.copy()
    # si idx est NDRE/NDVI en [-1,1], on le remap pour preview
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

    with open(out / "candidates.txt", "w", encoding="utf-8") as f:
        f.write("rank\tarea\tx\ty\tw\th\tcx\tcy\n")
        for k, (area, x, y, w, h, cx, cy) in enumerate(candidates[:50], start=1):
            f.write(f"{k}\t{area}\t{x}\t{y}\t{w}\t{h}\t{cx:.1f}\t{cy:.1f}\n")

    print(f"OK: {len(candidates)} zones candidates")
    print(f"Outputs: {out}/anomaly.png, {out}/mask.png, {out}/candidates.png, {out}/candidates.txt")
    print(f"Used input: {index_path}")

if __name__ == "__main__":
    main()

