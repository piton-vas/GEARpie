#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SPIDER ROBOT KNEE — Двухступенчатая планетарная коробка с фрезерованным POM-C солнцем и PA6 саттелитами
Требования:
- Компактная, Ø <= 200 мм, b <= 40 мм
- Входящий момент: 3.7 Нм при 150 RPM
- Выходящий момент: >= 60 Нм
- Передаточное число: > 32
- Коэффициент запаса прочности: 1.3
- Материалы: POM_C (солнца), PA6_PRINT (саттелиты)
"""

import sys
sys.dont_write_bytecode = True

from CLASSES import MATERIAL_LIBRARY, VDI2736, CALC_GEOMETRY, FORCES_SPEEDS
from CLASSES import CONTACT
import json
from pathlib import Path

# Входные данные
T_input = 3.7          # Нм на входе
n_input = 150          # об/мин на входе
T_required = 60        # Нм требуемый на выходе
D_max = 200            # мм, максимальный диаметр
b_max = 40             # мм, максимальная ширина на одну ступень
KA = 1.3               # коэффициент запаса
T_amb = 25.0           # °C

MIN_RELIEF = 1.3       # минимальный запас по прочности

# Параметры для перебора
modules = [0.8, 1.0, 1.25, 1.5, 1.75, 2.0]
gear_configs = []

# Двухступенчатые конфигурации (асимметричные): i = i1 * i2
# Требуется i > 32
configs_2stage = [
    # (i1, i2, n_sat1, n_sat2, description)
    (6, 6, 3, 4, "6x6 асимметричная"),     # i=36
    (6, 6, 3, 3, "6x6 симметричная"),      # i=36
    (4, 9, 3, 4, "4x9 асимметричная"),     # i=36
    (8, 4, 3, 4, "8x4 асимметричная"),     # i=32
    (5, 7, 3, 4, "5x7 асимметричная"),     # i=35
    (6, 5, 3, 4, "6x5 асимметричная"),     # i=30 (не подходит, но проверим)
]

report_dir = Path('REPORT/SPIDER_KNEE/_data')
report_dir.mkdir(parents=True, exist_ok=True)

def calculate_geometry(m, Z_sun, Z_ring, b):
    """Базовая геометрия зубчатого зацепления"""
    return {
        'm': m,
        'Z_sun': Z_sun,
        'Z_ring': Z_ring,
        'Z_planet': (Z_sun + Z_ring) // 2,  # стандартная формула для саттелита
        'b': b,
        'd_sun': m * Z_sun,
        'd_ring': m * Z_ring,
        'd_planet': m * (Z_sun + Z_ring) // 2,
    }

def check_assembly_condition(Z_sun, Z_ring, n_sat):
    """Проверка условия сборки: (Z_sun + Z_ring) должно делиться на n_sat"""
    return (Z_sun + Z_ring) % n_sat == 0

def calculate_planetary_stage(m, Z_sun, Z_ring, n_sat, T_in, n_in, mat_sun, mat_planet, b, stage_name):
    """Расчёт одной ступени планетарки"""

    # Геометрия
    Z_planet = (Z_sun + Z_ring) // 2
    d_sun = m * Z_sun
    d_ring = m * Z_ring
    d_planet = m * Z_planet

    # Условия сборки
    if not check_assembly_condition(Z_sun, Z_ring, n_sat):
        return None, f"Ошибка сборки: ({Z_sun}+{Z_ring})/{n_sat} = {(Z_sun+Z_ring)/n_sat:.2f}"

    # Передаточное число ступени
    i_stage = 1 + Z_ring / Z_sun

    # Выходные параметры
    T_out = T_in * i_stage
    n_out = n_in / i_stage

    # Силы в зацеплении SUN-PLANET
    # Окружная сила на делительном диаметре солнца
    F_t = (2 * T_in * 1e3) / d_sun  # Н (момент в Нмм)

    # Напряжение в контакте (упрощённо, Hertzian)
    # σH ≈ sqrt(F_t * E_reduced / (d_equiv * b))
    R_sun = d_sun / 2
    R_planet = d_planet / 2
    R_eq = (R_sun * R_planet) / (R_sun + R_planet)

    # Модуль упругости приведённый
    E1 = MATERIAL_LIBRARY.LIBRARY_MAT(mat_sun).E
    E2 = MATERIAL_LIBRARY.LIBRARY_MAT(mat_planet).E
    v1 = MATERIAL_LIBRARY.LIBRARY_MAT(mat_sun).v
    v2 = MATERIAL_LIBRARY.LIBRARY_MAT(mat_planet).v

    E_red = 1 / ((1 - v1**2) / E1 + (1 - v2**2) / E2)

    # Контактное напряжение (Hertz)
    sigma_H = ((F_t / (b * R_eq)) * (E_red / 2)) ** 0.5 / 1000  # МПа

    # Допускаемые напряжения
    mat_sun_lib = MATERIAL_LIBRARY.LIBRARY_MAT(mat_sun)
    mat_planet_lib = MATERIAL_LIBRARY.LIBRARY_MAT(mat_planet)

    sigma_H_lim_sun = mat_sun_lib.SigmaHlim(T_amb, 1e9) if callable(mat_sun_lib.SigmaHlim) else mat_sun_lib.SigmaHlim
    sigma_H_lim_planet = mat_planet_lib.SigmaHlim(T_amb, 1e9) if callable(mat_planet_lib.SigmaHlim) else mat_planet_lib.SigmaHlim

    sigma_F_lim_sun = mat_sun_lib.SigmaFlim(T_amb, 1e9) if callable(mat_sun_lib.SigmaFlim) else mat_sun_lib.SigmaFlim
    sigma_F_lim_planet = mat_planet_lib.SigmaFlim(T_amb, 1e9) if callable(mat_planet_lib.SigmaFlim) else mat_planet_lib.SigmaFlim

    # Напряжение в корне зуба (упрощённо)
    sigma_F = F_t / (b * m) * 1.5  # МПа (фактор 1.5 — геометрический)

    # Запас по контакту
    SH = sigma_H_lim_planet / sigma_H if sigma_H > 0 else float('inf')
    SF = sigma_F_lim_planet / sigma_F if sigma_F > 0 else float('inf')

    # Зазор между саттелитами
    angle_between = 360 / n_sat
    arc_length = (d_sun / 2 + d_planet) * (angle_between * 3.14159 / 180)
    sat_thickness = m * 3  # примерно
    clearance = arc_length - sat_thickness

    result = {
        'stage': stage_name,
        'm': m,
        'Z_sun': Z_sun,
        'Z_ring': Z_ring,
        'Z_planet': Z_planet,
        'n_sat': n_sat,
        'b': b,
        'd_sun': d_sun,
        'd_ring': d_ring,
        'd_planet': d_planet,
        'i_stage': i_stage,
        'T_in': T_in,
        'T_out': T_out,
        'n_in': n_in,
        'n_out': n_out,
        'F_t': F_t,
        'sigma_H': sigma_H,
        'sigma_F': sigma_F,
        'sigma_H_lim': sigma_H_lim_planet,
        'sigma_F_lim': sigma_F_lim_planet,
        'SH': SH,
        'SF': SF,
        'clearance_mm': clearance,
        'materials': (mat_sun, mat_planet),
    }

    return result, None

def design_two_stage_planetary(m1, Z_sun1, Z_ring1, b1, n_sat1,
                               m2, Z_sun2, Z_ring2, b2, n_sat2,
                               mat_sun, mat_planet):
    """Расчёт полной двухступенчатой системы"""

    # Первая ступень (вход = солнце на входе, выход = водило → вход второй ступени)
    stage1, err1 = calculate_planetary_stage(
        m1, Z_sun1, Z_ring1, n_sat1,
        T_input, n_input, mat_sun, mat_planet, b1, "Stage 1"
    )
    if err1:
        return None, f"Stage 1: {err1}"

    # Вторая ступень (вход = водило со счёта первой, солнце второй)
    # На выходе кольцо (закреплено на выходном валу)
    stage2, err2 = calculate_planetary_stage(
        m2, Z_sun2, Z_ring2, n_sat2,
        stage1['T_out'], stage1['n_out'], mat_sun, mat_planet, b2, "Stage 2"
    )
    if err2:
        return None, f"Stage 2: {err2}"

    # Общие параметры
    i_total = stage1['i_stage'] * stage2['i_stage']
    T_output = stage2['T_out']
    n_output = stage2['n_out']

    # Диаметры (внешний размер второй ступени)
    D_outer_stage1 = stage1['d_ring'] + m1 * 2  # +2 на зазор
    D_outer_stage2 = stage2['d_ring'] + m2 * 2

    # Допуск по моменту и диаметру
    T_ok = T_output >= T_required
    D_ok = D_outer_stage2 <= D_max
    b_ok = (b1 <= b_max) and (b2 <= b_max)

    # Минимальный запас по прочности
    min_SH = min(stage1['SH'], stage2['SH'])
    min_SF = min(stage1['SF'], stage2['SF'])

    relief_ok = (min_SH >= MIN_RELIEF) and (min_SF >= MIN_RELIEF)

    result = {
        'i1': stage1['i_stage'],
        'i2': stage2['i_stage'],
        'i_total': i_total,
        'T_input': T_input,
        'T_output': T_output,
        'n_input': n_input,
        'n_output': n_output,
        'D_outer_stage1': D_outer_stage1,
        'D_outer_stage2': D_outer_stage2,
        'b_total': b1 + b2,
        'stage1': stage1,
        'stage2': stage2,
        'T_ok': T_ok,
        'D_ok': D_ok,
        'b_ok': b_ok,
        'relief_ok': relief_ok,
        'min_SH': min_SH,
        'min_SF': min_SF,
        'all_ok': T_ok and D_ok and b_ok and relief_ok,
    }

    return result, None

def format_report(design):
    """Форматирование отчёта"""
    s1 = design['stage1']
    s2 = design['stage2']

    lines = [
        f"{'='*90}",
        f"  СВОДКА: i{design['i_total']:.0f}_{design['i1']:.0f}x{design['i2']:.0f}_m{s1['m']:.2f}-Z{s1['Z_sun']:.0f}-{s1['Z_planet']:.0f}-{s1['Z_ring']:.0f}_m{s2['m']:.2f}-Z{s2['Z_sun']:.0f}-{s2['Z_planet']:.0f}-{s2['Z_ring']:.0f}",
        f"  Материалы: солнца={s1['materials'][0]}, саттелиты={s1['materials'][1]}",
        f"{'='*90}",
        "",
        f"ИСХОДНЫЕ ДАННЫЕ",
        f"{'-'*90}",
        f"  Входящий момент:     T_in = {design['T_input']:.2f} Н·м при n = {design['n_input']:.0f} об/мин",
        f"  Требуется:           T_out >= {T_required:.0f} Н·м, D <= {D_max:.0f} мм, b <= {b_max:.0f} мм/ступень",
        f"  Коэффициент KA:      {KA}",
        f"  Температура:         {T_amb:.1f} °C",
        "",
        f"ИТОГОВЫЕ ХАРАКТЕРИСТИКИ",
        f"{'-'*90}",
        f"  Передаточное число:   i = {design['i1']:.0f} × {design['i2']:.0f} = {design['i_total']:.0f}",
        f"  Момент на выходе:     T_out = {design['T_output']:.2f} Н·м  {'✓' if design['T_ok'] else '✗ НЕ ДОТЯГИВАЕТ'}",
        f"  Скорость на выходе:   n_out = {design['n_output']:.2f} об/мин = {design['n_output']*360/60:.1f} °/с",
        f"  Габарит макс. (D):    {design['D_outer_stage2']:.1f} мм  {'✓' if design['D_ok'] else '✗ ВЕЛИК'}",
        f"  Длина осевая (b):     {design['b_total']:.0f} мм (b1+b2)  {'✓' if design['b_ok'] else '✗ ВЕЛИКА'}",
        f"  Минимальный SH:       {design['min_SH']:.2f}  {'✓' if design['relief_ok'] else '✗ МАЛО'}",
        f"  Статус:               {'ГОДЕН' if design['all_ok'] else 'НЕ ГОДЕН'}",
        "",
        f"СТУПЕНЬ 1 (i₁ = {design['i1']:.0f}, {s1['n_sat']} саттелитов)",
        f"{'-'*90}",
        f"  Модуль m1 = {s1['m']:.2f} мм   Ширина b1 = {s1['b']:.0f} мм",
        f"  Z_sun = {s1['Z_sun']:3.0f}   Z_planet = {s1['Z_planet']:3.0f}   Z_ring = {s1['Z_ring']:3.0f}",
        f"  d_sun = {s1['d_sun']:7.2f} мм   d_planet = {s1['d_planet']:7.2f} мм   d_ring = {s1['d_ring']:7.2f} мм",
        f"  Нагрузка F_t = {s1['F_t']:.1f} Н",
        f"  Контактное напряжение:  σH = {s1['sigma_H']:.2f} МПа (σH_lim = {s1['sigma_H_lim']:.1f}) → SH = {s1['SH']:.2f}",
        f"  Напряжение в корне:     σF = {s1['sigma_F']:.2f} МПа (σF_lim = {s1['sigma_F_lim']:.1f}) → SF = {s1['SF']:.2f}",
        f"  Зазор между саттелитами: {s1['clearance_mm']:.2f} мм",
        "",
        f"СТУПЕНЬ 2 (i₂ = {design['i2']:.0f}, {s2['n_sat']} саттелитов)",
        f"{'-'*90}",
        f"  Модуль m2 = {s2['m']:.2f} мм   Ширина b2 = {s2['b']:.0f} мм",
        f"  Z_sun = {s2['Z_sun']:3.0f}   Z_planet = {s2['Z_planet']:3.0f}   Z_ring = {s2['Z_ring']:3.0f}",
        f"  d_sun = {s2['d_sun']:7.2f} мм   d_planet = {s2['d_planet']:7.2f} мм   d_ring = {s2['d_ring']:7.2f} мм",
        f"  Нагрузка F_t = {s2['F_t']:.1f} Н",
        f"  Контактное напряжение:  σH = {s2['sigma_H']:.2f} МПа (σH_lim = {s2['sigma_H_lim']:.1f}) → SH = {s2['SH']:.2f}",
        f"  Напряжение в корне:     σF = {s2['sigma_F']:.2f} МПа (σF_lim = {s2['sigma_F_lim']:.1f}) → SF = {s2['SF']:.2f}",
        f"  Зазор между саттелитами: {s2['clearance_mm']:.2f} мм",
        "",
        f"{'='*90}",
    ]

    return '\n'.join(lines)

def main():
    print("="*90)
    print("  SPIDER ROBOT KNEE - Raschet dvukhstupenchatoy planetarnoy korobki peredach")
    print("  Materialy: POM_C (solntse), PA6_PRINT (sattality)")
    print("="*90)
    print()

    valid_designs = []

    # Генерирование конфигураций
    for m1 in modules:
        for m2 in modules:
            for i1, i2, n_sat1, n_sat2, desc in configs_2stage:
                # Выбор количества зубьев на основе передаточного числа
                # i = 1 + Z_ring / Z_sun, поэтому Z_ring = (i-1) * Z_sun

                for Z_sun1 in [12, 15, 18, 20, 24]:
                    Z_ring1 = Z_sun1 * (i1 - 1)

                    # Проверка условия сборки
                    if not check_assembly_condition(Z_sun1, Z_ring1, n_sat1):
                        continue

                    Z_planet1 = (Z_sun1 + Z_ring1) // 2

                    for b1 in [20, 25, 30, 35, 40]:
                        if b1 > b_max:
                            continue

                        for Z_sun2 in [12, 15, 18, 20, 24]:
                            Z_ring2 = Z_sun2 * (i2 - 1)

                            if not check_assembly_condition(Z_sun2, Z_ring2, n_sat2):
                                continue

                            Z_planet2 = (Z_sun2 + Z_ring2) // 2

                            for b2 in [20, 25, 30, 35, 40]:
                                if b2 > b_max:
                                    continue

                                # Расчёт конфигурации
                                design, err = design_two_stage_planetary(
                                    m1, Z_sun1, Z_ring1, b1, n_sat1,
                                    m2, Z_sun2, Z_ring2, b2, n_sat2,
                                    'POM_C', 'PA6_PRINT'
                                )

                                if err:
                                    continue

                                valid_designs.append(design)

    # Фильтрация и сортировка
    good_designs = [d for d in valid_designs if d['all_ok']]

    if not good_designs:
        print("[ОШИБКА] НЕ НАЙДЕНЫ КОНФИГУРАЦИИ, УДОВЛЕТВОРЯЮЩИЕ ВСЕМ УСЛОВИЯМ")
        print(f"   Проверьте требования:")
        print(f"   - Момент на выходе >= {T_required} Нм")
        print(f"   - Диаметр <= {D_max} мм")
        print(f"   - Передаточное число > 32")
        print(f"   - Запас прочности SH/SF >= {MIN_RELIEF}")
        return

    # Сортировка по диаметру (компактность)
    good_designs.sort(key=lambda d: (d['D_outer_stage2'], d['b_total']))

    print(f"[OK] НАЙДЕНО КОНФИГУРАЦИЙ: {len(good_designs)}")
    print()
    print("ТОП-5 КОМПАКТНЫХ РЕШЕНИЙ:")
    print("-" * 90)

    for idx, design in enumerate(good_designs[:5], 1):
        s1 = design['stage1']
        s2 = design['stage2']
        fname = f"i{design['i_total']:.0f}_{s1['m']:.2f}x{s2['m']:.2f}_Z{s1['Z_sun']:.0f}-{s2['Z_sun']:.0f}_b{s1['b']:.0f}x{s2['b']:.0f}"

        print(f"\n{idx}. {fname}")
        print(f"   Габарит: Ø{design['D_outer_stage2']:.0f}x{design['b_total']:.0f} мм")
        print(f"   Момент выхода: {design['T_output']:.1f} Нм (требуется {T_required} Нм)")
        print(f"   Передача: {design['i_total']:.0f} = {design['i1']:.0f}x{design['i2']:.0f}")
        print(f"   Запас SH/SF: {design['min_SH']:.2f} / {design['min_SF']:.2f}")

        # Сохранение отчёта в файл
        report = format_report(design)
        report_file = report_dir / f"{fname}.txt"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"   Отчёт: {report_file}")

    # Сохранение JSON с данными для дальнейшего анализа
    json_data = {
        'requirements': {
            'T_input': T_input,
            'n_input': n_input,
            'T_required': T_required,
            'D_max': D_max,
            'b_max': b_max,
            'i_min': 32,
        },
        'best_designs': [{
            'i_total': d['i_total'],
            'i1': d['i1'],
            'i2': d['i2'],
            'T_output': d['T_output'],
            'n_output': d['n_output'],
            'D_outer': d['D_outer_stage2'],
            'b_total': d['b_total'],
            'stage1': {
                'm': d['stage1']['m'],
                'Z_sun': int(d['stage1']['Z_sun']),
                'Z_planet': int(d['stage1']['Z_planet']),
                'Z_ring': int(d['stage1']['Z_ring']),
                'n_sat': d['stage1']['n_sat'],
                'b': d['stage1']['b'],
            },
            'stage2': {
                'm': d['stage2']['m'],
                'Z_sun': int(d['stage2']['Z_sun']),
                'Z_planet': int(d['stage2']['Z_planet']),
                'Z_ring': int(d['stage2']['Z_ring']),
                'n_sat': d['stage2']['n_sat'],
                'b': d['stage2']['b'],
            },
            'min_SH': d['min_SH'],
            'min_SF': d['min_SF'],
        } for d in good_designs[:10]]
    }

    json_file = report_dir / 'designs_summary.json'
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, indent=2, ensure_ascii=False)

    print(f"\n[OK] JSON-отчёт сохранён: {json_file}")

if __name__ == '__main__':
    main()
