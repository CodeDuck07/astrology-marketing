# Astrology Marketing — кейс для портфолио

## Задача

Автоматизировать контент для сообщества VK [Goodness Astrology](https://vk.com/goodness_astrology): регулярные экспертные посты из своих учебников без ручного копирования и без повторов.

## Решение

Python-пайплайн из трёх этапов:

1. **Импорт** — PDF с Desktop конвертируются в `.txt` (pymupdf; для сканов — ocrmypdf).
2. **Генерация** — GPT-4o-mini пишет пост по случайному фрагменту учебника в фирменном стиле («Всех приветствую!», призыв к консультации, `#GoodnessAstrology`).
3. **Публикация** — отложенный пост в VK (`wall.post` + `publish_date`): вторник → среда 12:00 МСК, суббота → воскресенье 12:00 МСК.

## Технологии

| Компонент | Стек |
|-----------|------|
| Язык | Python 3 |
| VK API | requests, `groups.getById`, `wall.post` |
| LLM | OpenAI API (gpt-4o-mini) |
| Хранение | SQLite — опубликованные фрагменты и ротация тем |
| Документы | pymupdf, ocrmypdf + tesseract |
| Деплой | cron на VPS, `.env` для секретов |

## Архитектура

```
materials/{astro,nlp,psycho,chinese,fengshui,chakras,esoteric}/*.txt
        ↓ случайный фрагмент + ротация тем
generate_post.py  →  GPT  →  текст поста
        ↓
publish_post.py  →  VK publish_date  →  posts.db
```

**Ротация тем:** каждый новый пост — следующая категория по кругу (астрология → НЛП → психосоматика → … → эзотерика). Один фрагмент не публикуется дважды.

## Что сделано

- Настроены `.env`, `.gitignore`, README; учебники остаются локально (не в git).
- Скрипты: `test_vk.py`, `generate_post.py`, `publish_post.py`, `import_pdfs.py`, `ocr_one.py`.
- Промпт с жёсткой структурой поста и лимитом 1500 символов.
- Расписание отложенных постов и пример cron для VPS.

## Ограничения (честно)

- Личный проект для своего сообщества, не коммерческий продукт.
- Материалы — авторские учебники, в репозиторий не выкладываются.
- GPT иногда превышает лимит символов — можно доработать постобработку.

## Как повторить локально

```bash
cd astrology_marketing
python3 -m pip install -r requirements.txt
# .env + materials/ (см. materials/README.md, scripts/import_pdfs.py)
python3 test_vk.py
python3 generate_post.py --theme nlp
python3 publish_post.py   # во вторник или субботу
```

## Связанные проекты

- [vkbot-goodness](https://github.com/CodeDuck07/vkbot-goodness) — VK-бот с ответами по астрологии (общая логика материалов и OCR).
