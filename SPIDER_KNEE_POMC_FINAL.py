#!/usr/bin/env python3
"""
SPIDER KNEE design with D16T (milled aluminum) sun
Two-stage planetary gearbox with asymmetric ratios

Requirements:
- Compact: D <= 200 mm, b <= 40 mm per stage
- Input: 3.7 Nm at 150 RPM
- Output: >= 60 Nm
- Ratio: > 32 (asymmetric stages: e.g., 5.7x6=34.2)
- Safety: >= 1.3
- Material: D16T (aluminum) sun, PA6_PRINT (FFF) satellites
"""

import sys
sys.dont_write_bytecode = True

from CLASSES import MATERIAL_LIBRARY
from pathlib import Path
import math

T_amb = 25.0

# Material properties
mat_pa6 = MATERIAL_LIBRARY.LIBRARY_MAT('PA6_PRINT')
mat_d16t = MATERIAL_LIBRARY.LIBRARY_MAT('D16T')

# Candidate configurations (name, m1, Z1_sun, Z1_planet, Z1_ring, b1, n_sat1,
#                                m2, Z2_sun, Z2_planet, Z2_ring, b2, n_sat2)
# D16T sun + PA6_PRINT satellites, asymmetric ratios for i > 32
# Formula: i_stage = 1 + Z_ring/Z_sun
# Assembly condition: (Z_sun + Z_ring) % n_sat == 0

candidates = [
    # Stage 1: i=5.5 (Z_ring/Z_sun=4.5, Z_sun=18, Z_ring=81)
    # Stage 2: i=6.0 (Z_ring/Z_sun=5.0, Z_sun=20, Z_ring=100)
    # Total: i ≈ 33, m=1.25/1.5, compact
    ("i33_5.5x6.0_m1.25-m1.5_D16T",
     1.25, 18, 36, 81, 28, 3,
     1.5, 20, 30, 100, 35, 4),

    # Stage 1: i=5.5 (Z_sun=20, Z_ring=90)
    # Stage 2: i=6.0 (Z_sun=20, Z_ring=100)
    # Total: i ≈ 33, m=1.5, slightly larger
    ("i33_5.5x6.0_m1.5_D16T",
     1.5, 20, 30, 90, 30, 3,
     1.5, 20, 30, 100, 35, 4),

    # Stage 1: i=6.0 (Z_sun=16, Z_ring=80)
    # Stage 2: i=5.7 (Z_sun=18, Z_ring=85)
    # Total: i ≈ 34.2, m=1.25/1.5
    ("i34_6.0x5.7_m1.25-m1.5_D16T",
     1.25, 16, 40, 80, 28, 4,
     1.5, 18, 36, 85, 35, 3),

    # Stage 1: i=6.0 (Z_sun=16, Z_ring=80)
    # Stage 2: i=6.0 (Z_sun=16, Z_ring=80)
    # Total: i = 36, equal stages, m=1.5
    ("i36_6.0x6.0_m1.5_D16T",
     1.5, 16, 40, 80, 32, 4,
     1.5, 16, 40, 80, 35, 4),

    # Stage 1: i=5.7 (Z_sun=18, Z_ring=85)
    # Stage 2: i=5.7 (Z_sun=18, Z_ring=85)
    # Total: i ≈ 32.5, m=1.5
    ("i33_5.7x5.7_m1.5_D16T",
     1.5, 18, 36, 85, 32, 3,
     1.5, 18, 36, 85, 35, 3),

    # Stage 1: i=4.5 (Z_sun=20, Z_ring=70)
    # Stage 2: i=7.5 (Z_sun=16, Z_ring=100)
    # Total: i ≈ 33.75, highly asymmetric
    ("i34_4.5x7.5_m1.5_D16T",
     1.5, 20, 30, 70, 30, 5,
     1.5, 16, 40, 100, 35, 4),

    # Stage 1: i=5.5 (Z_sun=18, Z_ring=81)
    # Stage 2: i=6.5 (Z_sun=18, Z_ring=99)
    # Total: i ≈ 35.75, m=1.25/1.5
    ("i36_5.5x6.5_m1.25-m1.5_D16T",
     1.25, 18, 36, 81, 28, 3,
     1.5, 18, 36, 99, 36, 3),
]

