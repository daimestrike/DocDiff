# CLI и API

## Командная строка

Портативная установка:

```bash
/opt/docdiff/docdiff-cli old.docx new.docx
```

Из исходников: `.venv/bin/python -m app.cli old.docx new.docx`.

| Параметр | Описание |
|---|---|
| `--html FILE` | Сохранить HTML-отчёт (как кнопка «Отчёт HTML») |
| `--json FILE` | Сохранить результат в JSON |
| `-i`, `--ignore-case` | Не учитывать регистр |
| `-w`, `--ignore-whitespace` | Не учитывать пробелы |
| `-q`, `--quiet` | Не печатать различия в терминал |

**Код выхода:** `0` — документы совпадают, `1` — есть различия, `2` — ошибка (файл не найден, формат не поддерживается).

Пример вывода:

```
contract_v1.docx  →  contract_v2.docx
Сходство: 69.2%   +1  -0  ~3
-     6 Общая стоимость товара составляет 1 250 000 рублей, включая НДС 20%.
+     6 Общая стоимость товара составляет 1 310 000 рублей, включая НДС 20%.
+     8 Покупатель вправе удержать неустойку из суммы оплаты.
```

Для Excel — по ячейкам:

```
== Лист: Прайс → Прайс [changed]
  C3: '79' → '84'
+ строка 5: 1006 | Йогурт питьевой | 65 | 150
- строка 6: 1005 | Масло сливочное 82% | 229 | 60
```

### Примеры в скриптах

Проверить, что шаблон договора не менялся:

```bash
if ! docdiff-cli template.docx incoming.docx -q -w; then
  echo "Договор отличается от шаблона"
fi
```

Сравнить все пары файлов из двух папок и сложить отчёты:

```bash
for f in old/*.xlsx; do
  n=$(basename "$f")
  docdiff-cli "old/$n" "new/$n" -q --html "reports/${n%.xlsx}.html"
done
```

## HTTP API

Интерактивная документация (Swagger): `http://<сервер>:8080/api/docs`.

| Метод | Путь | Описание |
|---|---|---|
| `GET` | `/` | Веб-интерфейс |
| `GET` | `/health` | Проверка живости: `{"status":"ok","version":"1.0.0"}` |
| `GET` | `/api/info` | Версия, список форматов, наличие LibreOffice, лимит размера |
| `POST` | `/api/compare` | Сравнение двух файлов |

### POST /api/compare

`multipart/form-data`:

| Поле | Тип | Описание |
|---|---|---|
| `file_a` | файл | «Было» |
| `file_b` | файл | «Стало» |
| `ignore_case` | bool | Не учитывать регистр (`false`) |
| `ignore_whitespace` | bool | Не учитывать пробелы (`false`) |

```bash
curl -F file_a=@old.docx -F file_b=@new.docx -F ignore_case=true \
     http://server:8080/api/compare
```

Python:

```python
import requests
with open("old.xlsx", "rb") as a, open("new.xlsx", "rb") as b:
    r = requests.post("http://server:8080/api/compare",
                      files={"file_a": a, "file_b": b}).json()
print(r["stats"])
```

Ошибки: `413` — файл больше лимита, `415` — формат не поддерживается или файл повреждён. Текст ошибки — в поле `detail`.

### Формат ответа: текст

```json
{
  "mode": "text",
  "left":  {"name": "old.docx", "size": 37245},
  "right": {"name": "new.docx", "size": 37288},
  "stats": {"equal": 9, "insert": 1, "delete": 0, "replace": 3, "similarity": 0.6923},
  "rows": [
    {"op": "equal",   "l": 1, "r": 1, "a": [["=", "Договор поставки"]], "b": [["=", "Договор поставки"]]},
    {"op": "replace", "l": 6, "r": 6,
     "a": [["=", "стоимость "], ["-", "1 250 000"], ["=", " рублей"]],
     "b": [["=", "стоимость "], ["+", "1 310 000"], ["=", " рублей"]]},
    {"op": "insert",  "l": null, "r": 8, "a": null, "b": [["+", "Новый пункт"]]}
  ]
}
```

- `op`: `equal` / `insert` / `delete` / `replace`
- `l`, `r` — номера строк в старом и новом документе
- `a`, `b` — сегменты `[операция, текст]`: `=` без изменений, `-` удалено, `+` добавлено
- `similarity` — доля совпадающих строк (0…1)

### Формат ответа: таблицы

```json
{
  "mode": "table",
  "stats": {"equal": 5, "insert": 2, "delete": 1, "replace": 1, "cells_changed": 1,
            "similarity": 0.66, "sheets_added": 1, "sheets_removed": 0},
  "sheets": [
    {"name_a": "Прайс", "name_b": "Прайс", "status": "changed",
     "cols": ["A", "B", "C", "D"],
     "stats": {...},
     "rows": [
       {"op": "replace", "l": 3, "r": 3,
        "cells": [["=", "1002", null], ["=", "Кефир", null], ["~", "79", "84"], ["=", "80", null]]}
     ]}
  ]
}
```

- `status` листа: `same` / `changed` / `added` / `removed`
- `cells`: `[статус, было, стало]`; статус `=` без изменений, `~` изменено, `+`/`-` у добавленных/удалённых строк

---

← [Настройка](06-configuration.md) · [Оглавление](README.md) · [Обновление и релизы](08-updates-and-releases.md) →
