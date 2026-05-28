"""
SPIDER-KNEE — двухступенчатая планетарная коробка для коленного сустава паука.

Назначение
----------
Параметрический расчёт двухступенчатых вариантов: для каждой пары
"солнце–саттелит" прогоняется полный пайплайн GEARpie (VDI 2736),
для внутренней пары "саттелит–венец" применяется Lewis + Hertz
(GEARpie/MAAG не поддерживает внутренние пары).

Варианты живут в отдельном файле — ``spider_knee_variants.py``.
Скрипт хранит только расчёт и формирование отчётов.

Запуск:
    python spider_knee.py                 # все варианты
    python spider_knee.py X_REC V64LH     # только указанные legacy_name'ы

Результаты:
    REPORT/SPIDER_KNEE/<auto-name>.txt     — сводка по варианту
    REPORT/SPIDER_KNEE/COMPARE.txt         — сравнительная таблица

Имя ``<auto-name>`` собирается из параметров:
    i{i_total}_{i1}x{i2}_m{m1}-Z{z_s1}-{z_p1}-{z_r1}_m{m2}-Z{z_s2}-{z_p2}-{z_r2}
При конфликте параметров — добавляется суффикс по ширинам / смещениям.

Исходные данные:
    Мотор:   T_in = 3.3 Н·м, n_in = 150 об/мин  (Kt=0.22 Нм/А, I_cont=15 А)
    Сустав:  T_out >= 60 Н·м (статически)
    Габарит: Ø <= 180 мм (текущий лимит; POM_C/PETG семейство)
    Материалы: PA6_PRINT (чистый PA6, FFF-печать) — все колёса
"""

import os
import sys
import math
import gc
import json
import glob as _glob
from types import SimpleNamespace

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

from CLASSES import (
    MATERIAL_LIBRARY, CALC_GEOMETRY, LOAD_SHARING, FORCES_SPEEDS,
    CONTACT, INVOLUTE_GEOMETRY, VDI2736, I18N,
)
from spider_knee_variants import VARIANTS
try:
    from spider_knee_variants_new import HIGH_I_VARIANTS_2026
    VARIANTS = VARIANTS + HIGH_I_VARIANTS_2026
except ImportError:
    pass
try:
    from spider_knee_variants_improved import IMPROVED_HIGH_I
    VARIANTS = VARIANTS + IMPROVED_HIGH_I
except ImportError:
    pass
try:
    from spider_knee_variants_final import FINAL_HIGH_I
    VARIANTS = VARIANTS + FINAL_HIGH_I
except ImportError:
    pass

I18N.set_lang('ru')

# ============================================================================
#  Параметры эксплуатации
# ============================================================================
T_MOTOR = 3.7
N_MOTOR = 150.0
T_OUT_REQ = 60.0
D_MAX = 200.0
KA = 1.3
T_AMB = 25.0
ETA_STAGE = 0.9

REPORT_DIR = os.path.join('REPORT', 'SPIDER_KNEE')
DATA_DIR = os.path.join(REPORT_DIR, '_data')

# ============================================================================
#  Вспомогательные функции
# ============================================================================
def _gtype(name, m, z_pinion, z_wheel, b, x_pinion=0.0, x_wheel=0.0,
           dshaft_p=8.0, dshaft_w=8.0):
    return SimpleNamespace(
        GEAR_NAME=name,
        alpha=20.0, beta=0.0,
        m=m,
        z=[z_pinion, z_wheel],
        x=[x_pinion, x_wheel],
        addendum_reduction='N',
        b=[b, b],
        dshaft=[dshaft_p, dshaft_w],
        al=None,
        haP=1.0, hfP=1.25, rfP=0.38,
        Ra=[0.6, 0.6], Rq=[0.7, 0.7], Rz=[4.8, 4.8],
    )


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


