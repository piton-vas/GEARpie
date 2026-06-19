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
DESIGN_CYCLES_DEFAULT = 1e8  # расчётный ресурс по умолчанию, циклов (S-N точка σF/σH).
                             # Единый для ОБЕИХ пар (внешняя пара GEARpie тоже 1e8).
                             # Задаётся пользователем через limits.cycles.

B_OVER_M_MAX = 12.0         # VDI 2736-2: K=KA·KV·KHβ·KHα≈1…1.25 валидно при b/m ≤ 12
DEFLECTION_LIMIT = 0.07     # VDI 2736-2: прогиб вершины зуба λ ≤ 0.07·m
WEAR_LIMIT_FACTOR = 0.2     # ориентир допустимого линейного износа ≈ 0.2·m (VDI 2736-2)
WEAR_NL_REF = 1e6           # опорные циклы для публикации Wm в отчёте
SN_TEMP_MAX = 120.0         # S-N кривые VDI 2736-2 заданы до 120 °C (выше — кламп)

# Смазка → множитель к сухому μ в формуле температуры VDI 2736 (нагрев θ−θ0 ∝ μ).
# Сухой μ (dry_cof) = таблица CONTACT.HERTZ. Множители — консервативный край
# измеренного снижения трения смазкой (−60 % grease, −75 % oil; в лит-ре до −87 %).
LUBE_FRICTION_FACTOR = {'dry': 1.0, 'grease': 0.40, 'oil': 0.25}
# Смазка → множитель к сухому kw. VDI даёт kw только для POM/сталь и PBT/сталь
# (всухую); прочее — оценка из лит-ры. Снижение износа смазкой ~−85 % (grease) при
# достаточном PV, ~−95 % (oil); низкий PV для полиамида — отдельное предупреждение.
LUBE_WEAR_FACTOR = {'dry': 1.0, 'grease': 0.15, 'oil': 0.05}
LUBRICATIONS = tuple(LUBE_FRICTION_FACTOR.keys())
PV_GREASE_LOW = 10.0        # МПа·м/с — ниже консистентная смазка перестаёт снижать
                            # (а у полиамидов может УВЕЛИЧИВАТЬ) износ (лит-ра PA66)

# Пластики/металлы библиотеки — те же списки, что в VDI2736.LCC / CONTACT.HERTZ.
POLYMERS = ('POM', 'POM_C', 'PA66', 'PA6_CAST', 'PA6_CF', 'PA_CF',
            'PA6_PRINT', 'PA6_ANNEAL', 'PETG')
METALS = ('STEEL', 'ADI', 'D16T')
_PA_FAMILY = ('PA66', 'PA6_CAST', 'PA6_PRINT', 'PA6_ANNEAL', 'PA6_CF', 'PA_CF')
_POM_FAMILY = ('POM', 'POM_C')
_CARBON_FILLED = ('PA6_CF', 'PA_CF')


@dataclass
class Config:
    """Операционная точка и пороги приёмки (всё, что не геометрия ступеней)."""
    Ka: float = 1.3              # коэффициент нагрузки (умножает момент ДО напряжений)
    T_amb: float = 25.0          # окружающая температура, °C
    eta_stage: float = 0.9       # КПД одной ступени (для режима motor и оценки)
    ring_wall: float = 4.0       # радиальный припуск делит.Ø→наруж.Ø, мм (OD=m·z_ring+2·ring_wall).
                                 # backing за корнем зуба = ring_wall−1.25·m (m≤2.0 → ≥1.5 мм)
    stage_axial_gap: float = 30.0  # осевой конструктивный припуск на ступень, мм (водило, опоры
                                 # саттелитов, межступенчатые зазоры): L = Σb + n·stage_axial_gap
    SF_min: float = 2.0          # порог приёмки по изгибу (VDI 2736)
    SH_min: float = 1.4          # порог приёмки по контакту (VDI 2736)
    D_max: float = None          # лимит наружного Ø, мм (None = без лимита)
    n_in_ref: float = 150.0      # опорная входная скорость для кинематики VDI, об/мин
    planet_clearance_min: float = NEIGHBOR_CLEAR_WARN  # мин. зазор саттелитов для авто-подбора n, мм
    n_planets_cap: int = 12      # потолок при авто-подборе числа саттелитов
    alpha_deg: float = 20.0      # угол профиля/зацепления, град (стандарт 20; 25 — выше нагруз. способность,
                                 # σH ∝ 1/√(sin2α), но распорная сила ∝ tanα). При x=0 геометрия (соосность/
                                 # сборка/зазор) от α не зависит — α входит только в напряжения.
    lubrication: str = 'grease'  # 'dry' | 'grease' | 'oil' — задаёт μ в формуле нагрева
                                 # VDI 2736 (θ−θ0 ∝ μ) и kw износа. Смазка снижает нагрев
                                 # → у S-N материалов (POM/PA66/капролон) растут SF/SH.
    cycles: float = DESIGN_CYCLES_DEFAULT  # расчётный ресурс, циклов нагружения.
                                 # Точка на S-N кривой для σFlim/σHlim — ЕДИНАЯ для обеих
                                 # пар (солнце–саттелит и саттелит–венец). У S-N материалов
                                 # (POM/PA66/капролон) σ-предел при 1e6 на ~60% выше, чем при
                                 # 1e8 → ресурс прямо определяет запасы. У материалов с
                                 # константным σ (печатные пластики, POM_C, металлы) не влияет.


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


