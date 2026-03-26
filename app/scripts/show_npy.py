# scripts/show_npy.py
import argparse
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt


def main():
    ap = argparse.ArgumentParser(description="Afficher un fichier .npy comme image.")
    ap.add_argument("--input", required=True, help="Chemin vers le fichier .npy")
    ap.add_argument("--save", default=None, help="Chemin optionnel pour sauvegarder en .png")
    ap.add_argument("--cmap", default="viridis", help="Colormap (viridis, gray, inferno, plasma...)")
    args = ap.parse_args()

    path = Path(args.input)
    if not path.exists():
        raise FileNotFoundError(path)

    x = np.load(path)

    print("Shape:", x.shape)
    print("Min / Max:", np.nanmin(x), np.nanmax(x))
    print("Mean / Std:", np.nanmean(x), np.nanstd(x))
    print("NaN:", np.isnan(x).sum(), "Inf:", np.isinf(x).sum())

    # Normalisation robuste (ignore les NaN)
    vmin = np.nanmin(x)
    vmax = np.nanpercentile(x, 99)  # évite que quelques valeurs extrêmes écrasent tout

    x_norm = (x - vmin) / (vmax - vmin + 1e-6)
    x_norm = np.clip(x_norm, 0, 1)

    plt.figure(figsize=(8, 6))
    plt.imshow(x_norm, cmap=args.cmap)
    plt.colorbar()
    plt.title(path.name)
    plt.axis("off")  # 🔥 enlève la grille
    plt.tight_layout()

    if args.save is not None:
        plt.savefig(args.save, dpi=300)
        print("Image sauvegardée dans:", args.save)

    plt.show()


if __name__ == "__main__":
    main()
