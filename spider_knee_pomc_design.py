#!/usr/bin/env python3
"""
SPIDER ROBOT KNEE - Two-stage planetary gearbox with POM-C sun and PA6 satellites
Requirements:
- Compact, D <= 200 mm, b <= 40 mm per stage
- Input: 3.7 Nm at 150 RPM
- Output: >= 60 Nm
- Gear ratio: > 32
- Safety factor: >= 1.3
- Materials: POM_C (sun), PA6_PRINT (satellites)
"""

import sys
sys.dont_write_bytecode = True

from CLASSES import MATERIAL_LIBRARY
import json
from pathlib import Path

# Input specifications
T_input = 3.7          # Nm at input
n_input = 150          # rpm at input
T_required = 60        # Nm minimum at output
D_max = 200            # mm, maximum diameter
b_max = 40             # mm, maximum width per stage
KA = 1.3               # safety coefficient
T_amb = 25.0           # Celsius

MIN_RELIEF = 1.3       # minimum safety factor

# Modules to test
modules = [0.8, 1.0, 1.25, 1.5, 1.75, 2.0]

# Two-stage configs: (i1, i2, n_sat1, n_sat2, description)
configs_2stage = [
    (6, 6, 3, 4, "6x6 asymmetric"),
    (6, 6, 3, 3, "6x6 symmetric"),
    (4, 9, 3, 4, "4x9 asymmetric"),
    (8, 4, 3, 4, "8x4 asymmetric"),
    (5, 7, 3, 4, "5x7 asymmetric"),
]

report_dir = Path('REPORT/SPIDER_KNEE/_data')
report_dir.mkdir(parents=True, exist_ok=True)

def check_assembly(Z_sun, Z_ring, n_sat):
    """Check assembly condition: (Z_sun + Z_ring) % n_sat == 0"""
    return (Z_sun + Z_ring) % n_sat == 0

def calc_stage(m, Z_sun, Z_ring, n_sat, T_in, n_in, mat_sun, mat_planet, b, stage_name):
    """Calculate one planetary stage"""

    Z_planet = (Z_sun + Z_ring) // 2
    d_sun = m * Z_sun
    d_ring = m * Z_ring
    d_planet = m * Z_planet

    # Assembly check
    if not check_assembly(Z_sun, Z_ring, n_sat):
        return None, f"Assembly error: ({Z_sun}+{Z_ring})/{n_sat}"

    # Stage gear ratio
    i_stage = 1 + Z_ring / Z_sun

    # Output parameters
    T_out = T_in * i_stage
    n_out = n_in / i_stage

    # Contact force
    F_t = (2 * T_in * 1e3) / d_sun  # N

    # Reduced modulus
    mat_sun_lib = MATERIAL_LIBRARY.LIBRARY_MAT(mat_sun)
    mat_planet_lib = MATERIAL_LIBRARY.LIBRARY_MAT(mat_planet)

    E1 = mat_sun_lib.E
    E2 = mat_planet_lib.E
    v1 = mat_sun_lib.v
    v2 = mat_planet_lib.v

    E_red = 1 / ((1 - v1**2) / E1 + (1 - v2**2) / E2)

    # Equivalent radius
    R_sun = d_sun / 2
    R_planet = d_planet / 2
    R_eq = (R_sun * R_planet) / (R_sun + R_planet)

    # Hertz contact stress
    sigma_H = ((F_t / (b * R_eq)) * (E_red / 2)) ** 0.5 / 1000  # MPa

    # Bending stress (simplified)
    sigma_F = F_t / (b * m) * 1.5  # MPa

    # Allowable stresses
    sigma_H_lim = mat_planet_lib.SigmaHlim(T_amb, 1e9) if callable(mat_planet_lib.SigmaHlim) else mat_planet_lib.SigmaHlim
    sigma_F_lim = mat_planet_lib.SigmaFlim(T_amb, 1e9) if callable(mat_planet_lib.SigmaFlim) else mat_planet_lib.SigmaFlim

    # Safety factors
    SH = sigma_H_lim / sigma_H if sigma_H > 0 else float('inf')
    SF = sigma_F_lim / sigma_F if sigma_F > 0 else float('inf')

    # Clearance between satellites
    angle_between = 360 / n_sat
    arc_length = (d_sun / 2 + d_planet) * (angle_between * 3.14159 / 180)
    sat_thickness = m * 3
    clearance = arc_length - sat_thickness

    result = {
        'stage': stage_name,
        'm': m,
        'Z_sun': Z_sun,
        'Z_ring': Z_ring,
        'Z_planet': Z_planet,
        'n_sat': n_sat,
        'b': b,
        'd_sun': d_sun,
        'd_ring': d_ring,
        'd_planet': d_planet,
        'i_stage': i_stage,
        'T_in': T_in,
        'T_out': T_out,
        'n_in': n_in,
        'n_out': n_out,
        'F_t': F_t,
        'sigma_H': sigma_H,
        'sigma_F': sigma_F,
        'sigma_H_lim': sigma_H_lim,
        'sigma_F_lim': sigma_F_lim,
        'SH': SH,
        'SF': SF,
        'clearance_mm': clearance,
    }

    return result, None