def planet_ring_check(name, m, z_planet, z_ring, b, force_t_n,
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
        'name': name,
        'force_n': force_t_n,
        'd_planet': m * z_planet, 'd_ring': m * z_ring,
        'sigma_p': sigma_p, 'sigma_r': sigma_r,
        'sigma_lim_p': material_sigmaFlim(mat_planet, cycles=cycles),
        'sigma_lim_r': material_sigmaFlim(mat_ring, cycles=cycles),
        'sf_p': material_sigmaFlim(mat_planet, cycles=cycles) * ys / sigma_p,
        'sf_r': material_sigmaFlim(mat_ring, cycles=cycles) * ys / sigma_r,
        'sigma_h': sigma_h_pr,
        'sigma_h_lim_p': material_sigmaHlim(mat_planet, cycles=cycles),
        'sigma_h_lim_r': material_sigmaHlim(mat_ring, cycles=cycles),
        'sh_p': sh_p, 'sh_r': sh_r,
        'r_eq': r_eq_pr,
    }


def _run_pair_at(size, name, m, z_pinion, z_wheel, b,
                 torque_pinion_nm, speed_pinion_rpm,
                 mat_pinion, mat_wheel, x_pinion, x_wheel):
    gtype = _gtype(name, m, z_pinion, z_wheel, b,
                   x_pinion=x_pinion, x_wheel=x_wheel)
    gmat = MATERIAL_LIBRARY.MATERIAL(mat_pinion, mat_wheel)
    geo = CALC_GEOMETRY.MAAG(gtype)
    pprof = INVOLUTE_GEOMETRY.LITVIN('P', geo, size)
    wprof = INVOLUTE_GEOMETRY.LITVIN('W', geo, size)
    gpath = LOAD_SHARING.LINES(size, geo, gmat, pprof, wprof)
    gfs = FORCES_SPEEDS.OPERATION('P', torque_pinion_nm, speed_pinion_rpm,
                                  geo, gpath, 'N')
    gcontact = CONTACT.HERTZ(gmat, None, geo, gpath, gfs, 'AC')
    glcc = VDI2736.LCC(gmat, geo, gfs, gpath, gcontact, T_AMB, KA)
    # OUTPUT_PRINT.PRINTING сюда не зовём — отдельные S*_SP.txt нам не нужны.
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
    sigma_h = float(glcc.SigmaH)
    sh_code = float(glcc.SH1)
    return {
        'name': name,
        'SF': (float(glcc.SF1), float(glcc.SF2)),
        'SH': (sh_code, float(glcc.SH2)),
        'SigmaF': (float(glcc.SigmaF1), float(glcc.SigmaF2)),
        'SigmaH': sigma_h,
        'SH_pess': sh_pessimistic(sh_code, mat_pinion, mat_wheel),
        'mats': (mat_pinion, mat_wheel),
    }


def planet_relative_speed(omega_sun_abs, i_stage):
    omega_carrier = omega_sun_abs / i_stage
    return omega_sun_abs - omega_carrier, omega_carrier


def sh_pessimistic(sh_code, mat_pinion, mat_wheel, cycles=1e6):
    """SH с учётом более слабого σHlim в смешанной паре материалов.

    VDI2736.LCC переоценивает SH для пары металл-пластик: реальный износ
    лимитируется пластиком, но в коде σHP берётся только по солнцу. Для
    одинаковых материалов SH_pess == SH_код.
    """
    s_lim_p = material_sigmaHlim(mat_pinion, cycles=cycles)
    s_lim_w = material_sigmaHlim(mat_wheel, cycles=cycles)
    return sh_code * min(s_lim_p, s_lim_w) / s_lim_p


# ============================================================================
#  Авто-имя варианта из параметров
# ============================================================================
def _fmt_num(x):
    """1.25 -> '1.25', 2.0 -> '2', 0.3 -> '0.3'."""
    return ('%g' % x)


def _base_name(v):
    i_total = v['i1'] * v['i2']
    return (
        f"i{i_total}_{v['i1']}x{v['i2']}"
        f"_m{_fmt_num(v['m1'])}-Z{v['z_s1']}-{v['z_p1']}-{v['z_r1']}"
        f"_m{_fmt_num(v['m2'])}-Z{v['z_s2']}-{v['z_p2']}-{v['z_r2']}"
    )


