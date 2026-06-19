"""Контракт ввода/вывода: нормализация spec, хэш для кэша, сборка отчёта.

Внешняя схема ввода (JSON) — человекочитаемая, см. SKILL.md. Здесь она
приводится к внутреннему виду движка (:mod:`engine`) и проверяется.
"""

import hashlib
import json
import math

from . import engine, catalog

_SLOTS = ('sun', 'planet', 'ring')


class SpecError(ValueError):
    """Ошибка во входной спецификации (понятное сообщение для агента)."""


# ============================================================================
#  Нормализация и валидация ввода
# ============================================================================
def _resolve_material(stage, spec, slot, idx):
    """Материал слота: mat_<slot> → stage.material → spec.material."""
    m = (stage.get(f'mat_{slot}')
         or stage.get('material')
         or spec.get('material'))
    if not m:
        raise SpecError(
            f"ступень {idx}: не задан материал слота '{slot}' "
            f"(укажите mat_{slot}, либо stage.material, либо верхний material)")
    m = str(m).upper()
    if m not in catalog.material_names():
        raise SpecError(
            f"ступень {idx}: неизвестный материал {m!r}. "
            f"Доступны: {', '.join(catalog.material_names())}")
    return m


def _req_num(stage, key, idx, positive=True, integer=False):
    if key not in stage:
        raise SpecError(f"ступень {idx}: не задан обязательный параметр '{key}'")
    val = stage[key]
    if not isinstance(val, (int, float)) or isinstance(val, bool):
        raise SpecError(f"ступень {idx}: '{key}' должен быть числом, получено {val!r}")
    if integer and int(val) != val:
        raise SpecError(f"ступень {idx}: '{key}' должен быть целым, получено {val!r}")
    if positive and val <= 0:
        raise SpecError(f"ступень {idx}: '{key}' должен быть > 0, получено {val!r}")
    return int(val) if integer else float(val)


def normalize_stage(stage, spec, idx):
    s = {
        'm': _req_num(stage, 'm', idx),
        'b': _req_num(stage, 'b', idx),
        'z_sun': _req_num(stage, 'z_sun', idx, integer=True),
        'z_planet': _req_num(stage, 'z_planet', idx, integer=True),
        'z_ring': _req_num(stage, 'z_ring', idx, integer=True),
        # n_planets опционально: None → движок подберёт максимум, что влезает
        'n_planets': (int(stage['n_planets'])
                      if stage.get('n_planets') is not None else None),
        'x_sun': float(stage.get('x_sun', 0.0)),
        'x_planet': float(stage.get('x_planet', 0.0)),
        'x_ring': float(stage.get('x_ring', 0.0)),
    }
    if s['z_ring'] <= s['z_planet']:
        raise SpecError(
            f"ступень {idx}: z_ring ({s['z_ring']}) должно быть > z_planet "
            f"({s['z_planet']}) для внутреннего зацепления")
    if s['n_planets'] is not None and s['n_planets'] < 2:
        raise SpecError(f"ступень {idx}: n_planets должно быть >= 2 (или не задавайте — подберём авто)")
    for slot in _SLOTS:
        s[f'mat_{slot}'] = _resolve_material(stage, spec, slot, idx)
    return s