def design_2stage(m1, Z_sun1, Z_ring1, b1, n_sat1,
                  m2, Z_sun2, Z_ring2, b2, n_sat2):
    """Design full two-stage planetary system"""

    stage1, err1 = calc_stage(m1, Z_sun1, Z_ring1, n_sat1, T_input, n_input, 'POM_C', 'PA6_PRINT', b1, "S1")
    if err1:
        return None, err1

    stage2, err2 = calc_stage(m2, Z_sun2, Z_ring2, n_sat2, stage1['T_out'], stage1['n_out'], 'POM_C', 'PA6_PRINT', b2, "S2")
    if err2:
        return None, err2

    i_total = stage1['i_stage'] * stage2['i_stage']
    T_output = stage2['T_out']
    n_output = stage2['n_out']

    D_outer1 = stage1['d_ring'] + m1 * 2
    D_outer2 = stage2['d_ring'] + m2 * 2

    T_ok = T_output >= T_required
    D_ok = D_outer2 <= D_max
    b_ok = (b1 <= b_max) and (b2 <= b_max)

    min_SH = min(stage1['SH'], stage2['SH'])
    min_SF = min(stage1['SF'], stage2['SF'])

    relief_ok = (min_SH >= MIN_RELIEF) and (min_SF >= MIN_RELIEF)

    result = {
        'i1': stage1['i_stage'],
        'i2': stage2['i_stage'],
        'i_total': i_total,
        'T_output': T_output,
        'n_output': n_output,
        'D_outer_stage1': D_outer1,
        'D_outer_stage2': D_outer2,
        'b_total': b1 + b2,
        'stage1': stage1,
        'stage2': stage2,
        'T_ok': T_ok,
        'D_ok': D_ok,
        'b_ok': b_ok,
        'relief_ok': relief_ok,
        'min_SH': min_SH,
        'min_SF': min_SF,
        'all_ok': T_ok and D_ok and b_ok and relief_ok,
    }

    return result, None