def _b_suffix(v):
    return f"_b{v['b1']}x{v['b2']}"


def _x_suffix(v):
    def fmt(x):
        return f"{x:+.1f}".replace('.', '')
    return f"_x{fmt(v['x_s1'])}{fmt(v['x_p1'])}{fmt(v['x_s2'])}{fmt(v['x_p2'])}"


def _mat_suffix(v):
    """Короткая метка материалов: 'PA' / 'N6' / 'PETG' / 'D16T-s2' / etc."""
    mats = (v['mat_s1'], v['mat_p1'], v['mat_r1'],
            v['mat_s2'], v['mat_p2'], v['mat_r2'])
    uniform_tags = {
        'PA6_CF':    '_PA',
        'PA6_PRINT': '_N6',
        'PETG':      '_PETG',
        'POM_C':     '_POMC',
    }
    for mat, tag in uniform_tags.items():
        if all(m == mat for m in mats):
            return tag
    # mixed — выписываем отличающиеся от PA6_CF слотов (исторический дефолт)
    parts = []
    for slot, m in zip(('s1', 'p1', 'r1', 's2', 'p2', 'r2'), mats):
        if m != 'PA6_CF':
            parts.append(f"{slot}-{m}")
    return '_' + '_'.join(parts) if parts else ''


def assign_filenames(variants):
    """Имя файла для каждого варианта; конфликты разруливаем суффиксами.

    Идея: пробуем суффиксы в порядке b → x → материалы → буквенный.
    Каждый суффикс добавляем только если он реально различает варианты
    (иначе получали мусорные ``_x+00+00+00+00`` в имени).
    """
    names = [None] * len(variants)
    by_base = {}
    for idx, v in enumerate(variants):
        by_base.setdefault(_base_name(v), []).append(idx)

    def _resolve(group, name_so_far, suffix_funcs):
        if len(group) == 1:
            names[group[0]] = name_so_far
            return
        if not suffix_funcs:
            for k, idx in enumerate(group):
                names[idx] = f"{name_so_far}_{chr(97 + k)}"
            return
        suffix_fn, *rest = suffix_funcs
        sub = {}
        for idx in group:
            sub.setdefault(suffix_fn(variants[idx]), []).append(idx)
        if len(sub) == 1:
            # суффикс не разделяет — пропускаем
            _resolve(group, name_so_far, rest)
            return
        for suf, sg in sub.items():
            _resolve(sg, name_so_far + suf, rest)

    for base, group in by_base.items():
        _resolve(group, base, [_b_suffix, _x_suffix, _mat_suffix])
    return names


