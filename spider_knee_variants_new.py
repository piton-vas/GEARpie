"""
Новые варианты HIGH_I для требований 2026-05-28:
i > 32, 100% PA6-CF, компактные, 4 сателлита на ст.2.
"""

HIGH_I_VARIANTS_2026 = [
    {
        'legacy_name': 'HI_i35_7x5_A',
        'description': 'i=35 (7×5) компактная. m1=1.25 Z18-45-108 b1=20, m2=1.5 Z20-30-80 b2=25. T_out~105Nm, Lax~75.',
        'i1': 7, 'i2': 5,
        'n_sat_1': 3, 'n_sat_2': 4,
        'm1': 1.25, 'z_s1': 18, 'z_p1': 45, 'z_r1': 108, 'b1': 20,
        'x_s1': 0.0, 'x_p1': 0.0,
        'm2': 1.5, 'z_s2': 20, 'z_p2': 30, 'z_r2': 80, 'b2': 25,
        'x_s2': 0.0, 'x_p2': 0.0,
        'mat_s1': 'PA6_CF', 'mat_p1': 'PA6_CF', 'mat_r1': 'PA6_CF',
        'mat_s2': 'PA6_CF', 'mat_p2': 'PA6_CF', 'mat_r2': 'PA6_CF',
    },
    {
        'legacy_name': 'HI_i35_7x5_B',
        'description': 'i=35 (7×5) стандарт. b1=25 b2=35. T_out~105Nm, Lax~90. Баланс размера и запаса.',
        'i1': 7, 'i2': 5,
        'n_sat_1': 3, 'n_sat_2': 4,
        'm1': 1.25, 'z_s1': 18, 'z_p1': 45, 'z_r1': 108, 'b1': 25,
        'x_s1': 0.0, 'x_p1': 0.0,
        'm2': 1.5, 'z_s2': 20, 'z_p2': 30, 'z_r2': 80, 'b2': 35,
        'x_s2': 0.0, 'x_p2': 0.0,
        'mat_s1': 'PA6_CF', 'mat_p1': 'PA6_CF', 'mat_r1': 'PA6_CF',
        'mat_s2': 'PA6_CF', 'mat_p2': 'PA6_CF', 'mat_r2': 'PA6_CF',
    },
    {
        'legacy_name': 'HI_i32_8x4_A',
        'description': 'i=32 (8×4) минимум. m1=1.25 Z18-54-126 b1=20, m2=1.5 Z22-22-66 b2=20. T_out~96Nm, Lax~70.',
        'i1': 8, 'i2': 4,
        'n_sat_1': 3, 'n_sat_2': 4,
        'm1': 1.25, 'z_s1': 18, 'z_p1': 54, 'z_r1': 126, 'b1': 20,
        'x_s1': 0.0, 'x_p1': 0.0,
        'm2': 1.5, 'z_s2': 22, 'z_p2': 22, 'z_r2': 66, 'b2': 20,
        'x_s2': 0.0, 'x_p2': 0.0,
        'mat_s1': 'PA6_CF', 'mat_p1': 'PA6_CF', 'mat_r1': 'PA6_CF',
        'mat_s2': 'PA6_CF', 'mat_p2': 'PA6_CF', 'mat_r2': 'PA6_CF',
    },
    {
        'legacy_name': 'HI_i32_8x4_B',
        'description': 'i=32 (8×4) стандарт. b1=25 b2=32. T_out~96Nm, Lax~87. Рекомендуется.',
        'i1': 8, 'i2': 4,
        'n_sat_1': 3, 'n_sat_2': 4,
        'm1': 1.25, 'z_s1': 18, 'z_p1': 54, 'z_r1': 126, 'b1': 25,
        'x_s1': 0.0, 'x_p1': 0.0,
        'm2': 1.5, 'z_s2': 22, 'z_p2': 22, 'z_r2': 66, 'b2': 32,
        'x_s2': 0.0, 'x_p2': 0.0,
        'mat_s1': 'PA6_CF', 'mat_p1': 'PA6_CF', 'mat_r1': 'PA6_CF',
        'mat_s2': 'PA6_CF', 'mat_p2': 'PA6_CF', 'mat_r2': 'PA6_CF',
    },
    {
        'legacy_name': 'HI_i32_8x4_C',
        'description': 'i=32 (8×4) премиум. b1=30 b2=40. T_out~96Nm, Lax~100. Максимальный запас.',
        'i1': 8, 'i2': 4,
        'n_sat_1': 3, 'n_sat_2': 4,
        'm1': 1.25, 'z_s1': 18, 'z_p1': 54, 'z_r1': 126, 'b1': 30,
        'x_s1': 0.0, 'x_p1': 0.0,
        'm2': 1.5, 'z_s2': 22, 'z_p2': 22, 'z_r2': 66, 'b2': 40,
        'x_s2': 0.0, 'x_p2': 0.0,
        'mat_s1': 'PA6_CF', 'mat_p1': 'PA6_CF', 'mat_r1': 'PA6_CF',
        'mat_s2': 'PA6_CF', 'mat_p2': 'PA6_CF', 'mat_r2': 'PA6_CF',
    },
    {
        'legacy_name': 'HI_i36_6x6_A',
        'description': 'i=36 (6×6) симметричная. m1=1.5 Z18-36-90 b1=25, m2=1.5 Z18-36-90 b2=35. T_out~108Nm, Lax~90.',
        'i1': 6, 'i2': 6,
        'n_sat_1': 3, 'n_sat_2': 4,
        'm1': 1.5, 'z_s1': 18, 'z_p1': 36, 'z_r1': 90, 'b1': 25,
        'x_s1': 0.0, 'x_p1': 0.0,
        'm2': 1.5, 'z_s2': 18, 'z_p2': 36, 'z_r2': 90, 'b2': 35,
        'x_s2': 0.0, 'x_p2': 0.0,
        'mat_s1': 'PA6_CF', 'mat_p1': 'PA6_CF', 'mat_r1': 'PA6_CF',
        'mat_s2': 'PA6_CF', 'mat_p2': 'PA6_CF', 'mat_r2': 'PA6_CF',
    },
    {
        'legacy_name': 'HI_i40_8x5_A',
        'description': 'i=40 (8×5) максимум. m1=1.25 Z18-54-126 b1=28, m2=1.5 Z20-30-80 b2=35. T_out~120Nm, Lax~93.',
        'i1': 8, 'i2': 5,
        'n_sat_1': 3, 'n_sat_2': 4,
        'm1': 1.25, 'z_s1': 18, 'z_p1': 54, 'z_r1': 126, 'b1': 28,
        'x_s1': 0.0, 'x_p1': 0.0,
        'm2': 1.5, 'z_s2': 20, 'z_p2': 30, 'z_r2': 80, 'b2': 35,
        'x_s2': 0.0, 'x_p2': 0.0,
        'mat_s1': 'PA6_CF', 'mat_p1': 'PA6_CF', 'mat_r1': 'PA6_CF',
        'mat_s2': 'PA6_CF', 'mat_p2': 'PA6_CF', 'mat_r2': 'PA6_CF',
    },
]

if __name__ == '__main__':
    import sys
    sys.path.insert(0, '.')
    from spider_knee_variants import VARIANTS

    # Экспорт расширенного списка
    ALL_VARIANTS = VARIANTS + HIGH_I_VARIANTS_2026
    print(f"Загружено {len(VARIANTS)} базовых вариантов")
    print(f"Добавлено {len(HIGH_I_VARIANTS_2026)} новых вариантов")
    print(f"Итого: {len(ALL_VARIANTS)} вариантов")
