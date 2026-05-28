"""
Filter variants with transmission ratio 32-35
"""

import json

# Load JSON report
with open('REPORT/SPIDER_KNEE/design_variants.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Filter variants with i between 32 and 35
filtered = [v for v in data['variants'] if 32 <= v['i_total'] <= 35]

# Sort by diameter and module (prefer larger module for printing)
filtered.sort(key=lambda x: (x['max_diameter_mm'], -x['module_mm']))

print("=" * 90)
print("OPTIMAL VARIANTS WITH TRANSMISSION RATIO 32-35")
print("Spider robot knee")
print("=" * 90)

print(f"\nFound {len(filtered)} variants with i in [32..35]\n")

# Show first 15 variants
for i, var in enumerate(filtered[:15], 1):
    s1 = var['stage_1']
    s2 = var['stage_2']

    print(f"\n--- VARIANT {i} ---")
    print(f"Transmission ratio: {var['i_total']:.2f}x")
    print(f"Housing diameter: {var['max_diameter_mm']:.1f} mm | Module: {var['module_mm']} mm")
    print(f"Output torque: {var['output_torque_nm']:.1f} Nm")
    print(f"Safety factor: {var['stress_analysis']['min_sf']:.1f}")

    print(f"\n  STAGE 1 (i={var['stage_1']['ratio']:.2f}x):")
    print(f"    Sun: z={s1['z_sun']}, d={s1['d_sun_mm']:.1f} mm")
    print(f"    Ring: z={s1['z_ring']}, d={s1['d_ring_mm']:.1f} mm")
    print(f"    Satellites: {s1['n_satellites']}x (z={s1['z_satellite']}, d={s1['d_satellite_mm']:.1f} mm)")
    print(f"    Housing: d={s1['d_housing_mm']:.1f} mm, width {s1['width_mm']} mm")

    print(f"\n  STAGE 2 (i={var['stage_2']['ratio']:.2f}x):")
    print(f"    Sun: z={s2['z_sun']}, d={s2['d_sun_mm']:.1f} mm")
    print(f"    Ring: z={s2['z_ring']}, d={s2['d_ring_mm']:.1f} mm")
    print(f"    Satellites: {s2['n_satellites']}x (z={s2['z_satellite']}, d={s2['d_satellite_mm']:.1f} mm)")
    print(f"    Housing: d={s2['d_housing_mm']:.1f} mm, width {s2['width_mm']} mm")

    print(f"\n  PETG Stresses:")
    print(f"    Stage 1: {var['stress_analysis']['stage_1_stress_mpa']:.1f} MPa (SF={var['stress_analysis']['stage_1_sf']:.1f})")
    print(f"    Stage 2: {var['stress_analysis']['stage_2_stress_mpa']:.1f} MPa (SF={var['stress_analysis']['stage_2_sf']:.1f})")

print("\n" + "=" * 90)
print("\nTOP RECOMMENDATIONS FOR PETG 3D PRINTING:")
print("=" * 90)

# Find variants with good module (>= 1.5) and diameter 30-60 mm
best = [v for v in filtered if 1.5 <= v['module_mm'] and 30 <= v['max_diameter_mm'] <= 60]
best.sort(key=lambda x: (x['module_mm'], x['max_diameter_mm']))

if best:
    for i, var in enumerate(best[:3], 1):
        s1 = var['stage_1']
        s2 = var['stage_2']
        print(f"\n[BEST-{i}] i={var['i_total']:.2f}, m={var['module_mm']} mm, D={var['max_diameter_mm']:.1f} mm")
        print(f"  Stage 1: Z{s1['z_sun']}-{s1['z_ring']}-{s1['z_satellite']} ({s1['n_satellites']} sat), ratio {var['stage_1']['ratio']:.2f}x")
        print(f"  Stage 2: Z{s2['z_sun']}-{s2['z_ring']}-{s2['z_satellite']} ({s2['n_satellites']} sat), ratio {var['stage_2']['ratio']:.2f}x")
        print(f"  Output torque: {var['output_torque_nm']:.1f} Nm | Min SF: {var['stress_analysis']['min_sf']:.1f}")
else:
    print("\nNo variants with m >= 1.5 and D 30-60 mm found.")
    print("Looking for more compact options (D <= 30 mm):")
    compact = [v for v in filtered if v['max_diameter_mm'] <= 30]
    compact.sort(key=lambda x: (-x['module_mm'], x['max_diameter_mm']))
    for i, var in enumerate(compact[:3], 1):
        s1 = var['stage_1']
        s2 = var['stage_2']
        print(f"\n[COMPACT-{i}] i={var['i_total']:.2f}, m={var['module_mm']} mm, D={var['max_diameter_mm']:.1f} mm")
        print(f"  Stage 1: Z{s1['z_sun']}-{s1['z_ring']}-{s1['z_satellite']} ({s1['n_satellites']} sat)")
        print(f"  Stage 2: Z{s2['z_sun']}-{s2['z_ring']}-{s2['z_satellite']} ({s2['n_satellites']} sat)")
        print(f"  Torque: {var['output_torque_nm']:.1f} Nm | SF: {var['stress_analysis']['min_sf']:.1f}")

print("\n" + "=" * 90)
