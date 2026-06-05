"""Генерация черновика поста для VK из случайного фрагмента учебника. На стену не публикует."""

import os
import random
import re
import sys
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

from db import AllFragmentsPublishedError, fragment_hash, next_theme, set_last_theme

ROOT = Path(__file__).resolve().parent
ENV_PATH = ROOT / ".env"
MATERIALS_DIR = ROOT / "materials"

MIN_FRAGMENT_CHARS = 300
MAX_FRAGMENT_CHARS = 2000
MODEL = "gpt-4o-mini"

THEMES: tuple[str, ...] = (
    "astro",
    "nlp",
    "psycho",
    "chinese",
    "fengshui",
    "chakras",
    "esoteric",
)

THEME_LABELS: dict[str, str] = {
    "astro": "астрология",
    "nlp": "НЛП",
    "psycho": "психосоматика",
    "chinese": "бацзы",
    "fengshui": "фэн-шуй",
    "chakras": "чакры",
    "esoteric": "эзотерика",
}

SYSTEM_PROMPT = """Ты — автор сообщества VK Goodness Astrology. Пишешь пост от первого лица («я»), обращаясь к читателю на «вы».

Темы по папке источника:
- astro — европейская астрология, таро
- nlp — НЛП
- psycho — психосоматика
- chinese — китайская астрология (бацзы)
- fengshui — фэн-шуй
- chakras — чакры
- esoteric — эзотерика, духовные практики

По фрагменту учебника напиши пост для стены ВКонтакте. Только смысл из фрагмента — без выдумок, без фактов, которых нет в тексте.

СТРУКТУРА (обязательно):
1. Приветствие — всегда начинай с: «Всех приветствую!».
2. Первый абзац — о чём пост, зацепить интерес.
3. Основная часть — польза из фрагмента; профессиональные термины объясни простыми словами; читатель должен узнать себя («а как у меня?», «а что со мной?»).
4. Мягкий призыв — пригласи на консультацию ко мне; формулировка по теме поста (астрология — карта/разбор, НЛП — паттерн/поведение, психосоматика — связь тела и эмоций, фэн-шуй/бацзы/чакры — по теме, не своди всё к натальной карте).
5. Концовка — всегда дословно:
Если у вас есть ко мне какие-либо вопросы по этой или любой другой теме, вы можете написать мне и мы вместе во всём разберёмся!
#GoodnessAstrology

Правила:
- до 1500 символов (строго, включая пробелы и хештег);
- 3–6 уместных эмодзи по тексту;
- для psycho/здоровья: образовательный материал, не медицинский диагноз;
- без markdown, без «я ИИ», без служебных пояснений;
- верни только текст поста."""


def load_env() -> tuple[str, str | None]:
    load_dotenv(ENV_PATH)
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    base_url = os.getenv("OPENAI_BASE_URL", "").strip() or None
    if not api_key:
        print("Ошибка: OPENAI_API_KEY не задан в .env")
        sys.exit(1)
    return api_key, base_url


def normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def _fragments_from_file(path: Path) -> list[str]:
    text = normalize_text(path.read_text(encoding="utf-8"))
    if len(text) < MIN_FRAGMENT_CHARS:
        return []

    paragraphs = [
        p.strip()
        for p in re.split(r"\n\s*\n", text)
        if len(p.strip()) >= MIN_FRAGMENT_CHARS
    ]

    if paragraphs:
        return [
            p[:MAX_FRAGMENT_CHARS].rsplit(" ", 1)[0].strip() if len(p) > MAX_FRAGMENT_CHARS else p
            for p in paragraphs
        ]

    fragments: list[str] = []
    step = max(MIN_FRAGMENT_CHARS, MAX_FRAGMENT_CHARS // 2)
    for start in range(0, len(text) - MIN_FRAGMENT_CHARS + 1, step):
        chunk = text[start : start + MAX_FRAGMENT_CHARS].strip()
        if len(chunk) >= MIN_FRAGMENT_CHARS:
            fragments.append(chunk)
    return fragments


def collect_fragment_candidates(theme: str | None = None) -> list[tuple[str, str]]:
    candidates: list[tuple[str, str]] = []
    search_root = MATERIALS_DIR / theme if theme else MATERIALS_DIR
    if not search_root.is_dir():
        return candidates

    for path in sorted(search_root.rglob("*.txt")):
        rel = path.relative_to(MATERIALS_DIR).as_posix()
        for fragment in _fragments_from_file(path):
            candidates.append((rel, fragment))
    return candidates


def _rotate_themes(start: str) -> list[str]:
    idx = THEMES.index(start)
    return list(THEMES[idx:] + THEMES[:idx])


def random_fragment_for_theme(
    theme: str,
    exclude_hashes: set[str] | None = None,
) -> tuple[str, str]:
    exclude = exclude_hashes or set()
    candidates = [
        (source, fragment)
        for source, fragment in collect_fragment_candidates(theme)
        if fragment_hash(source, fragment) not in exclude
    ]
    if not candidates:
        raise AllFragmentsPublishedError()
    set_last_theme(theme)
    return random.choice(candidates)


def random_fragment(exclude_hashes: set[str] | None = None) -> tuple[str, str, str]:
    if not MATERIALS_DIR.is_dir():
        print("Ошибка: папка materials/ не найдена")
        sys.exit(1)

    exclude = exclude_hashes or set()
    start_theme = next_theme(THEMES)

    for theme in _rotate_themes(start_theme):
        candidates = [
            (source, fragment)
            for source, fragment in collect_fragment_candidates(theme)
            if fragment_hash(source, fragment) not in exclude
        ]
        if candidates:
            set_last_theme(theme)
            source, fragment = random.choice(candidates)
            return theme, source, fragment

    raise AllFragmentsPublishedError()


def generate_post(client: OpenAI, theme: str, source: str, fragment: str) -> str:
    user_prompt = (
        f"Тема: {THEME_LABELS.get(theme, theme)}\n"
        f"Источник: {source}\n\n"
        f"--- Фрагмент учебника ---\n{fragment}\n\n"
        "Напиши пост для VK."
    )
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.7,
    )
    return (response.choices[0].message.content or "").strip()


def create_post(
    exclude_hashes: set[str] | None = None,
    theme: str | None = None,
) -> tuple[str, str, str, str]:
    """Возвращает (тема, путь_к_файлу, фрагмент, текст_поста)."""
    api_key, base_url = load_env()
    client = OpenAI(api_key=api_key, base_url=base_url)
    if theme:
        if theme not in THEMES:
            raise ValueError(f"Неизвестная тема: {theme}")
        source, fragment = random_fragment_for_theme(theme, exclude_hashes=exclude_hashes)
    else:
        theme, source, fragment = random_fragment(exclude_hashes=exclude_hashes)
    post = generate_post(client, theme, source, fragment)
    return theme, source, fragment, post


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Черновик поста для VK")
    parser.add_argument(
        "--theme",
        choices=THEMES,
        help="взять фрагмент из конкретной темы (для проверки)",
    )
    args = parser.parse_args()

    try:
        theme, source, fragment, post = create_post(theme=args.theme)
    except Exception as exc:
        print(f"Ошибка GPT: {exc}")
        return 1

    print(f"Тема: {THEME_LABELS.get(theme, theme)}")
    print(f"Источник: materials/{source}")
    print(f"Фрагмент ({len(fragment)} симв.):\n{fragment[:400]}{'…' if len(fragment) > 400 else ''}\n")
    print("--- Пост для VK ---")
    print(post)
    print(f"\n({len(post)} символов, на стену не опубликовано)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
