"""
Генерация и подбор асимметричных двухступенчатых планетарных коробок
с солнцем из D16T (фрезерованный алюминий).

Параметры подбора:
  - U_total > 32 (большое передаточное число)
  - D_max <= 200 мм
  - b_max <= 40 мм
  - Материалы: D16T (солнца), PA6 (планеты + венцы)
  - KA = 1.3 (неспешный робот)
  - Асимметричное распределение: (U1 < U2)

Обычная схема планетарки:
  U_stage = (Z_ring + Z_sun) / Z_sun  (для одного саттелита)

Для N саттелитов условие сборки: (Z_sun + Z_ring) % N == 0

Условие соседства саттелитов:
  clearance = 2*r_carrier*sin(π/N) - 2*r_planet_tip > 1 мм

где r_carrier = m*(Z_sun + Z_planet)/2, r_planet_tip = m*Z_planet/2 + m
"""

import os
import sys
import math
import json
from itertools import product

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from CLASSES import MATERIAL_LIBRARY, CALC_GEOMETRY, LOAD_SHARING, FORCES_SPEEDS, \
    CONTACT, INVOLUTE_GEOMETRY, VDI2736, I18N

I18N.set_lang('ru')

# ============================================================================
#  Параметры эксплуатации
# ============================================================================
T_MOTOR = 3.7
N_MOTOR = 150.0
T_OUT_REQ = 60.0
D_MAX = 200.0
B_MAX = 40.0
U_MIN = 32.0
KA = 1.3
T_AMB = 25.0
ETA_STAGE = 0.9

REPORT_DIR = os.path.join('REPORT', 'SPIDER_KNEE')
DATA_DIR = os.path.join(REPORT_DIR, '_data')

# ============================================================================
#  Вспомогательные функции (скопированы из spider_knee.py)
# ============================================================================
def material_sigmaFlim(name, t_amb=T_AMB, cycles=1e6):
    lib = MATERIAL_LIBRARY.LIBRARY_MAT(name)
    fn = lib.SigmaFlim
    if callable(fn):
        try:
            return fn(t_amb, cycles)
        except TypeError:
            return fn(cycles)
    return float(fn)

def material_sigmaHlim(name, t_amb=T_AMB, cycles=1e6):
    lib = MATERIAL_LIBRARY.LIBRARY_MAT(name)
    fn = lib.SigmaHlim
    if callable(fn):
        try:
            return fn(t_amb, cycles)
        except TypeError:
            return fn(cycles)
    return float(fn)

def material_E(name):
    return MATERIAL_LIBRARY.LIBRARY_MAT(name).E

def material_v(name):
    return MATERIAL_LIBRARY.LIBRARY_MAT(name).v

def _yfa(z, x=0.0):
    base = {
        10: 3.50, 12: 3.20, 14: 3.00, 16: 2.85, 18: 2.75, 20: 2.65,
        22: 2.58, 24: 2.52, 26: 2.46, 28: 2.42, 30: 2.39, 34: 2.32,
        40: 2.25, 50: 2.16, 60: 2.12, 80: 2.05, 100: 2.02, 150: 1.97,
    }
    keys = sorted(base.keys())
    if z <= keys[0]:
        y = base[keys[0]]
    elif z >= keys[-1]:
        y = base[keys[-1]]
    else:
        for i in range(len(keys) - 1):
            if keys[i] <= z <= keys[i + 1]:
                t = (z - keys[i]) / (keys[i + 1] - keys[i])
                y = base[keys[i]] * (1 - t) + base[keys[i + 1]] * t
                break
    y -= 0.4 * x
    return max(y, 1.5)