def calc_stage(m, Z_sun, Z_planet, Z_ring, b, n_sat, T_in, n_in, is_first=True):
    """Calculate stage with D16T sun and PA6_PRINT satellites"""

    # Check assembly condition: (Z_sun + Z_ring) must be divisible by n_sat
    if (Z_sun + Z_ring) % n_sat != 0:
        return None, f"Assembly: ({Z_sun}+{Z_ring})/{n_sat} not integer"

    d_sun = m * Z_sun
    d_ring = m * Z_ring
    d_planet = m * Z_planet

    i_stage = 1 + Z_ring / Z_sun
    T_out = T_in * i_stage
    n_out = n_in / i_stage

    # Tangential force (at sun-planet mesh)
    F_t = (2 * T_in * 1e3) / d_sun

    # D16T sun, PA6_PRINT satellites
    # Reduced modulus for D16T-PA6 contact (Hertzian contact)
    E_red = 1 / ((1 - mat_d16t.v**2) / mat_d16t.E + (1 - mat_pa6.v**2) / mat_pa6.E)

    # PA6_PRINT is the critical material (soft)
    sigma_H_lim = mat_pa6.SigmaHlim(T_amb, 1e9) if callable(mat_pa6.SigmaHlim) else mat_pa6.SigmaHlim
    sigma_F_lim = mat_pa6.SigmaFlim(T_amb, 1e9) if callable(mat_pa6.SigmaFlim) else mat_pa6.SigmaFlim

    # Contact stress (Hertzian approximation for sun-planet mesh)
    # σH ≈ sqrt((E_red * F_t) / (π * R_sun * R_planet * b))
    # Where F_t = 2*T_in/d_sun
    # Simplification: σH ≈ C_H * sqrt(T_in * E_red / (d_sun * d_planet * b))
    # With C_H ≈ 0.35 for planetary, using metric units with T in Nm, d in mm
    R_sun = d_sun / 2
    R_planet = d_planet / 2
    # Contact stress in MPa: σH ≈ sqrt(F_t * E_red / (π * R_sun * R_planet * b * 10^-3))
    # F_t in Newtons = T_in * 1000 / R_sun (in mm)
    sigma_H_contact = math.sqrt((2 * T_in * 1e3) * E_red / (math.pi * R_sun * R_planet * b)) / 1000 if (R_sun * R_planet * b) > 0 else 0

    # Bending stress (simplified Lewis formula for planetary gear)
    # σF ≈ (F_t / (b * m)) * Y_F * Y_S
    # F_t = 2*T/d_sun (in N), Y_F ≈ 0.4-0.5 for Z=18-40, Y_S ≈ 1.0
    # Result in MPa
    Y_F = 0.45  # Form factor for typical planetary gears
    Y_S = 1.0   # Size factor
    sigma_F_bend = (F_t / (b * m)) * Y_F * Y_S if (b * m) > 0 else 0

    # Use contact stress for SH
    sigma_H = sigma_H_contact

    # Use bending stress for SF
    sigma_F = sigma_F_bend

    # Safety factors
    SH = sigma_H_lim / sigma_H if sigma_H > 0.01 else 999
    SF = sigma_F_lim / sigma_F if sigma_F > 0.01 else 999

    return {
        'Z_sun': Z_sun,
        'Z_planet': Z_planet,
        'Z_ring': Z_ring,
        'n_sat': n_sat,
        'd_sun': d_sun,
        'd_ring': d_ring,
        'd_planet': d_planet,
        'i': i_stage,
        'T_in': T_in,
        'T_out': T_out,
        'n_in': n_in,
        'n_out': n_out,
        'b': b,
        'm': m,
        'F_t': F_t,
        'sigma_H': sigma_H,
        'sigma_F': sigma_F,
        'SH': SH,
        'SF': SF,
        'sigma_H_lim': sigma_H_lim,
        'sigma_F_lim': sigma_F_lim,
    }, None