def sh_pessimistic(sh_code, mat_pinion, mat_wheel, t_amb=25.0, cycles=1e6,
                   t_wheel=None):
    """SH с учётом более слабого σHlim в смешанной паре материалов.

    VDI2736.LCC берёт σHP только по солнцу — для пары металл-пластик это
    переоценивает SH (реальный износ лимитируется пластиком). Для одинаковых
    материалов SH_pess == SH_код. t_amb — температура шестерни (или общая),
    t_wheel — температура колеса (None → как у шестерни).
    """
    s_lim_p = material_sigmaHlim(mat_pinion, t_amb, cycles)
    s_lim_w = material_sigmaHlim(
        mat_wheel, t_wheel if t_wheel is not None else t_amb, cycles)
    return sh_code * min(s_lim_p, s_lim_w) / s_lim_p


def dry_cof(mat1, mat2):
    """Сухой коэффициент трения пары — та же таблица, что CONTACT.HERTZ (GLUB=None).

    Дублируется здесь, потому что HERTZ считает CoF только внутри полного
    VDI-пайплайна, а внутренняя пара считается аналитически.
    """
    if mat1 == mat2 == 'POM':
        return 0.28
    if mat1 == mat2 == 'PA66':
        return 0.40
    if mat1 == mat2 and mat1 in ('PA6_CF', 'PA_CF'):
        return 0.30
    if mat1 in POLYMERS and mat2 in POLYMERS:
        return 0.30
    if (mat1 in POLYMERS and mat2 in METALS) or \
       (mat2 in POLYMERS and mat1 in METALS):
        return 0.20
    if mat1 == mat2 == 'STEEL':
        return 0.8
    return 0.30


def mesh_friction(mat1, mat2, lubrication='dry'):
    """Коэффициент трения пары с учётом смазки: μ_сухой × множитель смазки.

    Нагрев зуба в VDI 2736 линеен по μ (θ−θ0 ∝ Pvzp ∝ μ), поэтому смазка входит
    в ту же формулу через сниженный μ (подтверждено: «пересчёт θ с уменьшенным μ
    значительно улучшает совпадение с измерениями»). Сухой μ — таблица dry_cof
    (= CONTACT.HERTZ); множитель — :data:`LUBE_FRICTION_FACTOR`.
    """
    return dry_cof(mat1, mat2) * LUBE_FRICTION_FACTOR.get(lubrication, 1.0)


def wear_coefficient(mat1, mat2, lubrication='dry'):
    """Удельный коэффициент износа kw пары, мм³/(Н·м) — ОЦЕНКА.

    VDI 2736-2 публикует kw только для POM/сталь и PBT/сталь и только всухую;
    для полиамидов, печатных пластиков, пар пластик/пластик и для смазки данных
    в стандарте нет. Берём базовый сухой kw по классу пары (порядки из лит-ры) и
    множитель смазки (:data:`LUBE_WEAR_FACTOR`). Низкий PV для полиамида под
    консистентной смазкой — отдельная оговорка (см. compute → model_warnings).
    """
    if mat1 in _CARBON_FILLED or mat2 in _CARBON_FILLED:
        base = 2.0e-6          # углеволокно: низкий износ наполненного колеса
    elif mat1 in METALS or mat2 in METALS:
        base = 3.0e-6          # пластик/металл ≈ POM/сталь (VDI-диапазон 1–5e-6)
    elif mat1 in _POM_FAMILY and mat2 in _POM_FAMILY:
        base = 6.0e-6          # POM/POM
    else:
        base = 1.0e-5          # пары с полиамидом / прочее пластик-пластик — выше
    return base * LUBE_WEAR_FACTOR.get(lubrication, 1.0)