def planet_ring_check(m, z_planet, z_ring, b, force_t_n,
                      mat_planet, mat_ring, x_planet=0.0, x_ring=0.0,
                      cycles=1e6, ys=2.0, alpha_deg=20.0, ka=KA):
    """Lewis (изгиб) + Hertz (контакт, выпукло-вогнутый) для внутренней пары."""
    y_planet = _yfa(z_planet, x_planet)
    y_ring = _yfa(z_ring, x_ring) * 0.85
    y_eps = 0.75
    f_eff = force_t_n * ka
    sigma_p = f_eff / (b * m) * y_planet * ys * y_eps
    sigma_r = f_eff / (b * m) * y_ring * ys * y_eps

    alpha = math.radians(alpha_deg)
    r_planet_curv = (m * z_planet / 2.0) * math.sin(alpha)
    r_ring_curv = (m * z_ring / 2.0) * math.sin(alpha)
    inv_req = 1.0 / r_planet_curv - 1.0 / r_ring_curv
    r_eq_pr = 1.0 / inv_req

    E_p, E_r = material_E(mat_planet), material_E(mat_ring)
    v_p, v_r = material_v(mat_planet), material_v(mat_ring)
    e_eff = 1.0 / ((1 - v_p**2) / E_p + (1 - v_r**2) / E_r)

    f_n_per_b = (f_eff / math.cos(alpha)) / b
    sigma_h_pr = math.sqrt(f_n_per_b * e_eff / (math.pi * r_eq_pr))

    sh_p = material_sigmaHlim(mat_planet, cycles=cycles) / sigma_h_pr
    sh_r = material_sigmaHlim(mat_ring, cycles=cycles) / sigma_h_pr

    return {
        'sigma_p': sigma_p, 'sigma_r': sigma_r,
        'sigma_lim_p': material_sigmaFlim(mat_planet, cycles=cycles),
        'sigma_lim_r': material_sigmaFlim(mat_ring, cycles=cycles),
        'sf_p': material_sigmaFlim(mat_planet, cycles=cycles) * ys / sigma_p,
        'sf_r': material_sigmaFlim(mat_ring, cycles=cycles) * ys / sigma_r,
        'sigma_h': sigma_h_pr,
        'sigma_h_lim_p': material_sigmaHlim(mat_planet, cycles=cycles),
        'sigma_h_lim_r': material_sigmaHlim(mat_ring, cycles=cycles),
        'sh_p': sh_p, 'sh_r': sh_r,
    }

def _gtype(name, m, z_pinion, z_wheel, b, x_pinion=0.0, x_wheel=0.0):
    from types import SimpleNamespace
    return SimpleNamespace(
        GEAR_NAME=name,
        alpha=20.0, beta=0.0,
        m=m,
        z=[z_pinion, z_wheel],
        x=[x_pinion, x_wheel],
        addendum_reduction='N',
        b=[b, b],
        dshaft=[8.0, 8.0],
        al=None,
        haP=1.0, hfP=1.25, rfP=0.38,
        Ra=[0.6, 0.6], Rq=[0.7, 0.7], Rz=[4.8, 4.8],
    )

def _run_pair_at(size, name, m, z_pinion, z_wheel, b,
                 torque_pinion_nm, speed_pinion_rpm,
                 mat_pinion, mat_wheel, x_pinion, x_wheel):
    gtype = _gtype(name, m, z_pinion, z_wheel, b, x_pinion, x_wheel)
    gmat = MATERIAL_LIBRARY.MATERIAL(mat_pinion, mat_wheel)
    geo = CALC_GEOMETRY.MAAG(gtype)
    pprof = INVOLUTE_GEOMETRY.LITVIN('P', geo, size)
    wprof = INVOLUTE_GEOMETRY.LITVIN('W', geo, size)
    gpath = LOAD_SHARING.LINES(size, geo, gmat, pprof, wprof)
    gfs = FORCES_SPEEDS.OPERATION('P', torque_pinion_nm, speed_pinion_rpm, geo, gpath, 'N')
    gcontact = CONTACT.HERTZ(gmat, None, geo, gpath, gfs, 'AC')
    glcc = VDI2736.LCC(gmat, geo, gfs, gpath, gcontact, T_AMB, KA)
    return gtype, geo, gfs, gcontact, glcc

def run_external_pair(name, m, z_pinion, z_wheel, b,
                      torque_pinion_nm, speed_pinion_rpm,
                      mat_pinion, mat_wheel,
                      x_pinion=0.0, x_wheel=0.0, size=1000):
    last_err = None
    for s in (size, 500, 300):
        try:
            gtype, geo, gfs, gcontact, glcc = _run_pair_at(
                s, name, m, z_pinion, z_wheel, b,
                torque_pinion_nm, speed_pinion_rpm,
                mat_pinion, mat_wheel, x_pinion, x_wheel)
            break
        except (MemoryError, ValueError) as e:
            last_err = e
            continue
    else:
        raise last_err

    return {
        'SF': (float(glcc.SF1), float(glcc.SF2)),
        'SH': (float(glcc.SH1), float(glcc.SH2)),
        'SigmaF': (float(glcc.SigmaF1), float(glcc.SigmaF2)),
        'SigmaH': float(glcc.SigmaH),
        'mats': (mat_pinion, mat_wheel),
    }

def planet_relative_speed(omega_sun_abs, i_stage):
    omega_carrier = omega_sun_abs / i_stage
    return omega_sun_abs - omega_carrier, omega_carrier