def evaluate_config(name, m1, Z1_sun, Z1_planet, Z1_ring, b1, n_sat1,
                    m2, Z2_sun, Z2_planet, Z2_ring, b2, n_sat2):
    """Evaluate a complete two-stage configuration"""

    T_input = 3.7
    n_input = 150
    T_required = 60
    D_max = 200
    b_max = 40

    # Stage 1
    s1, err1 = calc_stage(m1, Z1_sun, Z1_planet, Z1_ring, b1, n_sat1, T_input, n_input, is_first=True)
    if err1:
        return None, err1

    # Stage 2
    s2, err2 = calc_stage(m2, Z2_sun, Z2_planet, Z2_ring, b2, n_sat2, s1['T_out'], s1['n_out'], is_first=False)
    if err2:
        return None, err2

    i_total = s1['i'] * s2['i']
    T_out = s2['T_out']
    n_out = s2['n_out']
    D_outer = s2['d_ring'] + m2 * 2

    min_SH = min(s1['SH'], s2['SH'])
    min_SF = min(s1['SF'], s2['SF'])

    pass_T = T_out >= T_required
    pass_D = D_outer <= D_max
    pass_b = (b1 <= b_max) and (b2 <= b_max)
    pass_relief = (min_SH >= 1.3) and (min_SF >= 1.3)

    return {
        'name': name,
        'i_total': i_total,
        'i1': s1['i'],
        'i2': s2['i'],
        'T_output': T_out,
        'n_output': n_out,
        'D_outer': D_outer,
        'b_total': b1 + b2,
        'stage1': s1,
        'stage2': s2,
        'min_SH': min_SH,
        'min_SF': min_SF,
        'pass_T': pass_T,
        'pass_D': pass_D,
        'pass_b': pass_b,
        'pass_relief': pass_relief,
        'overall': pass_T and pass_D and pass_b and pass_relief,
    }, None

def format_report(config):
    """Format detailed report"""
    s1 = config['stage1']
    s2 = config['stage2']

    # Get material properties
    sig_h_d16t = mat_d16t.SigmaHlim(T_amb, 1e9) if callable(mat_d16t.SigmaHlim) else mat_d16t.SigmaHlim
    sig_h_pa6 = mat_pa6.SigmaHlim(T_amb, 1e9) if callable(mat_pa6.SigmaHlim) else mat_pa6.SigmaHlim

    lines = [
        f"{'='*90}",
        f"  SPIDER ROBOT KNEE: {config['name']}",
        f"  Materials: Sun=D16T Aluminum (σH_lim={sig_h_d16t:.0f} MPa), Satellites=PA6_PRINT (σH_lim={sig_h_pa6:.0f} MPa)",
        f"{'='*90}",
        f"",
        f"INPUT DATA",
        f"{'-'*90}",
        f"  Input:       T = 3.7 Nm at n = 150 rpm",
        f"  Requirements: T_out >= 60 Nm, D <= 200 mm, Ratio > 32, Safety >= 1.3",
        f"",
        f"SUMMARY",
        f"{'-'*90}",
        f"  Gear ratio:    i = {s1['i']:.1f} x {s2['i']:.1f} = {config['i_total']:.1f}",
        f"  Output torque: {config['T_output']:.1f} Nm ({'PASS' if config['pass_T'] else 'FAIL'})",
        f"  Output speed:  {config['n_output']:.2f} rpm",
        f"  Max diameter:  {config['D_outer']:.1f} mm ({'PASS' if config['pass_D'] else 'FAIL'})",
        f"  Total width:   {config['b_total']} mm ({'PASS' if config['pass_b'] else 'FAIL'})",
        f"  Min safety:    SH={config['min_SH']:.2f}, SF={config['min_SF']:.2f} ({'PASS' if config['pass_relief'] else 'MARGINAL'})",
        f"  Overall:       {'ACCEPTABLE' if config['overall'] else 'REVIEW NEEDED'}",
        f"",
        f"STAGE 1 (i={s1['i']:.1f}, {s1['n_sat']} satellites)",
        f"{'-'*90}",
        f"  Module m={s1['m']}, Width b={s1['b']} mm",
        f"  Z_sun={s1['Z_sun']}, Z_planet={s1['Z_planet']}, Z_ring={s1['Z_ring']}",
        f"  d_sun={s1['d_sun']:.1f}, d_planet={s1['d_planet']:.1f}, d_ring={s1['d_ring']:.1f} mm",
        f"  Load F_t={s1['F_t']:.1f} N",
        f"  Contact: σH={s1['sigma_H']:.2f} MPa (lim={s1['sigma_H_lim']:.1f}) -> SH={s1['SH']:.2f}",
        f"  Bending:  σF={s1['sigma_F']:.2f} MPa (lim={s1['sigma_F_lim']:.1f}) -> SF={s1['SF']:.2f}",
        f"  Output: T={s1['T_out']:.1f} Nm, n={s1['n_out']:.1f} rpm",
        f"",
        f"STAGE 2 (i={s2['i']:.1f}, {s2['n_sat']} satellites)",
        f"{'-'*90}",
        f"  Module m={s2['m']}, Width b={s2['b']} mm",
        f"  Z_sun={s2['Z_sun']}, Z_planet={s2['Z_planet']}, Z_ring={s2['Z_ring']}",
        f"  d_sun={s2['d_sun']:.1f}, d_planet={s2['d_planet']:.1f}, d_ring={s2['d_ring']:.1f} mm",
        f"  Load F_t={s2['F_t']:.1f} N",
        f"  Contact: σH={s2['sigma_H']:.2f} MPa (lim={s2['sigma_H_lim']:.1f}) -> SH={s2['SH']:.2f}",
        f"  Bending:  σF={s2['sigma_F']:.2f} MPa (lim={s2['sigma_F_lim']:.1f}) -> SF={s2['SF']:.2f}",
        f"  Output: T={s2['T_out']:.1f} Nm, n={s2['n_out']:.2f} rpm",
        f"",
        f"{'='*90}",
    ]
    return '\n'.join(lines)

