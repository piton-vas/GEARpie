"""GEARpie i18n module.

Provides string translations for English and Russian.
Default language is English (preserves original GEARpie behavior).
Russian translation follows GOST terminology with English term in parentheses
for engineering clarity. See docs/GLOSSARY_RU.md for term reference.

Usage:
    from CLASSES import I18N
    I18N.set_lang('ru')          # switch language
    I18N.t('header_gear_materials')  # → 'МАТЕРИАЛЫ ШЕСТЕРЁН'
"""

LANG = 'en'


def set_lang(code):
    """Set active language. Falls back to 'en' for unknown codes."""
    global LANG
    LANG = code if code in STRINGS else 'en'


def t(key):
    """Translate `key` into the active language. Falls back to EN, then key."""
    return STRINGS[LANG].get(key, STRINGS['en'].get(key, key))


STRINGS = {
    'en': {
        # === language selector ==============================================
        'prompt_lang': 'Language / Язык (en/ru) [en]: ',

        # === GEARpie.py CLI prompts =========================================
        'cli_geom_list': 'Gear geometries available:',
        'cli_geom_new': 'To use a new geometry, type NEW',
        'prompt_gear_type': 'Input gear geometry: ',
        'cli_mat_list': 'Materials available:',
        'prompt_pinion_mat': 'Pinion material (default: STEEL): ',
        'prompt_wheel_mat': 'Wheel material (default: STEEL): ',
        'prompt_base_oil': 'Base Oil (M - mineral, P - PAO, E - ester, G - polyglicol, D - dry): ',
        'prompt_ambient_temp': 'Ambient temperature / °C: ',
        'prompt_iso_vg': 'ISO VG grade (32 to 680): ',
        'prompt_lub_temp': 'Lubricant temperature / °C: ',
        'prompt_pw_select': 'Select (P - Pinion, W - Wheel or F - FZG) to apply torque and speed: ',
        'prompt_fzg_speed': 'FZG motor speed / rpm: ',
        'prompt_torque': 'Torque / Nm: ',
        'prompt_speed': 'Speed / rpm: ',
        'prompt_load_sharing': 'Consider Load-Sharing (Y/N): ',
        'prompt_stress_pos': 'Stress field position along AE (A, B, C, D or E): ',
        'prompt_graphics': 'Graphical output (Y/N): ',
        'prompt_mesh': 'FEM mesh generation (Y/N): ',
        'prompt_mesh_dim': 'Mesh dimension (2/3): ',
        'prompt_elem_order': 'Element order (1/2): ',
        'prompt_pinion_teeth': 'Number of tooth for pinion mesh: ',
        'prompt_pinion_nodes': 'Nº of nodes on pinion meshing surface: ',
        'prompt_wheel_teeth': 'Number of tooth for wheel mesh: ',
        'prompt_wheel_nodes': 'Nº of nodes on wheel meshing surface: ',
        'prompt_exit': 'Press enter to exit',

        # === OUTPUT_PRINT.py report headers =================================
        'rep_suffix_gear': ' GEAR',
        'rep_suffix_lubricant': ' LUBRICANT',
        'header_gear_materials': 'GEAR MATERIALS',
        'header_gear_geometry': 'GEAR GEOMETRY:',
        'header_contact_ratio': 'CONTACT RATIO',
        'header_path_dims': 'PATH OF CONTACT DIMENSIONS',
        'header_operating': 'OPERATING CONDITIONS',
        'header_contact_results': 'CONTACT RESULTS',
        'header_film_thickness': 'FILM THICKNESS',
        'header_power_loss': 'POWER LOSS',
        'header_lcc': 'LOAD CARRYING CAPACITY',

        # === OUTPUT_PRINT.py subheadings ====================================
        'sub_pinion': 'Pinion:',
        'sub_wheel': 'Wheel:',
        'sub_max_pressure': 'Maximum pressure p0:',
        'sub_mean_pressure': 'Mean pressure pm:',
        'sub_contact_half_width': 'Contact half-width aH:',
        'sub_central_film': 'Central Film Thickness h0C:',
        'sub_min_film': 'Minimum Film Thickness hmC:',
        'sub_influence_factors': 'Influence factors:',
        'sub_contact_factors': 'Contact factors:',
        'sub_bending_factors': 'Bending factors:',
        'sub_contact_factors_pa66': 'Contact factors (Valid for lubricated PA66 gears):',
        'sub_at_pitch_point': '  At pitch point:',
        'sub_max_along_ae': '  Maximum along AE:',
        'sub_min_along_ae': '  Minimum along AE:',
        'sub_avg_along_ae': '  Average along AE:',

        # === OUTPUT_PRINT.py fields: geometry ===============================
        'fld_pressure_angle': 'Pressure angle α:',
        'fld_helix_angle': 'Helix angle β:',
        'fld_module': 'Module m:',
        'fld_z1': 'Number of teeth z1:',
        'fld_z2': 'Number of teeth z2:',
        'fld_x1': 'Profile shift x1:',
        'fld_x2': 'Profile shift x2:',
        'fld_axis_distance': 'Axis distance:',
        'fld_base_pitch_n': 'Base pitch n:',
        'fld_base_pitch_t': 'Base pitch t:',
        'fld_root_radius': 'Root radius:',
        'fld_base_radius': 'Base radius:',
        'fld_reference_radius': 'Reference radius:',
        'fld_pitch_radius': 'Pitch radius:',
        'fld_tip_radius': 'Tip radius:',

        # === OUTPUT_PRINT.py fields: contact ratio ==========================
        'fld_eps_alpha': 'Transverse εα:',
        'fld_eps_beta': 'Overlap εβ:',
        'fld_eps_gama': 'Total εγ:',

        # === OUTPUT_PRINT.py fields: materials ==============================
        'fld_E1': '  Young modulus E1:',
        'fld_v1': '  Poisson ratio ν1:',
        'fld_cp1': '  Thermal capacity cp1:',
        'fld_k1': '  Thermal conductivity k1:',
        'fld_rho1': '  Density ρ1:',
        'fld_E2': '  Young modulus E2:',
        'fld_v2': '  Poisson ratio ν2:',
        'fld_cp2': '  Thermal capacity cp2:',
        'fld_k2': '  Thermal conductivity k2:',
        'fld_rho2': '  Density ρ2:',

        # === OUTPUT_PRINT.py fields: lubricant ==============================
        'fld_lub_temp': 'Lubricant temperature',
        'fld_kin_visc': 'Kinematic viscosity ν:',
        'fld_dyn_visc': 'Dynamic viscosity η:',
        'fld_density_15': 'Density @ 15 °C  ρ₀:',
        'fld_density_at': 'Density @ {temp:.0f} °C ρ:',
        'fld_piezo': 'Piezo-viscosity coefficient α:',
        'fld_thermo': 'Thermo-viscosity β:',
        'fld_xl': 'Lubricant parameter XL:',

        # === OUTPUT_PRINT.py fields: operating ==============================
        'fld_pin': 'Input power Pin:',
        'fld_torque': 'Torque T:',
        'fld_speed': 'Speed n:',
        'fld_omega': 'Angular speed ω:',
        'fld_vt': 'Tangential speed vt:',
        'fld_vtb': 'Base tangent speed vtb:',
        'fld_gs_max': 'Maximum specific sliding gs:',
        'fld_ft': 'Tangential load F_t:',
        'fld_fr': 'Radial load F_r:',
        'fld_fn': 'Normal load F_n:',
        'fld_fa': 'Axial load F_a:',
        'fld_fbt': 'Base circle load F_bt:',
        'fld_fbn': 'Base circle load F_bn:',

        # === OUTPUT_PRINT.py fields: contact results ========================
        'fld_mises': 'Maximum von Mises Stress:',
        'fld_tau_max': 'Maximum Shear Stress:',
        'fld_tau_oct': 'Maximum Octahedric Shear Stress:',

        # === OUTPUT_PRINT.py fields: film thickness =========================
        'fld_inlet_shear': 'Average Inlet Shear Heating:',
        'fld_lambda_central': 'Central lambda ratio Λ0C:',
        'fld_lambda_min': 'Minimum lambda ratio ΛmC:',

        # === OUTPUT_PRINT.py fields: power loss =============================
        'fld_hvl_wimmer': 'Gear Loss Factor HVL:',
        'fld_hv_ohlendorf': 'Gear Loss Factor HV:',
        'fld_cof': 'Coefficient of Friction μmZ:',
        'fld_pvzp_avg': 'Average Power Loss Pvzp:',
        'fld_pvzp_max': 'Maximum Local Power Loss Pvzp:',
        'fld_pvzp_min': 'Minimum Local Power Loss Pvzp:',

        # === OUTPUT_PRINT.py fields: LCC (DIN 3990) =========================
        'fld_ka': '  Application factor KA: ',
        'fld_kv': '  Dynamic factor KV: ',
        'fld_khb': '  Face load factor contact KHβ: ',
        'fld_kfb': '  Face load factor bending KFβ: ',
        'fld_kha': '  Transverse factor contact KHα: ',
        'fld_kfa': '  Transverse factor bending KFα: ',
        'fld_ze': '  Elasticity factor ZE: ',
        'fld_zh': '  Zone factor ZH: ',
        'fld_zeps': '  Contact ratio factor Zε: ',
        'fld_zbeta': '  Helix angle factor Zβ: ',
        'fld_zl': '  Lubrication factor ZL: ',
        'fld_zv': '  Speed factor ZV: ',
        'fld_sigmaH0': 'Nominal contact stress: ',
        'fld_sigmaH': 'Contact stress: ',
        'fld_sigmaHP': 'Permissible contact stress: ',
        'fld_sh': 'Contact stress safety factor SH: ',
        'fld_yf': '  Form factor YF: ',
        'fld_ys': '  Stress correction factor YS: ',
        'fld_yb': '  Helix angle factor Yβ: ',
        'fld_ydelt': '  Notch sensitivity factor YδT: ',
        'fld_yrt': '  Surface factor YRT: ',
        'fld_sigmaF0': 'Nominal root stress: ',
        'fld_sigmaF': 'Tooth root stress: ',
        'fld_sigmaFG': 'Limit tooth root stress: ',
        'fld_sigmaFP': 'Permissible tooth root stress: ',
        'fld_sf': 'Tooth root stress safety factor SF: ',

        # === OUTPUT_PRINT.py fields: LCC (VDI 2736 plastic) =================
        'fld_ambient_temp': 'Ambient temperature',
        'fld_root_temp': 'Root temperature',
        'fld_flank_temp': 'Flank temperature',
        'fld_ka_combined': '  Application factor KA=KF=KH: ',
        'fld_yfa': '  Form factor YFa: ',
        'fld_ysa': '  Stress correction factor YSa: ',
        'fld_yeps': '  Contact ratio factor Yε: ',
        'fld_ybeta': '  Helix angle factor Yβ: ',

        # === PLOTTING.py titles and legends =================================
        'plot_lbl_pinion': 'pinion',
        'plot_lbl_wheel': 'wheel',
        'plot_specific_sliding': 'Specific Sliding',
        'plot_load_face_width': 'Load per face width',
        'plot_load_face_width_friction': 'Load per face width with friction',
        'plot_sliding_speed': 'Sliding Speed',
        'plot_contact_pressure': 'Contact pressure',
        'plot_heat_flux_inst': 'Instantaneous heat flux',
        'plot_heat_flux_avg': 'Average heat flux',
    },

    'ru': {
        # === селектор языка =================================================
        'prompt_lang': 'Language / Язык (en/ru) [en]: ',

        # === CLI prompts (GEARpie.py) =======================================
        'cli_geom_list': 'Доступные геометрии передач:',
        'cli_geom_new': 'Для новой геометрии введите NEW',
        'prompt_gear_type': 'Геометрия передачи: ',
        'cli_mat_list': 'Доступные материалы:',
        'prompt_pinion_mat': 'Материал шестерни (по умолчанию STEEL): ',
        'prompt_wheel_mat': 'Материал колеса (по умолчанию STEEL): ',
        'prompt_base_oil': 'Базовое масло (M — минер., P — ПАО, E — эфир, G — полигликоль, D — без смазки): ',
        'prompt_ambient_temp': 'Температура окружающей среды / °C: ',
        'prompt_iso_vg': 'Класс вязкости ISO VG (32–680): ',
        'prompt_lub_temp': 'Температура смазки / °C: ',
        'prompt_pw_select': 'Где задаются крутящий момент и частота вращения (P — шестерня, W — колесо, F — FZG): ',
        'prompt_fzg_speed': 'Частота вращения двигателя FZG / об/мин: ',
        'prompt_torque': 'Крутящий момент / Н·м: ',
        'prompt_speed': 'Частота вращения / об/мин: ',
        'prompt_load_sharing': 'Учитывать распределение нагрузки между зубьями (Y/N): ',
        'prompt_stress_pos': 'Положение для расчёта поля напряжений на AE (A, B, C, D или E): ',
        'prompt_graphics': 'Графический вывод (Y/N): ',
        'prompt_mesh': 'Генерация конечно-элементной сетки (Y/N): ',
        'prompt_mesh_dim': 'Размерность сетки (2/3): ',
        'prompt_elem_order': 'Порядок конечного элемента (1/2): ',
        'prompt_pinion_teeth': 'Число зубьев для сетки шестерни: ',
        'prompt_pinion_nodes': 'Число узлов на рабочей поверхности шестерни: ',
        'prompt_wheel_teeth': 'Число зубьев для сетки колеса: ',
        'prompt_wheel_nodes': 'Число узлов на рабочей поверхности колеса: ',
        'prompt_exit': 'Нажмите Enter для выхода',

        # === заголовки разделов отчёта ======================================
        'rep_suffix_gear': ' — ЗУБЧАТАЯ ПЕРЕДАЧА',
        'rep_suffix_lubricant': ' — СМАЗКА',
        'header_gear_materials': 'МАТЕРИАЛЫ ЗУБЧАТЫХ КОЛЁС',
        'header_gear_geometry': 'ГЕОМЕТРИЯ ПЕРЕДАЧИ:',
        'header_contact_ratio': 'КОЭФФИЦИЕНТ ПЕРЕКРЫТИЯ',
        'header_path_dims': 'РАЗМЕРЫ ЛИНИИ ЗАЦЕПЛЕНИЯ',
        'header_operating': 'РЕЖИМ РАБОТЫ',
        'header_contact_results': 'КОНТАКТНЫЕ ХАРАКТЕРИСТИКИ',
        'header_film_thickness': 'ТОЛЩИНА СМАЗОЧНОЙ ПЛЁНКИ',
        'header_power_loss': 'ПОТЕРИ МОЩНОСТИ',
        'header_lcc': 'НАГРУЗОЧНАЯ СПОСОБНОСТЬ',

        # === подзаголовки ====================================================
        'sub_pinion': 'Шестерня:',
        'sub_wheel': 'Колесо:',
        'sub_max_pressure': 'Макс. контактное давление p0:',
        'sub_mean_pressure': 'Среднее контактное давление pm:',
        'sub_contact_half_width': 'Полуширина пятна контакта aH:',
        'sub_central_film': 'Центральная толщина плёнки h0C:',
        'sub_min_film': 'Минимальная толщина плёнки hmC:',
        'sub_influence_factors': 'Поправочные коэффициенты:',
        'sub_contact_factors': 'Контактные коэффициенты:',
        'sub_bending_factors': 'Коэффициенты изгибной прочности:',
        'sub_contact_factors_pa66': 'Контактные коэффициенты (только для PA66 со смазкой):',
        'sub_at_pitch_point': '  В полюсе зацепления:',
        'sub_max_along_ae': '  Максимум по AE:',
        'sub_min_along_ae': '  Минимум по AE:',
        'sub_avg_along_ae': '  Среднее по AE:',

        # === поля: геометрия ================================================
        'fld_pressure_angle': 'Угол профиля α (pressure angle):',
        'fld_helix_angle': 'Угол наклона зуба β (helix angle):',
        'fld_module': 'Модуль m (module):',
        'fld_z1': 'Число зубьев шестерни z1:',
        'fld_z2': 'Число зубьев колеса z2:',
        'fld_x1': 'Коэф. смещения x1 (profile shift):',
        'fld_x2': 'Коэф. смещения x2 (profile shift):',
        'fld_axis_distance': 'Межосевое расстояние (axis distance):',
        'fld_base_pitch_n': 'Основной шаг (normal) n:',
        'fld_base_pitch_t': 'Основной шаг (transverse) t:',
        'fld_root_radius': 'Радиус впадин (root):',
        'fld_base_radius': 'Радиус основной окружности (base):',
        'fld_reference_radius': 'Делительный радиус (reference):',
        'fld_pitch_radius': 'Начальный радиус (pitch):',
        'fld_tip_radius': 'Радиус вершин (tip):',

        # === поля: коэф. перекрытия =========================================
        'fld_eps_alpha': 'Торцовый εα (transverse):',
        'fld_eps_beta': 'Осевой εβ (overlap):',
        'fld_eps_gama': 'Суммарный εγ (total):',

        # === поля: материалы ================================================
        'fld_E1': '  Модуль упругости E1 (Young):',
        'fld_v1': '  Коэф. Пуассона ν1 (Poisson):',
        'fld_cp1': '  Удельная теплоёмкость cp1:',
        'fld_k1': '  Теплопроводность k1:',
        'fld_rho1': '  Плотность ρ1:',
        'fld_E2': '  Модуль упругости E2 (Young):',
        'fld_v2': '  Коэф. Пуассона ν2 (Poisson):',
        'fld_cp2': '  Удельная теплоёмкость cp2:',
        'fld_k2': '  Теплопроводность k2:',
        'fld_rho2': '  Плотность ρ2:',

        # === поля: смазка ====================================================
        'fld_lub_temp': 'Температура смазки',
        'fld_kin_visc': 'Кинематическая вязкость ν:',
        'fld_dyn_visc': 'Динамическая вязкость η:',
        'fld_density_15': 'Плотность при 15 °C  ρ₀:',
        'fld_density_at': 'Плотность при {temp:.0f} °C ρ:',
        'fld_piezo': 'Коэф. пьезовязкости α (piezo-viscosity):',
        'fld_thermo': 'Коэф. термовязкости β (thermo-viscosity):',
        'fld_xl': 'Параметр смазки XL:',

        # === поля: режим работы =============================================
        'fld_pin': 'Входная мощность Pin (input power):',
        'fld_torque': 'Крутящий момент T (torque):',
        'fld_speed': 'Частота вращения n (speed):',
        'fld_omega': 'Угловая скорость ω (angular speed):',
        'fld_vt': 'Окружная скорость vt (tangential):',
        'fld_vtb': 'Скорость по основной окружности vtb:',
        'fld_gs_max': 'Макс. удельное скольжение gs (specific sliding):',
        'fld_ft': 'Окружная сила F_t (tangential):',
        'fld_fr': 'Радиальная сила F_r (radial):',
        'fld_fn': 'Нормальная сила F_n (normal):',
        'fld_fa': 'Осевая сила F_a (axial):',
        'fld_fbt': 'Сила по основной окружности F_bt:',
        'fld_fbn': 'Сила по основной окружности F_bn:',

        # === поля: контактные результаты ====================================
        'fld_mises': 'Макс. напряжение по Мизесу (von Mises):',
        'fld_tau_max': 'Макс. касательное напряжение (shear):',
        'fld_tau_oct': 'Макс. октаэдрическое касат. напр. (octahedric):',

        # === поля: плёнка ===================================================
        'fld_inlet_shear': 'Средний коэф. сдвигового нагрева на входе φT:',
        'fld_lambda_central': 'Отношение толщины плёнки Λ0C (film thickness ratio):',
        'fld_lambda_min': 'Мин. отношение толщины плёнки ΛmC (film thickness ratio):',

        # === поля: потери мощности ==========================================
        'fld_hvl_wimmer': 'Коэф. потерь зацепления HVL (gear loss factor):',
        'fld_hv_ohlendorf': 'Коэф. потерь зацепления HV (gear loss factor):',
        'fld_cof': 'Коэф. трения μmZ (CoF):',
        'fld_pvzp_avg': 'Средние потери мощности Pvzp (power loss):',
        'fld_pvzp_max': 'Макс. локальные потери мощности Pvzp:',
        'fld_pvzp_min': 'Мин. локальные потери мощности Pvzp:',

        # === поля: LCC (DIN 3990) ===========================================
        'fld_ka': '  Коэф. внешней дин. нагрузки KA (application): ',
        'fld_kv': '  Коэф. внутр. дин. нагрузки KV (dynamic): ',
        'fld_khb': '  Коэф. неравномерности по длине (контакт) KHβ: ',
        'fld_kfb': '  Коэф. неравномерности по длине (изгиб) KFβ: ',
        'fld_kha': '  Коэф. распределения между зубьями (контакт) KHα: ',
        'fld_kfa': '  Коэф. распределения между зубьями (изгиб) KFα: ',
        'fld_ze': '  Коэф. упругости материалов ZE (elasticity): ',
        'fld_zh': '  Коэф. формы сопряж. поверхностей ZH (zone): ',
        'fld_zeps': '  Коэф. торцового перекрытия Zε (contact ratio): ',
        'fld_zbeta': '  Коэф. угла наклона зуба Zβ (helix): ',
        'fld_zl': '  Коэф. влияния смазки ZL (lubrication): ',
        'fld_zv': '  Коэф. влияния скорости ZV (speed): ',
        'fld_sigmaH0': 'Номинальное контактное напряжение σH0 (nominal): ',
        'fld_sigmaH': 'Контактное напряжение σH (contact stress): ',
        'fld_sigmaHP': 'Допускаемое контактное напр. σHP (permissible): ',
        'fld_sh': 'Коэф. запаса по контакту SH (safety factor): ',
        'fld_yf': '  Коэф. формы зуба YF (form): ',
        'fld_ys': '  Коэф. концентрации напряжений YS (stress corr.): ',
        'fld_yb': '  Коэф. угла наклона зуба Yβ (helix): ',
        'fld_ydelt': '  Коэф. отн. чувствительности YδT (notch sens.): ',
        'fld_yrt': '  Коэф. отн. шероховатости YRT (surface): ',
        'fld_sigmaF0': 'Номинальное изгибное напр. σF0 (nominal root): ',
        'fld_sigmaF': 'Изгибное напряжение σF (root stress): ',
        'fld_sigmaFG': 'Предельное изгибное напр. σFG (limit): ',
        'fld_sigmaFP': 'Допускаемое изгибное напр. σFP (permissible): ',
        'fld_sf': 'Коэф. запаса по изгибу SF (safety factor): ',

        # === поля: LCC (VDI 2736, пластики) =================================
        'fld_ambient_temp': 'Температура окр. среды (ambient)',
        'fld_root_temp': 'Температура ножки зуба (root)',
        'fld_flank_temp': 'Температура рабочей поверхности зуба (flank)',
        'fld_ka_combined': '  Коэф. нагрузки KA=KF=KH (application): ',
        'fld_yfa': '  Коэф. формы зуба YFa (form): ',
        'fld_ysa': '  Коэф. концентрации напряжений YSa (stress corr.): ',
        'fld_yeps': '  Коэф. перекрытия Yε (contact ratio): ',
        'fld_ybeta': '  Коэф. угла наклона зуба Yβ (helix): ',

        # === графики ========================================================
        'plot_lbl_pinion': 'шестерня',
        'plot_lbl_wheel': 'колесо',
        'plot_specific_sliding': 'Удельное скольжение',
        'plot_load_face_width': 'Распределение нагрузки по ширине',
        'plot_load_face_width_friction': 'Нагрузка по ширине с учётом трения',
        'plot_sliding_speed': 'Скорость скольжения',
        'plot_contact_pressure': 'Контактное давление',
        'plot_heat_flux_inst': 'Мгновенный тепловой поток',
        'plot_heat_flux_avg': 'Средний тепловой поток',
    },
}