def sh_pessimistic(sh_code, mat_pinion, mat_wheel, cycles=1e6):
    """SH с учётом более слабого материала."""
    s_lim_p = material_sigmaHlim(mat_pinion, cycles=cycles)
    s_lim_w = material_sigmaHlim(mat_wheel, cycles=cycles)
    return sh_code * min(s_lim_p, s_lim_w) / s_lim_p

# ============================================================================
#  Генерация комбинаций параметров
# ============================================================================
def generate_candidates():
    """Генерирует кандидаты для заданных передаточных чисел и ступеней."""
    candidates = []

    # Целевые асимметричные передаточные числа U1 x U2
    target_pairs = [
        (4.0, 8.0),   # U ≈ 32
        (4.0, 8.5),   # U ≈ 34
        (5.0, 7.0),   # U ≈ 35
        (4.0, 9.0),   # U ≈ 36
        (5.0, 7.5),   # U ≈ 37.5
        (4.0, 9.5),   # U ≈ 38
        (6.0, 6.0),   # U ≈ 36 (симметрично)
    ]

    modules = [1.0, 1.25, 1.5, 2.0]
    widths_1 = [18, 20, 25]
    widths_2 = [25, 30, 35]

    for u1, u2 in target_pairs:
        for m1 in modules:
            for b1 in widths_1:
                for m2 in modules:
                    for b2 in widths_2:
                        if b2 > B_MAX:
                            continue

                        # Ступень 1: подбираем Z для достижения U1 с 3 саттелитами
                        for z_s1 in range(14, 26):
                            # Для планетарной ступени: i = (z_r + z_s) / z_s
                            # Хотим: (z_r + z_s) / z_s = u1
                            # Значит: z_r = z_s * (u1 - 1)
                            z_r1_ideal = z_s1 * (u1 - 1)
                            z_r1 = round(z_r1_ideal)

                            # z_p = (z_r - z_s) / 2
                            z_p1 = (z_r1 - z_s1) // 2

                            # Проверка условия сборки для 3 саттелитов
                            if (z_s1 + z_r1) % 3 != 0:
                                continue

                            if z_p1 < 12 or z_p1 > 60:
                                continue

                            # Проверка условия соседства
                            r_c = m1 * (z_s1 + z_p1) / 2.0
                            r_t = m1 * z_p1 / 2.0 + m1
                            clearance1 = 2*r_c*math.sin(math.pi/3) - 2*r_t
                            if clearance1 < 1.0:
                                continue

                            d_ring1 = m1 * z_r1 + 6 * m1
                            if d_ring1 > D_MAX:
                                continue

                            # Ступень 2: подбираем Z для достижения U2 с 4 саттелитами
                            for z_s2 in range(14, 26):
                                z_r2_ideal = z_s2 * (u2 - 1)
                                z_r2 = round(z_r2_ideal)
                                z_p2 = (z_r2 - z_s2) // 2

                                # Проверка условия сборки для 4 саттелитов
                                if (z_s2 + z_r2) % 4 != 0:
                                    continue

                                if z_p2 < 12 or z_p2 > 60:
                                    continue

                                # Проверка условия соседства для 4 саттелитов
                                r_c = m2 * (z_s2 + z_p2) / 2.0
                                r_t = m2 * z_p2 / 2.0 + m2
                                clearance2 = 2*r_c*math.sin(math.pi/4) - 2*r_t
                                if clearance2 < 1.0:
                                    continue

                                d_ring2 = m2 * z_r2 + 6 * m2
                                d_max = max(d_ring1, d_ring2)
                                if d_max > D_MAX:
                                    continue

                                # Вычисленные передаточные числа
                                i1_real = (z_r1 + z_s1) / z_s1
                                i2_real = (z_r2 + z_s2) / z_s2
                                i_total = i1_real * i2_real

                                if i_total < U_MIN - 0.5:
                                    continue

                                candidates.append({
                                    'i1': i1_real, 'i2': i2_real,
                                    'n_sat_1': 3, 'n_sat_2': 4,
                                    'm1': m1,
                                    'z_s1': z_s1, 'z_p1': z_p1, 'z_r1': z_r1,
                                    'b1': b1,
                                    'x_s1': 0.0, 'x_p1': 0.0,
                                    'm2': m2,
                                    'z_s2': z_s2, 'z_p2': z_p2, 'z_r2': z_r2,
                                    'b2': b2,
                                    'x_s2': 0.0, 'x_p2': 0.0,
                                    'mat_s1': 'D16T', 'mat_p1': 'PA6_CF', 'mat_r1': 'PA6_CF',
                                    'mat_s2': 'D16T', 'mat_p2': 'PA6_CF', 'mat_r2': 'PA6_CF',
                                })

    print(f"Сгенерировано {len(candidates)} кандидатов")
    return candidates