def bm_warnings(stages):
    """Предупреждения b/m > 12 по ступеням (применимость упрощения VDI 2736).

    Чистая геометрия (не зависит от нагрузки/прочности) — используется и в
    compute(), и как fallback для отчётов из старого кэша без model_warnings.
    """
    out = []
    for idx, s in enumerate(stages, 1):
        bm = s['b'] / s['m']
        if bm > B_OVER_M_MAX:
            out.append(
                f"ст.{idx}: b/m = {bm:.1f} > {B_OVER_M_MAX:g} — упрощение "
                f"K=KA·KV·KHβ·KHα≈1…1.25 (VDI 2736) вне области применимости: "
                f"широкое колесо работает не всей шириной (перекос/прогиб "
                f"валов) — реальные SF/SH ниже расчётных; предпочесть крупнее "
                f"модуль вместо ширины либо поднять Ka")
    return out


def tooth_deflection(f_t, b, e1, e2, beta=0.0):
    """VDI 2736-2: прогиб вершины зуба λ = 7.5·Ft/(b·cosβ)·(1/E1+1/E2), мм.

    Предел λ ≤ 0.07·m — иначе мягкий зуб «проседает» и зацепление выходит
    из эвольвентного контакта (интерференция, шум, рост локальной нагрузки).
    """
    return 7.5 * f_t / (b * math.cos(beta)) * (1.0 / e1 + 1.0 / e2)


def planet_relative_speed(omega_sun_abs, i_stage):
    omega_carrier = omega_sun_abs / i_stage
    return omega_sun_abs - omega_carrier, omega_carrier


# ============================================================================
#  Расчёт пар зацепления
# ============================================================================
def _eps_alpha_internal(m, z_planet, z_ring, x_planet, x_ring, alpha):
    """Коэффициент торцевого перекрытия внутренней пары (β=0), без клампа.

    εα = [√(ra_p²−rb_p²) + a_w·sin α_w − √(ra_r²−rb_r²)] / (π·m·cos α).
    εα < 1 — прерывистое зацепление: validate_stage даст предупреждение,
    потребители для Hv клампят к 1 сами.
    """
    rb_p = m * z_planet / 2.0 * math.cos(alpha)
    ra_p = m * (z_planet / 2.0 + 1.0 + x_planet)
    rb_r = m * z_ring / 2.0 * math.cos(alpha)
    ra_r = m * (z_ring / 2.0 - 1.0 + x_ring)  # вершина внутреннего венца — к центру
    aw = _aw_internal(m, z_ring, z_planet, x_ring, x_planet, alpha)
    cos_aw = m * (z_ring - z_planet) / 2.0 * math.cos(alpha) / aw
    alpha_w = math.acos(min(1.0, max(-1.0, cos_aw)))
    g_a = (math.sqrt(max(ra_p ** 2 - rb_p ** 2, 0.0)) + aw * math.sin(alpha_w)
           - math.sqrt(max(ra_r ** 2 - rb_r ** 2, 0.0)))
    return g_a / (math.pi * m * math.cos(alpha))


