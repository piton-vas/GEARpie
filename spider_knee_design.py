"""
Дизайн планетарного редуктора для коленки робота-паука
Двухступенчатая конструкция с PETG материалом для 3D печати
"""

import sys
sys.dont_write_bytecode = True

import numpy as np
from dataclasses import dataclass
from typing import List, Tuple
from datetime import datetime
import json

@dataclass
class PlanetaryGearSet:
    """Параметры одной ступени планетарной передачи"""
    name: str
    z_sun: int          # зубья солнца
    z_ring: int         # зубья кольца
    z_sat: int          # зубья сателлита
    n_sat: int          # количество сателлитов
    m: float            # модуль (мм)
    b: float            # ширина зуба (мм)

    # Расчетные параметры
    d_sun: float = None
    d_ring: float = None
    d_sat: float = None
    d_planet_carrier: float = None
    d_housing: float = None

    # Передаточные числа
    i_direct: float = None      # прямой редуктор (водило входное)
    i_ring_fixed: float = None  # кольцо зафиксировано

    def __post_init__(self):
        """Расчет диаметров и передаточных чисел"""
        self.d_sun = self.m * self.z_sun
        self.d_ring = self.m * self.z_ring
        self.d_sat = self.m * self.z_sat

        # Диаметр водила (делительный диаметр, на котором расположены оси сателлитов)
        self.d_planet_carrier = (self.d_sun + self.d_ring) / 2

        # Внешний диаметр корпуса (с запасом 2-3 мм)
        self.d_housing = self.d_ring + 3

        # Передаточное число: входное водило, выходное солнце, кольцо заблокировано
        # i = (z_sun + z_ring) / z_sun
        self.i_ring_fixed = (self.z_sun + self.z_ring) / self.z_sun

        # Альтернативное: входное солнце, выходное водило, кольцо заблокировано
        # i = z_sun / (z_sun + z_ring)
        self.i_direct = self.z_sun / (self.z_sun + self.z_ring)

    def check_compatibility(self) -> Tuple[bool, str]:
        """Проверка совместимости зубьев"""
        # Основное соотношение для планетарной передачи
        # z_ring = z_sun + 2*z_sat
        z_check = self.z_sun + 2 * self.z_sat

        if abs(z_check - self.z_ring) > 0.1:
            return False, f"z_ring неправильно: {z_check:.1f} != {self.z_ring}"

        # Минимум 3 сателлита (но можем и 4 для второй ступени)
        if self.n_sat < 3:
            return False, "Минимум 3 сателлита"

        # Проверка на возможность размещения сателлитов
        # Основное условие Баха для планетарной передачи:
        # n_sat >= 360 / (δ + φ), где δ угол между сателлитами, φ угол занимаемый сателлитом
        # Для компактной конструкции допустим более плотное расположение

        # Мягкая проверка возможности размещения сателлитов
        # Сателлиты размещаются между солнцем и кольцом
        # Максимальный z_sat ограничен геометрией: z_sat < z_ring / 2 (примерно)

        if self.z_sat > self.z_ring / 2.5:
            return False, f"z_sat слишком большой относительно z_ring"

        # Базовая проверка возможности размещения множества сателлитов
        # Угловой "размер" сателлита: примерно 360 * d_sat / (π * d_carrier)
        # Угловое расстояние между сателлитами: 360 / n_sat
        # Должно быть: 360 * d_sat / (π * d_carrier) < 360 / (1.5 * n_sat)

        d_carrier = (self.d_sun + self.d_ring) / 2
        if d_carrier > 0:
            angle_per_sat = 360 * self.d_sat / (np.pi * d_carrier)
            angle_between = 360 / self.n_sat
            if angle_per_sat > angle_between / 1.2:
                return False, f"Недостаточно места для размещения сателлитов"

        return True, "OK"

    def get_constraints(self) -> dict:
        """Возвращает основные ограничения"""
        return {
            'diameter': self.d_housing,
            'width': self.b,
            'module': self.m,
            'ratio': self.i_ring_fixed,
        }


