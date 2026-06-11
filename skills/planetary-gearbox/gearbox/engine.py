"""Переносимое ядро расчёта многоступенчатой планетарной коробки.

Физика — БЕЗ ИЗМЕНЕНИЙ из ``spider_thigh.py`` / GEARpie:
  * внешняя пара «солнце–саттелит» → полный пайплайн VDI 2736 (пакет CLASSES);
  * внутренняя пара «саттелит–венец» → аналитика Lewis + Hertz
    (MAAG/GEARpie не считает внутреннее зацепление).

Отличие от прежних скриптов: вся операционная точка (Ka, T_amb, КПД, …) и
требования (T_out, Ø) вынесены в :class:`Config` — никаких модульных констант,
чтобы движок переиспользовался для любой коробки и любого вендора-агента.

Поддерживаются два режима задания нагрузки (см. :func:`compute`):
  * ``output`` — задан требуемый выходной момент; нагрузка на зубья каждой
    ступени получается обратной раскруткой по передаточным числам (статическое
    равновесие моментов, без КПД в тракте нагрузки);
  * ``motor`` — задан мотор (T_in, n); момент идёт вперёд через ступени с КПД,
    T_out вычисляется (поведение spider_knee / spider_thigh один-в-один).
"""

import os
import sys
import math
from dataclasses import dataclass
from types import SimpleNamespace


# --- найти корень репозитория GEARpie (каталог с пакетом CLASSES) ------------
def _find_repo_root(start):
    d = os.path.abspath(start)
    for _ in range(8):
        if os.path.isdir(os.path.join(d, 'CLASSES')):
            return d
        nd = os.path.dirname(d)
        if nd == d:
            break
        d = nd
    raise RuntimeError(
        "Не найден пакет CLASSES (корень GEARpie) вверх от %r" % start)