# ============================================================================
#  Прогон варианта
# ============================================================================
def run_variant(v):
    """Полный расчёт варианта; возвращает dict с результатами."""
    i_total = v['i1'] * v['i2']
    t_out = T_MOTOR * i_total * ETA_STAGE**2
    n_out = N_MOTOR / i_total

    # ----- Ступень 1 -----
    omega_sun1_rel, omega_c1 = planet_relative_speed(N_MOTOR, v['i1'])
    T_mesh_s1 = T_MOTOR / v['n_sat_1']

    s1 = run_external_pair(
        name='__s1_internal__',
        m=v['m1'], z_pinion=v['z_s1'], z_wheel=v['z_p1'], b=v['b1'],
        torque_pinion_nm=T_mesh_s1, speed_pinion_rpm=omega_sun1_rel,
        mat_pinion=v['mat_s1'], mat_wheel=v['mat_p1'],
        x_pinion=v['x_s1'], x_wheel=v['x_p1'],
    )
    r_sun1 = v['m1'] * v['z_s1'] / 2.0
    F_t1 = T_MOTOR * 1000.0 / (v['n_sat_1'] * r_sun1)
    pr1 = planet_ring_check(
        name='__pr1_internal__',
        m=v['m1'], z_planet=v['z_p1'], z_ring=v['z_r1'],
        b=v['b1'], force_t_n=F_t1,
        mat_planet=v['mat_p1'], mat_ring=v['mat_r1'],
        x_planet=v['x_p1'], x_ring=0.0,
    )

    # ----- Ступень 2 -----
    T_in_2 = T_MOTOR * v['i1'] * ETA_STAGE
    omega_sun2_rel, omega_c2 = planet_relative_speed(omega_c1, v['i2'])
    T_mesh_s2 = T_in_2 / v['n_sat_2']

    s2 = run_external_pair(
        name='__s2_internal__',
        m=v['m2'], z_pinion=v['z_s2'], z_wheel=v['z_p2'], b=v['b2'],
        torque_pinion_nm=T_mesh_s2, speed_pinion_rpm=omega_sun2_rel,
        mat_pinion=v['mat_s2'], mat_wheel=v['mat_p2'],
        x_pinion=v['x_s2'], x_wheel=v['x_p2'],
    )
    r_sun2 = v['m2'] * v['z_s2'] / 2.0
    F_t2 = T_in_2 * 1000.0 / (v['n_sat_2'] * r_sun2)
    pr2 = planet_ring_check(
        name='__pr2_internal__',
        m=v['m2'], z_planet=v['z_p2'], z_ring=v['z_r2'],
        b=v['b2'], force_t_n=F_t2,
        mat_planet=v['mat_p2'], mat_ring=v['mat_r2'],
        x_planet=v['x_p2'], x_ring=0.0,
    )

    return {
        'i_total': i_total, 't_out': t_out, 'n_out': n_out,
        'T_in_2': T_in_2,
        's1': s1, 's2': s2, 'pr1': pr1, 'pr2': pr2,
    }


