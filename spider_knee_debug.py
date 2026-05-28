#!/usr/bin/env python3
"""Debug script to see what configurations are generated"""

import sys
sys.dont_write_bytecode = True

from CLASSES import MATERIAL_LIBRARY
import json
from pathlib import Path

T_input = 3.7
n_input = 150
T_required = 60
D_max = 200
b_max = 40
T_amb = 25.0

modules = [1.0, 1.25, 1.5]
configs_2stage = [
    (6, 6, 3, 4, "6x6"),
    (8, 4, 3, 4, "8x4"),
]

def check_assembly(Z_sun, Z_ring, n_sat):
    return (Z_sun + Z_ring) % n_sat == 0

def calc_stage(m, Z_sun, Z_ring, n_sat, T_in, n_in, mat_sun, mat_planet, b):
    """Calculate one planetary stage"""

    Z_planet = (Z_sun + Z_ring) // 2
    d_sun = m * Z_sun
    d_ring = m * Z_ring
    d_planet = m * Z_planet

    if not check_assembly(Z_sun, Z_ring, n_sat):
        return None

    i_stage = 1 + Z_ring / Z_sun
    T_out = T_in * i_stage
    n_out = n_in / i_stage

    F_t = (2 * T_in * 1e3) / d_sun

    mat_sun_lib = MATERIAL_LIBRARY.LIBRARY_MAT(mat_sun)
    mat_planet_lib = MATERIAL_LIBRARY.LIBRARY_MAT(mat_planet)

    E1 = mat_sun_lib.E
    E2 = mat_planet_lib.E
    v1 = mat_sun_lib.v
    v2 = mat_planet_lib.v

    E_red = 1 / ((1 - v1**2) / E1 + (1 - v2**2) / E2)

    R_sun = d_sun / 2
    R_planet = d_planet / 2
    R_eq = (R_sun * R_planet) / (R_sun + R_planet)

    sigma_H = ((F_t / (b * R_eq)) * (E_red / 2)) ** 0.5 / 1000

    sigma_F = F_t / (b * m) * 1.5

    sigma_H_lim = mat_planet_lib.SigmaHlim(T_amb, 1e9) if callable(mat_planet_lib.SigmaHlim) else mat_planet_lib.SigmaHlim
    sigma_F_lim = mat_planet_lib.SigmaFlim(T_amb, 1e9) if callable(mat_planet_lib.SigmaFlim) else mat_planet_lib.SigmaFlim

    SH = sigma_H_lim / sigma_H if sigma_H > 0 else float('inf')
    SF = sigma_F_lim / sigma_F if sigma_F > 0 else float('inf')

    return {
        'm': m,
        'Z_sun': Z_sun,
        'Z_ring': Z_ring,
        'Z_planet': Z_planet,
        'n_sat': n_sat,
        'b': b,
        'd_sun': d_sun,
        'd_ring': d_ring,
        'i_stage': i_stage,
        'T_out': T_out,
        'n_out': n_out,
        'sigma_H': sigma_H,
        'sigma_F': sigma_F,
        'sigma_H_lim': sigma_H_lim,
        'sigma_F_lim': sigma_F_lim,
        'SH': SH,
        'SF': SF,
    }

print("Testing configuration: i=36 (6x6)")
print("Materials: POM_C sun, PA6_PRINT satellites")
print()

# Test i=6x6
i1, i2 = 6, 6

# Stage 1: i1=6, so Z_ring/Z_sun = 5
# Test Z_sun=18, Z_ring=90, 3 satellites
s1 = calc_stage(1.5, 18, 90, 3, T_input, n_input, 'POM_C', 'PA6_PRINT', 30)

if s1:
    print(f"Stage 1: m=1.5, Z={s1['Z_sun']}-{s1['Z_planet']}-{s1['Z_ring']}, b=30")
    print(f"  i1 = {s1['i_stage']:.2f}")
    print(f"  T_out = {s1['T_out']:.2f} Nm")
    print(f"  d_ring = {s1['d_ring']:.1f} mm")
    print(f"  sigma_H = {s1['sigma_H']:.2f} MPa, limit = {s1['sigma_H_lim']:.1f}, SH = {s1['SH']:.2f}")
    print(f"  sigma_F = {s1['sigma_F']:.2f} MPa, limit = {s1['sigma_F_lim']:.1f}, SF = {s1['SF']:.2f}")
    print()

    # Stage 2: i2=6
    s2 = calc_stage(2.0, 18, 90, 4, s1['T_out'], s1['n_out'], 'POM_C', 'PA6_PRINT', 40)

    if s2:
        print(f"Stage 2: m=2.0, Z={s2['Z_sun']}-{s2['Z_planet']}-{s2['Z_ring']}, b=40")
        print(f"  i2 = {s2['i_stage']:.2f}")
        print(f"  T_out = {s2['T_out']:.2f} Nm (required: {T_required} Nm)")
        print(f"  d_ring = {s2['d_ring']:.1f} mm (max: {D_max} mm)")
        print(f"  sigma_H = {s2['sigma_H']:.2f} MPa, limit = {s2['sigma_H_lim']:.1f}, SH = {s2['SH']:.2f}")
        print(f"  sigma_F = {s2['sigma_F']:.2f} MPa, limit = {s2['sigma_F_lim']:.1f}, SF = {s2['SF']:.2f}")
        print()

        i_total = s1['i_stage'] * s2['i_stage']
        print(f"Total: i = {i_total:.1f}")
        print(f"Output speed: {s2['n_out']:.2f} rpm")
        print()

        # Checks
        print("Checks:")
        print(f"  Torque: {s2['T_out']:.2f} >= {T_required} ? {s2['T_out'] >= T_required}")
        print(f"  Diameter: {s2['d_ring'] + 4:.0f} <= {D_max} ? {s2['d_ring'] + 4 <= D_max}")
        print(f"  SH: {s2['SH']:.2f} >= 1.3 ? {s2['SH'] >= 1.3}")
        print(f"  SF: {s2['SF']:.2f} >= 1.3 ? {s2['SF'] >= 1.3}")

