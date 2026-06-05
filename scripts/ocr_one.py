#!/usr/bin/env python3
"""OCR одного PDF → .txt (ocrmypdf + pymupdf, как vkbot/scripts/ocr_batch.py)."""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MATERIALS_DIR = ROOT / "materials"
OCR_PDF_DIR = MATERIALS_DIR / "pdf_ocr"
DEFAULT_PDF = Path.home() / "Desktop" / "учебники дополнительно" / "как стать магом.pdf"
DEFAULT_OUT = MATERIALS_DIR / "esoteric" / "как_стать_магом.txt"

MIN_TEXT_CHARS = 500
OCR_LANG = "rus+eng"

try:
    import fitz
except ImportError:
    print("Установите pymupdf: python3 -m pip install pymupdf", file=sys.stderr)
    sys.exit(1)


def normalize_lesson_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"([а-яёА-ЯЁa-zA-Z])-\s*\n\s*([а-яёa-zа-яё])", r"\1\2", text)
    text = re.sub(r"([а-яёА-ЯЁ])-\s+([а-яё])", r"\1\2", text)
    text = re.sub(r"([a-zA-Z])-\s+([a-z])", r"\1\2", text)
    return text.strip()


def slugify(name: str) -> str:
    stem = Path(name).stem
    s = re.sub(r"[^\w\-]+", "_", stem, flags=re.UNICODE)
    s = re.sub(r"_+", "_", s).strip("_")
    return (s[:120] or "book")


def pdf_to_text(pdf_path: Path) -> str:
    doc = fitz.open(pdf_path)
    try:
        parts = [page.get_text() for page in doc]
    finally:
        doc.close()
    return normalize_lesson_text("\n".join(parts))


def run_ocrmypdf(src: Path, dst: Path, skip_text: bool) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ocrmypdf",
        "-l",
        OCR_LANG,
        "--rotate-pages",
        "--deskew",
    ]
    if skip_text:
        cmd.append("--skip-text")
    cmd.extend([str(src), str(dst)])
    subprocess.run(cmd, check=True, capture_output=True, text=True)


def ocr_pdf(src: Path, work_dir: Path) -> Path:
    slug = slugify(src.name)
    out_skip = work_dir / f"{slug}_skip.pdf"
    out_full = work_dir / f"{slug}_full.pdf"

    run_ocrmypdf(src, out_skip, skip_text=True)
    if len(pdf_to_text(out_skip)) >= MIN_TEXT_CHARS:
        return out_skip

    if out_full.exists():
        out_full.unlink()
    run_ocrmypdf(src, out_full, skip_text=False)
    return out_full


def process_one(pdf_path: Path, out_txt: Path, force: bool) -> int:
    if not pdf_path.is_file():
        print(f"PDF не найден: {pdf_path}")
        return 1

    if out_txt.is_file() and not force:
        existing = out_txt.read_text(encoding="utf-8")
        if len(existing.strip()) >= MIN_TEXT_CHARS:
            print(f"Уже есть {out_txt} ({len(existing)} симв.). Используйте --force для перезаписи.")
            return 0

    OCR_PDF_DIR.mkdir(parents=True, exist_ok=True)
    out_txt.parent.mkdir(parents=True, exist_ok=True)

    try:
        text = pdf_to_text(pdf_path)
        source_pdf = pdf_path
        note = "текст из pdf"

        if len(text) < MIN_TEXT_CHARS:
            print("Мало текста в PDF, запускаю ocrmypdf…")
            source_pdf = ocr_pdf(pdf_path, OCR_PDF_DIR)
            text = pdf_to_text(source_pdf)
            note = "ocr"

        text = normalize_lesson_text(text)
        out_txt.write_text(text, encoding="utf-8")
        n = len(text)
        status = "OK" if n >= MIN_TEXT_CHARS else "СКАН"
        print(f"{pdf_path.name} → {out_txt.relative_to(ROOT)}: {n} симв. [{status}, {note}]")
        return 0 if n >= MIN_TEXT_CHARS else 1
    except subprocess.CalledProcessError as exc:
        err = (exc.stderr or exc.stdout or str(exc))[:300]
        print(f"ocrmypdf ошибка: {err}")
        return 1
    except Exception as exc:
        print(f"Ошибка: {exc}")
        return 1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="OCR одного PDF в .txt")
    parser.add_argument(
        "pdf",
        nargs="?",
        default=str(DEFAULT_PDF),
        help=f"путь к PDF (по умолчанию: {DEFAULT_PDF})",
    )
    parser.add_argument(
        "--out",
        default=str(DEFAULT_OUT),
        help=f"куда сохранить .txt (по умолчанию: {DEFAULT_OUT})",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="перезаписать .txt даже если уже достаточно текста",
    )
    return parser.parse_args()


def main() -> int:
    if not shutil.which("ocrmypdf"):
        print(
            "Не найден ocrmypdf. Установите:\n"
            "  brew install tesseract tesseract-lang ocrmypdf",
            file=sys.stderr,
        )
        return 1

    args = parse_args()
    return process_one(Path(args.pdf), Path(args.out), args.force)


if __name__ == "__main__":
    raise SystemExit(main())