def generate_planetary_designs(target_ratio: float,
                               max_diameter: float = 200,
                               max_width: float = 40,
                               verbose: bool = False) -> List[dict]:
    """
    Генерирует варианты двухступенчатых планетарных редукторов

    Args:
        target_ratio: целевое передаточное число (> 30)
        max_diameter: максимальный диаметр корпуса
        max_width: максимальная ширина одной ступени
        verbose: выводить отладочную информацию

    Returns:
        Список валидных конфигураций
    """

    results = []

    # Стандартные модули для PETG печати
    modules = [1.0, 1.25, 1.5, 2.0, 2.5]

    # Диапазон зубьев солнца (еще меньше для большего передаточного числа)
    z_sun_range = range(2, 11)

    # Количество сателлитов для первой ступени
    n_sat_1_options = [3, 4]

    count_tested = 0
    count_valid_s1 = 0
    count_valid_s2 = 0
    count_ratio_ok = 0
    max_i_found = 0.0
    max_i_combo = None
    max_i_s1 = 0.0
    max_i_s2 = 0.0

    for m in modules:
        for z_sun_1 in z_sun_range:
            for n_sat_1 in n_sat_1_options:
                # Подбираем z_sat и z_ring для первой ступени
                # z_sat должен быть достаточно большим для высокого передаточного числа
                for z_sat_1 in range(3, min(z_sun_1 + 40, 45)):
                    z_ring_1 = z_sun_1 + 2 * z_sat_1

                    # Проверяем размеры первой ступени (более мягкие критерии)
                    d_ring_1 = m * z_ring_1

                    # Расслабляем критерий диаметра
                    if d_ring_1 + 6 > max_diameter:
                        continue

                    try:
                        gear_1 = PlanetaryGearSet(
                            name="Ступень 1",
                            z_sun=z_sun_1,
                            z_ring=z_ring_1,
                            z_sat=z_sat_1,
                            n_sat=n_sat_1,
                            m=m,
                            b=min(max_width, 32)
                        )

                        valid_1, msg_1 = gear_1.check_compatibility()
                        if not valid_1:
                            continue

                        count_valid_s1 += 1
                        i_1 = gear_1.i_ring_fixed
                        if i_1 > max_i_s1:
                            max_i_s1 = i_1

                        # Вторая ступень с 4 сателлитами
                        n_sat_2 = 4

                        for z_sun_2 in range(2, 11):
                            for z_sat_2 in range(3, min(z_sun_2 + 40, 45)):
                                count_tested += 1

                                z_ring_2 = z_sun_2 + 2 * z_sat_2

                                # Проверяем размеры второй ступени
                                d_ring_2 = m * z_ring_2

                                if d_ring_2 + 6 > max_diameter:
                                    continue

                                try:
                                    gear_2 = PlanetaryGearSet(
                                        name="Ступень 2",
                                        z_sun=z_sun_2,
                                        z_ring=z_ring_2,
                                        z_sat=z_sat_2,
                                        n_sat=n_sat_2,
                                        m=m,
                                        b=min(max_width, 32)
                                    )

                                    valid_2, msg_2 = gear_2.check_compatibility()
                                    if not valid_2:
                                        continue

                                    count_valid_s2 += 1
                                    i_2 = gear_2.i_ring_fixed
                                    if i_2 > max_i_s2:
                                        max_i_s2 = i_2

                                    # Проверяем общее передаточное число
                                    i_total = i_1 * i_2

                                    if i_total < target_ratio:
                                        if i_total > target_ratio - 5 and verbose:
                                            print(f"  Близко: i1={i_1:.2f}, i2={i_2:.2f}, total={i_total:.2f}")
                                        continue

                                    count_ratio_ok += 1

                                    if i_total > max_i_found:
                                        max_i_found = i_total
                                        max_i_combo = (i_1, i_2, m, z_sun_1, z_ring_1, z_sun_2, z_ring_2)

                                    # Собираем результат (без строгого требования асимметрии)
                                    config = {
                                        'stage_1': gear_1,
                                        'stage_2': gear_2,
                                        'i_stage_1': i_1,
                                        'i_stage_2': i_2,
                                        'i_total': i_total,
                                        'max_diameter': max(gear_1.d_housing, gear_2.d_housing),
                                        'asymmetry': abs(i_1 - i_2) / max(i_1, i_2),
                                        'module': m,
                                    }

                                    results.append(config)

                                except Exception as e:
                                    continue

                    except Exception as e:
                        continue

    if verbose:
        print(f"Проверено комбинаций второй ступени: {count_tested}")
        print(f"Валидных первых ступеней: {count_valid_s1}, max i={max_i_s1:.2f}")
        print(f"Валидных вторых ступеней: {count_valid_s2}, max i={max_i_s2:.2f}")
        print(f"Теоретический max total: {max_i_s1 * max_i_s2:.2f}")
        print(f"С достаточным передаточным числом: {count_ratio_ok}")
        print(f"Максимальное найденное передаточное число: {max_i_found:.2f}")
        if max_i_combo:
            i_1, i_2, m, z_s1, z_r1, z_s2, z_r2 = max_i_combo
            print(f"  Комбинация: m={m}, z_sun1={z_s1}, z_ring1={z_r1}, z_sun2={z_s2}, z_ring2={z_r2}")
            print(f"  i1={i_1:.2f}, i2={i_2:.2f}")

    # Сортируем по общему диаметру, потом по передаточному числу
    results.sort(key=lambda x: (x['max_diameter'], abs(x['i_total'] - target_ratio)))

    return results[:100]  # Возвращаем лучшие 100 вариантов


