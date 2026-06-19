# planetary-gearbox (skill)

Переносимый расчёт многоступенчатой планетарной коробки (VDI 2736) в формате
агентского скила — вендор-нейтрально (Claude, OpenAI, любой агент, способный
запустить команду). Контракт и примеры для агента — в [SKILL.md](SKILL.md).

## Структура

```
planetary-gearbox/
├── SKILL.md            манифест: материалы, моторы, формат ввода/вывода, примеры
├── cli.py              CLI: calc / search / best / materials / motors
├── examples/           готовые spec-файлы
├── designs/            кэш рассчитанных коробок (растущая библиотека, *.json по hash)
├── regen_cache.py      пересборка кэша под единый режим (смазка/ресурс)
├── verify_cache.py     сверка кэша: стабильность хэшей + воспроизводимость SF/SH
└── gearbox/
    ├── engine.py       ядро: пайплайн VDI 2736 + Lewis/Hertz, валидация геометрии, кинематика
    ├── catalog.py      каталоги материалов (из CLASSES.MATERIAL_LIBRARY) и моторов
    ├── spec.py         нормализация ввода, хэш для кэша, сборка отчёта со «слабым местом»
    └── library.py      индекс кэша designs/ + поиск/best по фильтрам
```

## Зависимости

Движок импортирует пакет `CLASSES` из корня GEARpie (numpy/scipy). Запускать
интерпретатором проекта:

```powershell
.venv\Scripts\python.exe skills\planetary-gearbox\cli.py calc --in skills\planetary-gearbox\examples\two_stage_pa6cf.json --pretty
```

## Связь с spider_knee.py / spider_thigh.py

Ядро — обобщение N-ступенчатого движка `spider_thigh.py`: операционная точка
(Ka, T_amb, КПД, требования, смазка, расчётный ресурс) вынесена в `engine.Config`,
добавлен режим нагрузки «от выходного момента». Физика VDI 2736 с тех пор уточнена
(применение KA, единое число циклов NL для обеих пар, смазка в нагреве — см.
CHANGELOG). Исторические наборы «колено»/«бедро» однократно пересчитаны актуальной
физикой в общий кэш `designs/`; отдельные legacy-источники больше не читаются.

## Расширение

- **Новый мотор:** добавь запись в `catalog.MOTORS`.
- **Новый материал:** добавь метод в `CLASSES/MATERIAL_LIBRARY.py` и строку в
  `catalog.MATERIALS`.
- **Программный вызов:** `import gearbox; gearbox.calculate(spec_dict)`.

## Python API

```python
import sys; sys.path.insert(0, 'skills/planetary-gearbox')
import gearbox
report = gearbox.calculate(spec_dict)            # расчёт (с кэшем)
hits   = gearbox.library.search(i=20, passing_only=True, d_max=180)
mats   = gearbox.catalog.list_materials()
```