def format_report(design):
    """Format design report"""
    s1 = design['stage1']
    s2 = design['stage2']

    lines = [
        f"{'='*85}",
        f"  SUMMARY: i{design['i_total']:.0f}_{design['i1']:.0f}x{design['i2']:.0f}_m{s1['m']:.2f}-Z{s1['Z_sun']:.0f}-{s1['Z_ring']:.0f}_m{s2['m']:.2f}-Z{s2['Z_sun']:.0f}-{s2['Z_ring']:.0f}",
        f"  Materials: Sun=POM_C, Satellites=PA6_PRINT",
        f"{'='*85}",
        f"",
        f"INPUT DATA",
        f"{'-'*85}",
        f"  Input torque:         T_in = {T_input:.2f} Nm at n = {n_input:.0f} rpm",
        f"  Requirements:         T_out >= {T_required:.0f} Nm, D <= {D_max:.0f} mm, b <= {b_max:.0f} mm/stage",
        f"  Safety coefficient:   KA = {KA}",
        f"  Temperature:          {T_amb:.1f} C",
        f"",
        f"FINAL CHARACTERISTICS",
        f"{'-'*85}",
        f"  Gear ratio:           i = {design['i1']:.0f} x {design['i2']:.0f} = {design['i_total']:.0f}",
        f"  Output torque:        T_out = {design['T_output']:.2f} Nm  {'OK' if design['T_ok'] else 'FAIL - TOO LOW'}",
        f"  Output speed:         n_out = {design['n_output']:.2f} rpm",
        f"  Max diameter (D):     {design['D_outer_stage2']:.1f} mm  {'OK' if design['D_ok'] else 'FAIL - TOO LARGE'}",
        f"  Axial length (b):     {design['b_total']:.0f} mm (b1+b2)  {'OK' if design['b_ok'] else 'FAIL - TOO LONG'}",
        f"  Min safety factor SH: {design['min_SH']:.2f}  {'OK' if design['relief_ok'] else 'FAIL - TOO LOW'}",
        f"  Status:               {'ACCEPTABLE' if design['all_ok'] else 'REJECTED'}",
        f"",
        f"STAGE 1 (i1 = {design['i1']:.0f}, {s1['n_sat']} satellites)",
        f"{'-'*85}",
        f"  Module m1 = {s1['m']:.2f} mm   Width b1 = {s1['b']:.0f} mm",
        f"  Z_sun = {s1['Z_sun']:3.0f}   Z_ring = {s1['Z_ring']:3.0f}   Z_planet = {s1['Z_planet']:3.0f}",
        f"  d_sun = {s1['d_sun']:7.2f} mm   d_ring = {s1['d_ring']:7.2f} mm   d_planet = {s1['d_planet']:7.2f} mm",
        f"  Load F_t = {s1['F_t']:.1f} N",
        f"  Contact stress:       sigma_H = {s1['sigma_H']:.2f} MPa (limit={s1['sigma_H_lim']:.1f}) -> SH = {s1['SH']:.2f}",
        f"  Bending stress:       sigma_F = {s1['sigma_F']:.2f} MPa (limit={s1['sigma_F_lim']:.1f}) -> SF = {s1['SF']:.2f}",
        f"  Satellite clearance:  {s1['clearance_mm']:.2f} mm",
        f"",
        f"STAGE 2 (i2 = {design['i2']:.0f}, {s2['n_sat']} satellites)",
        f"{'-'*85}",
        f"  Module m2 = {s2['m']:.2f} mm   Width b2 = {s2['b']:.0f} mm",
        f"  Z_sun = {s2['Z_sun']:3.0f}   Z_ring = {s2['Z_ring']:3.0f}   Z_planet = {s2['Z_planet']:3.0f}",
        f"  d_sun = {s2['d_sun']:7.2f} mm   d_ring = {s2['d_ring']:7.2f} mm   d_planet = {s2['d_planet']:7.2f} mm",
        f"  Load F_t = {s2['F_t']:.1f} N",
        f"  Contact stress:       sigma_H = {s2['sigma_H']:.2f} MPa (limit={s2['sigma_H_lim']:.1f}) -> SH = {s2['SH']:.2f}",
        f"  Bending stress:       sigma_F = {s2['sigma_F']:.2f} MPa (limit={s2['sigma_F_lim']:.1f}) -> SF = {s2['SF']:.2f}",
        f"  Satellite clearance:  {s2['clearance_mm']:.2f} mm",
        f"",
        f"{'='*85}",
    ]

    return '\n'.join(lines)

