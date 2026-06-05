#!/usr/bin/env python3
"""Импорт PDF из «учебники дополнительно» в materials/."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MATERIALS_DIR = ROOT / "materials"
DEFAULT_SOURCE = Path.home() / "Desktop" / "учебники дополнительно"
MIN_TEXT_CHARS = 500

FOLDER_MAP: dict[str, str] = {
    "нлп": "nlp",
    "психосоматика": "psycho",
    "бацзы": "chinese",
    "феншуй": "fengshui",
}

ROOT_PDFS: tuple[str, ...] = (
    "как стать магом.pdf",
    "сила ведьм.pdf",
    "хроники акаши.pdf",
)
ESOTERIC_TARGET = "esoteric"

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


def find_chakras_dir(source_root: Path) -> Path | None:
    for child in source_root.iterdir():
        if child.is_dir() and child.name.lower().startswith("чакры"):
            return child
    return None


def convert_pdf_list(pdfs: list[Path], target_dir: Path) -> tuple[int, int]:
    target_dir.mkdir(parents=True, exist_ok=True)
    ok, fail = 0, 0

    for pdf_path in pdfs:
        out_path = target_dir / f"{slugify(pdf_path.name)}.txt"
        try:
            text = pdf_to_text(pdf_path)
        except Exception as exc:
            print(f"  {pdf_path.name}: ОШИБКА — {exc}")
            fail += 1
            continue

        out_path.write_text(text, encoding="utf-8")
        n = len(text)
        tag = " [СКАН — мало текста]" if n < MIN_TEXT_CHARS else ""
        print(f"  {pdf_path.name} → {target_dir.name}/{out_path.name}: {n} симв.{tag}")
        ok += 1

    return ok, fail


def convert_pdfs(source_dir: Path, target_dir: Path) -> tuple[int, int]:
    pdfs = sorted(source_dir.rglob("*.pdf"))
    if not pdfs:
        print(f"  PDF не найдены в {source_dir.name}/")
        return 0, 0
    return convert_pdf_list(pdfs, target_dir)


def import_esoteric(source_root: Path | None = None) -> int:
    source_root = source_root or DEFAULT_SOURCE
    if not source_root.is_dir():
        print(f"Исходная папка не найдена: {source_root}")
        return 1

    pdfs: list[Path] = []
    missing: list[str] = []
    for name in ROOT_PDFS:
        path = source_root / name
        if path.is_file():
            pdfs.append(path)
        else:
            missing.append(name)

    if missing:
        for name in missing:
            print(f"  не найден: {name}")
        if not pdfs:
            return 1

    print(f"Импорт эзотерики из {source_root} → materials/{ESOTERIC_TARGET}/\n")
    ok, fail = convert_pdf_list(pdfs, MATERIALS_DIR / ESOTERIC_TARGET)
    print(f"\nГотово: {ok} файлов, ошибок: {fail}")
    return 0 if fail == 0 else 1


def import_all(source_root: Path | None = None) -> int:
    source_root = source_root or DEFAULT_SOURCE
    if not source_root.is_dir():
        print(f"Исходная папка не найдена: {source_root}")
        return 1

    total_ok, total_fail = 0, 0
    print(f"Импорт PDF из {source_root}\n")

    for folder_name, target_name in FOLDER_MAP.items():
        src = source_root / folder_name
        dst = MATERIALS_DIR / target_name
        if not src.is_dir():
            print(f"— {folder_name}/: папка не найдена, пропуск")
            continue
        print(f"— {folder_name}/ → materials/{target_name}/")
        ok, fail = convert_pdfs(src, dst)
        total_ok += ok
        total_fail += fail
        print()

    chakras_src = find_chakras_dir(source_root)
    if chakras_src:
        print(f"— {chakras_src.name}/ → materials/chakras/")
        ok, fail = convert_pdfs(chakras_src, MATERIALS_DIR / "chakras")
        total_ok += ok
        total_fail += fail
        print()
    else:
        print("— папка «Чакры…»: не найдена, пропуск\n")

    print(f"— корень → materials/{ESOTERIC_TARGET}/")
    esoteric_pdfs = [source_root / name for name in ROOT_PDFS if (source_root / name).is_file()]
    if esoteric_pdfs:
        ok, fail = convert_pdf_list(esoteric_pdfs, MATERIALS_DIR / ESOTERIC_TARGET)
        total_ok += ok
        total_fail += fail
    else:
        print("  PDF в корне не найдены")
    print()

    print(f"Готово: {total_ok} файлов, ошибок: {total_fail}")
    return 0 if total_fail == 0 else 1


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    flags = {a for a in sys.argv[1:] if a.startswith("-")}

    if "--esoteric" in flags:
        src = Path(args[0]) if args else DEFAULT_SOURCE
        raise SystemExit(import_esoteric(src))

    src = Path(args[0]) if args else DEFAULT_SOURCE
    raise SystemExit(import_all(src))