def _ext_mesh_geometry(m, z1, z2, x1, x2, alpha):
    """Геометрия зацепления внешней пары (β=0): εα, ε1/ε2, активные длины профилей.

    lFl — длина активного участка эвольвенты (дуга от нижней точки контакта
    до вершины): между roll-координатами s_f и s_a дуга = (s_a²−s_f²)/(2·rb).
    Нужна среднему износу VDI 2736-2.
    """
    rb1 = m * z1 / 2.0 * math.cos(alpha)
    ra1 = m * (z1 / 2.0 + 1.0 + x1)
    rb2 = m * z2 / 2.0 * math.cos(alpha)
    ra2 = m * (z2 / 2.0 + 1.0 + x2)
    aw = _aw_external(m, z1, z2, x1, x2, alpha)
    cos_aw = m * (z1 + z2) / 2.0 * math.cos(alpha) / aw
    alpha_w = math.acos(min(1.0, max(-1.0, cos_aw)))
    t1 = math.sqrt(max(ra1 ** 2 - rb1 ** 2, 0.0))  # roll-координата вершины
    t2 = math.sqrt(max(ra2 ** 2 - rb2 ** 2, 0.0))
    line = aw * math.sin(alpha_w)                  # между точками касания базовых
    pbt = math.pi * m * math.cos(alpha)
    eps1 = (t1 - rb1 * math.tan(alpha_w)) / pbt
    eps2 = (t2 - rb2 * math.tan(alpha_w)) / pbt
    low1 = max(line - t2, 0.0)                     # нижняя активная точка колеса 1
    low2 = max(line - t1, 0.0)
    return {
        'eps_alpha': eps1 + eps2, 'eps1': eps1, 'eps2': eps2,
        'l_fl1': max((t1 ** 2 - low1 ** 2) / (2.0 * rb1), 1e-9),
        'l_fl2': max((t2 ** 2 - low2 ** 2) / (2.0 * rb2), 1e-9),
    }


def mean_wear_external(m, z1, z2, b, torque_mesh_nm, kw, x1=0.0, x2=0.0,
                       alpha=ALPHA_N, nl_ref=WEAR_NL_REF):
    """Средний линейный износ внешней пары по VDI 2736-2.

    Wm = Td·2π·NL·Hv·kw / (b·z·lFl) [мм] — на каждое колесо со СВОИМ
    моментом Td [Н·м], числом зубьев z и длиной активного профиля lFl [мм];
    kw [мм³/(Н·м)] → размерность сходится без переводов. Hv — Ohlendorf
    с точными ε1/ε2. N_to_limit — циклы данного колеса до ориентира 0.2·m
    (шестерня крутится в u раз быстрее колеса — циклы у каждого свои).
    """
    g = _ext_mesh_geometry(m, z1, z2, x1, x2, alpha)
    eps_a = max(g['eps_alpha'], 1.0)
    u = z2 / z1
    hv = math.pi * (u + 1.0) / (z1 * u) * (
        1.0 - eps_a + g['eps1'] ** 2 + g['eps2'] ** 2)
    hv = max(hv, 1e-9)
    w_lim = WEAR_LIMIT_FACTOR * m
    w_ref, n_lim = [], []
    for td_i, z_i, l_i in ((torque_mesh_nm, z1, g['l_fl1']),
                           (torque_mesh_nm * z2 / z1, z2, g['l_fl2'])):
        w_cycle = td_i * 2.0 * math.pi * hv * kw / (b * z_i * l_i)
        w_ref.append(w_cycle * nl_ref)
        n_lim.append(w_lim / w_cycle if w_cycle > 1e-18 else None)
    return {
        'NL_ref': nl_ref,
        'W_mean_mm': tuple(w_ref),     # износ за NL_ref циклов своего колеса
        'W_limit_mm': w_lim,
        'N_to_limit': tuple(n_lim),
        'kw_mm3_per_Nm': kw,
        'Hv': hv,
    }