def normalize(spec):
    """Привести входной spec к (stages, load, cfg, meta). Бросает SpecError."""
    if not isinstance(spec, dict):
        raise SpecError("spec должен быть объектом JSON")
    raw_stages = spec.get('stages')
    if not isinstance(raw_stages, list) or not raw_stages:
        raise SpecError("'stages' должен быть непустым списком ступеней")
    stages = [normalize_stage(st, spec, i + 1) for i, st in enumerate(raw_stages)]

    load = _normalize_load(spec.get('load', {}))

    lim = spec.get('limits', {}) or {}
    lube = str(lim.get('lubrication', 'grease')).lower()
    if lube not in engine.LUBRICATIONS:
        raise SpecError(
            f"неизвестная смазка {lube!r}; допустимо: "
            f"{', '.join(engine.LUBRICATIONS)}")
    cfg = engine.Config(
        Ka=float(load.pop('_Ka')),
        T_amb=float(lim.get('T_amb', 25.0)),
        eta_stage=float(load.pop('_eta_stage')),
        ring_wall=float(lim.get('ring_wall', 4.0)),
        SF_min=float(lim.get('SF_min', 2.0)),
        SH_min=float(lim.get('SH_min', 1.4)),
        D_max=(None if lim.get('D_max') in (None, '') else float(lim['D_max'])),
        n_in_ref=float(load.get('n_in', 150.0)),
        planet_clearance_min=float(lim.get('planet_clearance_min',
                                           engine.NEIGHBOR_CLEAR_WARN)),
        n_planets_cap=int(lim.get('n_planets_cap', 12)),
        alpha_deg=float(lim.get('alpha', 20.0)),
        lubrication=lube,
        cycles=_parse_cycles(lim),
    )
    meta = {'name': spec.get('name'), 'description': spec.get('description')}
    return stages, load, cfg, meta


def _parse_cycles(lim):
    """Расчётный ресурс limits.cycles (циклов нагружения) → cfg.cycles.

    Единая S-N точка для обеих пар. По умолчанию engine.DESIGN_CYCLES_DEFAULT
    (1e8). Должен быть > 0.
    """
    val = lim.get('cycles', lim.get('NL'))
    if val in (None, ''):
        return engine.DESIGN_CYCLES_DEFAULT
    try:
        c = float(val)
    except (TypeError, ValueError):
        raise SpecError(f"'cycles' должен быть числом, получено {val!r}")
    if c <= 0:
        raise SpecError(f"'cycles' должен быть > 0, получено {val!r}")
    return c


def _normalize_load(load):
    if not isinstance(load, dict):
        raise SpecError("'load' должен быть объектом")
    mode = str(load.get('mode', 'output')).lower()
    out = {'mode': mode}
    # Ka / eta — общие; прячем во временные ключи, их забирает Config.
    out['_Ka'] = float(load.get('Ka', 1.3))
    out['_eta_stage'] = float(load.get('eta_stage', 0.9))
    if 'n_in' in load and load['n_in'] is not None:
        out['n_in'] = float(load['n_in'])

    if mode == 'output':
        if 'T_out_req' not in load:
            raise SpecError("режим 'output' требует 'T_out_req' (Н·м)")
        t = float(load['T_out_req'])
        if t <= 0:
            raise SpecError("'T_out_req' должен быть > 0")
        out['T_out_req'] = t
    elif mode == 'motor':
        if load.get('motor'):
            mot = catalog.get_motor(str(load['motor']))
            out['T_in'] = float(mot['T_cont'])
            out.setdefault('n_in', float(mot['n_nom']))
            out['motor'] = str(load['motor'])
        elif 'T_in' in load:
            out['T_in'] = float(load['T_in'])
        else:
            raise SpecError(
                "режим 'motor' требует 'motor' (id пресета) либо 'T_in' (Н·м)")
        if out['T_in'] <= 0:
            raise SpecError("'T_in' должен быть > 0")
    else:
        raise SpecError(f"неизвестный режим нагрузки {mode!r} (output|motor)")
    return out


# ============================================================================
#  Канонический хэш (только физически значимые входы → ключ кэша)
# ============================================================================
_HASH_STAGE_KEYS = ('m', 'b', 'z_sun', 'z_planet', 'z_ring', 'n_planets',
                    'x_sun', 'x_planet', 'x_ring',
                    'mat_sun', 'mat_planet', 'mat_ring')


