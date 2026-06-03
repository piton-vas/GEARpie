#!/usr/bin/env python3
"""CLI планетарной коробки — переносимый движок для любого LLM-агента.

Подкоманды:
    calc       — рассчитать коробку по spec (JSON), вернуть запасы/слабое место/габарит
    search     — найти готовые коробки в библиотеке по фильтрам
    materials  — список доступных материалов
    motors     — список моторов-пресетов (для режима нагрузки 'motor')

Вывод по умолчанию — JSON в stdout (машиночитаемо). Флаг --pretty — таблица/сводка
для человека. Примеры см. в SKILL.md.
"""

import argparse
import json
import os
import sys

sys.dont_write_bytecode = True
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gearbox
from gearbox.spec import SpecError


def _emit(obj, pretty_fn, pretty):
    if pretty and pretty_fn is not None:
        print(pretty_fn(obj))
    else:
        print(json.dumps(obj, ensure_ascii=False, indent=2))


def _read_spec(args):
    if args.json:
        return json.loads(args.json)
    if args.stdin or args.infile in (None, '-'):
        data = sys.stdin.read()
        if not data.strip():
            raise SpecError("пустой ввод: передайте --in FILE, --json '...' или подайте JSON в stdin")
        return json.loads(data)
    with open(args.infile, 'r', encoding='utf-8') as f:
        return json.load(f)


# ============================================================================
#  Человекочитаемые принтеры
# ============================================================================
def _pretty_calc(r):
    L = []
    head = r.get('name') or r['spec_hash']
    L.append(f"=== {head} ===  (hash {r['spec_hash']}{' · из кэша' if r['from_cache'] else ''})")
    rt = r['ratio']
    L.append(f"i = {' × '.join(map(str, rt['per_stage']))} = {rt['total']}   "
             f"({r['kinematics'].get('eta_est')} КПД, {r['load']['mode']}-режим)")
    k = r['kinematics']
    L.append(f"T_out = {k['T_out_Nm']} Н·м,  n_out = {k['n_out_rpm']} об/мин,  "
             f"T_in(экв) = {k['T_in_equiv_Nm']} Н·м")
    d = r['dimensions']
    L.append(f"Габарит: Ø {d['D_outer_mm']} мм,  L_ax {d['L_axial_mm']} мм")
    sat = []
    for s in d['by_stage']:
        n, nm, auto = s.get('n_planets'), s.get('n_planets_max'), s.get('n_planets_auto')
        if auto:
            sat.append(f"ст{s['stage']}={n}")
        else:
            sat.append(f"ст{s['stage']}={n} (задано, макс {nm})")
    if sat:
        auto_all = all(s.get('n_planets_auto') for s in d['by_stage'])
        L.append("Саттелиты: " + ", ".join(sat)
                 + ("  [авто-максимум, что влезает]" if auto_all else ""))
    geo = r['geometry']
    if not geo['valid']:
        L.append("ГЕОМЕТРИЯ НЕВАЛИДНА:")
        for e in geo['errors']:
            L.append(f"  ✗ {e}")
        return '\n'.join(L)
    for w in geo.get('warnings', []):
        L.append(f"  ⚠ {w}")
    s = r['safety']
    def at(x):
        a = x['at']
        return f"{x['value']} (ст.{a['stage']} {a['mesh']}/{a['member']})"
    L.append(f"SF_min = {at(s['SF_min'])}   [порог {s['thresholds']['SF_min']}]")
    L.append(f"SH_min = {at(s['SH_min'])}   [порог {s['thresholds']['SH_min']}]")
    L.append(f"SH_pess= {at(s['SH_pess_min'])}")
    g = s['governing']
    L.append(f"Слабое место: {g['metric']} = {g['value']} в ст.{g['stage']} "
             f"{g['mesh']}/{g['member']}  (запас к порогу ×{g['margin_ratio']})")
    for w in s.get('warnings', []):
        if w not in geo.get('warnings', []):
            L.append(f"  ⚠ {w}")
    req = r.get('requirements', {})
    flags = []
    if 'D_ok' in req:
        flags.append(f"Ø {'OK' if req['D_ok'] else 'ПРЕВЫШЕН'}")
    if 'T_out_ok' in req:
        flags.append(f"T_out {'OK' if req['T_out_ok'] else 'НЕ ДОТЯГИВАЕТ'}")
    L.append(f"ИТОГ: {'ПРОХОДИТ' if r['pass'] else 'НЕ ПРОХОДИТ'}"
             + (f"  ({', '.join(flags)})" if flags else ''))
    return '\n'.join(L)