def _internal_mesh_temps(m, z_planet, z_ring, b, force_t_n, mat_planet,
                         mat_ring, x_planet, x_ring, alpha,
                         n_planet_rel_rpm, t_amb, lubrication='dry'):
    """Температура зуба внутренней пары по VDI 2736-2.

    Та же формула и коэффициенты kθ, что в VDI2736.LCC для внешней пары:
    θ = T0 + Pvzp·kθ/(b·z·(vt·m)^0.75), открытый корпус (RLG=0).
    Pvzp = P·Hv·μ, Hv — Ohlendorf для внутреннего зацепления
    (π(u−1)/(z_p·u)·(1−εα+ε1²+ε2²), ε1≈ε2≈εα/2), μ — пара с учётом смазки
    (mesh_friction). Возвращает ({flank}, {root}, Pvzp Вт, CoF);
    без скорости — всё при t_amb.
    """
    flank = {'planet': t_amb, 'ring': t_amb}
    root = {'planet': t_amb, 'ring': t_amb}
    cof = mesh_friction(mat_planet, mat_ring, lubrication)
    if not n_planet_rel_rpm:
        return flank, root, 0.0, cof
    if mat_planet in METALS and mat_ring in METALS:
        # Модель нагрева VDI 2736 — для пластиков; чисто металлическая пара
        # остаётся при T_amb (σ-пределы металлов библиотеки от T не зависят),
        # иначе kθ «пластик/пластик» давал бы фиктивные сотни °C.
        return flank, root, 0.0, cof
    omega_p = abs(n_planet_rel_rpm) * 2.0 * math.pi / 60.0
    v_t = omega_p * (m * z_planet / 2.0) / 1000.0           # м/с на делительной
    if v_t < 1e-9:
        return flank, root, 0.0, cof
    eps_a = max(_eps_alpha_internal(m, z_planet, z_ring, x_planet, x_ring,
                                    alpha), 1.0)
    u = z_ring / z_planet
    hv = math.pi * (u - 1.0) / (z_planet * u) * (1.0 - eps_a + eps_a ** 2 / 2.0)
    pvzp = force_t_n * v_t * hv * cof                       # Вт на одно зацепление
    mixed = ((mat_planet in POLYMERS and mat_ring in METALS) or
             (mat_ring in POLYMERS and mat_planet in METALS))
    k_flank, k_root = (6300.0, 895.0) if mixed else (9000.0, 2148.0)
    vm = (v_t * m) ** 0.75
    for key, z in (('planet', z_planet), ('ring', z_ring)):
        flank[key] = t_amb + pvzp * k_flank / (b * z * vm)
        root[key] = t_amb + pvzp * k_root / (b * z * vm)
    return flank, root, pvzp, cof


