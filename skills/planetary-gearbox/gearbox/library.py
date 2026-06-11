"""Библиотека готовых коробок: кэш расчётов + поиск.

Единственный источник индекса — кэш расчётов скила ``designs/*.json`` (формат
:func:`spec.raw_to_cache`). Исторические наборы «колено»/«бедро» однократно
пересчитаны в этот кэш актуальной физикой (VDI 2736 + фиксы), поэтому отдельные
legacy-источники (``REPORT/SPIDER_KNEE/_data``, ``spider_thigh_results.json``)
больше не читаются.

Все записи приводятся к единому компактному виду для фильтрации; габариты
пересчитываются одной формулой (стенка венца 6 мм, L = Σb + 15·n).
"""

import glob as _glob
import json
import os

from . import engine

REPO_ROOT = engine.REPO_ROOT
SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DESIGNS_DIR = os.path.join(SKILL_DIR, 'designs')

_VDI_SF, _VDI_SH = 2.0, 1.4   # пороги VDI 2736 для отметки pass


# ============================================================================
#  Извлечение запасов из разных форматов результата
# ============================================================================
def _lists_from_stage_results(stage_results):
    """SF/SH/SH_pess из списка ступеней (формат кэша расчётов)."""
    sf, sh, shp = [], [], []
    for st in stage_results:
        sp, pr = st['sp'], st['pr']
        sf += list(sp['SF']); sh += list(sp['SH']); shp.append(sp['SH_pess'])
        sf += [pr['sf_p'], pr['sf_r']]
        sh += [pr['sh_p'], pr['sh_r']]
        shp += [pr['sh_p'], pr['sh_r']]
    return sf, sh, shp


def _briefs_from_stages(stages):
    return [{
        'm': s['m'], 'b': s['b'], 'z_sun': s['z_sun'],
        'z_planet': s['z_planet'], 'z_ring': s['z_ring'],
        'n_planets': s['n_planets'], 'mat_sun': s['mat_sun'],
        'mat_planet': s['mat_planet'], 'mat_ring': s['mat_ring'],
    } for s in stages]


def _dims(briefs):
    d = max(b['m'] * b['z_ring'] + 8.0 for b in briefs)   # стенка 4 мм (2·ring_wall)
    l = sum(b['b'] for b in briefs) + 15 * len(briefs)
    return round(d, 2), round(l, 1)


def _materials(briefs):
    s = set()
    for b in briefs:
        s |= {b['mat_sun'], b['mat_planet'], b['mat_ring']}
    return sorted(s)


def _entry(design_id, source, briefs, sf, sh, shp, i_total, t_out, n_out, name):
    d, l = _dims(briefs)
    sf_min, sh_min, shp_min = round(min(sf), 3), round(min(sh), 3), round(min(shp), 3)
    return {
        'id': design_id, 'source': source, 'name': name,
        'n_stages': len(briefs),
        'i_total': round(float(i_total), 3),
        'T_out_Nm': round(float(t_out), 2) if t_out is not None else None,
        'n_out_rpm': round(float(n_out), 3) if n_out is not None else None,
        'D_outer_mm': d, 'L_axial_mm': l,
        'SF_min': sf_min, 'SH_min': sh_min, 'SH_pess_min': shp_min,
        'pass_vdi': sf_min >= _VDI_SF and sh_min >= _VDI_SH,
        'materials': _materials(briefs),
        'stages': briefs,
    }


# ============================================================================
#  Загрузка источников
# ============================================================================
def _load_calc(index):
    if not os.path.isdir(DESIGNS_DIR):
        return
    for path in _glob.glob(os.path.join(DESIGNS_DIR, '*.json')):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                c = json.load(f)
            raw = c['raw']
            briefs = _briefs_from_stages(c['stages'])
            if raw['stages']:
                sf, sh, shp = _lists_from_stage_results(raw['stages'])
            else:                       # геометрически невалидно — пропускаем
                continue
            e = _entry(c['spec_hash'], 'calc', briefs, sf, sh, shp,
                       raw['i_total'], raw.get('t_out'), raw.get('n_out'),
                       (c.get('meta') or {}).get('name'))
            index[('calc', e['id'])] = e
        except (OSError, ValueError, KeyError, TypeError):
            continue