# ============================================================================
#  Проверка варианта
# ============================================================================
def check_variant(v):
    """Быстрая проверка варианта на прочность."""
    try:
        i_total = v['i1'] * v['i2']
        t_out = T_MOTOR * i_total * ETA_STAGE**2
        n_out = N_MOTOR / i_total

        if t_out < T_OUT_REQ - 5:  # с небольшой погрешностью
            return None, "Недостаточный момент"

        # Ступень 1
        omega_sun1_rel, omega_c1 = planet_relative_speed(N_MOTOR, v['i1'])
        T_mesh_s1 = T_MOTOR / v['n_sat_1']

        s1 = run_external_pair(
            name='__s1__',
            m=v['m1'], z_pinion=v['z_s1'], z_wheel=v['z_p1'], b=v['b1'],
            torque_pinion_nm=T_mesh_s1, speed_pinion_rpm=omega_sun1_rel,
            mat_pinion=v['mat_s1'], mat_wheel=v['mat_p1'],
            x_pinion=v['x_s1'], x_wheel=v['x_p1'],
        )

        r_sun1 = v['m1'] * v['z_s1'] / 2.0
        F_t1 = T_MOTOR * 1000.0 / (v['n_sat_1'] * r_sun1)
        pr1 = planet_ring_check(
            m=v['m1'], z_planet=v['z_p1'], z_ring=v['z_r1'],
            b=v['b1'], force_t_n=F_t1,
            mat_planet=v['mat_p1'], mat_ring=v['mat_r1'],
            x_planet=v['x_p1'], x_ring=0.0,
        )

        # Ступень 2
        T_in_2 = T_MOTOR * v['i1'] * ETA_STAGE
        omega_sun2_rel, omega_c2 = planet_relative_speed(omega_c1, v['i2'])
        T_mesh_s2 = T_in_2 / v['n_sat_2']

        s2 = run_external_pair(
            name='__s2__',
            m=v['m2'], z_pinion=v['z_s2'], z_wheel=v['z_p2'], b=v['b2'],
            torque_pinion_nm=T_mesh_s2, speed_pinion_rpm=omega_sun2_rel,
            mat_pinion=v['mat_s2'], mat_wheel=v['mat_p2'],
            x_pinion=v['x_s2'], x_wheel=v['x_p2'],
        )

        r_sun2 = v['m2'] * v['z_s2'] / 2.0
        F_t2 = T_in_2 * 1000.0 / (v['n_sat_2'] * r_sun2)
        pr2 = planet_ring_check(
            m=v['m2'], z_planet=v['z_p2'], z_ring=v['z_r2'],
            b=v['b2'], force_t_n=F_t2,
            mat_planet=v['mat_p2'], mat_ring=v['mat_r2'],
            x_planet=v['x_p2'], x_ring=0.0,
        )

        # Собираем минимальный запас
        sf_min = min(s1['SF'] + s2['SF'] +
                     (pr1['sf_p'], pr1['sf_r'],
                      pr2['sf_p'], pr2['sf_r']))
        sh_min = min(s1['SH'] + s2['SH'] +
                     (pr1['sh_p'], pr1['sh_r'],
                      pr2['sh_p'], pr2['sh_r']))

        if sf_min < 1.3 or sh_min < 1.0:
            return None, f"Недостаточный запас (SF={sf_min:.2f}, SH={sh_min:.2f})"

        d_ring1 = v['m1'] * v['z_r1'] + 6 * v['m1']
        d_ring2 = v['m2'] * v['z_r2'] + 6 * v['m2']
        d_max = max(d_ring1, d_ring2)

        return {
            'i_total': i_total, 't_out': t_out, 'n_out': n_out,
            'sf_min': sf_min, 'sh_min': sh_min,
            'd_max': d_max,
            's1': s1, 's2': s2, 'pr1': pr1, 'pr2': pr2,
        }, None

    except Exception as e:
        return None, str(e)

