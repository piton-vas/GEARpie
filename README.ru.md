# GEARpie

*Русская версия — [English version](README.md)*

## Требования

GEARpie требует Python 3 и следующие библиотеки:

- scipy, numpy и matplotlib — устанавливаются через `pip install scipy`, `pip install numpy`, `pip install matplotlib`
- API gmsh — `pip install gmsh`

## Как использовать

Запустите `GEARpie.py` и заполните параметры в окне ввода:

<p align="center">
    <img src="SCREENSHOTS/INPUT.png" height="800"/>
</p>

## Возможности

GEARpie предназначен для расчёта цилиндрических зубчатых передач:

- геометрия по книге MAAG (с заданием межосевого расстояния и одного коэффициента смещения либо обоих коэффициентов смещения x1 и x2);
- контактное давление и поля напряжений с учётом трения (положение по линии зацепления: A, B, C, D, E или любая другая точка);
- толщина смазочной плёнки вдоль линии зацепления;
- потери мощности в зацеплении (локальные и средние);
- мгновенное и среднее тепловыделение по методике из [8];
- структурированная конечно-элементная сетка (элементы 1-го или 2-го порядка);
- нагрузочная способность по DIN 3990 method B (для стальных колёс);
- нагрузочная способность и объёмная температура по VDI 2736 Part 2 (для пластиковых колёс) [10];
- изгибное напряжение в основании зуба по VDI 2736 рассчитывается методом C (как рекомендует стандарт; метод B также возможен);
- по VDI 2736 — локальный износ, проверка деформации и пиковых нагрузок.

Модель распределения нагрузки между зубьями (rigid load sharing), реализованная в программе, описана в [1]. Если задан результат распределения нагрузки извне (например, результат МКЭ в виде текстового файла k=f(положение в зацеплении)), при расчётах учитывается соответствующая жёсткость.

Модели потерь мощности описаны в [2–5, 7]. Реализованы коэффициенты потерь Олендорфа (аналитический) и Виммера (численный).

Расчёт температуры по VDI 2736 использует коэффициент потерь Виммера вместо Олендорфа — для большей точности. По умолчанию VDI 2736 рассчитывается для открытых передач (площадь поверхности корпуса не требуется). Для закрытых и полузакрытых передач — изменить значение по умолчанию внутри класса `VDI2736`.

Реализация VDI 2736 выполняет проверку как по изгибной прочности зуба, так и по контактной. Однако проверка контактной прочности обычно выполняется только для пластиковых колёс из PA66 со смазкой (только для этих случаев расчёт точен и соответствует стандарту). Свойства материалов доступны только для рабочих температур ниже 120 °C. Любой коэффициент запаса (SF или SH), рассчитанный выше 120 °C, неверен из-за отсутствия данных о материале — свойства фиксируются на значениях при 120 °C. При наличии точных данных о материале их следует добавить в класс `MATERIAL_LIBRARY`.

Генерация сетки полезна, например, для создания МКЭ-модели тепловых расчётов из [8–9]. Сетка пригодна для любого МКЭ-анализа (проверено в Abaqus и CalculiX).

## Пример графического вывода

<p align="center">
    <img src="SCREENSHOTS/logo1.png" height="400"/>
    <img src="SCREENSHOTS/logo2.png" height="400"/>
</p>

Трёхмерный вывод по умолчанию не реализован, но возможен — добавлением 3D-вызовов в класс `PLOTTING`. Все величины, рассчитываемые в классе `CONTACT`, дискретизированы вдоль линии зацепления и по ширине венца, поэтому подходят для 3D-визуализации. Пример: центральная толщина смазочной плёнки с поправкой на нагрев на входе в контакт для косозубой передачи:

<p align="center">
    <img src="SCREENSHOTS/logo3.png" height="400"/>
</p>

## Пример текстового отчёта

Отчёт автоматически сохраняется в папку `REPORT` в формате txt.

<p align="center">
    <img src="SCREENSHOTS/OUT0.png" width="600"/>
    <img src="SCREENSHOTS/OUT1.png" width="600"/>
    <img src="SCREENSHOTS/OUT2.png" width="600"/>
    <img src="SCREENSHOTS/OUT3.png" width="600"/>
</p>

## Список литературы

[1] Fernandes, C. M. C. G., Marques, P. M. T., Martins, R. C., & Seabra, J. H. O. (2015).
Influence of gear loss factor on the power loss prediction. Mechanical Sciences, 6(2),
81–88. https://doi.org/10.5194/ms-6-81-2015

[2] Fernandes, C. M. C. G., Martins, R. C., & Seabra, J. H. O. (2014).
Torque loss of type C40 FZG gears lubricated with wind turbine gear oils.
Tribology International, 70(0), 83–93. https://doi.org/10.1016/j.triboint.2013.10.003

[3] Fernandes, C. M. C. G., Marques, P. M. T., Martins, R. C., & Seabra, J. H. O. (2015).
Gearbox power loss. Part I: Losses in rolling bearings.
Tribology International, 88(0), 298–308. https://doi.org/10.1016/j.triboint.2014.11.017

[4] Fernandes, C. M. C. G., Marques, P. M. T. T., Martins, R. C., & Seabra, J. H. O. (2015).
Gearbox power loss. Part II: Friction losses in gears.
Tribology International, 88, 309–316. https://doi.org/10.1016/j.triboint.2014.12.004

[5] Fernandes, C. M. C. G., Marques, P. M. T., Martins, R. C., & Seabra, J. H. O. (2015).
Gearbox power loss. Part III: Application to a parallel axis and a planetary gearbox.
Tribology International, 88, 317–326. https://doi.org/10.1016/j.triboint.2015.03.029

[6] Fernandes, C. M. C. G., Martins, R. C., & Seabra, J. H. O. (2016). Coefficient of
friction equation for gears based on a modified Hersey parameter. Tribology International,
101, 204–217. https://doi.org/10.1016/j.triboint.2016.03.028

[7] Fernandes, C. M. C. G. M., Hammami, M., Martins, R. C., & Seabra, J. H. O. H. (2016).
Power loss prediction: Application to a 2.5 MW wind turbine gearbox.
Proceedings of the Institution of Mechanical Engineers, Part J: Journal of Engineering Tribology,
230(8), 983–995. https://doi.org/10.1177/1350650115622362

[8] Fernandes, C. M. C. G., Rocha, D. M. P., Martins, R. C., Magalhães, L., & Seabra, J. H. O. (2018).
Finite element method model to predict bulk and flash temperatures on polymer gears.
Tribology International, 120, 255–268. https://doi.org/10.1016/j.triboint.2017.12.027

[9] Fernandes, C. M. C. G., Rocha, D. M. P., Martins, R. C., Magalhães, L., & Seabra, J. H. O. (2019).
Hybrid Polymer Gear Concepts to Improve Thermal Behavior.
Journal of Tribology, 141(3), 032201. https://doi.org/10.1115/1.4041461

[10] V. Roda-casanova, C.M.C.G. Fernandes, A comparison of analytical methods to predict the bulk temperature in polymer spur gears, Mechanism and Machine Theory. 173 (2022) 104849. https://doi.org/10.1016/j.mechmachtheory.2022.104849

---

Copyright (c) 2023 Carlos M.C.G. Fernandes

Перевод на русский язык: см. [docs/GLOSSARY_RU.md](docs/GLOSSARY_RU.md) — глоссарий терминов с привязкой к ГОСТ.
