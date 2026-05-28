"""
БЫСТРЫЙ подбор асимметричных планетарок с D16T-солнцем.
Целевые конфигурации для U > 32, минимальный объём.
"""

import os
import sys
import math

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from CLASSES import MATERIAL_LIBRARY, CALC_GEOMETRY, LOAD_SHARING, FORCES_SPEEDS, \
    CONTACT, INVOLUTE_GEOMETRY, VDI2736, I18N

I18N.set_lang('ru')

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
    """Lewis + Hertz для внутренней пары."""
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
        'sf_p': material_sigmaFlim(mat_planet, cycles=cycles) * ys / sigma_p,
        'sf_r': material_sigmaFlim(mat_ring, cycles=cycles) * ys / sigma_r,
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
    }

def planet_relative_speed(omega_sun_abs, i_stage):
    omega_carrier = omega_sun_abs / i_stage
    return omega_sun_abs - omega_carrier, omega_carrier

# ЦЕЛЕВЫЕ ВАРИАНТЫ - вручную подобранные для быстрой проверки
QUICK_VARIANTS = [
    {
        'name': 'D16T_U34_compact',
        'i1': 4.0, 'i2': 8.5,  # U = 34
        'm1': 1.25, 'b1': 18,
        'z_s1': 18, 'z_p1': 27, 'z_r1': 72,
        'm2': 1.5, 'b2': 30,
        'z_s2': 18, 'z_p2': 27, 'z_r2': 72,
    },
    {
        'name': 'D16T_U35_balanced',
        'i1': 5.0, 'i2': 7.0,  # U = 35
        'm1': 1.5, 'b1': 20,
        'z_s1': 18, 'z_p1': 27, 'z_r1': 72,
        'm2': 1.5, 'b2': 30,
        'z_s2': 18, 'z_p2': 27, 'z_r2': 72,
    },
    {
        'name': 'D16T_U36_wide',
        'i1': 6.0, 'i2': 6.0,  # U = 36
        'm1': 1.25, 'b1': 22,
        'z_s1': 18, 'z_p1': 36, 'z_r1': 90,
        'm2': 1.5, 'b2': 32,
        'z_s2': 18, 'z_p2': 27, 'z_r2': 72,
    },
]

def check_quick_variant(v):
    """Проверяет один вариант."""
    try:
        print(f"\n  Проверка {v['name']}...", end=' ')

        i_total = v['i1'] * v['i2']
        t_out = T_MOTOR * i_total * ETA_STAGE**2

        if t_out < T_OUT_REQ - 5:
            print(f"T_out={t_out:.1f} < требуемого")
            return None

        # Ступень 1
        omega_sun1_rel, omega_c1 = planet_relative_speed(N_MOTOR, v['i1'])
        T_mesh_s1 = T_MOTOR / 3

        s1 = run_external_pair(
            name='__s1__',
            m=v['m1'], z_pinion=v['z_s1'], z_wheel=v['z_p1'], b=v['b1'],
            torque_pinion_nm=T_mesh_s1, speed_pinion_rpm=omega_sun1_rel,
            mat_pinion='D16T', mat_wheel='PA6_CF',
        )

        # Ступень 2
        T_in_2 = T_MOTOR * v['i1'] * ETA_STAGE
        omega_sun2_rel, _ = planet_relative_speed(omega_c1, v['i2'])
        T_mesh_s2 = T_in_2 / 4

        s2 = run_external_pair(
            name='__s2__',
            m=v['m2'], z_pinion=v['z_s2'], z_wheel=v['z_p2'], b=v['b2'],
            torque_pinion_nm=T_mesh_s2, speed_pinion_rpm=omega_sun2_rel,
            mat_pinion='D16T', mat_wheel='PA6_CF',
        )

        # Проверка внутренних пар
        r_sun1 = v['m1'] * v['z_s1'] / 2.0
        F_t1 = T_MOTOR * 1000.0 / (3 * r_sun1)
        pr1 = planet_ring_check(
            m=v['m1'], z_planet=v['z_p1'], z_ring=v['z_r1'],
            b=v['b1'], force_t_n=F_t1,
            mat_planet='PA6_CF', mat_ring='PA6_CF',
        )

        r_sun2 = v['m2'] * v['z_s2'] / 2.0
        F_t2 = T_in_2 * 1000.0 / (4 * r_sun2)
        pr2 = planet_ring_check(
            m=v['m2'], z_planet=v['z_p2'], z_ring=v['z_r2'],
            b=v['b2'], force_t_n=F_t2,
            mat_planet='PA6_CF', mat_ring='PA6_CF',
        )

        # Мин запас
        sf_min = min(s1['SF'] + s2['SF'] + (pr1['sf_p'], pr1['sf_r'], pr2['sf_p'], pr2['sf_r']))
        sh_min = min(s1['SH'] + s2['SH'] + (pr1['sh_p'], pr1['sh_r'], pr2['sh_p'], pr2['sh_r']))

        d_ring1 = v['m1'] * v['z_r1'] + 6 * v['m1']
        d_ring2 = v['m2'] * v['z_r2'] + 6 * v['m2']
        d_max = max(d_ring1, d_ring2)

        if sf_min < 1.3 or sh_min < 1.0:
            print(f"SF={sf_min:.2f}, SH={sh_min:.2f} - недостаточно")
            return None

        print(f"OK: U={i_total:.1f}, T_out={t_out:.1f}, D={d_max:.0f}, SF={sf_min:.2f}, SH={sh_min:.2f}")

        return {
            'i_total': i_total, 't_out': t_out,
            'd_max': d_max, 'sf_min': sf_min, 'sh_min': sh_min,
        }

    except Exception as e:
        print(f"ОШИБКА: {type(e).__name__}")
        return None

def main():
    os.makedirs(REPORT_DIR, exist_ok=True)

    print("=" * 70)
    print("  БЫСТРЫЙ ПОДБОР: D16T-СОЛНЦЕ, U > 32")
    print("=" * 70)

    valid = []
    for v in QUICK_VARIANTS:
        res = check_quick_variant(v)
        if res:
            valid.append((v, res))

    if not valid:
        print("\nНе найдено валидных вариантов из быстрого набора.")
        return

    print("\n" + "=" * 70)
    print(f"НАЙДЕНО {len(valid)} ВАЛИДНЫХ ВАРИАНТОВ")
    print("=" * 70)

    for v, res in valid:
        d_ring1 = v['m1'] * v['z_r1'] + 6 * v['m1']
        d_ring2 = v['m2'] * v['z_r2'] + 6 * v['m2']
        print(f"\n{v['name']}:")
        print(f"  U = {res['i_total']:.2f}")
        print(f"  T_out = {res['t_out']:.1f} Нм")
        print(f"  D = {res['d_max']:.0f} мм, SF_min = {res['sf_min']:.2f}, SH_min = {res['sh_min']:.2f}")
        print(f"  Ст.1: m={v['m1']}, b={v['b1']}, Z={v['z_s1']}/{v['z_p1']}/{v['z_r1']}, D={d_ring1:.0f}")
        print(f"  Ст.2: m={v['m2']}, b={v['b2']}, Z={v['z_s2']}/{v['z_p2']}/{v['z_r2']}, D={d_ring2:.0f}")

if __name__ == '__main__':
    main()
