"""Каталоги доступных материалов и моторов.

Материалы берутся из ``CLASSES/MATERIAL_LIBRARY.py`` (единый источник правды
для физики). Здесь — только список имён, пригодных для зубчатых колёс, плюс
краткие пояснения для вывода при активации скила.
"""

from . import engine

# Имена материалов, пригодных для колёс (как в CLASSES.MATERIAL_LIBRARY).
MATERIALS = [
    ('STEEL',      'Сталь конструкционная (σHlim=1500, σFlim=430 МПа). Эталон.'),
    ('ADI',        'Чугун ADI (изотермически закалённый). σHlim=700, σFlim=250.'),
    ('D16T',       'Алюминий Д16Т, фрезеровка. σH/σF=170/130 (константа, без S-N).'),
    ('POM',        'POM (полиацеталь), литьё. S-N по VDI 2736.'),
    ('POM_C',      'POM-C, фрезеровка. σHlim≈35, σFlim≈26 МПа.'),
    ('PA66',       'PA66 (полиамид-66), литьё. S-N по VDI 2736.'),
    ('PA6_CAST',   'Капролон (блочный ПА6), фрезеровка. S-N как PA66, E=2000 (кондиц.).'),
    ('PA6_CF',     'PA6-CF (FFF, ~20% рубленого углеволокна). σHlim≈35, σFlim≈18.'),
    ('PA_CF',      'PA12-CF (FFF). σHlim≈27, σFlim≈12 МПа.'),
    ('PA6_PRINT',  'PA6 печатный (FFF, без отжига). σHlim≈25, σFlim≈16 МПа.'),
    ('PA6_ANNEAL', 'PA6 печатный ПОСЛЕ ОТЖИГА. σHlim≈29, σFlim≈19 (+~8% SH).'),
    ('PETG',       'PETG (FFF). Слабый: σHlim≈22, σFlim≈12 МПа.'),
]

#: Моторы-пресеты для режима нагрузки "motor" (forward).
#: T_cont — длительный момент, Н·м; n_nom — номинальная скорость, об/мин.
MOTORS = {
    'M3v3': {
        'T_cont': 3.3, 'n_nom': 150.0, 'Kt': 0.22, 'I_cont': 15.0,
        'desc': 'BLDC сустава паука (колено/бедро): Kt=0.22 Нм/А, I_cont=15 А '
                '→ T_cont=3.3 Н·м при n_nom=150 об/мин.',
    },
}


def list_materials(t_amb=25.0, cycles=1e6):
    """Список материалов с ключевыми свойствами (для вывода/справки).

    σHlim/σFlim показаны при опорных (t_amb, cycles); реальный пайплайн VDI 2736
    для внешней пары берёт NL=1e8 внутри — здесь значения индикативные.
    """
    out = []
    for name, note in MATERIALS:
        try:
            out.append({
                'name': name,
                'E_MPa': engine.material_E(name),
                'nu': engine.material_v(name),
                'SigmaHlim_ref': round(engine.material_sigmaHlim(name, t_amb, cycles), 1),
                'SigmaFlim_ref': round(engine.material_sigmaFlim(name, t_amb, cycles), 1),
                'note': note,
            })
        except Exception as e:  # материал без какого-то поля — пропускаем мягко
            out.append({'name': name, 'note': note, 'error': str(e)})
    return out


def material_names():
    return [name for name, _ in MATERIALS]


def list_motors():
    return [dict(id=mid, **spec) for mid, spec in MOTORS.items()]


def get_motor(motor_id):
    if motor_id not in MOTORS:
        raise KeyError(
            f"Мотор {motor_id!r} не найден. Доступны: {sorted(MOTORS)}")
    return MOTORS[motor_id]
