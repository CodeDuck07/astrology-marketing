"""Веб-админка: просмотр и правка постов из posts.db."""

import hashlib
import os
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
from dotenv import load_dotenv
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.sessions import SessionMiddleware

from db import get_published_post, list_published_posts, update_post_text
from generate_post import THEME_LABELS

ROOT = Path(__file__).resolve().parent
ENV_PATH = ROOT / ".env"
TEMPLATES = Jinja2Templates(directory=str(ROOT / "templates"))
API_VERSION = "5.199"
MSK = ZoneInfo("Europe/Moscow")

app = FastAPI(title="Astrology Marketing Admin")
load_dotenv(ENV_PATH)

admin_password = os.getenv("ADMIN_PASSWORD", "").strip()
if not admin_password:
    print("Ошибка: ADMIN_PASSWORD не задан в .env", file=sys.stderr)
    sys.exit(1)

session_secret = hashlib.sha256(admin_password.encode("utf-8")).hexdigest()


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if path.startswith("/login") or path == "/favicon.ico":
            return await call_next(request)
        if not request.session.get("authenticated"):
            return RedirectResponse("/login", status_code=303)
        return await call_next(request)


app.add_middleware(AuthMiddleware)
app.add_middleware(SessionMiddleware, secret_key=session_secret)


def load_vk_config() -> tuple[str, int]:
    token = os.getenv("VK_TOKEN", "").strip()
    group_id_raw = os.getenv("VK_GROUP_ID", "").strip()
    if not token or not group_id_raw:
        raise RuntimeError("VK_TOKEN или VK_GROUP_ID не заданы в .env")
    return token, int(group_id_raw)


def edit_wall_post(token: str, group_id: int, post_id: int, message: str) -> None:
    owner_id = -abs(group_id)
    response = requests.post(
        "https://api.vk.com/method/wall.edit",
        data={
            "access_token": token,
            "v": API_VERSION,
            "owner_id": owner_id,
            "post_id": post_id,
            "message": message,
        },
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()
    if "error" in data:
        err = data["error"]
        raise RuntimeError(f"VK API {err.get('error_code')}: {err.get('error_msg')}")


def theme_from_source(source_file: str) -> str:
    theme = source_file.split("/", 1)[0]
    return THEME_LABELS.get(theme, theme)


def format_dt(value: str | None) -> str:
    if not value:
        return "—"
    try:
        dt = datetime.fromisoformat(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=ZoneInfo("UTC"))
        return dt.astimezone(MSK).strftime("%d.%m.%Y %H:%M")
    except ValueError:
        return value


def post_date(post: dict) -> str:
    return format_dt(post.get("scheduled_for") or post.get("published_at"))


def vk_wall_url(group_id: int, vk_post_id: int | None) -> str | None:
    if not vk_post_id:
        return None
    return f"https://vk.com/wall{-abs(group_id)}_{vk_post_id}"


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request, error: str | None = None) -> HTMLResponse:
    if request.session.get("authenticated"):
        return RedirectResponse("/", status_code=303)
    return TEMPLATES.TemplateResponse(
        request,
        "login.html",
        {"error": error},
    )


@app.post("/login")
def login_submit(request: Request, password: str = Form(...)) -> RedirectResponse:
    if password == admin_password:
        request.session["authenticated"] = True
        return RedirectResponse("/", status_code=303)
    return RedirectResponse("/login?error=1", status_code=303)


@app.get("/", response_class=HTMLResponse)
def index(request: Request) -> HTMLResponse:
    posts = list_published_posts()
    try:
        _, group_id = load_vk_config()
    except RuntimeError:
        group_id = 0

    rows = []
    for post in posts:
        preview = post["post_text"].replace("\n", " ")
        if len(preview) > 120:
            preview = preview[:120] + "…"
        rows.append(
            {
                "id": post["id"],
                "preview": preview,
                "theme": theme_from_source(post["source_file"]),
                "date": post_date(post),
                "vk_post_id": post["vk_post_id"],
                "vk_url": vk_wall_url(group_id, post["vk_post_id"]),
            }
        )

    return TEMPLATES.TemplateResponse(request, "index.html", {"posts": rows})


@app.get("/post/{post_id}", response_class=HTMLResponse)
def post_view(
    request: Request,
    post_id: int,
    saved: str | None = None,
    vk_error: str | None = None,
) -> HTMLResponse:
    post = get_published_post(post_id)
    if not post:
        return RedirectResponse("/", status_code=303)

    try:
        _, group_id = load_vk_config()
    except RuntimeError:
        group_id = 0

    return TEMPLATES.TemplateResponse(
        request,
        "post_edit.html",
        {
            "post": post,
            "theme": theme_from_source(post["source_file"]),
            "date": post_date(post),
            "vk_url": vk_wall_url(group_id, post["vk_post_id"]),
            "saved": saved == "1",
            "vk_error": vk_error,
        },
    )


@app.post("/post/{post_id}")
def post_save(
    request: Request,
    post_id: int,
    post_text: str = Form(...),
) -> RedirectResponse:
    post = get_published_post(post_id)
    if not post:
        return RedirectResponse("/", status_code=303)

    text = post_text.strip()
    if not text:
        return RedirectResponse(f"/post/{post_id}?vk_error=empty", status_code=303)

    update_post_text(post_id, text)

    vk_post_id = post.get("vk_post_id")
    if vk_post_id:
        try:
            token, group_id = load_vk_config()
            edit_wall_post(token, group_id, int(vk_post_id), text)
        except (RuntimeError, requests.RequestException) as exc:
            from urllib.parse import quote

            return RedirectResponse(
                f"/post/{post_id}?saved=1&vk_error={quote(str(exc))}",
                status_code=303,
            )

    return RedirectResponse(f"/post/{post_id}?saved=1", status_code=303)