def _pretty_search(entries):
    if not entries:
        return "(ничего не найдено)"
    L = [f"{'id':<40} {'src':<5} {'n':>1} {'i':>6} {'T_out':>6} {'Ø':>6} "
         f"{'L':>5} {'SF':>5} {'SH':>5} {'SHp':>5} {'OK':>3}  материалы",
         '-' * 120]
    for e in entries:
        L.append(
            f"{str(e['id'])[:40]:<40} {e['source']:<5} {e['n_stages']:>1} "
            f"{e['i_total']:>6} {e['T_out_Nm'] or 0:>6.1f} {e['D_outer_mm']:>6.1f} "
            f"{e['L_axial_mm']:>5.0f} {e['SF_min']:>5.2f} {e['SH_min']:>5.2f} "
            f"{e['SH_pess_min']:>5.2f} {'OK' if e['pass_vdi'] else '-':>3}  "
            f"{'+'.join(e['materials'])}")
    L.append(f"\nвсего: {len(entries)}")
    return '\n'.join(L)


def _pretty_best(entries):
    if not entries:
        return "(ничего не найдено)"
    from collections import OrderedDict
    groups = OrderedDict()
    for e in entries:
        groups.setdefault(e.get('group') or '+'.join(e['materials']), []).append(e)
    L = ["Чемпионы — формат  Ø_мм / b_по_ступеням(мм):", '-' * 92]
    for gname, items in groups.items():
        L.append(f"▸ {gname}")
        for e in items:
            bparts = '+'.join(('%g' % s['b']) for s in e['stages'])
            L.append(f"    {e['D_outer_mm']:>6.0f} / {bparts:<14} "
                     f"i={e['i_total']:<6g} T_out={e['T_out_Nm'] or 0:>6.1f}  "
                     f"SF={e['SF_min']:.2f} SH={e['SH_min']:.2f} "
                     f"{'OK' if e['pass_vdi'] else ' -'}  [{e['id']}]")
    L.append(f"\nвсего: {len(entries)}")
    return '\n'.join(L)


def _pretty_materials(mats):
    L = [f"{'материал':<12} {'E,МПа':>7} {'ν':>5} {'σHlim*':>7} {'σFlim*':>7}  примечание",
         '-' * 100]
    for m in mats:
        if 'error' in m:
            L.append(f"{m['name']:<12} (нет данных)  {m.get('note','')}")
            continue
        L.append(f"{m['name']:<12} {m['E_MPa']:>7.0f} {m['nu']:>5.2f} "
                 f"{m['SigmaHlim_ref']:>7.1f} {m['SigmaFlim_ref']:>7.1f}  {m['note']}")
    L.append("\n* σHlim/σFlim — индикативно при 25 °C, 1e6 циклов "
             "(внешняя пара в пайплайне VDI берёт NL=1e8).")
    return '\n'.join(L)


def _pretty_motors(motors):
    L = [f"{'id':<8} {'T_cont,Нм':>9} {'n_nom,об/мин':>12}  описание", '-' * 90]
    for m in motors:
        L.append(f"{m['id']:<8} {m['T_cont']:>9.2f} {m['n_nom']:>12.0f}  {m['desc']}")
    return '\n'.join(L)


