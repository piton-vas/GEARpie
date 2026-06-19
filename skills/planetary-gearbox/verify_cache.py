"""Сверка кэша designs/: пересчёт каждой коробки текущим движком.

Для каждого JSON в designs/:
  1. восстановить stages/load/cfg из сохранённого кэша;
  2. проверить стабильность physics_hash (имя файла == пересчитанный хэш);
  3. пересчитать engine.compute и сравнить min SF / min SH / SH_pess
     со складированным raw.

Выход: verify_cache_report.json + сводка в stdout.
"""

import json
import math
import os
import sys

sys.dont_write_bytecode = True
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from gearbox import engine, spec  # noqa: E402

DESIGNS = os.path.join(HERE, 'designs')


def safety_mins(raw):
    """min SF / min SH по всем зацеплениям (как spec._safety_entries)."""
    sf, sh = [], []
    for st in raw['stages']:
        sp_, pr = st['sp'], st['pr']
        sf += [sp_['SF'][0], sp_['SF'][1], pr['sf_p'], pr['sf_r']]
        sh += [sp_['SH'][0], sp_['SH'][1], pr['sh_p'], pr['sh_r']]
    return (min(sf), min(sh)) if sf else (None, None)


def ext_mins(raw):
    """min SF / min SH только по внешним парам (sun-planet) — их затронул фикс Ka."""
    sf = [x for st in raw['stages'] for x in st['sp']['SF']]
    sh = [x for st in raw['stages'] for x in st['sp']['SH']]
    return (min(sf), min(sh)) if sf else (None, None)


def main():
    files = sorted(f for f in os.listdir(DESIGNS) if f.endswith('.json'))
    report, n_hash_bad, n_stale, n_err = [], 0, 0, 0
    for idx, fname in enumerate(files, 1):
        path = os.path.join(DESIGNS, fname)
        with open(path, 'r', encoding='utf-8') as f:
            cached = json.load(f)
        entry = {'file': fname, 'name': (cached.get('meta') or {}).get('name')}
        try:
            stages = cached['stages']
            load = dict(cached['load'])
            c = cached.get('cfg', {})
            cfg = engine.Config(
                Ka=float(c.get('Ka', 1.3)),
                T_amb=float(c.get('T_amb', 25.0)),
                eta_stage=float(c.get('eta_stage', 0.9)),
                n_in_ref=float(c.get('n_in_ref', 150.0)),
                alpha_deg=float(c.get('alpha_deg', 20.0)),
                # старый кэш считался всухую и поля lubrication не имел → 'dry',
                # чтобы пересчёт воспроизводил сохранённые SF/SH без расхождений.
                lubrication=str(c.get('lubrication', 'dry')),
                # cycles появился позже: в старом кэше поля нет → дефолт 1e8.
                cycles=float(c.get('cycles', engine.DESIGN_CYCLES_DEFAULT)),
            )
            h = spec.physics_hash(stages, load, cfg)
            entry['hash_stored'] = cached.get('spec_hash')
            entry['hash_recalc'] = h
            entry['hash_ok'] = (h == fname[:-5] == cached.get('spec_hash'))
            if not entry['hash_ok']:
                n_hash_bad += 1

            old_raw = cached['raw']
            if not old_raw.get('stages'):
                entry['note'] = 'геометрия невалидна — прочности нет'
                report.append(entry)
                continue
            new_raw = engine.compute(stages, load, cfg)
            for tag, r in (('old', old_raw), ('new', new_raw)):
                s_all = safety_mins(r)
                s_ext = ext_mins(r)
                entry[f'{tag}_SF'] = round(s_all[0], 4)
                entry[f'{tag}_SH'] = round(s_all[1], 4)
                entry[f'{tag}_SF_ext'] = round(s_ext[0], 4)
                entry[f'{tag}_SH_ext'] = round(s_ext[1], 4)
            entry['stale'] = (abs(entry['old_SF'] - entry['new_SF']) > 5e-3 or
                              abs(entry['old_SH'] - entry['new_SH']) > 5e-3)
            # ожидаемое соотношение для дофиксового кэша: old/new = Ka (SF), √Ka (SH)
            ka = cfg.Ka
            entry['ratio_SF_ext'] = round(entry['old_SF_ext'] / entry['new_SF_ext'], 4)
            entry['ratio_SH_ext'] = round(entry['old_SH_ext'] / entry['new_SH_ext'], 4)
            entry['matches_Ka_pattern'] = (
                entry['stale'] and
                abs(entry['ratio_SF_ext'] - ka) < 0.02 and
                abs(entry['ratio_SH_ext'] - math.sqrt(ka)) < 0.02)
            if entry['stale']:
                n_stale += 1
        except Exception as e:  # noqa: BLE001 — отчёт по всем, падать нельзя
            entry['error'] = f'{type(e).__name__}: {e}'
            n_err += 1
        report.append(entry)
        if idx % 25 == 0:
            print(f'... {idx}/{len(files)}', flush=True)

    out = os.path.join(HERE, 'verify_cache_report.json')
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=1)

    print(f'Всего: {len(files)}; хэш не сошёлся: {n_hash_bad}; '
          f'устаревших (SF/SH разошлись): {n_stale}; ошибок: {n_err}')
    stale = [e for e in report if e.get('stale')]
    if stale:
        print('\nУстаревшие (old → new, по всем зацеплениям):')
        for e in stale[:40]:
            print(f"  {e['file'][:20]:<22} {str(e.get('name'))[:34]:<36} "
                  f"SF {e['old_SF']:>7.3f}→{e['new_SF']:>7.3f}  "
                  f"SH {e['old_SH']:>6.3f}→{e['new_SH']:>6.3f}  "
                  f"Ka-паттерн: {'да' if e['matches_Ka_pattern'] else 'НЕТ'}")
        if len(stale) > 40:
            print(f'  ... и ещё {len(stale) - 40}')


if __name__ == '__main__':
    main()