# ============================================================================
#  Отчёт по варианту
# ============================================================================
def write_summary(v, filename, res):
    s1, s2, pr1, pr2 = res['s1'], res['s2'], res['pr1'], res['pr2']
    i_total, t_out, n_out = res['i_total'], res['t_out'], res['n_out']
    d_ring1 = v['m1'] * v['z_r1'] + 6 * v['m1']
    d_ring2 = v['m2'] * v['z_r2'] + 6 * v['m2']
    d_max = max(d_ring1, d_ring2)
    axial = v['b1'] + v['b2'] + 30

    W = 86
    L = []
    L.append('=' * W)
    L.append(f"  СВОДКА: {filename}")
    if v.get('legacy_name'):
        L.append(f"  Историческое имя: {v['legacy_name']}")
    if v.get('description'):
        L.append(f"  {v['description']}")
    L.append('=' * W)
    L.append('')
    L.append('ИСХОДНЫЕ ДАННЫЕ И ТРЕБОВАНИЯ')
    L.append('-' * W)
    L.append(f"  Вход:        T = {T_MOTOR:.2f} Н·м,  n = {N_MOTOR:.0f} об/мин")
    L.append(f"  Требуется:   T_out >= {T_OUT_REQ:.0f} Н·м,  Ø <= {D_MAX:.0f} мм")
    L.append(f"  Коэф. KA:    {KA}  (запас на динамику)")
    L.append(f"  T_amb:       {T_AMB} °C")
    L.append('')
    L.append('ИТОГОВЫЕ ХАРАКТЕРИСТИКИ')
    L.append('-' * W)
    L.append(f"  Передаточное число   i = {v['i1']} x {v['i2']} = {i_total}")
    L.append(f"  КПД (оценка)         η ≈ {ETA_STAGE**2:.3f}")
    L.append(f"  Момент на выходе     T_out ≈ {t_out:.1f} Н·м "
             f"({'OK' if t_out >= T_OUT_REQ else 'НЕ ДОТЯГИВАЕТ'})")
    L.append(f"  Скорость на выходе   n_out = {n_out:.2f} об/мин "
             f"= {n_out*6:.1f} °/с")
    L.append(f"  Габарит макс. (Ø)    {d_max:.1f} мм "
             f"({'OK' if d_max <= D_MAX else 'ПРЕВЫШЕНИЕ'})")
    L.append(f"  Осевая длина грубо   ≈ {axial} мм "
             f"(b1 + b2 + 30 мм на водила/подшипники)")
    L.append('')

    for stage, prefix in ((1, ''), (2, '')):
        m = v[f'm{stage}']; b = v[f'b{stage}']
        zs, zp, zr = v[f'z_s{stage}'], v[f'z_p{stage}'], v[f'z_r{stage}']
        xs, xp = v[f'x_s{stage}'], v[f'x_p{stage}']
        n_sat = v[f'n_sat_{stage}']
        i_st = v[f'i{stage}']
        mat_s = v[f'mat_s{stage}']
        mat_p = v[f'mat_p{stage}']
        mat_r = v[f'mat_r{stage}']
        d_ring_ext = m * zr + 6 * m
        sp = s1 if stage == 1 else s2
        pr = pr1 if stage == 1 else pr2

        L.append(f"СТУПЕНЬ {stage} (i{stage} = {i_st}, {n_sat} саттелита)")
        L.append('-' * W)
        L.append(f"  Модуль m{stage} = {m} мм   Ширина b{stage} = {b} мм")
        L.append(f"  Z_sun = {zs:>3d}   Z_planet = {zp:>3d}   Z_ring = {zr:>3d}")
        L.append(f"  Смещение профиля:  x_sun = {xs:+.2f},  x_planet = {xp:+.2f}")
        L.append(f"  d_sun    = {m*zs:6.2f} мм   (делительный)")
        L.append(f"  d_planet = {m*zp:6.2f} мм")
        L.append(f"  d_ring   = {m*zr:6.2f} мм   (внутреннее зацепление)")
        L.append(f"  Ø наружный венца ≈ {d_ring_ext:.1f} мм")
        L.append(f"  Материалы: солнце – {mat_s}, саттелит – {mat_p}, венец – {mat_r}")
        L.append('')
        L.append('  ▸ Зацепление SUN-PLANET (VDI 2736, полный пайплайн):')
        L.append(f"      σF = {sp['SigmaF'][0]:6.2f} / {sp['SigmaF'][1]:6.2f} МПа  "
                 f"→  SF = {sp['SF'][0]:5.2f} / {sp['SF'][1]:5.2f}")
        L.append(f"      σH = {sp['SigmaH']:6.2f} МПа                "
                 f"→  SH = {sp['SH'][0]:5.2f} / {sp['SH'][1]:5.2f}")
        L.append(f"      SH_pess ({sp['mats'][0]}/{sp['mats'][1]}) = {sp['SH_pess']:.2f}")
        L.append('  ▸ Зацепление PLANET-RING (аналитика, внутренняя пара):')
        L.append(f"      F_t = {pr['force_n']:.1f} Н на один саттелит, "
                 f"R_eq = {pr['r_eq']:.2f} мм")
        L.append(f"      σF_planet = {pr['sigma_p']:5.2f} МПа  "
                 f"(σFlim = {pr['sigma_lim_p']:.1f})  →  SF = {pr['sf_p']:.2f}")
        L.append(f"      σF_ring   = {pr['sigma_r']:5.2f} МПа  "
                 f"(σFlim = {pr['sigma_lim_r']:.1f})  →  SF = {pr['sf_r']:.2f}")
        L.append(f"      σH        = {pr['sigma_h']:5.2f} МПа  "
                 f"(σHlim_pl/rg = {pr['sigma_h_lim_p']:.1f}/{pr['sigma_h_lim_r']:.1f}) "
                 f" →  SH = {pr['sh_p']:.2f}/{pr['sh_r']:.2f}")
        L.append('')

    L.append('УСЛОВИЕ СБОРКИ (assembly condition)')
    L.append('-' * W)
    s1_sum = v['z_s1'] + v['z_r1']
    s2_sum = v['z_s2'] + v['z_r2']
    L.append(f"  Ступ.1:  (Z_sun + Z_ring) / n_sat = ({v['z_s1']} + {v['z_r1']})/{v['n_sat_1']} "
             f"= {s1_sum/v['n_sat_1']:.3f}   "
             f"{'OK' if s1_sum % v['n_sat_1'] == 0 else 'НЕЦЕЛОЕ'}")
    L.append(f"  Ступ.2:  (Z_sun + Z_ring) / n_sat = ({v['z_s2']} + {v['z_r2']})/{v['n_sat_2']} "
             f"= {s2_sum/v['n_sat_2']:.3f}   "
             f"{'OK' if s2_sum % v['n_sat_2'] == 0 else 'НЕЦЕЛОЕ'}")
    L.append('')
    L.append('УСЛОВИЕ СОСЕДСТВА (планеты не должны касаться)')
    L.append('-' * W)
    for stage_idx, m_st, zs, zp, ns in [
        (1, v['m1'], v['z_s1'], v['z_p1'], v['n_sat_1']),
        (2, v['m2'], v['z_s2'], v['z_p2'], v['n_sat_2'])]:
        r_carrier = m_st * (zs + zp) / 2.0
        r_planet_tip = m_st * zp / 2.0 + m_st
        clearance = 2.0 * r_carrier * math.sin(math.pi / ns) - 2.0 * r_planet_tip
        L.append(f"  Ступ.{stage_idx}: зазор между планетами ≈ {clearance:.2f} мм   "
                 f"{'OK' if clearance > 1.0 else 'ОПАСНО'}")
    L.append('')
    L.append('=' * W)

    path = os.path.join(REPORT_DIR, f'{filename}.txt')
    with open(path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(L))
    return path