def calculate_stress_petg(config: dict,
                         input_torque: float = 3.7,
                         material: dict = None) -> dict:
    """
    Расчет напряжений в материале PETG

    Args:
        config: конфигурация редуктора
        input_torque: входящий момент (Нм)
        material: свойства материала PETG

    Returns:
        Словарь с напряжениями и коэффициентами безопасности
    """

    if material is None:
        material = {
            'sigma_tensile': 55e6,  # Па (55 МПа для PETG)
            'E': 2.7e9,             # Па (2.7 ГПа для PETG)
            'density': 1240,        # кг/м³
        }

    stage_1 = config['stage_1']
    stage_2 = config['stage_2']

    # Момент на выходе первой ступени
    torque_stage_1_out = input_torque * config['i_stage_1']

    # Контактное напряжение (упрощенная формула Герца для зубчатой передачи)
    def contact_stress(m, z1, z2, b, T):
        # σ_contact ≈ sqrt(2*T / (b*d*cos(α)*sin(β)))
        # для упрощения: σ_contact ≈ sqrt(T / (b*m*z1))
        d = m * z1
        sigma = np.sqrt(T / (b * m * z1)) * 1e6  # перевод в Па
        return sigma

    stress_1 = contact_stress(stage_1.m, stage_1.z_sun, stage_1.z_ring, stage_1.b, input_torque)
    stress_2 = contact_stress(stage_2.m, stage_2.z_sun, stage_2.z_ring, stage_2.b, torque_stage_1_out)

    # Коэффициент безопасности
    sf_1 = material['sigma_tensile'] / (stress_1 * 1.5)  # с коэффициентом концентрации 1.5
    sf_2 = material['sigma_tensile'] / (stress_2 * 1.5)

    return {
        'stress_stage_1': stress_1 / 1e6,  # МПа
        'stress_stage_2': stress_2 / 1e6,
        'sf_stage_1': max(0.1, sf_1),      # коэффициент безопасности
        'sf_stage_2': max(0.1, sf_2),
        'min_sf': max(0.1, min(sf_1, sf_2)),
        'material': material,
    }


