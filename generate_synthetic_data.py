#!/usr/bin/env python3
"""
Phase 2: Synthetic Data Generator for HVAC CAD Symbols
=======================================================
Windows-Compatible Version -- Works with YOUR flat icons directory.

Features:
  - Reads icons from data/icons/ (flat structure, 417 PNGs)
  - Smart class grouping from filenames  (page_10_symbol, gate_valve_threaded, etc.)
  - No albumentations dependency (pure PIL + OpenCV)
  - 4 CAD-realistic background types
  - Correct alpha blending for symbols on white backgrounds
  - 90°/180°/270° preferred rotations (realistic for HVAC CAD)
  - YOLO-format annotations (class cx cy w h, all normalised)
  - Built-in dataset verifier + visualiser
  - tqdm optional (falls back gracefully)

Usage:
  python generate_synthetic_data.py                        # 3000 images, generate+verify
  python generate_synthetic_data.py --num-images 5000      # 5000 images
  python generate_synthetic_data.py --mode verify          # verify only
"""

import cv2
import numpy as np
from PIL import Image, ImageEnhance
import random
import json
import yaml
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import argparse
import time
import sys

# ?? optional tqdm ??????????????????????????????????????????????
try:
    from tqdm import tqdm as _tqdm
    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False
    print("[INFO]  tqdm not installed – using built-in progress display.")


