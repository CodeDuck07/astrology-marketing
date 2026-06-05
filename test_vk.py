"""Проверка доступа к группе VK через API. Посты не публикуются."""

import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

API_VERSION = "5.199"
ENV_PATH = Path(__file__).resolve().parent / ".env"


def main() -> int:
    load_dotenv(ENV_PATH)

    token = os.getenv("VK_TOKEN", "").strip()
    group_id = os.getenv("VK_GROUP_ID", "").strip()

    if not token:
        print("Ошибка: VK_TOKEN не задан в .env")
        return 1
    if not group_id:
        print("Ошибка: VK_GROUP_ID не задан в .env")
        return 1

    try:
        response = requests.get(
            "https://api.vk.com/method/groups.getById",
            params={
                "access_token": token,
                "v": API_VERSION,
                "group_id": group_id,
            },
            timeout=30,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        print(f"Ошибка сети: {exc}")
        return 1

    data = response.json()

    if "error" in data:
        err = data["error"]
        print(f"VK API ошибка {err.get('error_code')}: {err.get('error_msg')}")
        return 1

    payload = data.get("response")
    if isinstance(payload, dict):
        groups = payload.get("groups", [])
    elif isinstance(payload, list):
        groups = payload
    else:
        groups = []

    if not groups:
        print("Группа не найдена.")
        return 1

    group = groups[0]
    print("OK: группа найдена")
    print(f"  id: {group.get('id')}")
    print(f"  name: {group.get('name')}")
    print(f"  screen_name: {group.get('screen_name')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
