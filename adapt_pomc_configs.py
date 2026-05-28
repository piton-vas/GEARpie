#!/usr/bin/env python3
"""
Adapt existing PA6 designs to POM_C sun material
"""

import sys
sys.dont_write_bytecode = True

from CLASSES import MATERIAL_LIBRARY
from pathlib import Path
import json

T_amb = 25.0

# Material data
mat_pa6 = MATERIAL_LIBRARY.LIBRARY_MAT('PA6_PRINT')
mat_pomc = MATERIAL_LIBRARY.LIBRARY_MAT('POM_C')

# Extract from reports: (name, m1, Z1_sun, Z1_ring, b1, n_sat1, m2, Z2_sun, Z2_ring, b2, n_sat2)
configs = [
    ("i32_8x4_m1.25-Z18-54-126_m1.5-Z22-22-66_b25x40_POM_C",
     1.25, 18, 126, 25, 3, 1.5, 22, 66, 40, 4),

    ("i30_6x5_m1.25-Z18-36-90_m1.5-Z20-30-80_b25x40_POM_C",
     1.25, 18, 36, 25, 3, 1.5, 20, 30, 40, 5),
]

def calc_stress_hertz(F_t, b, R_eq, E_red):
    """Hertzian contact stress in MPa"""
    sigma_H = ((F_t / (b * R_eq)) * (E_red / 2)) ** 0.5 / 1000
    return sigma_H

def calc_stress_bending(F_t, b, m):
    """Bending stress in root (simplified)"""
    sigma_F = F_t / (b * m) * 1.5
    return sigma_F

