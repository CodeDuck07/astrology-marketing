# Astrology Marketing — автопосты для VK Goodness Astrology

Генерация коротких постов из учебников в `materials/` и **отложенная** публикация в [goodness_astrology](https://vk.com/goodness_astrology).

> Материалы локально, см. `scripts/import_pdfs.py`.

## Расписание

| Запуск скрипта | Пост выходит |
|----------------|--------------|
| **Вторник**    | **Среда 12:00** (МСК) |
| **Суббота**    | **Воскресенье 12:00** (МСК) |

Пост не появляется на стене сразу — VK получает `publish_date` (отложенный пост).

## Настройка

1. Создайте `.env` в корне проекта:

```env
VK_TOKEN=ваш_токен_сообщества
VK_GROUP_ID=223386386
OPENAI_API_KEY=ваш_ключ
OPENAI_BASE_URL=https://api.proxyapi.ru/openai/v1
```

2. Установите зависимости:

```bash
cd "/path/to/astrology_marketing"
python3 -m pip install -r requirements.txt
```

3. Учебники лежат в подпапках `materials/` (см. ниже).

Токен VK должен иметь право **«Публикация на стене»** сообщества.

## Материалы

```
materials/
├── astro/      # астрология
├── nlp/        # НЛП
├── psycho/     # психосоматика
├── chinese/    # бацзы
├── fengshui/   # фэн-шуй
├── chakras/    # чакры
└── esoteric/   # эзотерика (магия, акаши и т.п.)
```

### Ротация тем

Каждый новый пост берёт фрагмент из **следующей темы** по кругу:

`astro → nlp → psycho → chinese → fengshui → chakras → esoteric → astro …`

Тема сохраняется в `posts.db`, повторы фрагментов не допускаются.

### Импорт PDF с рабочего стола

Скрипт читает PDF из `~/Desktop/учебники дополнительно/` и конвертирует в `.txt`:

| Источник на Desktop | Куда попадает |
|---------------------|---------------|
| `нлп/` | `materials/nlp/` |
| `психосоматика/` | `materials/psycho/` |
| `бацзы/` | `materials/chinese/` |
| `феншуй/` | `materials/fengshui/` |
| `Чакры для начинающих…/` | `materials/chakras/` |
| `как стать магом.pdf` | `materials/esoteric/` |
| `сила ведьм.pdf` | `materials/esoteric/` |
| `хроники акаши.pdf` | `materials/esoteric/` |

Полный импорт всех папок и эзотерики из корня:

```bash
cd "/path/to/astrology_marketing"
python3 scripts/import_pdfs.py
```

Только три PDF эзотерики из корня:

```bash
python3 scripts/import_pdfs.py --esoteric
```

Другая исходная папка:

```bash
python3 scripts/import_pdfs.py --esoteric "/путь/к/папке"
```

Используется **pymupdf** (как в vkbot).

### OCR для сканов (один PDF)

Если PDF без текста (скан), например `как стать магом.pdf`:

```bash
# нужно один раз: brew install tesseract tesseract-lang ocrmypdf
cd "/path/to/astrology_marketing"
python3 scripts/ocr_one.py
```

Свой PDF и выходной файл:

```bash
python3 scripts/ocr_one.py "~/Desktop/учебники дополнительно/как стать магом.pdf" \
  --out materials/esoteric/как_стать_магом.txt
```

Перезаписать уже готовый `.txt`:

```bash
python3 scripts/ocr_one.py --force
```

Временные OCR-PDF: `materials/pdf_ocr/` (в git не попадает).

## Скрипты

### test_vk.py — проверка доступа к группе

```bash
python3 test_vk.py
```

### generate_post.py — черновик (без VK)

```bash
python3 generate_post.py
```

### publish_post.py — отложенный пост

Только **во вторник** или **в субботу** (иначе скрипт завершится с ошибкой).

С подтверждением:

```bash
python3 publish_post.py
```

Без вопроса (для cron):

```bash
python3 publish_post.py --auto
```

## Cron на VPS

Скопируйте проект на сервер, настройте `.env`, затем `crontab -e`:

```cron
# МСК: вторник 09:00 → пост на среду 12:00
0 9 * * 2 TZ=Europe/Moscow cd /path/to/astrology_marketing && /usr/bin/python3 publish_post.py --auto >> cron.log 2>&1

# МСК: суббота 09:00 → пост на воскресенье 12:00
0 9 * * 6 TZ=Europe/Moscow cd /path/to/astrology_marketing && /usr/bin/python3 publish_post.py --auto >> cron.log 2>&1
```

Замените `/path/to/astrology_marketing` на реальный путь на VPS.

Если cron без `TZ=`, переведите время в часовой пояс сервера (для UTC: **06:00** вместо 09:00 МСК).

## Без повторов

Запланированные фрагменты сохраняются в SQLite (`posts.db`). Один фрагмент из `materials/` не используется дважды.

Файлы `posts.db`, `.env` и содержимое `materials/` (кроме `materials/README.md`) не попадают в git.

## Структура

```
astrology_marketing/
├── .env
├── materials/          # локально; в git — README.md и .gitkeep
│   └── README.md
├── PORTFOLIO-КЕЙС.md
├── scripts/
│   ├── import_pdfs.py
│   └── ocr_one.py
├── posts.db
├── test_vk.py
├── generate_post.py
├── publish_post.py
├── schedule.py
└── db.py
```
