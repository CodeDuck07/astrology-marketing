# Материалы (локально)

Тексты учебников **не хранятся в git** — только на вашем Mac или VPS.

## Структура папок

```
materials/
├── astro/      # астрология
├── nlp/        # НЛП
├── psycho/     # психосоматика
├── chinese/    # бацзы
├── fengshui/   # фэн-шуй
├── chakras/    # чакры
└── esoteric/   # эзотерика
```

## Как получить .txt

1. **PDF из Desktop** — `python3 scripts/import_pdfs.py`  
   Источник: `~/Desktop/учебники дополнительно/`

2. **Только эзотерика из корня** — `python3 scripts/import_pdfs.py --esoteric`

3. **Скан без текста** — `python3 scripts/ocr_one.py`  
   (нужны `tesseract` и `ocrmypdf`)

Подробности — в корневом `README.md`.