def physics_hash(stages, load, cfg):
    def r(x):
        return round(float(x), 6)

    canon = {
        # хэшируем только физически значимые поля (n_planets — уже разрешённое,
        # см. engine.resolve_planets; производные поля не включаем)
        'stages': [
            {k: (r(s[k]) if isinstance(s.get(k), float) else s.get(k))
             for k in _HASH_STAGE_KEYS}
            for s in stages
        ],
        'load': {
            'mode': load['mode'],
            'T_out_req': r(load['T_out_req']) if load['mode'] == 'output' else None,
            'T_in': r(load['T_in']) if load['mode'] == 'motor' else None,
            'n_in': r(load.get('n_in', cfg.n_in_ref)),
            'Ka': r(cfg.Ka),
            'eta_stage': r(cfg.eta_stage),
            'T_amb': r(cfg.T_amb),
        },
    }
    # α включаем в хэш только при нестандартном значении — иначе кэш α=20° остаётся
    # совместим с ранее посчитанными коробками (где поля alpha не было).
    if abs(cfg.alpha_deg - 20.0) > 1e-9:
        canon['load']['alpha_deg'] = r(cfg.alpha_deg)
    # Расчётный ресурс включаем в хэш только при нестандартном значении — иначе
    # ключи кэша при дефолте (1e8) остаются совместимы с ранее посчитанными
    # коробками (где поля cycles не было).
    if abs(getattr(cfg, 'cycles', engine.DESIGN_CYCLES_DEFAULT)
           - engine.DESIGN_CYCLES_DEFAULT) > 1e-3:
        canon['load']['cycles'] = r(cfg.cycles)
    # Смазку включаем в хэш только при != 'dry': старый кэш считался всухую и поля
    # lubrication не имел — его хэши остаются стабильными, а смазанные расчёты
    # получают отдельные ключи (другая физика → другой результат).
    if getattr(cfg, 'lubrication', 'dry') != 'dry':
        canon['load']['lubrication'] = cfg.lubrication
    blob = json.dumps(canon, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(blob.encode('utf-8')).hexdigest()[:16]


# ============================================================================
#  Сборка человеко/машино-читаемого отчёта
# ============================================================================
def _safety_entries(raw):
    """Плоский список всех запасов: (metric, value, stage, mesh, member)."""
    sf, sh, sh_pess = [], [], []
    for st in raw['stages']:
        k = st['stage']
        sp, pr = st['sp'], st['pr']
        sf += [('SF', sp['SF'][0], k, 'sun-planet', 'sun'),
               ('SF', sp['SF'][1], k, 'sun-planet', 'planet'),
               ('SF', pr['sf_p'], k, 'planet-ring', 'planet'),
               ('SF', pr['sf_r'], k, 'planet-ring', 'ring')]
        sh += [('SH', sp['SH'][0], k, 'sun-planet', 'sun'),
               ('SH', sp['SH'][1], k, 'sun-planet', 'planet'),
               ('SH', pr['sh_p'], k, 'planet-ring', 'planet'),
               ('SH', pr['sh_r'], k, 'planet-ring', 'ring')]
        # SH_pess: для внешней пары — корректированный; для внутренней пара
        # материал-корректна по построению (sh_p/sh_r уже по своему материалу).
        sh_pess += [('SH', sp['SH_pess'], k, 'sun-planet', 'sun/planet'),
                    ('SH', pr['sh_p'], k, 'planet-ring', 'planet'),
                    ('SH', pr['sh_r'], k, 'planet-ring', 'ring')]
    return sf, sh, sh_pess


def _min_at(entries):
    metric, value, stage, mesh, member = min(entries, key=lambda e: e[1])
    return {'value': round(value, 3),
            'at': {'stage': stage, 'mesh': mesh, 'member': member}}


def _round_deep(x, nd=3):
    """Рекурсивное округление float'ов во вложенных dict/list (для отчёта)."""
    if isinstance(x, dict):
        return {k: _round_deep(v, nd) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_round_deep(v, nd) for v in x]
    if isinstance(x, float):
        return round(x, nd)
    return x


def build_report(stages, load, cfg, raw, spec_hash, meta, from_cache=False):
    n = raw['n_stages']
    d_outer = engine.outer_diameter(stages, cfg)
    l_axial = engine.axial_length(stages, cfg)

    report = {
        'spec_hash': spec_hash,
        'name': meta.get('name'),
        'from_cache': from_cache,
        'load': {
            'mode': load['mode'],
            'Ka': cfg.Ka, 'eta_stage': cfg.eta_stage, 'T_amb': cfg.T_amb,
            'n_in': load.get('n_in', cfg.n_in_ref), 'alpha_deg': cfg.alpha_deg,
            'lubrication': cfg.lubrication, 'cycles': cfg.cycles,
        },
        'ratio': {'per_stage': [round(x, 4) for x in raw['i']],
                  'total': round(raw['i_total'], 4)},
        'kinematics': {
            'T_out_Nm': round(raw['t_out'], 3),
            'n_out_rpm': round(raw['n_out'], 4),
            'T_in_equiv_Nm': round(raw['T_in_equiv'], 4),
            'eta_est': round(cfg.eta_stage ** n, 4),
        },
        'dimensions': {
            'D_outer_mm': round(d_outer, 2),
            'L_axial_mm': round(l_axial, 1),
            'by_stage': [
                {'stage': i + 1,
                 'D_ring_outer_mm': round(st['m'] * st['z_ring']
                                          + 2 * cfg.ring_wall, 2),
                 'b_mm': st['b'],
                 'n_planets': st.get('n_planets'),
                 'n_planets_max': st.get('n_planets_max'),
                 'n_planets_auto': st.get('n_planets_auto')}
                for i, st in enumerate(stages)
            ],
        },
        'geometry': raw['geometry'],
        'requirements': {},
        'stages': [],
    }
    if load['mode'] == 'output':
        report['load']['T_out_req_Nm'] = load['T_out_req']
    if load['mode'] == 'motor':
        report['load']['T_in_Nm'] = load['T_in']
        if 'motor' in load:
            report['load']['motor'] = load['motor']

    # --- требования ---
    req = report['requirements']
    if cfg.D_max is not None:
        req['D_max_mm'] = cfg.D_max
        req['D_ok'] = d_outer <= cfg.D_max
    if load['mode'] == 'output':
        req['T_out_req_Nm'] = load['T_out_req']
        req['T_out_ok'] = raw['t_out'] >= load['T_out_req'] - 1e-6

    # --- геометрия невалидна: возвращаем без прочности ---
    if not raw['geometry']['valid']:
        report['safety'] = None
        report['pass'] = False
        report['model_warnings'] = list(raw.get('model_warnings', []))
        report['note'] = ('Геометрически невалидно — расчёт прочности пропущен. '
                          'См. geometry.errors.')
        return report

    # --- подробности по ступеням ---
    for st in raw['stages']:
        sg = stages[st['stage'] - 1]
        sp, pr = st['sp'], st['pr']
        report['stages'].append({
            'stage': st['stage'], 'i': round(st['i'], 4),
            'n_planets': sg['n_planets'],
            'n_planets_max': sg.get('n_planets_max'),
            'n_planets_auto': sg.get('n_planets_auto'),
            'planet_clearance_at_max_mm': sg.get('planet_clearance_at_max_mm'),
            'm': sg['m'], 'b': sg['b'],
            'z': {'sun': sg['z_sun'], 'planet': sg['z_planet'], 'ring': sg['z_ring']},
            'x': {'sun': sg['x_sun'], 'planet': sg['x_planet'], 'ring': sg['x_ring']},
            'd': {'sun': round(sg['m'] * sg['z_sun'], 2),
                  'planet': round(sg['m'] * sg['z_planet'], 2),
                  'ring': round(sg['m'] * sg['z_ring'], 2)},
            'materials': {'sun': sg['mat_sun'], 'planet': sg['mat_planet'],
                          'ring': sg['mat_ring']},
            'sun_torque_Nm': round(st['sun_torque'], 4),
            # b/m и прогиб зуба (VDI 2736-2; .get — совместимость со старым кэшем)
            'b_over_m': round(sg['b'] / sg['m'], 2),
            'deflection': _round_deep(st.get('deflection'), 4),
            'sun_planet': {
                'SigmaF_MPa': [round(x, 3) for x in sp['SigmaF']],
                'SF': [round(x, 3) for x in sp['SF']],
                'SigmaH_MPa': round(sp['SigmaH'], 3),
                'SH': [round(x, 3) for x in sp['SH']],
                'SH_pess': round(sp['SH_pess'], 3),
                'tooth_temp_C': _round_deep(sp.get('temps'), 1),
                'wear': _round_deep(sp.get('wear'), 6),
            },
            'planet_ring': {
                'F_t_N': round(pr['force_n'], 2), 'R_eq_mm': round(pr['r_eq'], 3),
                'SigmaF_MPa': {'planet': round(pr['sigma_p'], 3),
                               'ring': round(pr['sigma_r'], 3)},
                'SF': {'planet': round(pr['sf_p'], 3), 'ring': round(pr['sf_r'], 3)},
                'SigmaH_MPa': round(pr['sigma_h'], 3),
                'SH': {'planet': round(pr['sh_p'], 3), 'ring': round(pr['sh_r'], 3)},
                'tooth_temp_C': _round_deep(
                    {'flank': pr.get('temp_flank'), 'root': pr.get('temp_root')}
                    if pr.get('temp_flank') else None, 1),
            },
        })

    # --- сводка по запасам и слабому месту ---
    sf_e, sh_e, shp_e = _safety_entries(raw)
    sf_min = _min_at(sf_e)
    sh_min = _min_at(sh_e)
    shp_min = _min_at(shp_e)
    passed = (sf_min['value'] >= cfg.SF_min and sh_min['value'] >= cfg.SH_min)

    warnings = list(raw['geometry'].get('warnings', []))
    if 'model_warnings' in raw:
        warnings += list(raw['model_warnings'])
    else:
        # старый кэш (raw без model_warnings): b/m восстановимо из геометрии
        warnings += engine.bm_warnings(stages)
    if shp_min['value'] < cfg.SH_min <= sh_min['value']:
        warnings.append(
            f"SH_pess={shp_min['value']} < {cfg.SH_min}: для смешанной пары "
            f"материалов контактная прочность под вопросом "
            f"(ст.{shp_min['at']['stage']}, {shp_min['at']['mesh']}).")

    # governing — у кого наименьший относительный запас (value / порог)
    cand = [('SF', sf_min, cfg.SF_min), ('SH', sh_min, cfg.SH_min)]
    g_metric, g, g_thr = min(cand, key=lambda c: c[1]['value'] / c[2])
    report['safety'] = {
        'SF_min': sf_min, 'SH_min': sh_min, 'SH_pess_min': shp_min,
        'thresholds': {'SF_min': cfg.SF_min, 'SH_min': cfg.SH_min},
        'pass': passed,
        'governing': {
            'metric': g_metric, 'value': g['value'],
            'margin_ratio': round(g['value'] / g_thr, 3), **g['at'],
        },
        'warnings': warnings,
    }
    report['pass'] = bool(
        passed
        and req.get('D_ok', True)
        and req.get('T_out_ok', True))
    return report


def raw_to_cache(stages, load, cfg, raw, spec_hash, meta):
    """Что кладём в кэш: вход + сырой результат прочности (физика)."""
    return {
        'spec_hash': spec_hash,
        'meta': meta,
        'stages': stages,
        'load': {k: v for k, v in load.items() if not k.startswith('_')},
        'cfg': {'Ka': cfg.Ka, 'T_amb': cfg.T_amb, 'eta_stage': cfg.eta_stage,
                'n_in_ref': cfg.n_in_ref, 'alpha_deg': cfg.alpha_deg,
                'lubrication': cfg.lubrication, 'cycles': cfg.cycles},
        'raw': raw,
    }