def load_index(sources=('calc',)):
    """Собрать индекс готовых коробок из кэша расчётов (``designs/``).

    Параметр ``sources`` сохранён для обратной совместимости вызовов; реальный
    источник один — ``calc``.
    """
    index = {}
    if 'calc' in sources:
        _load_calc(index)
    return list(index.values())


# ============================================================================
#  Поиск
# ============================================================================
_SORT_KEYS = {
    'd': lambda e: (e['D_outer_mm'], e['L_axial_mm']),
    'l': lambda e: (e['L_axial_mm'], e['D_outer_mm']),
    'sh': lambda e: -e['SH_min'],
    'sf': lambda e: -e['SF_min'],
    'i': lambda e: e['i_total'],
    't_out': lambda e: -(e['T_out_Nm'] or 0),
}


def search(entries=None, *, i=None, i_tol=0.5, n_stages=None,
           t_out_min=None, d_max=None, l_max=None,
           material=None, materials_subset=None,
           sf_min=None, sh_min=None, sh_pess_min=None,
           passing_only=False, sort='d', top=20):
    """Отфильтровать и отсортировать готовые коробки.

    material        — коробка ДОЛЖНА содержать этот материал (в любом слоте);
    materials_subset — коробка использует ТОЛЬКО материалы из этого множества.
    """
    if entries is None:
        entries = load_index()
    mat = material.upper() if material else None
    subset = {m.upper() for m in materials_subset} if materials_subset else None
    res = []
    for e in entries:
        if i is not None and abs(e['i_total'] - i) > i_tol:
            continue
        if n_stages is not None and e['n_stages'] != n_stages:
            continue
        if t_out_min is not None and (e['T_out_Nm'] or 0) < t_out_min:
            continue
        if d_max is not None and e['D_outer_mm'] > d_max:
            continue
        if l_max is not None and e['L_axial_mm'] > l_max:
            continue
        if sf_min is not None and e['SF_min'] < sf_min:
            continue
        if sh_min is not None and e['SH_min'] < sh_min:
            continue
        if sh_pess_min is not None and e['SH_pess_min'] < sh_pess_min:
            continue
        if mat and mat not in e['materials']:
            continue
        if subset and not set(e['materials']).issubset(subset):
            continue
        if passing_only and not e['pass_vdi']:
            continue
        res.append(e)
    res.sort(key=_SORT_KEYS.get(sort, _SORT_KEYS['d']))
    return res[:top] if top else res


def best_by_material(entries=None, *, per_group=3, sort='d',
                     passing_only=True, group_by='materials', **filters):
    """Лучшие коробки ПО ОДНОЙ (или per_group) на каждый материал/комбинацию.

    Поверх :func:`search`: отбирает по фильтрам (обычно ``t_out_min`` — требуемый
    выходной момент), сортирует по ``sort`` (по умолч. Ø — компактность), затем
    в каждой материальной группе оставляет per_group лучших. Каждой записи
    добавляется поле ``group`` (метка материала).

    group_by='materials' — группа = полный набор материалов коробки (моно/смесь);
    group_by='primary'   — группа = материал солнца 1-й ступени (упрощённо).
    """
    pool = search(entries=entries, sort=sort, passing_only=passing_only,
                  top=0, **filters)
    counts, out = {}, []
    for e in pool:
        if group_by == 'primary':
            key = e['stages'][0]['mat_sun'] if e.get('stages') else '?'
        else:
            key = '+'.join(e['materials'])
        if counts.get(key, 0) < per_group:
            counts[key] = counts.get(key, 0) + 1
            out.append({**e, 'group': key})
    return out


# ============================================================================
#  Кэш новых расчётов
# ============================================================================
def cache_path(spec_hash):
    return os.path.join(DESIGNS_DIR, f'{spec_hash}.json')


def load_cached(spec_hash):
    path = cache_path(spec_hash)
    if not os.path.isfile(path):
        return None
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def save_cache(cache_record):
    os.makedirs(DESIGNS_DIR, exist_ok=True)
    with open(cache_path(cache_record['spec_hash']), 'w', encoding='utf-8') as f:
        json.dump(cache_record, f, ensure_ascii=False, indent=2)