def main():
    print("="*85)
    print("  SPIDER ROBOT KNEE - Two-stage Planetary Gearbox Design")
    print("  Materials: POM_C (sun/gears), PA6_PRINT (satellites)")
    print("="*85)
    print()

    valid_designs = []

    print("Generating configurations...")

    # Generate configurations
    for m1 in modules:
        for m2 in modules:
            for i1, i2, n_sat1, n_sat2, desc in configs_2stage:

                for Z_sun1 in [12, 15, 18, 20, 24]:
                    Z_ring1 = int(Z_sun1 * (i1 - 1))

                    if not check_assembly(Z_sun1, Z_ring1, n_sat1):
                        continue

                    for b1 in [20, 25, 30, 35, 40]:
                        if b1 > b_max:
                            continue

                        for Z_sun2 in [12, 15, 18, 20, 24]:
                            Z_ring2 = int(Z_sun2 * (i2 - 1))

                            if not check_assembly(Z_sun2, Z_ring2, n_sat2):
                                continue

                            for b2 in [20, 25, 30, 35, 40]:
                                if b2 > b_max:
                                    continue

                                design, err = design_2stage(m1, Z_sun1, Z_ring1, b1, n_sat1,
                                                             m2, Z_sun2, Z_ring2, b2, n_sat2)

                                if err is None and design:
                                    valid_designs.append(design)

    # Filter and sort
    good_designs = [d for d in valid_designs if d['all_ok']]

    if not good_designs:
        print("\n[FAIL] No acceptable configurations found!")
        print(f"  Requirements:")
        print(f"  - Output torque >= {T_required} Nm")
        print(f"  - Diameter <= {D_max} mm")
        print(f"  - Gear ratio > 32")
        print(f"  - Safety factors >= {MIN_RELIEF}")
        return

    # Sort by compactness
    good_designs.sort(key=lambda d: (d['D_outer_stage2'], d['b_total']))

    print(f"\n[OK] Found {len(good_designs)} acceptable configurations")
    print("\nTop 5 Compact Solutions:")
    print("-" * 85)

    for idx, design in enumerate(good_designs[:5], 1):
        s1 = design['stage1']
        s2 = design['stage2']
        fname = f"i{design['i_total']:.0f}_{s1['m']:.2f}x{s2['m']:.2f}_Z{s1['Z_sun']:.0f}-{s2['Z_sun']:.0f}_b{s1['b']:.0f}x{s2['b']:.0f}_POM_C"

        print(f"\n{idx}. {fname}")
        print(f"    Size: D={design['D_outer_stage2']:.0f}x{design['b_total']:.0f} mm")
        print(f"    Torque: {design['T_output']:.1f} Nm (req: {T_required} Nm)")
        print(f"    Ratio: {design['i_total']:.0f} = {design['i1']:.0f}x{design['i2']:.0f}")
        print(f"    Safety: SH={design['min_SH']:.2f}, SF={design['min_SF']:.2f}")

        report = format_report(design)
        report_file = report_dir / f"{fname}.txt"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"    Report: {report_file}")

    # Save JSON summary
    json_data = {
        'requirements': {
            'T_input': T_input,
            'n_input': n_input,
            'T_required': T_required,
            'D_max': D_max,
            'b_max': b_max,
            'i_min': 32,
        },
        'best_designs': [{
            'index': idx + 1,
            'i_total': d['i_total'],
            'i1': d['i1'],
            'i2': d['i2'],
            'T_output': d['T_output'],
            'n_output': d['n_output'],
            'D_outer': d['D_outer_stage2'],
            'b_total': d['b_total'],
            'stage1': {
                'm': d['stage1']['m'],
                'Z_sun': int(d['stage1']['Z_sun']),
                'Z_ring': int(d['stage1']['Z_ring']),
                'Z_planet': int(d['stage1']['Z_planet']),
                'n_sat': d['stage1']['n_sat'],
                'b': d['stage1']['b'],
            },
            'stage2': {
                'm': d['stage2']['m'],
                'Z_sun': int(d['stage2']['Z_sun']),
                'Z_ring': int(d['stage2']['Z_ring']),
                'Z_planet': int(d['stage2']['Z_planet']),
                'n_sat': d['stage2']['n_sat'],
                'b': d['stage2']['b'],
            },
            'min_SH': d['min_SH'],
            'min_SF': d['min_SF'],
        } for idx, d in enumerate(good_designs[:10])]
    }

    json_file = report_dir / 'designs_summary_pomc.json'
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, indent=2)

    print(f"\n[OK] Summary saved to: {json_file}")

if __name__ == '__main__':
    main()