# ============================================================================
#  Команды
# ============================================================================
def cmd_calc(args):
    spec_dict = _read_spec(args)
    report = gearbox.calculate(spec_dict, use_cache=not args.no_cache,
                               save=not args.no_save)
    if args.out:
        with open(args.out, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
    _emit(report, _pretty_calc, args.pretty)
    return 0 if report.get('pass') else 1


def cmd_search(args):
    entries = gearbox.library.search(
        i=args.i, i_tol=args.i_tol, n_stages=args.n_stages,
        t_out_min=args.t_out_min, d_max=args.d_max, l_max=args.l_max,
        material=args.material, materials_subset=args.materials_subset,
        sf_min=args.sf_min, sh_min=args.sh_min, sh_pess_min=args.sh_pess_min,
        passing_only=args.passing, sort=args.sort, top=args.top)
    _emit(entries, _pretty_search, args.pretty)
    return 0


def cmd_best(args):
    entries = gearbox.library.best_by_material(
        per_group=args.per_material, sort=args.sort,
        passing_only=not args.include_failing, group_by=args.group_by,
        i=args.i, i_tol=args.i_tol, n_stages=args.n_stages,
        t_out_min=args.t_out_min, d_max=args.d_max, l_max=args.l_max,
        material=args.material, materials_subset=args.materials_subset,
        sf_min=args.sf_min, sh_min=args.sh_min, sh_pess_min=args.sh_pess_min)
    _emit(entries, _pretty_best, args.pretty)
    return 0


def cmd_materials(args):
    _emit(gearbox.catalog.list_materials(), _pretty_materials, args.pretty)
    return 0


def cmd_motors(args):
    _emit(gearbox.catalog.list_motors(), _pretty_motors, args.pretty)
    return 0


def build_parser():
    p = argparse.ArgumentParser(prog='planetary-gearbox',
                                description='Расчёт планетарной коробки (VDI 2736) для LLM-агентов.')
    sub = p.add_subparsers(dest='cmd', required=True)

    c = sub.add_parser('calc', help='рассчитать коробку по spec (JSON)')
    src = c.add_argument_group('источник spec')
    src.add_argument('--in', dest='infile', help="файл spec (JSON); '-' = stdin")
    src.add_argument('--stdin', action='store_true', help='читать spec из stdin')
    src.add_argument('--json', help='spec прямо строкой JSON')
    c.add_argument('--out', help='сохранить полный отчёт в файл')
    c.add_argument('--no-cache', action='store_true', help='не использовать кэш')
    c.add_argument('--no-save', action='store_true', help='не сохранять в библиотеку')
    c.add_argument('--pretty', action='store_true', help='человекочитаемая сводка')
    c.set_defaults(func=cmd_calc)

    s = sub.add_parser('search', help='найти готовые коробки в библиотеке')
    s.add_argument('--i', type=float, help='целевое суммарное передаточное')
    s.add_argument('--i-tol', type=float, default=0.5, help='допуск по i (±)')
    s.add_argument('--n-stages', type=int, help='число ступеней')
    s.add_argument('--t-out-min', type=float, help='T_out >= , Н·м')
    s.add_argument('--d-max', type=float, help='Ø <= , мм')
    s.add_argument('--l-max', type=float, help='L_ax <= , мм')
    s.add_argument('--material', help='должен содержать материал (любой слот)')
    s.add_argument('--materials-subset', nargs='+', help='только из этих материалов')
    s.add_argument('--sf-min', type=float, help='SF_min >=')
    s.add_argument('--sh-min', type=float, help='SH_min >=')
    s.add_argument('--sh-pess-min', type=float, help='SH_pess_min >=')
    s.add_argument('--passing', action='store_true', help='только проходящие VDI 2736')
    s.add_argument('--sort', default='d', choices=['d', 'l', 'sh', 'sf', 'i', 't_out'],
                   help='сортировка (d=Ø, l=длина, sh, sf, i, t_out)')
    s.add_argument('--top', type=int, default=20, help='сколько вернуть (0=все)')
    s.add_argument('--pretty', action='store_true')
    s.set_defaults(func=cmd_search)

    b = sub.add_parser('best', help='лучшие готовые коробки — по одной на материал')
    b.add_argument('--t-out-min', type=float, help='требуемый выходной момент, Н·м (T_out >=)')
    b.add_argument('--per-material', type=int, default=3, help='сколько лучших на материал (по умолч. 3)')
    b.add_argument('--group-by', default='materials', choices=['materials', 'primary'],
                   help="группировка: materials=полный набор, primary=материал солнца ст.1")
    b.add_argument('--include-failing', action='store_true',
                   help='не ограничиваться проходящими VDI 2736')
    b.add_argument('--i', type=float, help='целевое суммарное передаточное')
    b.add_argument('--i-tol', type=float, default=0.5, help='допуск по i (±)')
    b.add_argument('--n-stages', type=int, help='число ступеней')
    b.add_argument('--d-max', type=float, help='Ø <= , мм')
    b.add_argument('--l-max', type=float, help='L_ax <= , мм')
    b.add_argument('--material', help='должен содержать материал (любой слот)')
    b.add_argument('--materials-subset', nargs='+', help='только из этих материалов')
    b.add_argument('--sf-min', type=float, help='SF_min >=')
    b.add_argument('--sh-min', type=float, help='SH_min >=')
    b.add_argument('--sh-pess-min', type=float, help='SH_pess_min >=')
    b.add_argument('--sort', default='d', choices=['d', 'l', 'sh', 'sf', 'i', 't_out'],
                   help='критерий «лучшего» (d=Ø, l=длина, sh, sf, i, t_out)')
    b.add_argument('--pretty', action='store_true')
    b.set_defaults(func=cmd_best)

    m = sub.add_parser('materials', help='список доступных материалов')
    m.add_argument('--pretty', action='store_true')
    m.set_defaults(func=cmd_materials)

    mo = sub.add_parser('motors', help='список моторов-пресетов')
    mo.add_argument('--pretty', action='store_true')
    mo.set_defaults(func=cmd_motors)
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except SpecError as e:
        print(json.dumps({'error': str(e), 'type': 'SpecError'},
                         ensure_ascii=False), file=sys.stderr)
        return 2
    except (json.JSONDecodeError, KeyError) as e:
        print(json.dumps({'error': str(e), 'type': type(e).__name__},
                         ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
