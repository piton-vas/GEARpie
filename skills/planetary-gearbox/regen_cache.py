"""Пересборка кэша designs/ под новый операционный режим.

Каждую коробку пересчитываем текущим движком с:
  * lubrication = grease (раньше весь кэш был «насухую»);
  * cycles      = 1e7    (единый расчётный ресурс для ОБЕИХ пар; раньше
                          внешняя пара брала 1e8, внутренняя — 1e6).
Геометрия ступеней и операционный контекст (Ka, T_amb, eta, n_in, alpha,
режим/моменты) сохраняются из старой записи.

Смазка≠dry и cycles≠1e8 входят в physics_hash → у всех коробок НОВЫЕ хэши
(ID). Поэтому: пишем новые файлы, затем удаляем старые dry-файлы.

Запуск:  python regen_cache.py          (выполнить)
         python regen_cache.py --dry    (только показать сводку, не писать)
"""

import json
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
NEW_LUBE = 'grease'
NEW_CYCLES = 1e7
VDI_SF, VDI_SH = 2.0, 1.4


def _mins(raw):
    """min SF / min SH по всем зацеплениям (как spec._safety_entries). None — без прочности."""
    sf, sh = [], []
    for st in raw.get('stages', []):
        sp, pr = st['sp'], st['pr']
        sf += [sp['SF'][0], sp['SF'][1], pr['sf_p'], pr['sf_r']]
        sh += [sp['SH'][0], sp['SH'][1], pr['sh_p'], pr['sh_r']]
    return (min(sf), min(sh)) if sf else (None, None)


def _passes(raw):
    sf, sh = _mins(raw)
    return sf is not None and sf >= VDI_SF and sh >= VDI_SH


def main(dry_run=False):
    files = sorted(f for f in os.listdir(DESIGNS) if f.endswith('.json'))
    new_records = {}          # new_hash -> (record, raw)
    old_to_new = {}           # old_filename -> new_hash
    errors = []
    flips = []                # (name, old_pass, new_pass, old SF/SH, new SF/SH)

    for idx, fname in enumerate(files, 1):
        path = os.path.join(DESIGNS, fname)
        with open(path, 'r', encoding='utf-8') as f:
            cached = json.load(f)
        meta = cached.get('meta') or {}
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
                lubrication=NEW_LUBE,
                cycles=NEW_CYCLES,
            )
            h = spec.physics_hash(stages, load, cfg)
            raw = engine.compute(stages, load, cfg)
            record = spec.raw_to_cache(stages, load, cfg, raw, h, meta)

            old_pass = _passes(cached.get('raw', {}))
            new_pass = _passes(raw)
            if old_pass != new_pass:
                osf, osh = _mins(cached.get('raw', {}))
                nsf, nsh = _mins(raw)
                flips.append((meta.get('name') or fname[:-5], old_pass, new_pass,
                              osf, osh, nsf, nsh))

            new_records[h] = record
            old_to_new[fname] = h
        except Exception as e:  # noqa: BLE001
            errors.append((fname, f'{type(e).__name__}: {e}'))
        if idx % 50 == 0:
            print(f'... {idx}/{len(files)}', flush=True)

    print(f'\nВсего обработано: {len(files)}; ошибок пересчёта: {len(errors)}')
    print(f'Новых уникальных записей (по новым хэшам): {len(new_records)}')
    n_old_pass = sum(1 for f in files
                     if _passes(json.load(open(os.path.join(DESIGNS, f),
                                                encoding='utf-8')).get('raw', {})))
    n_new_pass = sum(1 for r in new_records.values() if _passes(r['raw']))
    print(f'PASS (VDI 2736) было: {n_old_pass} (dry/смешанный NL) -> стало: '
          f'{n_new_pass} (grease, NL=1e7)')
    print(f'Перевернулось PASS/FAIL: {len(flips)}')
    for name, op, nps, osf, osh, nsf, nsh in sorted(flips, key=lambda x: x[0])[:60]:
        arrow = 'PASS->FAIL' if op and not nps else 'FAIL->PASS'
        def fmt(v):
            return f'{v:.2f}' if isinstance(v, (int, float)) else '—'
        print(f'  {arrow}  {str(name)[:40]:<42} '
              f'SF {fmt(osf)}→{fmt(nsf)}  SH {fmt(osh)}→{fmt(nsh)}')
    if len(flips) > 60:
        print(f'  ... и ещё {len(flips) - 60}')
    if errors:
        print('\nОшибки пересчёта (старый файл сохранён):')
        for fn, err in errors[:20]:
            print(f'  {fn}: {err}')

    if dry_run:
        print('\n[--dry] Файлы НЕ изменены.')
        return

    # Пишем новые файлы
    for h, record in new_records.items():
        with open(os.path.join(DESIGNS, f'{h}.json'), 'w', encoding='utf-8') as f:
            json.dump(record, f, ensure_ascii=False, indent=2)
    # Удаляем старые dry-файлы, успешно пересчитанные в новый хэш
    new_names = set(new_records.keys())
    removed = 0
    for old_fname, new_h in old_to_new.items():
        old_h = old_fname[:-5]
        if old_h != new_h and old_h not in new_names:
            try:
                os.remove(os.path.join(DESIGNS, old_fname))
                removed += 1
            except OSError:
                pass
    print(f'\nЗаписано новых файлов: {len(new_records)}; удалено старых dry: {removed}')
    total = len([f for f in os.listdir(DESIGNS) if f.endswith('.json')])
    print(f'Итого файлов в designs/: {total}')


if __name__ == '__main__':
    main(dry_run='--dry' in sys.argv)
