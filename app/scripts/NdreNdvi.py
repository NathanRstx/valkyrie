#!/usr/bin/env python3
"""
Compute NDVI and NDRE indices from multispectral imagery.

Outputs:
  - .npy files (float32) for analysis
  - .tif files (float32 GeoTIFF) if rasterio is available
  - .png files (uint8) for preview only
"""

import argparse
import warnings
from pathlib import Path
from typing import Optional, Tuple

import cv2
import numpy as np

# Optional: rasterio for GeoTIFF export
try:
    import rasterio
    from rasterio.transform import Affine
    HAS_RASTERIO = True
    print("Utilisation de rasterio")
except ImportError:
    HAS_RASTERIO = False


def read_gray(path: Path) -> np.ndarray:

    """
    Read an image as grayscale float32
    
    Args:
        path: Path to the image file.
        
    Returns:
        Grayscale image as float32 array
        
    Raises:
        FileNotFoundError: If the image cannot be read.
    """
    if HAS_RASTERIO:
        with rasterio.open(path) as src:
            return src.read(1).astype(np.float32)
    else:
        img = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
        if img is None:
            raise FileNotFoundError(f"Cannot read image: {path}")
        if img.ndim == 3:
            img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        return img.astype(np.float32)


def nd(a: np.ndarray, b: np.ndarray, eps: float = 1e-6) -> np.ndarray:
    """
    Compute normalized difference: (a - b) / (a + b + eps).
    
    Args:
        a: Numerator addend (e.g., NIR).
        b: Numerator subtrahend (e.g., Red).
        eps: Small value to avoid division by zero.
        
    Returns:
        Normalized difference index in range approximately [-1, 1].
    """
    return (a - b) / (a + b + eps)


def print_stats(name: str, arr: np.ndarray) -> None:
    """Print min/max/mean statistics for an array."""
    print(f"  {name}: min={arr.min():.4f}, max={arr.max():.4f}, mean={arr.mean():.4f}")


def save_npy(path: Path, arr: np.ndarray) -> None:
    """Save array as .npy file (float32)."""
    np.save(str(path), arr.astype(np.float32))
    print(f"  Saved: {path}")


def save_geotiff(path: Path, arr: np.ndarray, reference_path: Path) -> None:
    if not HAS_RASTERIO:
        return

    with rasterio.open(reference_path) as src:
        profile = src.profile

    profile.update(
        dtype=rasterio.float32,
        count=1
    )

    with rasterio.open(str(path), 'w', **profile) as dst:
        dst.write(arr.astype(np.float32), 1)

    print(f"  Saved: {path}")

def save_preview_png(path: Path, arr: np.ndarray) -> None:
    """
    Save array as PNG uint8 for preview only.
    Maps [-1, 1] -> [0, 255].
    
    WARNING: This destroys float precision. Use only for visualization.
    """
    y = np.clip((arr + 1) * 0.5, 0, 1)
    cv2.imwrite(str(path), (y * 255).astype(np.uint8))
    print(f"  Saved (preview): {path}")