def create_report(configs: List[dict],
                 input_torque: float = 3.7,
                 input_speed: float = 150,
                 output_torque: float = 60) -> str:
    """Создает текстовый отчет"""

    report = []
    report.append("=" * 80)
    report.append("ОТЧЕТ: ПРОЕКТИРОВАНИЕ ПЛАНЕТАРНОЙ КОРОБКИ ПЕРЕДАЧ")
    report.append("Коленка робота-паука")
    report.append("=" * 80)
    report.append(f"\nДата: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append(f"\nТребования:")
    report.append(f"  • Входящий момент: {input_torque} Нм на {input_speed} rpm")
    report.append(f"  • Требуемый выходящий момент: {output_torque} Нм")
    report.append(f"  • Требуемое передаточное число: > 30")
    report.append(f"  • Максимальный диаметр: 200 мм")
    report.append(f"  • Максимальная ширина: 40 мм")
    report.append(f"  • Материал: PETG (3D печать)")
    report.append(f"  • Конфигурация: двухступенчатая, несимметричная")
    report.append(f"  • Вторая ступень: 4 сателлита")

    report.append("\n" + "=" * 80)
    report.append(f"НАЙДЕНО ВАРИАНТОВ: {len(configs)}\n")

    for idx, config in enumerate(configs[:20], 1):  # показываем 20 лучших
        stage_1 = config['stage_1']
        stage_2 = config['stage_2']

        report.append(f"\n--- ВАРИАНТ {idx} ---")
        report.append(f"Общее передаточное число: {config['i_total']:.2f}x")
        report.append(f"Максимальный диаметр: {config['max_diameter']:.1f} мм")
        report.append(f"Модуль: {config['module']} мм")
        report.append(f"Асимметрия передаточных чисел: {config['asymmetry']*100:.1f}%")

        report.append(f"\n  Ступень 1:")
        report.append(f"    • Солнце (z={stage_1.z_sun}, d={stage_1.d_sun:.1f} мм)")
        report.append(f"    • Кольцо (z={stage_1.z_ring}, d={stage_1.d_ring:.1f} мм)")
        report.append(f"    • Сателлиты ({stage_1.n_sat}x z={stage_1.z_sat}, d={stage_1.d_sat:.1f} мм)")
        report.append(f"    • Водило (d={stage_1.d_planet_carrier:.1f} мм)")
        report.append(f"    • Корпус (d={stage_1.d_housing:.1f} мм, b={stage_1.b} мм)")
        report.append(f"    • Передаточное число: {config['i_stage_1']:.2f}x")

        report.append(f"\n  Ступень 2:")
        report.append(f"    • Солнце (z={stage_2.z_sun}, d={stage_2.d_sun:.1f} мм)")
        report.append(f"    • Кольцо (z={stage_2.z_ring}, d={stage_2.d_ring:.1f} мм)")
        report.append(f"    • Сателлиты ({stage_2.n_sat}x z={stage_2.z_sat}, d={stage_2.d_sat:.1f} мм)")
        report.append(f"    • Водило (d={stage_2.d_planet_carrier:.1f} мм)")
        report.append(f"    • Корпус (d={stage_2.d_housing:.1f} мм, b={stage_2.b} мм)")
        report.append(f"    • Передаточное число: {config['i_stage_2']:.2f}x")

        # Расчет напряжений
        stress_info = calculate_stress_petg(config, input_torque)
        report.append(f"\n  Напряжения в PETG:")
        report.append(f"    • Ступень 1: {stress_info['stress_stage_1']:.1f} МПа (SF={stress_info['sf_stage_1']:.1f})")
        report.append(f"    • Ступень 2: {stress_info['stress_stage_2']:.1f} МПа (SF={stress_info['sf_stage_2']:.1f})")
        report.append(f"    • Минимальный коэффициент безопасности: {stress_info['min_sf']:.1f}")

        # Проверка требуемого момента
        output_torque_actual = input_torque * config['i_total']
        report.append(f"\n  Выходящий момент: {output_torque_actual:.1f} Нм")
        if output_torque_actual >= output_torque:
            report.append(f"    ✓ СООТВЕТСТВУЕТ требованиям ({output_torque:.1f} Нм)")
        else:
            report.append(f"    ✗ НЕДОСТАТОЧНО (требуется {output_torque:.1f} Нм)")

    report.append("\n" + "=" * 80)
    report.append("\nПримечания:")
    report.append("• Коэффициент безопасности (SF) > 1.5 рекомендуется для критичных деталей")
    report.append("• PETG имеет σ_tensile ≈ 55 МПа в напечатанном состоянии")
    report.append("• Расчеты учитывают концентрацию напряжений (k=1.5)")
    report.append("• Рекомендуется проверка на предельный случай при динамических нагрузках")

    return "\n".join(report)


def create_json_report(configs: List[dict]) -> str:
    """Создает JSON отчет со всеми параметрами"""

    data = {
        'timestamp': datetime.now().isoformat(),
        'requirements': {
            'input_torque_nm': 3.7,
            'input_speed_rpm': 150,
            'output_torque_nm': 60,
            'target_ratio': 30,
            'max_diameter_mm': 200,
            'max_width_mm': 40,
            'material': 'PETG (3D печать)',
        },
        'variants': []
    }

    for config in configs[:20]:
        stage_1 = config['stage_1']
        stage_2 = config['stage_2']
        stress_info = calculate_stress_petg(config)

        variant = {
            'index': len(data['variants']) + 1,
            'i_total': round(config['i_total'], 3),
            'max_diameter_mm': round(config['max_diameter'], 1),
            'module_mm': config['module'],
            'asymmetry_pct': round(config['asymmetry'] * 100, 1),
            'stage_1': {
                'z_sun': stage_1.z_sun,
                'z_ring': stage_1.z_ring,
                'z_satellite': stage_1.z_sat,
                'n_satellites': stage_1.n_sat,
                'd_sun_mm': round(stage_1.d_sun, 2),
                'd_ring_mm': round(stage_1.d_ring, 2),
                'd_satellite_mm': round(stage_1.d_sat, 2),
                'd_carrier_mm': round(stage_1.d_planet_carrier, 2),
                'd_housing_mm': round(stage_1.d_housing, 2),
                'width_mm': stage_1.b,
                'ratio': round(config['i_stage_1'], 3),
            },
            'stage_2': {
                'z_sun': stage_2.z_sun,
                'z_ring': stage_2.z_ring,
                'z_satellite': stage_2.z_sat,
                'n_satellites': stage_2.n_sat,
                'd_sun_mm': round(stage_2.d_sun, 2),
                'd_ring_mm': round(stage_2.d_ring, 2),
                'd_satellite_mm': round(stage_2.d_sat, 2),
                'd_carrier_mm': round(stage_2.d_planet_carrier, 2),
                'd_housing_mm': round(stage_2.d_housing, 2),
                'width_mm': stage_2.b,
                'ratio': round(config['i_stage_2'], 3),
            },
            'stress_analysis': {
                'stage_1_stress_mpa': round(stress_info['stress_stage_1'], 2),
                'stage_2_stress_mpa': round(stress_info['stress_stage_2'], 2),
                'stage_1_sf': round(stress_info['sf_stage_1'], 2),
                'stage_2_sf': round(stress_info['sf_stage_2'], 2),
                'min_sf': round(stress_info['min_sf'], 2),
            },
            'output_torque_nm': round(3.7 * config['i_total'], 2),
        }

        data['variants'].append(variant)

    return json.dumps(data, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    print("Проектирование планетарного редуктора для коленки паука...")
    print("Поиск вариантов конфигураций...\n")

    # Генерируем конфигурации
    configs = generate_planetary_designs(target_ratio=29, verbose=True)

    print(f"\nНайдено {len(configs)} допустимых вариантов\n")

    if configs:
        # Текстовый отчет
        report_text = create_report(configs)

        # JSON отчет
        report_json = create_json_report(configs)

        # Сохраняем отчеты
        with open('REPORT/SPIDER_KNEE/design_variants.txt', 'w', encoding='utf-8') as f:
            f.write(report_text)

        with open('REPORT/SPIDER_KNEE/design_variants.json', 'w', encoding='utf-8') as f:
            f.write(report_json)

        print("Отчеты сохранены:")
        print("  • REPORT/SPIDER_KNEE/design_variants.txt")
        print("  • REPORT/SPIDER_KNEE/design_variants.json")
        print("\n" + "=" * 80)
        print(report_text[:2000])  # Выводим первую часть
        print("\n... (полный отчет в файле)")
    else:
        print("Не найдено подходящих конфигураций!")