def progress_wrap(iterable, desc: str = "", total: int = None):
    """Thin wrapper: tqdm if available, otherwise simple percentage."""
    if HAS_TQDM:
        return _tqdm(iterable, desc=desc, total=total, ncols=80)

    items = list(iterable)
    n = total or len(items)
    start = time.time()

    def _gen():
        for i, item in enumerate(items):
            if i % max(1, n // 40) == 0 or i == n - 1:
                elapsed = time.time() - start
                pct = (i + 1) / n * 100
                rate = (i + 1) / elapsed if elapsed > 0 else 0
                eta = (n - i - 1) / rate if rate > 0 else 0
                sys.stdout.write(
                    f"\r{desc}: {i+1}/{n}  ({pct:5.1f}%)  ETA {eta:4.0f}s"
                )
                sys.stdout.flush()
            yield item
        print()  # newline when done

    return _gen()


# ??????????????????????????????????????????????????????????????
# CONFIGURATION
# ??????????????????????????????????????????????????????????????

@dataclass
class Config:
    """All tunable knobs in one place."""

    # ?? paths ?????????????????????????????????????????????????
    icons_dir: str = (
        r"C:\Users\Friends shop\OneDrive\Desktop\BOQ ESTOMATION"
        r"\HVAC_Project\data\icons"
    )
    output_dir: str = (
        r"C:\Users\Friends shop\OneDrive\Desktop\BOQ ESTOMATION"
        r"\HVAC_Project\data\dataset"
    )
    backgrounds_dir: str = (
        r"C:\Users\Friends shop\OneDrive\Desktop\BOQ ESTOMATION"
        r"\HVAC_Project\data\training_backgrounds_2000"
    )

    # ?? dataset size ??????????????????????????????????????????
    total_images: int = 3000          # 2000–5000 recommended
    train_ratio: float = 0.80
    val_ratio:   float = 0.15
    test_ratio:  float = 0.05

    # ?? canvas ????????????????????????????????????????????????
    img_width:  int = 2000
    img_height: int = 2000

    # ?? symbol placement ??????????????????????????????????????
    min_symbols_per_image: int = 1
    max_symbols_per_image: int = 8
    min_scale: float = 0.50   # relative to pre-capped icon size
    max_scale: float = 1.60
    max_icon_dim: int = 150   # cap raw icon size (px) before scale

    # ?? augmentation ?????????????????????????????????????????
    brightness_range: Tuple[float, float] = (0.75, 1.25)
    contrast_range:   Tuple[float, float] = (0.80, 1.20)

    # ?? quality / overlap ????????????????????????????????????
    max_overlap_iou:    float = 0.25
    margin:             int   = 15    # pixels from image edge
    min_icon_size_bytes: int  = 500   # skip empty/tiny files

    # ?? backgrounds ??????????????????????????????????????????
    num_backgrounds: int = 60


# ??????????????????????????????????????????????????????????????
# CLASS-NAME EXTRACTION
# ??????????????????????????????????????????????????????????????

def extract_class_name(icon_path: Path) -> str:
    """
    Derive a consistent class label from the icon filename.

    Rules (in order):
    1. page_XX_NNN_<name>.png  ->  <name>          (indexed named icon)
    2. page_XX_<name>.png      ->  <name>           (non-indexed named icon)
    3. page_XX_type_NNN.png    ->  page_XX_type     (generic numbered icon)

    Examples
    --------
    page_10_symbol_001.png          -> page_10_symbol
    page_12_line_symbol_005.png     -> page_12_line_symbol
    page_15_01_gate_valve_threaded  -> gate_valve_threaded
    page_15_wye_strainer_ball_valve -> wye_strainer_ball_valve
    """
    stem = icon_path.stem       # drop .png extension
    parts = stem.split("_")

    # Must begin with 'page_<num>'
    if len(parts) < 3 or parts[0] != "page":
        return stem

    # parts[1] should be the page number (digit-ish)
    tail = parts[2:]            # everything after "page_XX_"

    # Case A: trailing part is a pure number  -> generic group
    #   e.g., ['symbol','001'] or ['line','symbol','003']
    if tail and tail[-1].isdigit():
        return "_".join(parts[:-1])   # drop trailing number

    # Case B: first item of tail is itself a pure number  -> indexed named
    #   e.g., ['01','gate','valve','threaded']
    if len(tail) >= 2 and tail[0].isdigit():
        return "_".join(tail[1:])

    # Case C: all descriptive  -> everything from position 2 onwards
    #   e.g., ['wye','strainer','ball','valve','hose']
    return "_".join(tail)


# ??????????????????????????????????????????????????????????????
# SYNTHETIC DATA GENERATOR
# ??????????????????????????????????????????????????????????????

class SyntheticDataGenerator:

    def __init__(self, config: Config):
        self.cfg = config
        self.out = Path(config.output_dir)
        self.icons_path = Path(config.icons_dir)

        self.class_icons: Dict[str, List[Path]] = {}
        self.class_names: List[str] = []
        self.class_to_id: Dict[str, int] = {}
        self.backgrounds: List[np.ndarray] = []

        print("=" * 65)
        print("  HVAC SYNTHETIC DATA GENERATOR  --  Phase 2")
        print("=" * 65)

        self._create_dirs()
        self._load_icons()
        self._generate_backgrounds()

    # ?? directory setup ???????????????????????????????????????

    def _create_dirs(self):
        for sub in ("images/train", "images/val", "images/test",
                    "labels/train",  "labels/val",  "labels/test"):
            (self.out / sub).mkdir(parents=True, exist_ok=True)
        print(f"[DIR] Output -> {self.out}")

    # ?? icon loading ?????????????????????????????????????????

    def _load_icons(self):
        if not self.icons_path.exists():
            raise FileNotFoundError(f"Icons dir not found: {self.icons_path}")

        print(f"\n[SCAN] Scanning: {self.icons_path}")

        loaded = skipped = 0
        for p in sorted(self.icons_path.glob("*.png")):
            # skip internal debug files
            if p.name.startswith("_"):
                skipped += 1
                continue
            # skip suspiciously tiny files (likely empty or noise)
            if p.stat().st_size < self.cfg.min_icon_size_bytes:
                skipped += 1
                continue

            cls = extract_class_name(p)
            self.class_icons.setdefault(cls, []).append(p)
            loaded += 1

        self.class_names = sorted(self.class_icons)
        self.class_to_id = {n: i for i, n in enumerate(self.class_names)}

        print(f"[OK] {loaded} icons  ->  {len(self.class_names)} classes  "
              f"(skipped {skipped})\n")
        print(f"{'ID':>4}  {'Class name':<45}  Icons")
        print("-" * 60)
        for i, name in enumerate(self.class_names):
            print(f"  {i:>3}  {name:<45}  {len(self.class_icons[name])}")

        if not self.class_names:
            raise ValueError("No valid icons found -- check your icons directory.")

        self._save_class_files()

    def _save_class_files(self):
        # classes.txt
        ct = self.out / "classes.txt"
        ct.write_text("\n".join(self.class_names) + "\n", encoding="utf-8")

        # class_mapping.json  (human-readable reference)
        cm = self.out / "class_mapping.json"
        cm.write_text(json.dumps({
            "num_classes": len(self.class_names),
            "class_to_id": self.class_to_id,
            "id_to_class": {str(v): k for k, v in self.class_to_id.items()},
            "icons_per_class": {k: len(v) for k, v in self.class_icons.items()},
        }, indent=2), encoding="utf-8")

        print(f"\n[NOTE] classes.txt saved  ({len(self.class_names)} classes)")

    # ?? background generation ?????????????????????????????????

    def _generate_backgrounds(self):
        """Load real backgrounds. Supports all .png/.jpg files in backgrounds_dir."""
        bg_p = Path(self.cfg.backgrounds_dir)
        files = list(bg_p.glob("*.png")) + list(bg_p.glob("*.jpg"))

        if not files:
            print(f"[WARN] No backgrounds found in {bg_p}. Using white canvas.")
            self.backgrounds = [np.full((self.cfg.img_height, self.cfg.img_width, 3), 255, dtype=np.uint8)]
            return

        print(f"\n[BG] Loading {len(files)} real backgrounds (2000x2000) ...")
        for f in files[:self.cfg.num_backgrounds]:
            img = cv2.imread(str(f))
            if img is not None:
                # Ensure exact canvas size
                img = cv2.resize(img, (self.cfg.img_width, self.cfg.img_height))
                self.backgrounds.append(img)

        # Augment to fill up to num_backgrounds if fewer files available
        original_count = len(self.backgrounds)
        while len(self.backgrounds) < self.cfg.num_backgrounds:
            base = random.choice(self.backgrounds[:original_count]).copy()
            flip_code = random.choice([-1, 0, 1])
            base = cv2.flip(base, flip_code)
            self.backgrounds.append(base)

        print(f"[OK] {len(self.backgrounds)} backgrounds ready (including augmented flips)")


    def _crop_or_pad(self, img: np.ndarray, target_w: int, target_h: int) -> np.ndarray:
        h, w = img.shape[:2]
        if h == target_h and w == target_w:
            return img

        # Crop if too large
        if h > target_h or w > target_w:
            y = random.randint(0, max(0, h - target_h))
            x = random.randint(0, max(0, w - target_w))
            img = img[y:y+target_h, x:x+target_w]
            h, w = img.shape[:2]

        # Pad if too small
        if h < target_h or w < target_w:
            pad_bg = np.full((target_h, target_w, 3), 255, dtype=np.uint8)
            pad_bg[:h, :w] = img
            return pad_bg

        return img

    def _bg_grid(self) -> np.ndarray:
        """Engineering graph paper (white + light grid)."""
        W, H = self.cfg.img_width, self.cfg.img_height
        bg = np.full((H, W, 3), 253, dtype=np.uint8)
        for x in range(0, W, 20):
            cv2.line(bg, (x, 0), (x, H), (235, 235, 235), 1)
        for y in range(0, H, 20):
            cv2.line(bg, (0, y), (W, y), (235, 235, 235), 1)
        for x in range(0, W, 100):
            cv2.line(bg, (x, 0), (x, H), (215, 215, 215), 1)
        for y in range(0, H, 100):
            cv2.line(bg, (0, y), (W, y), (215, 215, 215), 1)
        # random duct / pipe lines
        for _ in range(random.randint(2, 6)):
            x1 = random.randint(0, W)
            y1 = random.randint(0, H)
            l  = random.randint(60, 280)
            c  = (random.randint(170, 195),) * 3
            if random.random() > 0.5:
                cv2.line(bg, (x1, y1), (x1 + l, y1), c, 2)
            else:
                cv2.line(bg, (x1, y1), (x1, y1 + l), c, 2)
        return self._noise(bg, 3)

    def _bg_blueprint(self) -> np.ndarray:
        """Light-blue blueprint style."""
        W, H = self.cfg.img_width, self.cfg.img_height
        bg = np.ones((H, W, 3), dtype=np.uint8)
        bg[:, :] = [222, 228, 238]    # BGR: pale blue-white
        gc = (207, 213, 228)
        for x in range(0, W, 25):
            cv2.line(bg, (x, 0), (x, H), gc, 1)
        for y in range(0, H, 25):
            cv2.line(bg, (0, y), (W, y), gc, 1)
        for _ in range(random.randint(1, 4)):
            p1 = (random.randint(0, W), random.randint(0, H))
            p2 = (random.randint(0, W), random.randint(0, H))
            cv2.line(bg, p1, p2, (192, 198, 213), 1)
        return self._noise(bg, 2)

    def _bg_clean_white(self) -> np.ndarray:
        """Pure white -- most common in modern CAD prints."""
        W, H = self.cfg.img_width, self.cfg.img_height
        bg = np.full((H, W, 3), 255, dtype=np.uint8)
        for x in range(0, W, 40):
            cv2.line(bg, (x, 0), (x, H), (248, 248, 248), 1)
        for y in range(0, H, 40):
            cv2.line(bg, (0, y), (W, y), (248, 248, 248), 1)
        return self._noise(bg, 2)

    def _bg_worn_paper(self) -> np.ndarray:
        """Slightly yellowed / aged drawing paper."""
        W, H = self.cfg.img_width, self.cfg.img_height
        bg = np.ones((H, W, 3), dtype=np.uint8)
        bg[:, :] = [
            random.randint(245, 252),  # B
            random.randint(245, 252),  # G
            random.randint(248, 255),  # R  (warm)
        ]
        return self._noise(bg, 5)

    @staticmethod
    def _noise(img: np.ndarray, std: int) -> np.ndarray:
        noise = np.random.normal(0, std, img.shape).astype(np.int16)
        return np.clip(img.astype(np.int16) + noise, 0, 255).astype(np.uint8)

    # ?? icon loading & augmentation ???????????????????????????

    def _load_and_augment_icon(
        self, icon_path: Path
    ) -> Optional[Tuple[np.ndarray, np.ndarray]]:
        """
        Load icon -> RGBA, augment, return (RGB array, alpha mask).
        Returns None on any failure.
        """
        try:
            pil = Image.open(icon_path)

            # ?? ensure RGBA ??????????????????????????????????
            if pil.mode == "RGBA":
                real_alpha = True
            elif pil.mode in ("RGB", "L", "P"):
                pil = pil.convert("RGBA")
                real_alpha = False
            else:
                pil = pil.convert("RGBA")
                real_alpha = True

            # ?? synthesise alpha for icons on white background ?
            if not real_alpha:
                r, g, b, _ = pil.split()
                gray = np.array(Image.merge("RGB", (r, g, b)).convert("L"))
                # dark pixels = symbol; white pixels = background
                alpha_arr = np.where(gray < 240, 255, 0).astype(np.uint8)
                pil = Image.merge("RGBA", (r, g, b, Image.fromarray(alpha_arr)))

            # ?? cap raw size before any scaling ??????????????
            W, H = pil.size
            cap = self.cfg.max_icon_dim
            if max(W, H) > cap:
                ratio = cap / max(W, H)
                W, H = max(1, int(W * ratio)), max(1, int(H * ratio))
                pil = pil.resize((W, H), Image.Resampling.LANCZOS)

            # ?? random scale ?????????????????????????????????
            scale = random.uniform(self.cfg.min_scale, self.cfg.max_scale)
            nW, nH = max(8, int(W * scale)), max(8, int(H * scale))
            pil = pil.resize((nW, nH), Image.Resampling.LANCZOS)

            # ?? rotation (prefer orthogonal for HVAC drawings) ?
            if random.random() < 0.45:
                angle = random.choice([0, 90, 180, 270])
            else:
                angle = random.uniform(0, 360)
            if angle:
                pil = pil.rotate(angle, expand=True,
                                 resample=Image.Resampling.BICUBIC)

            # ?? colour augmentation ???????????????????????????
            if random.random() < 0.60:
                r, g, b, a = pil.split()
                rgb = Image.merge("RGB", (r, g, b))
                rgb = ImageEnhance.Brightness(rgb).enhance(
                    random.uniform(*self.cfg.brightness_range))
                rgb = ImageEnhance.Contrast(rgb).enhance(
                    random.uniform(*self.cfg.contrast_range))
                if random.random() < 0.25:
                    rgb = ImageEnhance.Color(rgb).enhance(
                        random.uniform(0.80, 1.20))
                r2, g2, b2 = rgb.split()
                pil = Image.merge("RGBA", (r2, g2, b2, a))

            arr   = np.array(pil)
            rgb   = arr[:, :, :3]
            alpha = arr[:, :, 3]
            return rgb, alpha

        except Exception:
            return None

    # ?? placement helpers ?????????????????????????????????????

    @staticmethod
    def _iou(b1: Tuple[int, int, int, int],
             b2: Tuple[int, int, int, int]) -> float:
        x1, y1, w1, h1 = b1
        x2, y2, w2, h2 = b2
        ix1, iy1 = max(x1, x2),          max(y1, y2)
        ix2, iy2 = min(x1 + w1, x2 + w2), min(y1 + h1, y2 + h2)
        if ix2 <= ix1 or iy2 <= iy1:
            return 0.0
        inter = (ix2 - ix1) * (iy2 - iy1)
        union = w1 * h1 + w2 * h2 - inter
        return inter / union if union > 0 else 0.0

    def _find_position(
        self,
        iw: int, ih: int,
        placed: List[Tuple[int, int, int, int]],
        attempts: int = 35,
    ) -> Optional[Tuple[int, int]]:
        m  = self.cfg.margin
        W, H = self.cfg.img_width, self.cfg.img_height
        xmax, ymax = W - iw - m, H - ih - m
        if xmax < m or ymax < m:
            return None
        for _ in range(attempts):
            x, y = random.randint(m, xmax), random.randint(m, ymax)
            box  = (x, y, iw, ih)
            if all(self._iou(box, p) <= self.cfg.max_overlap_iou for p in placed):
                return x, y
        return None

    def _paste(self,
               bg:    np.ndarray,
               rgb:   np.ndarray,
               alpha: np.ndarray,
               x: int, y: int) -> None:
        """Alpha-blend icon onto background in-place."""
        h, w = rgb.shape[:2]
        # Safety clip
        h = min(h, bg.shape[0] - y)
        w = min(w, bg.shape[1] - x)
        if h <= 0 or w <= 0:
            return
        rgb   = rgb[:h, :w]
        alpha = alpha[:h, :w]

        a   = alpha.astype(np.float32) / 255.0   # (h, w)
        roi = bg[y:y+h, x:x+w].astype(np.float32)
        blended = rgb.astype(np.float32) * a[:, :, None] + roi * (1 - a[:, :, None])
        bg[y:y+h, x:x+w] = blended.astype(np.uint8)

    # ?? single image ?????????????????????????????????????????

    def _generate_image(self, img_id: int, split: str) -> Dict:
        bg = random.choice(self.backgrounds).copy()

        # Mild whole-background brightness jitter
        if random.random() < 0.30:
            pil_bg = Image.fromarray(cv2.cvtColor(bg, cv2.COLOR_BGR2RGB))
            pil_bg = ImageEnhance.Brightness(pil_bg).enhance(
                random.uniform(0.92, 1.08))
            bg = cv2.cvtColor(np.array(pil_bg), cv2.COLOR_RGB2BGR)

        n_symbols  = random.randint(self.cfg.min_symbols_per_image,
                                    self.cfg.max_symbols_per_image)
        annotations: List[str] = []
        placed:      List[Tuple[int,int,int,int]] = []
        placed_count = 0
        max_attempts = n_symbols * 10

        for _ in range(max_attempts):
            if placed_count >= n_symbols:
                break

            cls_name = random.choice(self.class_names)
            cls_id   = self.class_to_id[cls_name]
            icon_path = random.choice(self.class_icons[cls_name])

            result = self._load_and_augment_icon(icon_path)
            if result is None:
                continue
            rgb, alpha = result
            ih, iw = rgb.shape[:2]

            pos = self._find_position(iw, ih, placed)
            if pos is None:
                continue
            x, y = pos

            self._paste(bg, rgb, alpha, x, y)
            placed.append((x, y, iw, ih))
            placed_count += 1

            # YOLO label (normalised, clamped)
            W, H = self.cfg.img_width, self.cfg.img_height
            cx = min(max((x + iw / 2) / W, 1e-6), 1.0)
            cy = min(max((y + ih / 2) / H, 1e-6), 1.0)
            nw = min(max(iw / W,           1e-6), 1.0)
            nh = min(max(ih / H,           1e-6), 1.0)
            annotations.append(f"{cls_id} {cx:.6f} {cy:.6f} {nw:.6f} {nh:.6f}")

        # ?? save image ????????????????????????????????????????
        img_name = f"{split}_{img_id:06d}.jpg"
        img_path = self.out / "images" / split / img_name
        cv2.imwrite(str(img_path), bg, [cv2.IMWRITE_JPEG_QUALITY, 95])

        # ?? save label ????????????????????????????????????????
        lbl_name = f"{split}_{img_id:06d}.txt"
        lbl_path = self.out / "labels" / split / lbl_name
        lbl_path.write_text(
            "\n".join(annotations) + ("\n" if annotations else ""),
            encoding="utf-8",
        )

        return {"split": split, "objects": placed_count}

    # ?? full dataset ??????????????????????????????????????????

    def generate_dataset(self) -> Dict:
        cfg = self.cfg
        n_train = int(cfg.total_images * cfg.train_ratio)
        n_val   = int(cfg.total_images * cfg.val_ratio)
        n_test  = cfg.total_images - n_train - n_val

        print(f"\n[START] Generating {cfg.total_images} images …")
        print(f"   Train {n_train}  |  Val {n_val}  |  Test {n_test}")
        print(f"   Symbols / image: {cfg.min_symbols_per_image}–"
              f"{cfg.max_symbols_per_image}   |   Classes: {len(self.class_names)}\n")

        splits = ["train"] * n_train + ["val"] * n_val + ["test"] * n_test
        random.shuffle(splits)

        stats = {"train": 0, "val": 0, "test": 0, "total_objects": 0, "errors": 0}
        t0 = time.time()

        for i, split in enumerate(progress_wrap(splits, desc="Generating")):
            try:
                r = self._generate_image(i, split)
                stats[split]          += 1
                stats["total_objects"] += r["objects"]
            except Exception as exc:
                stats["errors"] += 1
                if stats["errors"] <= 5:
                    print(f"\n[WARN]  Image {i} failed: {exc}")

        elapsed = time.time() - t0
        self._save_yaml()

        print(f"\n{'='*65}")
        print("[OK]  GENERATION COMPLETE")
        print(f"{'='*65}")
        print(f"  [TIME]  {elapsed:.1f}s  ({elapsed/60:.1f} min)")
        print(f"  [STAT] Train        : {stats['train']:,}")
        print(f"  [STAT] Val          : {stats['val']:,}")
        print(f"  [STAT] Test         : {stats['test']:,}")
        print(f"  [HIT] Total objects: {stats['total_objects']:,}")
        if stats["errors"]:
            print(f"  [WARN]  Errors       : {stats['errors']}")
        print(f"  [DIR] Output       : {self.out}")
        print(f"{'='*65}")

        return stats

    def _save_yaml(self):
        data = {
            "path":  str(self.out.absolute()).replace("\\", "/"),
            "train": "images/train",
            "val":   "images/val",
            "test":  "images/test",
            "nc":    len(self.class_names),
            "names": {i: n for i, n in enumerate(self.class_names)},
        }
        yp = self.out / "dataset.yaml"
        yp.write_text(yaml.dump(data, default_flow_style=False,
                                allow_unicode=True), encoding="utf-8")
        print(f"[NOTE] Saved dataset.yaml")

    # ── NEW: generate() with 15% Negative Samples ──────────────────────────────

    def generate(self):
        """Main loop: Positive samples + 15% Negative (background-only) samples."""
        t0 = time.time()
        print(f"\n[START] Generating {self.cfg.total_images} images (15% will be negative samples)...")
        n_train = int(self.cfg.total_images * self.cfg.train_ratio)
        n_val   = int(self.cfg.total_images * self.cfg.val_ratio)

        for i in progress_wrap(range(self.cfg.total_images), desc="Generating"):
            # Determine split based on index
            r = i / self.cfg.total_images
            if r < self.cfg.train_ratio:
                split = "train"
            elif r < self.cfg.train_ratio + self.cfg.val_ratio:
                split = "val"
            else:
                split = "test"

            # 15% chance: pure background (no symbols) = Negative Sample
            is_negative = (random.random() < 0.15)
            self._create_image(i, split, is_negative)

        elapsed = time.time() - t0
        self._save_yaml()
        print(f"\n[OK] DONE! {self.cfg.total_images} images in {elapsed:.1f}s ({elapsed/60:.1f} min)")
        print(f"[DIR] Output -> {self.out}")

    def _create_image(self, idx: int, split: str, is_negative: bool) -> None:
        """Generate one image: paste icons on background, write YOLO label."""
        bg_np = random.choice(self.backgrounds).copy()
        # Convert to PIL RGB for alpha blending
        canvas = Image.fromarray(cv2.cvtColor(bg_np, cv2.COLOR_BGR2RGB))

        labels = []
        if not is_negative:
            num_syms = random.randint(self.cfg.min_symbols_per_image,
                                     self.cfg.max_symbols_per_image)
            for _ in range(num_syms):
                cls_name  = random.choice(self.class_names)
                icon_p    = random.choice(self.class_icons[cls_name])

                # Open and prepare icon
                icon = Image.open(icon_p).convert("RGBA")
                icon.thumbnail((self.cfg.max_icon_dim, self.cfg.max_icon_dim))

                scale = random.uniform(self.cfg.min_scale, self.cfg.max_scale)
                new_w = max(8, int(icon.width  * scale))
                new_h = max(8, int(icon.height * scale))
                icon  = icon.resize((new_w, new_h), Image.Resampling.LANCZOS)

                # HVAC standard rotations
                icon = icon.rotate(random.choice([0, 90, 180, 270]), expand=True)

                # Placement boundaries
                max_x = self.cfg.img_width  - icon.width  - 20
                max_y = self.cfg.img_height - icon.height - 20
                if max_x < 20 or max_y < 20:
                    continue

                x = random.randint(20, max_x)
                y = random.randint(20, max_y)

                # Alpha-blend onto canvas
                canvas.paste(icon, (x, y), icon)

                # YOLO normalised label
                cx = (x + icon.width  / 2) / self.cfg.img_width
                cy = (y + icon.height / 2) / self.cfg.img_height
                nw = icon.width  / self.cfg.img_width
                nh = icon.height / self.cfg.img_height
                labels.append(f"{self.class_to_id[cls_name]} {cx:.6f} {cy:.6f} {nw:.6f} {nh:.6f}")

        # Save image (high quality JPG)
        fname = f"synth_{idx:05d}"
        canvas.save(self.out / "images" / split / f"{fname}.jpg", quality=95)

        # Save label (.txt empty for negatives — YOLO standard)
        with open(self.out / "labels" / split / f"{fname}.txt", "w", encoding="utf-8") as f:
            if labels:
                f.write("\n".join(labels))



# ??????????????????????????????????????????????????????????????
# DATASET VERIFIER
# ??????????????????????????????????????????????????????????????

class DatasetVerifier:

    def __init__(self, dataset_dir: str):
        self.dp = Path(dataset_dir)

    # ?? master verify ?????????????????????????????????????????

    def verify(self) -> bool:
        print(f"\n[SCAN] Verifying: {self.dp}")
        print("=" * 65)

        checks = [
            self._check_dirs(),
            self._check_pairs(),
            self._check_labels(),
            self._check_classes_txt(),
            self._check_yaml(),
        ]

        print(f"\n{'='*65}")
        n_fail = checks.count(False)
        if n_fail == 0:
            print("[OK]  ALL CHECKS PASSED -- dataset is ready for training!")
        else:
            print(f"[WARN]   {n_fail} check(s) failed -- see details above.")
        print(f"{'='*65}")
        return all(checks)

    def _check_dirs(self) -> bool:
        print("\n[DIR] Directory structure:")
        ok = True
        for sub in ("images/train", "images/val", "images/test",
                    "labels/train",  "labels/val",  "labels/test"):
            p = self.dp / sub
            if p.exists():
                n = len(list(p.iterdir()))
                print(f"   [OK] {sub:<25} {n:>5} files")
            else:
                print(f"   [FAIL] {sub:<25} MISSING")
                ok = False
        return ok

    def _check_pairs(self) -> bool:
        print("\n[LINK] Image–label pairs:")
        ok = True
        for split in ("train", "val", "test"):
            img_dir = self.dp / "images" / split
            lbl_dir = self.dp / "labels" / split
            if not img_dir.exists():
                continue
            imgs    = list(img_dir.glob("*.jpg"))
            missing = [i for i in imgs
                       if not (lbl_dir / f"{i.stem}.txt").exists()]
            if not missing:
                print(f"   [OK] {split:<8} {len(imgs):>5} images, all labels present")
            else:
                print(f"   [FAIL] {split:<8} {len(missing)} labels missing")
                ok = False
        return ok

    def _check_labels(self) -> bool:
        print("\n[NOTE] Label format (YOLO  class cx cy w h):")
        issues:     List[str] = []
        total_lines = 0

        for split in ("train", "val", "test"):
            lbl_dir = self.dp / "labels" / split
            if not lbl_dir.exists():
                continue
            for lf in lbl_dir.glob("*.txt"):
                lines = [l.strip() for l in lf.read_text(encoding="utf-8").splitlines()
                         if l.strip()]
                total_lines += len(lines)
                for ln, line in enumerate(lines, 1):
                    parts = line.split()
                    if len(parts) != 5:
                        issues.append(f"{lf.name}:{ln} -- {len(parts)} values "
                                      f"(expected 5)")
                        continue
                    try:
                        cls  = float(parts[0])
                        vals = [float(p) for p in parts[1:]]
                        if not cls.is_integer() or cls < 0:
                            issues.append(f"{lf.name}:{ln} -- bad class {cls}")
                        for v in vals:
                            if not 0.0 <= v <= 1.0:
                                issues.append(f"{lf.name}:{ln} -- coord {v:.4f} "
                                              f"out of [0,1]")
                    except ValueError:
                        issues.append(f"{lf.name}:{ln} -- non-numeric value")

        if not issues:
            print(f"   [OK] {total_lines:,} annotation lines -- all valid")
        else:
            print(f"   [FAIL] {len(issues)} issue(s) found:")
            for issue in issues[:5]:
                print(f"      • {issue}")
            if len(issues) > 5:
                print(f"      … and {len(issues)-5} more")
        return not issues

    def _check_classes_txt(self) -> bool:
        print("\n? classes.txt:")
        cf = self.dp / "classes.txt"
        if not cf.exists():
            print("   [FAIL] Not found")
            return False
        classes = [l.strip() for l in cf.read_text(encoding="utf-8").splitlines()
                   if l.strip()]
        print(f"   [OK] {len(classes)} classes")
        print(f"   First 5: {classes[:5]}")
        return True

    def _check_yaml(self) -> bool:
        print("\n[CFG]  dataset.yaml:")
        yf = self.dp / "dataset.yaml"
        if not yf.exists():
            print("   [FAIL] Not found")
            return False
        cfg = yaml.safe_load(yf.read_text(encoding="utf-8"))
        missing = [k for k in ("path", "train", "val", "nc", "names")
                   if k not in cfg]
        if missing:
            print(f"   [FAIL] Missing keys: {missing}")
            return False
        print(f"   [OK] Valid  ({cfg['nc']} classes, train/val/test defined)")
        return True

    # ?? stats ????????????????????????????????????????????????

    def print_stats(self):
        print("\n[STAT] Dataset statistics:")
        gi = go = 0
        for split in ("train", "val", "test"):
            img_dir = self.dp / "images" / split
            lbl_dir = self.dp / "labels" / split
            if not img_dir.exists():
                continue
            imgs = list(img_dir.glob("*.jpg"))
            objs = sum(
                sum(1 for l in lf.read_text(encoding="utf-8").splitlines()
                    if l.strip())
                for lf in lbl_dir.glob("*.txt")
            ) if lbl_dir.exists() else 0
            avg  = objs / len(imgs) if imgs else 0
            print(f"   {split:<8}: {len(imgs):>5} imgs  "
                  f"{objs:>7} objects  ({avg:.1f} avg/img)")
            gi += len(imgs)
            go += objs
        print(f"   {'TOTAL':<8}: {gi:>5} imgs  {go:>7} objects")

    # ?? visualise ????????????????????????????????????????????

    def visualize_samples(self, num_samples: int = 3, split: str = "train"):
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
        except ImportError:
            print("[WARN]  matplotlib not installed -- skipping visualization")
            return

        cf = self.dp / "classes.txt"
        class_names: List[str] = []
        if cf.exists():
            class_names = [l.strip() for l in
                           cf.read_text(encoding="utf-8").splitlines() if l.strip()]

        img_dir = self.dp / "images" / split
        lbl_dir = self.dp / "labels" / split
        if not img_dir.exists():
            return

        imgs = list(img_dir.glob("*.jpg"))
        if not imgs:
            return
        samples = random.sample(imgs, min(num_samples, len(imgs)))

        fig, axes = plt.subplots(1, len(samples),
                                 figsize=(6 * len(samples), 6))
        if len(samples) == 1:
            axes = [axes]

        cmap = plt.cm.Set3(np.linspace(0, 1, max(len(class_names), 1)))

        for ax, ip in zip(axes, samples):
            img = cv2.cvtColor(cv2.imread(str(ip)), cv2.COLOR_BGR2RGB)
            H, W = img.shape[:2]
            lp = lbl_dir / f"{ip.stem}.txt"
            if lp.exists():
                for line in lp.read_text(encoding="utf-8").splitlines():
                    pts = line.strip().split()
                    if len(pts) == 5:
                        cid = int(float(pts[0]))
                        cx, cy, nw, nh = [float(p) for p in pts[1:]]
                        x1 = int((cx - nw / 2) * W)
                        y1 = int((cy - nh / 2) * H)
                        x2 = int((cx + nw / 2) * W)
                        y2 = int((cy + nh / 2) * H)
                        col = tuple(int(c * 255)
                                    for c in cmap[cid % len(cmap)][:3])
                        cv2.rectangle(img, (x1, y1), (x2, y2), col, 2)
                        lbl = (class_names[cid][:14]
                               if cid < len(class_names) else str(cid))
                        cv2.putText(img, lbl, (x1, max(y1 - 4, 10)),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.38, col, 1)
            ax.imshow(img)
            ax.set_title(f"{split}: {ip.name}", fontsize=8)
            ax.axis("off")

        plt.suptitle(f"Sample Annotations -- {split}",
                     fontsize=12, fontweight="bold")
        plt.tight_layout()
        sp = self.dp / f"sample_viz_{split}.png"
        plt.savefig(str(sp), dpi=150, bbox_inches="tight")
        plt.close()
        print(f"[STAT] Visualization saved -> {sp}")


# ??????????????????????????????????????????????????????????????
# ENTRY POINT
# ??????????????????????????????????????????????????????????????

def main():
    parser = argparse.ArgumentParser(
        description="HVAC Synthetic Data Generator -- Phase 2",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples
--------
  # Generate 3 000 images then verify (default):
  python generate_synthetic_data.py

  # Generate 5 000 images:
  python generate_synthetic_data.py --num-images 5000

  # Verify an already-generated dataset:
  python generate_synthetic_data.py --mode verify

  # Custom paths:
  python generate_synthetic_data.py --icons path/to/icons --output path/to/out
        """,
    )
    parser.add_argument("--mode", choices=["generate", "verify", "both"],
                        default="both", help="Operation mode (default: both)")
    parser.add_argument("--icons",
                        default=(r"C:\Users\Friends shop\OneDrive\Desktop"
                                 r"\BOQ ESTOMATION\HVAC_Project\data\icons"),
                        help="Path to icons directory")
    parser.add_argument("--output",
                        default=(r"C:\Users\Friends shop\OneDrive\Desktop"
                                 r"\BOQ ESTOMATION\HVAC_Project\data\dataset"),
                        help="Output directory for dataset")
    parser.add_argument("--num-images", type=int, default=3000,
                        help="Images to generate (default: 3000)")
    parser.add_argument("--min-symbols", type=int, default=1,
                        help="Min symbols per image (default: 1)")
    parser.add_argument("--max-symbols", type=int, default=8,
                        help="Max symbols per image (default: 8)")
    parser.add_argument("--seed", type=int, default=42,
                        help="Random seed (default: 42)")

    args = parser.parse_args()

    random.seed(args.seed)
    np.random.seed(args.seed)

    cfg = Config(
        icons_dir=args.icons,
        output_dir=args.output,
        total_images=args.num_images,
        min_symbols_per_image=args.min_symbols,
        max_symbols_per_image=args.max_symbols,
    )

    if args.mode in ("generate", "both"):
        gen = SyntheticDataGenerator(cfg)
        gen.generate()   # Uses 15% negative samples + PIL alpha blending

    if args.mode in ("verify", "both"):
        ver = DatasetVerifier(args.output)
        ver.verify()
        ver.print_stats()
        ver.visualize_samples(num_samples=3, split="train")
        ver.visualize_samples(num_samples=3, split="val")


if __name__ == "__main__":
    main()