def adapt_design(name, m1, Z1_sun, Z1_ring, b1, n_sat1,
                 m2, Z2_sun, Z2_ring, b2, n_sat2):
    """Adapt a design with POM_C sun and PA6_PRINT satellites"""

    # Constants
    T_input = 3.7
    n_input = 150

    lines = []
    lines.append("="*90)
    lines.append(f"  ADAPTATION: {name}")
    lines.append(f"  Original: PA6_PRINT throughout")
    lines.append(f"  Adapted:  POM_C sun, PA6_PRINT satellites")
    lines.append("="*90)
    lines.append("")
    lines.append("STAGE 1")
    lines.append("-"*90)

    # Geometry stage 1
    Z1_planet = (Z1_sun + Z1_ring) // 2
    d1_sun = m1 * Z1_sun
    d1_ring = m1 * Z1_ring
    d1_planet = m1 * Z1_planet

    i1 = 1 + Z1_ring / Z1_sun
    T1_out = T_input * i1
    n1_out = n_input / i1

    # Force
    F1_t = (2 * T_input * 1e3) / d1_sun

    # Materials: POM_C sun + PA6_PRINT planet/ring
    E_pomc = mat_pomc.E
    E_pa6 = mat_pa6.E
    v_pomc = mat_pomc.v
    v_pa6 = mat_pa6.v

    E_red1 = 1 / ((1 - v_pomc**2) / E_pomc + (1 - v_pa6**2) / E_pa6)

    R1_sun = d1_sun / 2
    R1_planet = d1_planet / 2
    R1_eq = (R1_sun * R1_planet) / (R1_sun + R1_planet)

    sigma_H1 = calc_stress_hertz(F1_t, b1, R1_eq, E_red1)
    sigma_F1 = calc_stress_bending(F1_t, b1, m1)

    # Limits for PA6_PRINT (satellite/ring)
    sig_H_lim_pa6 = mat_pa6.SigmaHlim(T_amb, 1e9) if callable(mat_pa6.SigmaHlim) else mat_pa6.SigmaHlim
    sig_F_lim_pa6 = mat_pa6.SigmaFlim(T_amb, 1e9) if callable(mat_pa6.SigmaFlim) else mat_pa6.SigmaFlim

    SH1 = sig_H_lim_pa6 / sigma_H1 if sigma_H1 > 0 else float('inf')
    SF1 = sig_F_lim_pa6 / sigma_F1 if sigma_F1 > 0 else float('inf')

    lines.append(f"  m1 = {m1}, Z = {Z1_sun}-{Z1_planet}-{Z1_ring}, b1 = {b1}, n_sat = {n_sat1}")
    lines.append(f"  i1 = {i1:.2f}, d_sun = {d1_sun:.1f}, d_ring = {d1_ring:.1f}")
    lines.append(f"  T_in = {T_input:.2f} Nm, T_out = {T1_out:.2f} Nm, n_out = {n1_out:.2f} rpm")
    lines.append(f"  Contact: sigma_H = {sigma_H1:.2f} MPa (limit = {sig_H_lim_pa6:.1f}) -> SH = {SH1:.2f}")
    lines.append(f"  Bending:  sigma_F = {sigma_F1:.2f} MPa (limit = {sig_F_lim_pa6:.1f}) -> SF = {SF1:.2f}")
    lines.append("")
    lines.append("STAGE 2")
    lines.append("-"*90)

    # Geometry stage 2
    Z2_planet = (Z2_sun + Z2_ring) // 2
    d2_sun = m2 * Z2_sun
    d2_ring = m2 * Z2_ring
    d2_planet = m2 * Z2_planet

    i2 = 1 + Z2_ring / Z2_sun
    T2_out = T1_out * i2
    n2_out = n1_out / i2

    # Force
    F2_t = (2 * T1_out * 1e3) / d2_sun

    # Materials: POM_C sun + PA6_PRINT planet/ring
    E_red2 = 1 / ((1 - v_pomc**2) / E_pomc + (1 - v_pa6**2) / E_pa6)

    R2_sun = d2_sun / 2
    R2_planet = d2_planet / 2
    R2_eq = (R2_sun * R2_planet) / (R2_sun + R2_planet)

    sigma_H2 = calc_stress_hertz(F2_t, b2, R2_eq, E_red2)
    sigma_F2 = calc_stress_bending(F2_t, b2, m2)

    SH2 = sig_H_lim_pa6 / sigma_H2 if sigma_H2 > 0 else float('inf')
    SF2 = sig_F_lim_pa6 / sigma_F2 if sigma_F2 > 0 else float('inf')

    lines.append(f"  m2 = {m2}, Z = {Z2_sun}-{Z2_planet}-{Z2_ring}, b2 = {b2}, n_sat = {n_sat2}")
    lines.append(f"  i2 = {i2:.2f}, d_sun = {d2_sun:.1f}, d_ring = {d2_ring:.1f}")
    lines.append(f"  T_in = {T1_out:.2f} Nm, T_out = {T2_out:.2f} Nm, n_out = {n2_out:.2f} rpm")
    lines.append(f"  Contact: sigma_H = {sigma_H2:.2f} MPa (limit = {sig_H_lim_pa6:.1f}) -> SH = {SH2:.2f}")
    lines.append(f"  Bending:  sigma_F = {sigma_F2:.2f} MPa (limit = {sig_F_lim_pa6:.1f}) -> SF = {SF2:.2f}")
    lines.append("")

    i_total = i1 * i2
    D_outer = d2_ring + m2 * 2

    min_SH = min(SH1, SH2)
    min_SF = min(SF1, SF2)

    lines.append("SUMMARY")
    lines.append("-"*90)
    lines.append(f"  Total ratio: i = {i1:.0f} x {i2:.0f} = {i_total:.0f}")
    lines.append(f"  Output torque: {T2_out:.1f} Nm (required: 60 Nm) -> {'OK' if T2_out >= 60 else 'FAIL'}")
    lines.append(f"  Output speed: {n2_out:.2f} rpm")
    lines.append(f"  Max diameter: {D_outer:.1f} mm (limit: 200 mm) -> {'OK' if D_outer <= 200 else 'FAIL'}")
    lines.append(f"  Total width: {b1 + b2} mm")
    lines.append(f"  Min safety (SH/SF): {min_SH:.2f} / {min_SF:.2f} -> {'OK' if min_SH >= 1.3 and min_SF >= 1.3 else 'MARGINAL'}")
    lines.append("")
    lines.append("="*90)

    return {
        'name': name,
        'i_total': i_total,
        'T_output': T2_out,
        'n_output': n2_out,
        'D_outer': D_outer,
        'b_total': b1 + b2,
        'SH': min_SH,
        'SF': min_SF,
        'report': '\n'.join(lines),
        'pass_T': T2_out >= 60,
        'pass_D': D_outer <= 200,
        'pass_relief': min_SH >= 1.3 and min_SF >= 1.3,
    }

print("="*90)
print("  ADAPTATION TO POM_C")
print("="*90)
print()

results = []
report_dir = Path('REPORT/SPIDER_KNEE/_data')
report_dir.mkdir(parents=True, exist_ok=True)

for config in configs:
    result = adapt_design(*config)
    results.append(result)
    print(result['report'])

    # Save report
    report_file = report_dir / f"{config[0]}.txt"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(result['report'])
    print(f"Saved: {report_file}\n")

# Summary
print("\nSUMMARY TABLE")
print("-"*90)
print(f"{'Name':<50} {'i':<6} {'T_out':<8} {'SH/SF':<10} {'Status'}")
print("-"*90)

for r in sorted(results, key=lambda x: (x['D_outer'], x['b_total'])):
    status = "OK" if (r['pass_T'] and r['pass_D'] and r['pass_relief']) else "REVIEW"
    print(f"{r['name']:<50} {r['i_total']:<6.0f} {r['T_output']:<8.1f} {r['SH']:.2f}/{r['SF']:.2f}   {status}")