def save_result_json(filename, v, res):
    """JSON-кэш результата — чтобы COMPARE мог собрать все ранее прогнанные
    варианты, даже если в текущем запуске обсчитан только подмножество."""
    payload = {
        'filename': filename,
        'variant': v,
        'i_total': res['i_total'], 't_out': res['t_out'], 'n_out': res['n_out'],
        'T_in_2': res['T_in_2'],
        's1': res['s1'], 's2': res['s2'],
        'pr1': res['pr1'], 'pr2': res['pr2'],
    }
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(os.path.join(DATA_DIR, f'{filename}.json'),
              'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def _retuplify(d, keys):
    for k in keys:
        if k in d and isinstance(d[k], list):
            d[k] = tuple(d[k])


def load_cached_results():
    """Прочитать все ранее сохранённые JSON-результаты из _data/."""
    out = {}
    if not os.path.isdir(DATA_DIR):
        return out
    for path in _glob.glob(os.path.join(DATA_DIR, '*.json')):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                r = json.load(f)
        except (OSError, ValueError):
            continue
        for sub_key in ('s1', 's2'):
            _retuplify(r.get(sub_key, {}), ('SF', 'SH', 'SigmaF', 'mats'))
        out[r['filename']] = r
    return out


# ============================================================================
#  Сравнительная сводка
# ============================================================================
def _mat_label(v):
    mats = {v['mat_s1'], v['mat_p1'], v['mat_r1'],
            v['mat_s2'], v['mat_p2'], v['mat_r2']}
    if mats == {'PA6_CF'}:
        return 'PA6-CF'
    if 'D16T' in mats:
        slots = []
        for tag, key in (('s1', 'mat_s1'), ('p1', 'mat_p1'), ('r1', 'mat_r1'),
                         ('s2', 'mat_s2'), ('p2', 'mat_p2'), ('r2', 'mat_r2')):
            if v[key] == 'D16T':
                slots.append(tag)
        return 'PA6-CF + D16T(' + ','.join(slots) + ')'
    return '+'.join(sorted(mats))


def write_overall_summary(results):
    """Главная сравнительная таблица. Два блока:
       (1) краткий — одна строка на вариант с запасами прочности;
       (2) подробный — параметры и материалы по ступеням.
    """
    W = 118
    L = []
    L.append('=' * W)
    L.append('  SPIDER_KNEE — СРАВНЕНИЕ ВАРИАНТОВ')
    L.append('=' * W)
    L.append(f"Вход: {T_MOTOR} Н·м, {N_MOTOR:.0f} об/мин    "
             f"Требуется: T_out >= {T_OUT_REQ:.0f} Н·м, Ø <= {D_MAX:.0f} мм    KA = {KA}")
    L.append('')

    # ---------- (1) КРАТКАЯ СВОДКА ----------
    L.append('-' * W)
    L.append('Краткая сводка (SF_min, SH_min, SH_pess — минимум среди всех зацеплений)')
    L.append('-' * W)
    header = (f"{'Имя файла':<60} "
              f"{'i':>4} {'T_out':>6} {'Ø':>6} {'Lax':>5} "
              f"{'SF_min':>6} {'SH_min':>6} {'SH_pess':>7}")
    L.append(header)
    L.append('-' * W)
    for r in results:
        v = r['variant']
        i_t = r['i_total']
        d_max = max(v['m1']*v['z_r1'] + 6*v['m1'],
                    v['m2']*v['z_r2'] + 6*v['m2'])
        lax = v['b1'] + v['b2'] + 30
        sf_min = min(r['s1']['SF'] + r['s2']['SF'] +
                     (r['pr1']['sf_p'], r['pr1']['sf_r'],
                      r['pr2']['sf_p'], r['pr2']['sf_r']))
        sh_min = min(r['s1']['SH'] + r['s2']['SH'] +
                     (r['pr1']['sh_p'], r['pr1']['sh_r'],
                      r['pr2']['sh_p'], r['pr2']['sh_r']))
        sh_pess = min(r['s1']['SH_pess'], r['s2']['SH_pess'],
                      r['pr1']['sh_p'], r['pr1']['sh_r'],
                      r['pr2']['sh_p'], r['pr2']['sh_r'])
        L.append(f"{r['filename']:<60} "
                 f"{i_t:>4} {r['t_out']:>6.1f} {d_max:>6.1f} {lax:>5} "
                 f"{sf_min:>6.2f} {sh_min:>6.2f} {sh_pess:>7.2f}")
    L.append('-' * W)
    L.append('')

    # ---------- (2) ПОДРОБНАЯ ТАБЛИЦА ПО СТУПЕНЯМ ----------
    L.append('-' * W)
    L.append('Параметры и материалы по ступеням')
    L.append('-' * W)
    L.append(f"{'Имя файла':<60} {'Ст':>3} {'m':>5} "
             f"{'Z_s':>4} {'Z_p':>4} {'Z_r':>4} "
             f"{'b':>4} {'n_s':>3} {'x_s':>5} {'x_p':>5} "
             f"{'Материалы s/p/r':<22}")
    L.append('-' * W)
    for r in results:
        v = r['variant']
        for stage in (1, 2):
            L.append(f"{r['filename'] if stage == 1 else '':<60} "
                     f"{stage:>3} {_fmt_num(v[f'm{stage}']):>5} "
                     f"{v[f'z_s{stage}']:>4} {v[f'z_p{stage}']:>4} {v[f'z_r{stage}']:>4} "
                     f"{v[f'b{stage}']:>4} {v[f'n_sat_{stage}']:>3} "
                     f"{v[f'x_s{stage}']:>+5.2f} {v[f'x_p{stage}']:>+5.2f} "
                     f"{v[f'mat_s{stage}']}/{v[f'mat_p{stage}']}/{v[f'mat_r{stage}']:<22}")
        L.append('')
    L.append('-' * W)
    L.append('')

    # ---------- (3) ЛЕГЕНДА ----------
    L.append('Расшифровка колонок:')
    L.append('  i           — передаточное число (i1 · i2)')
    L.append('  T_out, Н·м  — момент на суставе (с учётом КПД η ≈ ηст^2)')
    L.append('  Ø, мм       — наружный диаметр (по бо́льшему венцу + стенка ~3·m)')
    L.append('  Lax, мм     — осевой габарит (b1 + b2 + 30 мм на водила/подшипники)')
    L.append('  SF_min      — минимальный запас по изгибу корня среди всех зацеплений')
    L.append('  SH_min      — минимальный запас по контактной прочности (как в коде GEARpie)')
    L.append('  SH_pess     — то же, но σHP по более слабому материалу пары (актуально для D16T+PA6-CF)')
    L.append('  Z_s/p/r     — число зубьев солнца / саттелита / венца')
    L.append('  n_s         — число саттелитов')
    L.append('  x_s/x_p     — смещения профиля солнца/саттелита')
    L.append('')
    L.append('Норматив VDI 2736 для пластиковых шестерён: SF_min >= 2.0, SH_min >= 1.4.')
    L.append('=' * W)

    path = os.path.join(REPORT_DIR, 'COMPARE.txt')
    with open(path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(L))
    print(f"\n→ Сравнительная сводка: {path}")


# ============================================================================
#  Main
# ============================================================================
def _select_variants(argv):
    """Если переданы аргументы — фильтр по legacy_name."""
    if not argv:
        return VARIANTS
    wanted = set(argv)
    selected = [v for v in VARIANTS if v.get('legacy_name') in wanted]
    missing = wanted - {v.get('legacy_name') for v in selected}
    if missing:
        print(f"!!! Не найдены варианты: {sorted(missing)}")
    return selected


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    os.makedirs(REPORT_DIR, exist_ok=True)
    variants = _select_variants(argv)
    if not variants:
        print("Нет вариантов к запуску.")
        return

    filenames = assign_filenames(variants)
    results = []
    for v, filename in zip(variants, filenames):
        gc.collect()
        print()
        print('=' * 70)
        legacy = f" [{v.get('legacy_name')}]" if v.get('legacy_name') else ''
        print(f"  {filename}{legacy}")
        print('=' * 70)
        try:
            res = run_variant(v)
            path = write_summary(v, filename, res)
            save_result_json(filename, v, res)
            print(f"  → {path}")
            print(f"  i = {res['i_total']}, T_out ≈ {res['t_out']:.1f} Н·м, "
                  f"n_out = {res['n_out']:.2f} об/мин")
            print(f"  Ст.1 sun-planet: SF={res['s1']['SF'][0]:.2f}/{res['s1']['SF'][1]:.2f}, "
                  f"SH={res['s1']['SH'][0]:.2f}/{res['s1']['SH'][1]:.2f}")
            print(f"  Ст.1 planet-ring: SF_p={res['pr1']['sf_p']:.2f}, "
                  f"SF_r={res['pr1']['sf_r']:.2f}")
            print(f"  Ст.2 sun-planet: SF={res['s2']['SF'][0]:.2f}/{res['s2']['SF'][1]:.2f}, "
                  f"SH={res['s2']['SH'][0]:.2f}/{res['s2']['SH'][1]:.2f}")
            print(f"  Ст.2 planet-ring: SF_p={res['pr2']['sf_p']:.2f}, "
                  f"SF_r={res['pr2']['sf_r']:.2f}")
            results.append({'variant': v, 'filename': filename, **res})
        except Exception as e:
            print(f"!!! Ошибка в варианте {filename}: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()

    # Сводная таблица — по всем известным результатам (кэш + только что
    # прогнанные), чтобы COMPARE не «забывал» предыдущие запуски.
    merged = load_cached_results()
    for r in results:
        merged[r['filename']] = r

    if merged:
        # Порядок: сначала текущие VARIANTS в их порядке, потом «сироты»
        # (отчёты, имени которых нет в variants.py).
        try:
            current_order = assign_filenames(VARIANTS)
        except Exception:
            current_order = []
        ordered = []
        seen = set()
        for fname in current_order:
            if fname in merged:
                ordered.append(merged[fname])
                seen.add(fname)
        for fname, r in merged.items():
            if fname not in seen:
                ordered.append(r)
        write_overall_summary(ordered)


if __name__ == '__main__':
    main()