def planet_ring_check(name, m, z_planet, z_ring, b, force_t_n,
                      mat_planet, mat_ring, x_planet=0.0, x_ring=0.0,
                      cycles=DESIGN_CYCLES_DEFAULT, ys=2.0, alpha_deg=20.0,
                      ka=1.3, t_amb=25.0, n_planet_rel_rpm=None,
                      lubrication='dry'):
    """Lewis (изгиб) + Hertz (контакт, выпукло-вогнутый) для внутренней пары.

    Если задана скорость саттелита относительно водила (n_planet_rel_rpm),
    σ-пределы берутся при температуре зуба по VDI 2736-2 (нагрев трением
    в зацеплении), иначе — при t_amb (прежнее поведение).
    """
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

    # Нагрев зуба (Pvzp — от номинальной силы, как в LCC) → σ-пределы при
    # температуре корня (изгиб) и фланка (контакт) каждой детали.
    t_flank, t_root, pvzp, cof = _internal_mesh_temps(
        m, z_planet, z_ring, b, force_t_n, mat_planet, mat_ring,
        x_planet, x_ring, alpha, n_planet_rel_rpm, t_amb, lubrication)
    s_f_lim_p = material_sigmaFlim(mat_planet, t_root['planet'], cycles)
    s_f_lim_r = material_sigmaFlim(mat_ring, t_root['ring'], cycles)
    s_h_lim_p = material_sigmaHlim(mat_planet, t_flank['planet'], cycles)
    s_h_lim_r = material_sigmaHlim(mat_ring, t_flank['ring'], cycles)

    return {
        'force_n': force_t_n,
        'd_planet': m * z_planet, 'd_ring': m * z_ring,
        'sigma_p': sigma_p, 'sigma_r': sigma_r,
        'sigma_lim_p': s_f_lim_p,
        'sigma_lim_r': s_f_lim_r,
        'sf_p': s_f_lim_p * ys / sigma_p,
        'sf_r': s_f_lim_r * ys / sigma_r,
        'sigma_h': sigma_h_pr,
        'sigma_h_lim_p': s_h_lim_p,
        'sigma_h_lim_r': s_h_lim_r,
        'sh_p': s_h_lim_p / sigma_h_pr,
        'sh_r': s_h_lim_r / sigma_h_pr,
        'r_eq': r_eq_pr,
        'temp_flank': t_flank, 'temp_root': t_root,
        'Pvzp_W': pvzp, 'CoF': cof,
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
    # cof_override — μ с учётом смазки: LCC посчитает TF/TR (а значит и σ-пределы,
    # SF/SH) сразу при выбранной смазке, без пост-коррекции (θ−θ0 ∝ μ).
    cof = mesh_friction(mat_pinion, mat_wheel, cfg.lubrication)
    gcontact = CONTACT.HERTZ(gmat, None, geo, gpath, gfs, 'AC', cof_override=cof)
    # NL=cfg.cycles — единый расчётный ресурс для S-N (тот же, что у внутренней пары).
    glcc = VDI2736.LCC(gmat, geo, gfs, gpath, gcontact, cfg.T_amb, cfg.Ka,
                       NL=cfg.cycles)
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
    # Температуры зуба VDI 2736-2 (уже использованы внутри LCC для σ-пределов):
    # фланк → контакт, корень → изгиб; (1) — шестерня/солнце, (2) — колесо.
    temps = {'flank': (float(glcc.TF1), float(glcc.TF2)),
             'root': (float(glcc.TR1), float(glcc.TR2))}
    if mat_pinion in METALS and mat_wheel in METALS:
        # Модель нагрева VDI 2736 — для пластиков; LCC посчитал чисто
        # металлической паре фиктивные θ (kθ «пластик/пластик» + CoF стали).
        # На SF/SH это не влияет (σ-пределы металлов от T не зависят) —
        # публикуем T_amb, чтобы не пугать выводом и warning'ом >120 °C.
        temps = {'flank': (cfg.T_amb, cfg.T_amb),
                 'root': (cfg.T_amb, cfg.T_amb)}
    # Средний износ VDI 2736-2: Wm = Td·2π·NL·Hv·kw/(b·z·lFl). Локальный
    # W_LOCAL из LCC не публикуем: fnx [Н/мм]·ζ·kw [мм³/(Н·м)] размерно
    # не мм и расходится со средней формулой на ~4 порядка (пессимизм).
    # kw — оценка по классу пары × смазка (VDI даёт только POM/сталь всухую).
    kw = wear_coefficient(mat_pinion, mat_wheel, cfg.lubrication)
    wear = mean_wear_external(m, z_pinion, z_wheel, b, torque_pinion_nm, kw,
                              x1=x_pinion, x2=x_wheel,
                              alpha=math.radians(cfg.alpha_deg))
    return {
        'SF': (float(glcc.SF1), float(glcc.SF2)),
        'SH': (sh_code, float(glcc.SH2)),
        'SigmaF': (float(glcc.SigmaF1), float(glcc.SigmaF2)),
        'SigmaH': float(glcc.SigmaH),
        # σHlim слабого материала при температуре ЕГО фланка (не t_amb) и при
        # том же расчётном ресурсе cfg.cycles, что и SH_код (раньше было 1e6).
        'SH_pess': sh_pessimistic(sh_code, mat_pinion, mat_wheel,
                                  temps['flank'][0], cycles=cfg.cycles,
                                  t_wheel=temps['flank'][1]),
        'temps': temps,
        'wear': wear,
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


def validate_stage(m, zs, zp, zr, xs, xp, n_sat, xr=0.0, alpha=ALPHA_N):
    """Проверка одной планетарной ступени → (errors, warnings, info).

    alpha — фактический угол профиля (рад): при x≠0 межосевое зависит от α,
    поэтому проверка соосности обязана считаться при том же α, что и расчёт.
    """
    errors, warnings = [], []

    aw_ext = _aw_external(m, zs, zp, xs, xp, alpha)
    aw_int = _aw_internal(m, zr, zp, xr, xp, alpha)
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

    # Коэффициент перекрытия: εα < 1 — прерывистое зацепление (удар на каждом
    # зубе). Раньше εα внутренней пары тихо клампился к 1 в расчёте нагрева.
    eps_ext = _ext_mesh_geometry(m, zs, zp, xs, xp, alpha)['eps_alpha']
    eps_int = _eps_alpha_internal(m, zp, zr, xp, xr, alpha)
    if eps_ext < 1.0:
        warnings.append(
            f"ПЕРЕКРЫТИЕ: εα(солнце–саттелит) = {eps_ext:.3f} < 1 — "
            f"зацепление прерывистое; больше зубьев / меньше α")
    if eps_int < 1.0:
        warnings.append(
            f"ПЕРЕКРЫТИЕ: εα(саттелит–венец) = {eps_int:.3f} < 1 — "
            f"зацепление прерывистое; больше зубьев / меньше α")

    info = {'aw_ext': aw_ext, 'aw_int': aw_int, 'coax_err': coax_err,
            'clearance': clearance, 'coaxial_ok': coaxial_ok,
            'assembly_ok': assembly_ok,
            'eps_alpha_ext': eps_ext, 'eps_alpha_int': eps_int}
    return errors, warnings, info


def planet_clearance(m, zp, xp, aw_ext, n):
    """Зазор между вершинами соседних саттелитов при n саттелитах, мм."""
    ra_planet = m * zp / 2.0 + m * (1.0 + xp)
    return 2.0 * aw_ext * math.sin(math.pi / n) - 2.0 * ra_planet


def max_planets(m, zs, zp, zr, xs, xp, min_clearance, n_cap=12, alpha=ALPHA_N):
    """Максимум саттелитов, которые геометрически влезают в ступень.

    Ограничения: (1) условие сборки `(z_s+z_r) % n == 0` (равные интервалы),
    (2) соседство — зазор вершин соседних саттелитов >= ``min_clearance``.
    Возвращает (n_best, info). Если ни одно n с зазором не проходит — берём
    минимальное число саттелитов (наибольший зазор), а проверка геометрии
    позже это пометит.
    """
    aw = _aw_external(m, zs, zp, xs, xp, alpha)
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
            cfg.n_planets_cap, alpha=math.radians(cfg.alpha_deg))
        s2['n_planets_max'] = nmax
        s2['planet_clearance_at_max_mm'] = round(info['clearance'], 3)
        if s2.get('n_planets'):           # задано явно — уважаем override
            s2['n_planets_auto'] = False
        else:
            s2['n_planets'] = nmax
            s2['n_planets_auto'] = True
        out.append(s2)
    return out


def validate_geometry(stages, alpha=ALPHA_N):
    """Проверка всех ступеней (list нормализованных dict) → (errors, warnings)."""
    errors, warnings = [], []
    for idx, s in enumerate(stages, 1):
        e, w, _ = validate_stage(
            m=s['m'], zs=s['z_sun'], zp=s['z_planet'], zr=s['z_ring'],
            xs=s['x_sun'], xp=s['x_planet'], n_sat=s['n_planets'],
            xr=s.get('x_ring', 0.0), alpha=alpha)
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


def axial_length(stages, cfg):
    return sum(s['b'] for s in stages) + cfg.stage_axial_gap * len(stages)


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
    geo_err, geo_warn = validate_geometry(stages, math.radians(cfg.alpha_deg))
    kin = _stage_loads(stages, load, cfg)

    # Предупреждения модели (применимость VDI 2736), не зависящие от прочности.
    model_warn = bm_warnings(stages)

    result = {
        'i': kin['i'], 'i_total': kin['i_total'], 'n_stages': kin['n_stages'],
        't_out': kin['t_out'], 'n_out': kin['n_out'],
        'T_in_equiv': kin['T_in_equiv'],
        'geometry': {'valid': not geo_err, 'errors': geo_err,
                     'warnings': geo_warn},
        'model_warnings': model_warn,
        'stages': [],
    }
    if geo_err:
        # Геометрически невалидно — прочность не считаем (как в spider_*).
        return result

    grease_low_pv = None    # (min PV, число затронутых ступеней) для одного предупр.

    for k, s in enumerate(stages):
        m = s['m']
        n_sat = s['n_planets']
        r_sun = m * s['z_sun'] / 2.0
        sun_T = kin['sun_torque'][k]
        t_mesh = sun_T / n_sat
        f_t = sun_T * 1000.0 / (n_sat * r_sun)
        # скорость саттелита отн. водила (для нагрева внутренней пары)
        n_p_rel = kin['sun_speed_rel'][k] * s['z_sun'] / s['z_planet']

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
            ka=cfg.Ka, t_amb=cfg.T_amb, alpha_deg=cfg.alpha_deg,
            n_planet_rel_rpm=n_p_rel, lubrication=cfg.lubrication,
            cycles=cfg.cycles)

        # Прогиб зуба (VDI 2736-2): λ = 7.5·Ft/(b·cosβ)·(1/E1+1/E2) ≤ 0.07·m.
        # Ft — НОМИНАЛЬНАЯ сила на зацепление (как в VDI), β=0; обе пары ступени.
        # E — при 25 °C (библиотека не задаёт E(T)); со смазкой зуб холоднее, что
        # делает приближение точнее, но для горячего зуба фактический λ выше.
        e_s = material_E(s['mat_sun'])
        e_p = material_E(s['mat_planet'])
        e_r = material_E(s['mat_ring'])
        lam_sp = tooth_deflection(f_t, s['b'], e_s, e_p)
        lam_pr = tooth_deflection(f_t, s['b'], e_p, e_r)
        lam_lim = DEFLECTION_LIMIT * m
        deflection = {
            'lambda_sun_planet_mm': lam_sp,
            'lambda_planet_ring_mm': lam_pr,
            'limit_mm': lam_lim,
            'ok': max(lam_sp, lam_pr) <= lam_lim,
        }
        if not deflection['ok']:
            worst = max(lam_sp, lam_pr)
            mesh = 'sun-planet' if lam_sp >= lam_pr else 'planet-ring'
            model_warn.append(
                f"ст.{k + 1}: прогиб зуба λ = {worst:.3f} мм > 0.07·m = "
                f"{lam_lim:.3f} мм ({mesh}) — мягкий зуб «проседает», зацепление "
                f"уходит с эвольвенты: крупнее модуль / жёстче материал / "
                f"меньше нагрузка на зацепление")

        # Температуры зуба: S-N данные VDI 2736 заданы до 120 °C (выше — кламп,
        # т.е. σ-пределы экстраполируются и формально перестают быть валидными).
        t_max = max(max(sp['temps']['flank']), max(sp['temps']['root']),
                    max(pr['temp_flank'].values()),
                    max(pr['temp_root'].values()))
        if t_max > SN_TEMP_MAX:
            model_warn.append(
                f"ст.{k + 1}: температура зуба {t_max:.0f} °C > "
                f"{SN_TEMP_MAX:g} °C — вне диапазона S-N данных VDI 2736; "
                f"нужны теплоотвод/смазка/ниже скорость")

        # Консистентная смазка + полиамид при низком PV: смазка может НЕ снижать
        # (а у PA — увеличивать) износ (лит-ра по PA66, pin-on-disc). PV ≈ pm·vt,
        # pm = σH·π/4 (среднее герцево), vt — окружная на делительной (оценка).
        # Копим минимум по коробке → одно сводное предупреждение после цикла.
        if cfg.lubrication == 'grease':
            w_sun = abs(kin['sun_speed_rel'][k]) * 2.0 * math.pi / 60.0
            vt_sp = w_sun * (m * s['z_sun'] / 2.0) / 1000.0
            vt_pr = abs(n_p_rel) * 2.0 * math.pi / 60.0 \
                * (m * s['z_planet'] / 2.0) / 1000.0
            for sigh, vt, pair in (
                    (sp['SigmaH'], vt_sp, (s['mat_sun'], s['mat_planet'])),
                    (pr['sigma_h'], vt_pr, (s['mat_planet'], s['mat_ring']))):
                if (pair[0] in _PA_FAMILY or pair[1] in _PA_FAMILY) and vt > 1e-9:
                    pv = sigh * math.pi / 4.0 * vt
                    if pv < PV_GREASE_LOW and (grease_low_pv is None
                                               or pv < grease_low_pv[0]):
                        grease_low_pv = (pv, k + 1)

        result['stages'].append({
            'stage': k + 1, 'i': kin['i'][k], 'n_planets': n_sat,
            'sun_torque': sun_T, 'sun_speed_rel': kin['sun_speed_rel'][k],
            'sp': sp, 'pr': pr, 'deflection': deflection,
            'b_over_m': s['b'] / m,
        })

    if grease_low_pv is not None:
        model_warn.append(
            f"консистентная смазка + полиамид при низком PV (мин ≈ "
            f"{grease_low_pv[0]:.1f} МПа·м/с в ст.{grease_low_pv[1]}, "
            f"<{PV_GREASE_LOW:g}) — смазка может НЕ снижать (для PA даже "
            f"увеличивать) износ; проверить испытанием либо рассмотреть "
            f"масло/сухой ход")

    return result
