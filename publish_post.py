"""Генерация поста и отложенная публикация в VK (goodness_astrology)."""

import argparse
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

from db import AllFragmentsPublishedError, get_published_hashes, save_publication
from generate_post import THEME_LABELS, create_post
from schedule import WrongWeekdayError, schedule_label, scheduled_publish_time

API_VERSION = "5.199"
ENV_PATH = Path(__file__).resolve().parent / ".env"
GROUP_SCREEN_NAME = "goodness_astrology"


def load_vk_config() -> tuple[str, int]:
    load_dotenv(ENV_PATH)
    import os

    token = os.getenv("VK_TOKEN", "").strip()
    group_id_raw = os.getenv("VK_GROUP_ID", "").strip()

    if not token:
        print("Ошибка: VK_TOKEN не задан в .env")
        sys.exit(1)
    if not group_id_raw:
        print("Ошибка: VK_GROUP_ID не задан в .env")
        sys.exit(1)

    try:
        group_id = int(group_id_raw)
    except ValueError:
        print("Ошибка: VK_GROUP_ID должен быть числом")
        sys.exit(1)

    return token, group_id


def schedule_wall_post(
    token: str,
    group_id: int,
    message: str,
    publish_at: int,
) -> tuple[int, int]:
    owner_id = -abs(group_id)

    try:
        response = requests.post(
            "https://api.vk.com/method/wall.post",
            data={
                "access_token": token,
                "v": API_VERSION,
                "owner_id": owner_id,
                "from_group": 1,
                "message": message,
                "publish_date": publish_at,
            },
            timeout=30,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise RuntimeError(f"Ошибка сети: {exc}") from exc

    data = response.json()
    if "error" in data:
        err = data["error"]
        raise RuntimeError(f"VK API ошибка {err.get('error_code')}: {err.get('error_msg')}")

    post_id = int(data["response"]["post_id"])
    return owner_id, post_id


def confirm_schedule(when_label: str) -> bool:
    answer = input(f"Запланировать на {when_label}? да/нет: ").strip().lower()
    return answer in {"да", "yes", "y", "д"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Сгенерировать и поставить отложенный пост в VK",
    )
    parser.add_argument(
        "--auto",
        action="store_true",
        help="запланировать без вопроса да/нет (для cron на VPS)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="игнорировать день недели (для теста): завтра 12:00 МСК",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        publish_dt = scheduled_publish_time(force=args.force)
    except WrongWeekdayError as exc:
        print(exc)
        return 1

    if args.force:
        print("(режим --force: день недели игнорируется, пост на завтра 12:00 МСК)")

    publish_ts = int(publish_dt.timestamp())
    when_label = schedule_label(publish_dt)

    published = get_published_hashes()
    try:
        theme, source, fragment, post = create_post(exclude_hashes=published)
    except AllFragmentsPublishedError:
        print("Все доступные фрагменты уже опубликованы.")
        return 1
    except Exception as exc:
        print(f"Ошибка генерации: {exc}")
        return 1

    if not post:
        print("Ошибка: GPT вернул пустой пост")
        return 1

    print(f"Тема: {THEME_LABELS.get(theme, theme)}")
    print(f"Источник: materials/{source}")
    print(f"Фрагмент ({len(fragment)} симв.):\n{fragment[:400]}{'…' if len(fragment) > 400 else ''}\n")
    print("--- Пост для VK ---")
    print(post)
    print(f"\n({len(post)} символов)")
    print(f"Отложенная публикация: {when_label}")

    if not args.auto and not confirm_schedule(when_label):
        print("Отменено, пост не запланирован.")
        return 0

    token, group_id = load_vk_config()
    try:
        owner_id, post_id = schedule_wall_post(token, group_id, post, publish_ts)
    except RuntimeError as exc:
        print(exc)
        return 1

    save_publication(
        source,
        fragment,
        post,
        vk_post_id=post_id,
        scheduled_for=publish_dt.isoformat(),
    )
    print(f"Запланировано для {GROUP_SCREEN_NAME} на {when_label}")
    print(f"Черновик в VK: https://vk.com/wall{owner_id}_{post_id}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