REPO_ROOT = _find_repo_root(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

# CLASSES требует numpy/scipy — они в .venv проекта GEARpie.
from CLASSES import (  # noqa: E402
    MATERIAL_LIBRARY, CALC_GEOMETRY, LOAD_SHARING, FORCES_SPEEDS,
    CONTACT, INVOLUTE_GEOMETRY, VDI2736, I18N,
)

I18N.set_lang('ru')

ALPHA_N = math.radians(20.0)
NEIGHBOR_CLEAR_MIN = 0.3    # < этого — саттелиты пересекаются (ошибка)
NEIGHBOR_CLEAR_WARN = 1.5   # < этого — туго для FFF-печати (предупреждение)
_PR_CYCLES = 1e6            # циклы для аналитической внутренней пары (как в spider_*)


@dataclass
class Config:
    """Операционная точка и пороги приёмки (всё, что не геометрия ступеней)."""
    Ka: float = 1.3              # коэффициент нагрузки (умножает момент ДО напряжений)
    T_amb: float = 25.0          # окружающая температура, °C
    eta_stage: float = 0.9       # КПД одной ступени (для режима motor и оценки)
    ring_wall: float = 4.0       # радиальный припуск делит.Ø→наруж.Ø, мм (OD=m·z_ring+2·ring_wall).
                                 # backing за корнем зуба = ring_wall−1.25·m (m≤2.0 → ≥1.5 мм)
    SF_min: float = 2.0          # порог приёмки по изгибу (VDI 2736)
    SH_min: float = 1.4          # порог приёмки по контакту (VDI 2736)
    D_max: float = None          # лимит наружного Ø, мм (None = без лимита)
    n_in_ref: float = 150.0      # опорная входная скорость для кинематики VDI, об/мин
    planet_clearance_min: float = NEIGHBOR_CLEAR_WARN  # мин. зазор саттелитов для авто-подбора n, мм
    n_planets_cap: int = 12      # потолок при авто-подборе числа саттелитов
    alpha_deg: float = 20.0      # угол профиля/зацепления, град (стандарт 20; 25 — выше нагруз. способность,
                                 # σH ∝ 1/√(sin2α), но распорная сила ∝ tanα). При x=0 геометрия (соосность/
                                 # сборка/зазор) от α не зависит — α входит только в напряжения.


# ============================================================================
#  Вспомогательные функции (порт из spider_thigh.py, идентичны)
# ============================================================================
def _gtype(name, m, z_pinion, z_wheel, b, x_pinion=0.0, x_wheel=0.0,
           dshaft_p=8.0, dshaft_w=8.0, alpha_deg=20.0):
    return SimpleNamespace(
        GEAR_NAME=name,
        alpha=alpha_deg, beta=0.0,
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


def material_sigmaFlim(name, t_amb=25.0, cycles=1e6):
    lib = MATERIAL_LIBRARY.LIBRARY_MAT(name)
    fn = lib.SigmaFlim
    if callable(fn):
        try:
            return fn(t_amb, cycles)
        except TypeError:
            return fn(cycles)
    return float(fn)


def material_sigmaHlim(name, t_amb=25.0, cycles=1e6):
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


def sh_pessimistic(sh_code, mat_pinion, mat_wheel, t_amb=25.0, cycles=1e6):
    """SH с учётом более слабого σHlim в смешанной паре материалов.

    VDI2736.LCC берёт σHP только по солнцу — для пары металл-пластик это
    переоценивает SH (реальный износ лимитируется пластиком). Для одинаковых
    материалов SH_pess == SH_код.
    """
    s_lim_p = material_sigmaHlim(mat_pinion, t_amb, cycles)
    s_lim_w = material_sigmaHlim(mat_wheel, t_amb, cycles)
    return sh_code * min(s_lim_p, s_lim_w) / s_lim_p


def planet_relative_speed(omega_sun_abs, i_stage):
    omega_carrier = omega_sun_abs / i_stage
    return omega_sun_abs - omega_carrier, omega_carrier


# ============================================================================
#  Расчёт пар зацепления
# ============================================================================
def planet_ring_check(name, m, z_planet, z_ring, b, force_t_n,
                      mat_planet, mat_ring, x_planet=0.0, x_ring=0.0,
                      cycles=_PR_CYCLES, ys=2.0, alpha_deg=20.0,
                      ka=1.3, t_amb=25.0):
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

    sh_p = material_sigmaHlim(mat_planet, t_amb, cycles) / sigma_h_pr
    sh_r = material_sigmaHlim(mat_ring, t_amb, cycles) / sigma_h_pr

    return {
        'force_n': force_t_n,
        'd_planet': m * z_planet, 'd_ring': m * z_ring,
        'sigma_p': sigma_p, 'sigma_r': sigma_r,
        'sigma_lim_p': material_sigmaFlim(mat_planet, t_amb, cycles),
        'sigma_lim_r': material_sigmaFlim(mat_ring, t_amb, cycles),
        'sf_p': material_sigmaFlim(mat_planet, t_amb, cycles) * ys / sigma_p,
        'sf_r': material_sigmaFlim(mat_ring, t_amb, cycles) * ys / sigma_r,
        'sigma_h': sigma_h_pr,
        'sigma_h_lim_p': material_sigmaHlim(mat_planet, t_amb, cycles),
        'sigma_h_lim_r': material_sigmaHlim(mat_ring, t_amb, cycles),
        'sh_p': sh_p, 'sh_r': sh_r,
        'r_eq': r_eq_pr,
    }


def _run_pair_at(size, name, m, z_pinion, z_wheel, b,
                 torque_pinion_nm, speed_pinion_rpm,
                 mat_pinion, mat_wheel, x_pinion, x_wheel, cfg):
    gtype = _gtype(name, m, z_pinion, z_wheel, b,
                   x_pinion=x_pinion, x_wheel=x_wheel, alpha_deg=cfg.alpha_deg)
    gmat = MATERIAL_LIBRARY.MATERIAL(mat_pinion, mat_wheel)
    geo = CALC_GEOMETRY.MAAG(gtype)
    pprof = INVOLUTE_GEOMETRY.LITVIN('P', geo, size)
    wprof = INVOLUTE_GEOMETRY.LITVIN('W', geo, size)
    gpath = LOAD_SHARING.LINES(size, geo, gmat, pprof, wprof)
    gfs = FORCES_SPEEDS.OPERATION('P', torque_pinion_nm, speed_pinion_rpm,
                                  geo, gpath, 'N')
    gcontact = CONTACT.HERTZ(gmat, None, geo, gpath, gfs, 'AC')
    glcc = VDI2736.LCC(gmat, geo, gfs, gpath, gcontact, cfg.T_amb, cfg.Ka)
    return glcc


def run_external_pair(name, m, z_pinion, z_wheel, b,
                      torque_pinion_nm, speed_pinion_rpm,
                      mat_pinion, mat_wheel, cfg,
                      x_pinion=0.0, x_wheel=0.0, size=1000):
    """Внешняя пара через полный пайплайн VDI 2736 (солнце–саттелит)."""
    last_err = None
    glcc = None
    for s in (size, 500, 300):
        try:
            glcc = _run_pair_at(
                s, name, m, z_pinion, z_wheel, b,
                torque_pinion_nm, speed_pinion_rpm,
                mat_pinion, mat_wheel, x_pinion, x_wheel, cfg)
            break
        except (MemoryError, ValueError) as e:
            last_err = e
            continue
    if glcc is None:
        raise last_err
    sh_code = float(glcc.SH1)
    return {
        'SF': (float(glcc.SF1), float(glcc.SF2)),
        'SH': (sh_code, float(glcc.SH2)),
        'SigmaF': (float(glcc.SigmaF1), float(glcc.SigmaF2)),
        'SigmaH': float(glcc.SigmaH),
        'SH_pess': sh_pessimistic(sh_code, mat_pinion, mat_wheel, cfg.T_amb),
        'mats': (mat_pinion, mat_wheel),
    }


# ============================================================================
#  Геометрическая валидация планетарной ступени
#  Три условия (ГОСТ 50891 / Lynwander, "Gear Drive Systems"):
#    1) Соосность — a_w(sun-planet) == a_w(planet-ring);
#    2) Сборка    — (z_s + z_r) кратно числу саттелитов;
#    3) Соседство — вершины соседних саттелитов не пересекаются.
# ============================================================================
def _inv(a):
    return math.tan(a) - a


def _alpha_from_inv(target):
    lo, hi = 1e-7, math.radians(75.0)
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        if _inv(mid) < target:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def _aw_external(m, z1, z2, x1, x2, alpha=ALPHA_N):
    inv_aw = _inv(alpha) + 2.0 * math.tan(alpha) * (x1 + x2) / (z1 + z2)
    aw_alpha = _alpha_from_inv(inv_aw)
    return m * (z1 + z2) / 2.0 * math.cos(alpha) / math.cos(aw_alpha)


def _aw_internal(m, z_ring, z_planet, x_ring, x_planet, alpha=ALPHA_N):
    inv_aw = (_inv(alpha)
              + 2.0 * math.tan(alpha) * (x_ring - x_planet) / (z_ring - z_planet))
    aw_alpha = _alpha_from_inv(inv_aw)
    return m * (z_ring - z_planet) / 2.0 * math.cos(alpha) / math.cos(aw_alpha)


def validate_stage(m, zs, zp, zr, xs, xp, n_sat, xr=0.0):
    """Проверка одной планетарной ступени → (errors, warnings, info)."""
    errors, warnings = [], []

    aw_ext = _aw_external(m, zs, zp, xs, xp)
    aw_int = _aw_internal(m, zr, zp, xr, xp)
    coax_err = abs(aw_ext - aw_int)
    coaxial_ok = coax_err < 0.02
    if not coaxial_ok:
        need_zp = (zr - zs) / 2.0
        errors.append(
            f"СООСНОСТЬ: a_w(sun-planet)={aw_ext:.3f} != a_w(planet-ring)={aw_int:.3f} "
            f"(Δ={coax_err:.3f} мм). Для z_s={zs}, z_r={zr} нужен z_p={need_zp:g} "
            f"(сейчас {zp})")

    assembly_ok = (zs + zr) % n_sat == 0
    if not assembly_ok:
        errors.append(
            f"СБОРКА: (z_s+z_r)={zs + zr} не кратно n_sat={n_sat} "
            f"(={(zs + zr) / n_sat:.3f}) — равномерная расстановка невозможна")

    ra_planet = m * zp / 2.0 + m * (1.0 + xp)
    center_dist = 2.0 * aw_ext * math.sin(math.pi / n_sat)
    clearance = center_dist - 2.0 * ra_planet
    if clearance < NEIGHBOR_CLEAR_MIN:
        errors.append(
            f"СОСЕДСТВО: зазор между саттелитами {clearance:.2f} мм < "
            f"{NEIGHBOR_CLEAR_MIN} мм — саттелиты пересекаются ({n_sat} шт.)")
    elif clearance < NEIGHBOR_CLEAR_WARN:
        warnings.append(
            f"СОСЕДСТВО: зазор {clearance:.2f} мм мал (<{NEIGHBOR_CLEAR_WARN} мм) "
            f"для {n_sat} саттелитов — туго для FFF-печати")

    info = {'aw_ext': aw_ext, 'aw_int': aw_int, 'coax_err': coax_err,
            'clearance': clearance, 'coaxial_ok': coaxial_ok,
            'assembly_ok': assembly_ok}
    return errors, warnings, info


def planet_clearance(m, zp, xp, aw_ext, n):
    """Зазор между вершинами соседних саттелитов при n саттелитах, мм."""
    ra_planet = m * zp / 2.0 + m * (1.0 + xp)
    return 2.0 * aw_ext * math.sin(math.pi / n) - 2.0 * ra_planet


def max_planets(m, zs, zp, zr, xs, xp, min_clearance, n_cap=12):
    """Максимум саттелитов, которые геометрически влезают в ступень.

    Ограничения: (1) условие сборки `(z_s+z_r) % n == 0` (равные интервалы),
    (2) соседство — зазор вершин соседних саттелитов >= ``min_clearance``.
    Возвращает (n_best, info). Если ни одно n с зазором не проходит — берём
    минимальное число саттелитов (наибольший зазор), а проверка геометрии
    позже это пометит.
    """
    aw = _aw_external(m, zs, zp, xs, xp)
    divisors = [n for n in range(2, n_cap + 1) if (zs + zr) % n == 0]
    if not divisors:                      # (z_s+z_r) простое и > n_cap
        divisors = [2] if (zs + zr) % 2 == 0 else [3]
    feasible = [n for n in divisors
                if planet_clearance(m, zp, xp, aw, n) >= min_clearance]
    n_best = max(feasible) if feasible else min(divisors)
    return n_best, {
        'aw_ext': aw,
        'clearance': planet_clearance(m, zp, xp, aw, n_best),
        'candidates': {n: round(planet_clearance(m, zp, xp, aw, n), 3)
                       for n in divisors},
    }


def resolve_planets(stages, cfg):
    """Заполнить число саттелитов: авто-максимум, если в spec не задано явно.

    Идемпотентна: уже разрешённые ступени (есть ключ ``n_planets_max``) не трогаем.
    Для каждой ступени добавляет ``n_planets_max`` (сколько влезает) и флаг
    ``n_planets_auto`` (было ли подобрано автоматически).
    """
    if all('n_planets_max' in s for s in stages):
        return stages
    out = []
    for s in stages:
        s2 = dict(s)
        nmax, info = max_planets(
            s2['m'], s2['z_sun'], s2['z_planet'], s2['z_ring'],
            s2['x_sun'], s2['x_planet'], cfg.planet_clearance_min,
            cfg.n_planets_cap)
        s2['n_planets_max'] = nmax
        s2['planet_clearance_at_max_mm'] = round(info['clearance'], 3)
        if s2.get('n_planets'):           # задано явно — уважаем override
            s2['n_planets_auto'] = False
        else:
            s2['n_planets'] = nmax
            s2['n_planets_auto'] = True
        out.append(s2)
    return out


def validate_geometry(stages):
    """Проверка всех ступеней (list нормализованных dict) → (errors, warnings)."""
    errors, warnings = [], []
    for idx, s in enumerate(stages, 1):
        e, w, _ = validate_stage(
            m=s['m'], zs=s['z_sun'], zp=s['z_planet'], zr=s['z_ring'],
            xs=s['x_sun'], xp=s['x_planet'], n_sat=s['n_planets'],
            xr=s.get('x_ring', 0.0))
        errors += [f"ст.{idx}: {msg}" for msg in e]
        warnings += [f"ст.{idx}: {msg}" for msg in w]
    return errors, warnings


# ============================================================================
#  Кинематика / распределение момента по ступеням
# ============================================================================
def _ratio(stage):
    """Передаточное число планетарной ступени: i = 1 + z_ring / z_sun."""
    return 1.0 + stage['z_ring'] / stage['z_sun']


def _stage_loads(stages, load, cfg):
    """Вернуть на каждую ступень (sun_torque [Н·м], sun_speed_rel [об/мин]).

    sun_torque — ПОЛНЫЙ момент на солнце ступени (до деления на саттелиты);
    далее t_mesh = sun_torque / n_sat, F_t = sun_torque*1000 / (n_sat·r_sun).
    """
    i = [_ratio(s) for s in stages]
    i_total = math.prod(i)
    n = len(stages)

    if load['mode'] == 'output':
        # Обратная раскрутка из требуемого T_out — статическое равновесие
        # моментов (КПД в тракт нагрузки не вводим: при удержании момента
        # потери на трение не догружают зубья выходной ступени).
        t_out = float(load['T_out_req'])
        sun_T = [t_out / math.prod(i[k:]) for k in range(n)]
        n_in0 = float(load.get('n_in', cfg.n_in_ref))
        t_out_eff = t_out
    else:  # motor — момент идёт вперёд через ступени с КПД (как spider_*)
        t_motor = float(load['T_in'])
        sun_T = []
        t_in = t_motor
        for k in range(n):
            sun_T.append(t_in)
            t_in = t_in * i[k] * cfg.eta_stage
        n_in0 = float(load.get('n_in', cfg.n_in_ref))
        t_out_eff = t_motor * i_total * cfg.eta_stage**n

    # Скорости: опорная входная раскручивается вперёд по водилам.
    sun_speed_rel = []
    n_in = n_in0
    for k in range(n):
        omega_rel, omega_c = planet_relative_speed(n_in, i[k])
        sun_speed_rel.append(omega_rel)
        n_in = omega_c

    return {
        'i': i, 'i_total': i_total, 'n_stages': n,
        'sun_torque': sun_T, 'sun_speed_rel': sun_speed_rel,
        't_out': t_out_eff, 'n_out': n_in0 / i_total,
        'T_in_equiv': sun_T[0],
    }


# ============================================================================
#  Габариты
# ============================================================================
def outer_diameter(stages, cfg):
    return max(s['m'] * s['z_ring'] + 2 * cfg.ring_wall for s in stages)


def axial_length(stages):
    return sum(s['b'] for s in stages) + 15 * len(stages)


# ============================================================================
#  Главный драйвер расчёта
# ============================================================================
def compute(stages, load, cfg):
    """Полный расчёт коробки.

    ``stages`` — список нормализованных dict (ключи m,b,z_sun,z_planet,z_ring,
    n_planets,x_sun,x_planet,x_ring,mat_sun,mat_planet,mat_ring).
    ``load``   — dict: {'mode':'output','T_out_req':..} либо
                 {'mode':'motor','T_in':..,'n_in':..}.
    Возвращает «сырой» result-dict (без форматирования отчёта).
    """
    stages = resolve_planets(stages, cfg)   # авто-число саттелитов, если не задано
    geo_err, geo_warn = validate_geometry(stages)
    kin = _stage_loads(stages, load, cfg)

    result = {
        'i': kin['i'], 'i_total': kin['i_total'], 'n_stages': kin['n_stages'],
        't_out': kin['t_out'], 'n_out': kin['n_out'],
        'T_in_equiv': kin['T_in_equiv'],
        'geometry': {'valid': not geo_err, 'errors': geo_err,
                     'warnings': geo_warn},
        'stages': [],
    }
    if geo_err:
        # Геометрически невалидно — прочность не считаем (как в spider_*).
        return result

    for k, s in enumerate(stages):
        m = s['m']
        n_sat = s['n_planets']
        r_sun = m * s['z_sun'] / 2.0
        sun_T = kin['sun_torque'][k]
        t_mesh = sun_T / n_sat
        f_t = sun_T * 1000.0 / (n_sat * r_sun)

        sp = run_external_pair(
            name=f'__s{k + 1}__',
            m=m, z_pinion=s['z_sun'], z_wheel=s['z_planet'], b=s['b'],
            torque_pinion_nm=t_mesh, speed_pinion_rpm=kin['sun_speed_rel'][k],
            mat_pinion=s['mat_sun'], mat_wheel=s['mat_planet'], cfg=cfg,
            x_pinion=s['x_sun'], x_wheel=s['x_planet'])
        pr = planet_ring_check(
            name=f'__pr{k + 1}__',
            m=m, z_planet=s['z_planet'], z_ring=s['z_ring'], b=s['b'],
            force_t_n=f_t, mat_planet=s['mat_planet'], mat_ring=s['mat_ring'],
            x_planet=s['x_planet'], x_ring=s.get('x_ring', 0.0),
            ka=cfg.Ka, t_amb=cfg.T_amb, alpha_deg=cfg.alpha_deg)

        result['stages'].append({
            'stage': k + 1, 'i': kin['i'][k], 'n_planets': n_sat,
            'sun_torque': sun_T, 'sun_speed_rel': kin['sun_speed_rel'][k],
            'sp': sp, 'pr': pr,
        })

    return result
