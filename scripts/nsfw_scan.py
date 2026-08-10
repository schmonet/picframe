#!/usr/bin/env python3
"""Offline nudity pre-screen for a personal photo archive.

Scans images under a root directory and moves any file whose "nudity score" (max
confidence across a curated set of sensitive detection classes) meets or exceeds a
threshold into a `nude/` subfolder *next to where the file was found* (i.e.
`<any folder>/nude/<same filename>`, no prefix, no renaming), for manual review
before it's ever shown on the picframe display.

Runs fully offline: NudeNet's ONNX model is downloaded once on first use (cached
locally by the `nudenet` package's own cache dir) and never touches the network
again after that. No image data leaves this machine, ever.

Benign body-part classes (faces, feet, armpits, belly, and any "*_COVERED"
variant) are deliberately ignored - only exposed genitalia/breast/buttocks/anus
count toward the score, so e.g. beach/pool photos in swimwear should not trigger
a move.

Usage:
    python nsfw_scan.py <root_dir> [--threshold 0.70] [--dry-run]
                         [--extensions jpg,jpeg,png,heic] [--debug-classes]

Requires:  pip install nudenet
Optional:  pip install pillow-heif   (only if you need .heic support - see the
           HEIC note near IMAGE loading below; unverified, NudeNet's own image
           loader may not support HEIC even with this installed)
"""
import argparse
import shutil
import sys
import time
from pathlib import Path

# Detection classes counted as nudity. Everything else NudeNet reports (e.g.
# FACE_FEMALE/FACE_MALE, FEET_*, ARMPITS_*, BELLY_*, and every "*_COVERED"
# variant) is deliberately excluded from the score - those must never trigger a
# move by themselves, per explicit requirement.
#
# CAUTION: these are the class names used by NudeNet's default detector model
# as of this writing - library/model versions do change class naming over time.
# Before trusting the threshold on a real archive, run once with
# --debug-classes --dry-run and check nsfw_scan.log: it logs every class name
# actually seen. If none of them match SENSITIVE_CLASSES below (score always
# 0), update this set to match what your installed version actually reports.
SENSITIVE_CLASSES = {
    "FEMALE_BREAST_EXPOSED",
    "FEMALE_GENITALIA_EXPOSED",
    "MALE_GENITALIA_EXPOSED",
    "BUTTOCKS_EXPOSED",
    "ANUS_EXPOSED",
}

DEFAULT_EXTENSIONS = {"jpg", "jpeg", "png", "heic"}


def log(log_file: Path, message: str) -> None:
    line = f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {message}"
    print(line)
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def iter_images(root: Path, extensions: set):
    """Yield image files under root, skipping anything already inside a nude/
    review folder (so re-runs don't try to re-process already-sorted files)."""
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower().lstrip(".") not in extensions:
            continue
        rel_parents = path.relative_to(root).parts[:-1]
        if "nude" in rel_parents:
            continue
        yield path


def nude_score(detections):
    """Max confidence among SENSITIVE_CLASSES only; returns (score, all_classes_seen)."""
    best = 0.0
    seen_classes = set()
    for det in detections:
        cls = det.get("class") or det.get("label", "")
        seen_classes.add(cls)
        if cls in SENSITIVE_CLASSES:
            best = max(best, float(det.get("score", 0.0)))
    return best, seen_classes


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("root", type=Path, help="Root directory to scan recursively")
    parser.add_argument("--threshold", type=float, default=0.70,
                         help="Nudity score threshold (0.0-1.0), default 0.70")
    parser.add_argument("--dry-run", action="store_true",
                         help="Only log matches, don't actually move files")
    parser.add_argument("--extensions", default=",".join(sorted(DEFAULT_EXTENSIONS)),
                         help="Comma-separated file extensions to scan")
    parser.add_argument("--debug-classes", action="store_true",
                         help="Log every detected class name per file, for calibrating "
                              "SENSITIVE_CLASSES against your installed model version")
    args = parser.parse_args()

    root = args.root.resolve()
    if not root.is_dir():
        sys.exit(f"Not a directory: {root}")

    try:
        from nudenet import NudeDetector
    except ImportError:
        sys.exit("nudenet is not installed. Run: pip install nudenet")

    extensions = {e.strip().lower().lstrip(".") for e in args.extensions.split(",") if e.strip()}
    log_file = root / "nsfw_scan.log"

    detector = NudeDetector()
    all_seen_classes = set()
    scanned = 0
    moved = 0

    for image_path in iter_images(root, extensions):
        scanned += 1
        try:
            # NOTE re HEIC: NudeNet loads images itself (OpenCV-based), which does not
            # support HEIC out of the box. .heic files will likely raise here and just
            # get logged as an error below rather than silently mis-scored - if you hit
            # that a lot, pre-convert HEIC copies to JPEG for scanning purposes.
            detections = detector.detect(str(image_path))
        except Exception as e:
            log(log_file, f"ERROR scanning {image_path}: {e}")
            continue

        score, seen_classes = nude_score(detections)
        all_seen_classes |= seen_classes
        if args.debug_classes and seen_classes:
            log(log_file, f"DEBUG classes for {image_path}: {sorted(seen_classes)}")

        if score >= args.threshold:
            dest_dir = image_path.parent / "nude"
            dest_path = dest_dir / image_path.name  # keep filename, no prefix
            if args.dry_run:
                log(log_file, f"[DRY RUN] Would move {image_path} -> {dest_path} (score={score:.2f})")
            else:
                dest_dir.mkdir(exist_ok=True)
                if dest_path.exists():
                    log(log_file, f"WARNING: {dest_path} already exists, skipping move for {image_path}")
                else:
                    shutil.move(str(image_path), str(dest_path))
                    log(log_file, f"Moved {image_path} -> {dest_path} (score={score:.2f})")
            moved += 1

    log(log_file, f"Done. Scanned {scanned} files, {moved} matched threshold {args.threshold}.")
    if args.debug_classes:
        log(log_file, f"All classes seen this run: {sorted(all_seen_classes)}")


if __name__ == "__main__":
    main()