def align_image_ecc(
    reference: np.ndarray,
    target: np.ndarray,
    warp_mode: int = cv2.MOTION_EUCLIDEAN,
    num_iterations: int = 5000,
    termination_eps: float = 1e-10,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Align target image to reference using ECC (Enhanced Correlation Coefficient).
    
    Args:
        reference: Reference image (grayscale float32).
        target: Target image to align (grayscale float32).
        warp_mode: Type of motion model (default: MOTION_EUCLIDEAN).
        num_iterations: Maximum number of iterations.
        termination_eps: Convergence threshold.
        
    Returns:
        Tuple of (aligned_image, warp_matrix).
    """
    # Convert to uint8 for ECC (works better with 8-bit images)
    ref_u8 = (reference * 255).astype(np.uint8)
    tgt_u8 = (target * 255).astype(np.uint8)
    
    # Initialize warp matrix
    if warp_mode == cv2.MOTION_HOMOGRAPHY:
        warp_matrix = np.eye(3, 3, dtype=np.float32)
    else:
        warp_matrix = np.eye(2, 3, dtype=np.float32)
    
    # Define termination criteria
    criteria = (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, num_iterations, termination_eps)
    
    try:
        _, warp_matrix = cv2.findTransformECC(ref_u8, tgt_u8, warp_matrix, warp_mode, criteria)
    except cv2.error as e:
        warnings.warn(f"ECC alignment failed: {e}. Using original image.")
        return target.copy(), warp_matrix
    
    # Apply warp to float32 image
    h, w = reference.shape
    if warp_mode == cv2.MOTION_HOMOGRAPHY:
        aligned = cv2.warpPerspective(target, warp_matrix, (w, h), flags=cv2.INTER_LINEAR)
    else:
        aligned = cv2.warpAffine(target, warp_matrix, (w, h), flags=cv2.INTER_LINEAR)
    
    return aligned, warp_matrix


def crop_to_common(*arrays: np.ndarray) -> Tuple[np.ndarray, ...]:
    """
    Crop all arrays to the minimum common dimensions.
    
    WARNING: This is a fallback for mismatched sizes. Prefer using --align.
    """
    min_h = min(arr.shape[0] for arr in arrays)
    min_w = min(arr.shape[1] for arr in arrays)
    return tuple(arr[:min_h, :min_w] for arr in arrays)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compute NDVI and NDRE indices from multispectral imagery.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python NdreNdvi.py --in data/images --out results/indices
  python NdreNdvi.py --red red.png --nir nir.png --rededge rededge.png --out results/indices
  python NdreNdvi.py --in data/images --out results/indices --align
        """,
    )
    
    # Input options (either --in or individual files)
    parser.add_argument(
        "--in", dest="inp",
        type=Path,
        help="Input directory containing red.png, nir.png, rededge.png",
    )
    parser.add_argument(
        "--red",
        type=Path,
        help="Path to red band image",
    )
    parser.add_argument(
        "--nir",
        type=Path,
        help="Path to NIR band image",
    )
    parser.add_argument(
        "--rededge",
        type=Path,
        help="Path to RedEdge band image",
    )
    
    # Output
    parser.add_argument(
        "--out", dest="out",
        type=Path,
        required=True,
        help="Output directory for indices",
    )
    
    # Alignment option
    parser.add_argument(
        "--align",
        action="store_true",
        help="Align NIR and RedEdge to Red band using ECC before computing indices",
    )
    
    args = parser.parse_args()
    
    # Resolve input paths
    if args.inp is not None:
        red_path = args.inp / "red.TIF"
        nir_path = args.inp / "nir.TIF"
        rededge_path = args.inp / "rededge.TIF"
    elif args.red and args.nir and args.rededge:
        red_path = args.red
        nir_path = args.nir
        rededge_path = args.rededge
    else:
        parser.error("Either --in <dir> or (--red, --nir, --rededge) must be provided.")
    
    # Create output directory
    out: Path = args.out
    out.mkdir(parents=True, exist_ok=True)
    
    # Load input bands
    print("Loading input bands...")
    red = read_gray(red_path)
    nir = read_gray(nir_path)
    rededge = read_gray(rededge_path)
    
    print("\nInput band statistics:")
    print_stats("Red", red)
    print_stats("NIR", nir)
    print_stats("RedEdge", rededge)
    
    # Check dimensions
    shapes_match = (red.shape == nir.shape == rededge.shape)
    
    if args.align:
        print("\nAligning bands to Red reference using ECC...")
        
        # Crop to common size first if needed (for ECC to work)
        if not shapes_match:
            warnings.warn(
                f"Image sizes differ: Red={red.shape}, NIR={nir.shape}, RedEdge={rededge.shape}. "
                "Cropping to common area before alignment."
            )
            red, nir, rededge = crop_to_common(red, nir, rededge)
        
        nir_aligned, nir_warp = align_image_ecc(red, nir)
        rededge_aligned, re_warp = align_image_ecc(red, rededge)
        
        print("  NIR alignment complete.")
        print("  RedEdge alignment complete.")
        
        # Save aligned bands for debugging
        print("\nSaving aligned bands for debugging...")
        save_npy(out / "NIR_aligned.npy", nir_aligned)
        save_npy(out / "RE_aligned.npy", rededge_aligned)
        
        # Use aligned bands for index computation
        nir_final = nir_aligned
        rededge_final = rededge_aligned
    else:
        # No alignment: crop to common area if sizes differ
        if not shapes_match:
            warnings.warn(
                f"Image sizes differ: Red={red.shape}, NIR={nir.shape}, RedEdge={rededge.shape}. "
                "Cropping to common area. Consider using --align for better results."
            )
            red, nir, rededge = crop_to_common(red, nir, rededge)
        
        nir_final = nir
        rededge_final = rededge
    
    # Compute indices (formulas unchanged)
    print("\nComputing vegetation indices...")
    ndvi = nd(nir_final, red)
    ndre = nd(nir_final, rededge_final)
    
    print("\nIndex statistics:")
    print_stats("NDVI", ndvi)
    print_stats("NDRE", ndre)
    
    # Save outputs
    print("\nSaving outputs...")
    
    # 1. NumPy arrays (float32) - primary output for analysis
    save_npy(out / "NDVI.npy", ndvi)
    save_npy(out / "NDRE.npy", ndre)
    
    # 2. GeoTIFF (float32) - if rasterio is available
    if HAS_RASTERIO:
        save_geotiff(out / "NDVI.tif", ndvi, red_path)
        save_geotiff(out / "NDRE.tif", ndre, red_path)
    else:
        print("  (rasterio not available, skipping GeoTIFF export)")
    
    # 3. PNG preview (uint8) - for visualization only
    save_preview_png(out / "NDVI_preview.png", ndvi)
    save_preview_png(out / "NDRE_preview.png", ndre)
    
    print(f"\nDone! Outputs saved to: {out}")


if __name__ == "__main__":
    main()