# ============================================================================
#  Main
# ============================================================================
def main():
    os.makedirs(REPORT_DIR, exist_ok=True)

    print("=" * 70)
    print("  ГЕНЕРАЦИЯ АСИММЕТРИЧНЫХ ПЛАНЕТАРОК С D16T-СОЛНЦЕМ")
    print("=" * 70)
    print(f"  U_total > {U_MIN}, D <= {D_MAX} мм, b <= {B_MAX} мм, KA = {KA}")
    print()

    candidates = generate_candidates()

    print(f"\nПроверка {len(candidates)} кандидатов...")
    valid = []

    for idx, v in enumerate(candidates):
        if idx % 50 == 0:
            print(f"  [{idx}/{len(candidates)}]")

        result, error = check_variant(v)
        if result:
            valid.append((v, result))

    print(f"\nНайдено {len(valid)} валидных вариантов")

    if not valid:
        print("Нет валидных вариантов!")
        return

    # Сортируем по минимальной массе (примерно D * b)
    valid.sort(key=lambda x: x[1]['d_max'] * (x[0]['b1'] + x[0]['b2']))

    # Сохраняем топ-10
    report_lines = [
        "=" * 100,
        "АСИММЕТРИЧНЫЕ ПЛАНЕТАРКИ С D16T-СОЛНЦЕМ (минимальные варианты)",
        "=" * 100,
        f"U > {U_MIN}, D <= {D_MAX} мм, b <= {B_MAX} мм, KA = {KA}",
        "",
        "Топ-10 минимальных вариантов (по D·b):",
        "-" * 100,
    ]

    for rank, (v, res) in enumerate(valid[:10], 1):
        d_ring1 = v['m1'] * v['z_r1'] + 6 * v['m1']
        d_ring2 = v['m2'] * v['z_r2'] + 6 * v['m2']
        d_max = max(d_ring1, d_ring2)
        mass_proxy = d_max * (v['b1'] + v['b2'])

        report_lines.append("")
        report_lines.append(f"#{rank}: U={res['i_total']:.2f}, T_out={res['t_out']:.1f} Нм, "
                           f"D={d_max:.0f}mm, b={v['b1']+v['b2']:.0f}mm (proxy={mass_proxy:.0f})")
        report_lines.append(f"  Ст.1: m={v['m1']}, Z={v['z_s1']}/{v['z_p1']}/{v['z_r1']}, "
                           f"b={v['b1']}, 3 сат")
        report_lines.append(f"  Ст.2: m={v['m2']}, Z={v['z_s2']}/{v['z_p2']}/{v['z_r2']}, "
                           f"b={v['b2']}, 4 сат")
        report_lines.append(f"  SF_min={res['sf_min']:.2f}, SH_min={res['sh_min']:.2f}")

    report_path = os.path.join(REPORT_DIR, 'ASYMMETRIC_D16T_CANDIDATES.txt')
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(report_lines))

    print(f"\n→ Отчёт сохранён: {report_path}")

    # Сохраняем 3 лучших в spider_knee_variants.py формате
    print("\n" + "=" * 70)
    print("РЕКОМЕНДУЕМЫЕ ВАРИАНТЫ ДЛЯ ДОБАВЛЕНИЯ В spider_knee_variants.py:")
    print("=" * 70)

    for rank, (v, res) in enumerate(valid[:3], 1):
        i_total = res['i_total']
        d_ring1 = v['m1'] * v['z_r1'] + 6 * v['m1']
        d_ring2 = v['m2'] * v['z_r2'] + 6 * v['m2']
        d_max = max(d_ring1, d_ring2)

        print(f"\n# ВАРИАНТ {rank}: U ≈ {i_total:.1f}")
        t_out_val = res['t_out']
        print(f"    {{\n"
              f"        'legacy_name': 'V{int(i_total)}_D16T_{rank}',\n"
              f"        'description': 'U={i_total:.1f} асимметрич D16T, T_out≈{t_out_val:.0f}Нм, "
              f"D≈{d_max:.0f}мм.',\n"
              f"        'i1': {v['i1']:.2f}, 'i2': {v['i2']:.2f},\n"
              f"        'n_sat_1': 3, 'n_sat_2': 4,\n"
              f"        'm1': {v['m1']},\n"
              f"        'z_s1': {v['z_s1']}, 'z_p1': {v['z_p1']}, 'z_r1': {v['z_r1']},\n"
              f"        'b1': {v['b1']},\n"
              f"        'x_s1': 0.0, 'x_p1': 0.0,\n"
              f"        'm2': {v['m2']},\n"
              f"        'z_s2': {v['z_s2']}, 'z_p2': {v['z_p2']}, 'z_r2': {v['z_r2']},\n"
              f"        'b2': {v['b2']},\n"
              f"        'x_s2': 0.0, 'x_p2': 0.0,\n"
              f"        'mat_s1': 'D16T',   'mat_p1': 'PA6_CF', 'mat_r1': 'PA6_CF',\n"
              f"        'mat_s2': 'D16T',   'mat_p2': 'PA6_CF', 'mat_r2': 'PA6_CF',\n"
              f"    }},\n")

if __name__ == '__main__':
    main()
