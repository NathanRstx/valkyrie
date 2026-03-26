import argparse
from pathlib import Path
import cv2
import numpy as np

def read_gray(path: Path) -> np.ndarray:
    img = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    if img is None:
        raise FileNotFoundError(path)
    if img.ndim == 3:
        img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    img = img.astype(np.float32)
    mx = float(img.max()) if img.max() > 0 else 1.0
    return img / mx

def nd(a, b, eps=1e-6):
    return (a - b) / (a + b + eps)

def save_vis(path: Path, x):
    # map [-1,1] -> [0,255] pour visualiser
    y = np.clip((x + 1) * 0.5, 0, 1)
    cv2.imwrite(str(path), (y * 255).astype(np.uint8))

def align_ecc(moving, fixed, warp_mode=cv2.MOTION_AFFINE, n_iter=2000, eps=1e-6):
    """
    moving -> image à aligner
    fixed  -> image de référence
    Retourne moving alignée sur fixed
    """
    # ECC attend du float32
    moving_f = moving.astype(np.float32)
    fixed_f  = fixed.astype(np.float32)

    if warp_mode == cv2.MOTION_HOMOGRAPHY:
        warp = np.eye(3, 3, dtype=np.float32)
    else:
        warp = np.eye(2, 3, dtype=np.float32)

    criteria = (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, n_iter, eps)

    try:
        cc, warp = cv2.findTransformECC(fixed_f, moving_f, warp, warp_mode, criteria)
    except cv2.error as e:
        raise RuntimeError(f"ECC failed: {e}")

    h, w = fixed.shape
    if warp_mode == cv2.MOTION_HOMOGRAPHY:
        aligned = cv2.warpPerspective(moving, warp, (w, h), flags=cv2.INTER_LINEAR)
    else:
        aligned = cv2.warpAffine(moving, warp, (w, h), flags=cv2.INTER_LINEAR)
    return aligned

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True, help="Dossier contenant tes bandes PNG")
    ap.add_argument("--out", dest="out", required=True, help="Dossier de sortie")
    ap.add_argument("--red", default="red.png")
    ap.add_argument("--nir", default="nir.png")
    ap.add_argument("--rededge", default="rededge.png")
    args = ap.parse_args()

    inp = Path(args.inp)
    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)

    red = read_gray(inp / args.red)
    nir = read_gray(inp / args.nir)
    re  = read_gray(inp / args.rededge)

    # On aligne NIR et RedEdge sur Red
    nir_a = align_ecc(nir, red, warp_mode=cv2.MOTION_AFFINE)
    re_a  = align_ecc(re,  red, warp_mode=cv2.MOTION_AFFINE)

    # Calcul indices
    ndvi = nd(nir_a, red)
    ndre = nd(nir_a, re_a)

    save_vis(out / "NDVI.png", ndvi)
    save_vis(out / "NDRE.png", ndre)

    print("OK: NDVI/NDRE recalculés après alignement ECC.")

if __name__ == "__main__":
    main()