def main():
    print("="*90)
    print("  SPIDER ROBOT KNEE - D16T Aluminum Sun with PA6_PRINT Satellites")
    print("  Two-stage planetary gearbox with asymmetric ratios (i > 32)")
    print("="*90)
    print()

    report_dir = Path('REPORT/SPIDER_KNEE')
    report_dir.mkdir(parents=True, exist_ok=True)

    results = []

    for candidate in candidates:
        config, err = evaluate_config(*candidate)
        if err:
            print(f"SKIP {candidate[0]}: {err}")
            continue

        results.append(config)

        # Save report
        report = format_report(config)
        report_file = report_dir / f"{config['name']}.txt"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)

    # Sort by diameter (compactness)
    results.sort(key=lambda x: (not x['overall'], x['D_outer'], x['b_total']))

    print(f"\nEVALUATED {len(results)} CONFIGURATIONS\n")
    print(f"{'Config':<35} {'i':<5} {'T_out':<8} {'D':<6} {'SH/SF':<12} {'Status'}")
    print("-"*90)

    for config in results:
        status = "OK" if config['overall'] else "REVIEW"
        print(f"{config['name']:<35} {config['i_total']:<5.0f} {config['T_output']:<8.1f} "
              f"{config['D_outer']:<6.0f} {config['min_SH']:.2f}/{config['min_SF']:.2f}  {status}")

    print("\n" + "="*90)
    print("RECOMMENDATION")
    print("="*90)

    acceptable = [c for c in results if c['overall']]
    if acceptable:
        best = acceptable[0]
        print(f"\nBest option: {best['name']}")
        print(f"  Ratio: {best['i_total']:.0f} = {best['i1']:.1f} x {best['i2']:.1f}")
        print(f"  Output: {best['T_output']:.1f} Nm at {best['n_output']:.2f} rpm")
        print(f"  Size: D={best['D_outer']:.0f} mm, b={best['b_total']} mm")
        print(f"  Safety: SH={best['min_SH']:.2f}, SF={best['min_SF']:.2f}")
        print(f"\nReport saved to: REPORT/SPIDER_KNEE/{best['name']}.txt")
    else:
        print("\nNo fully acceptable configurations found with current constraints.")
        print("Review marginal options above.")

if __name__ == '__main__':
    main()
