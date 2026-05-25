# Changelog

## [Unreleased]
- `MATERIAL_LIBRARY`: добавлен материал `PA6_CF` — PA6 с углеволокном для FFF-печати (E=6500 МПа, ρ=1180 кг/м³, SigmaHlim=35, SigmaFlim=18 МПа); параметры по TDS Polymaker/Bambu/eSUN.
- Локализованы prompt'ы ввода параметров новой геометрии передачи (`GEAR_LIBRARY.NEW`) — ранее оставались на английском при выборе ru.
- `LUBRICANT_LIBRARY.LUBRICANT`: добавлена валидация базового масла и класса ISO VG — вместо невнятного `AttributeError: 'LUBRICANT' object has no attribute 'm'` теперь выбрасывается `ValueError` с перечнем допустимых значений (например, при попытке ввести VG 70).
- `MATERIAL_LIBRARY`: материалы `D16T` и `PA_CF` теперь отдают `SigmaHlim`/`SigmaFlim` как callable `(temp, cycles)` (константы) — совместимо с `VDI2736.LCC`, без этого расчёт несущей способности падал с `TypeError: 'int' object is not callable`.
- Совместимость с NumPy 2.x: `np.trapz` → `np.trapezoid` в `CLASSES/LOAD_SHARING.py` и `CLASSES/CONTACT.py` (раньше расчёт жёсткости и потерь падал с `AttributeError`).
- Добавлен `.gitignore` (Python-стандарт + `.venv/`, `.claude/`, IDE-папки, `REPORT/SPIDER*.txt`).
