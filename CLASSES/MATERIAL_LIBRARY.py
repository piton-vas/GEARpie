'''MIT License

Copyright (c) 2022 Carlos M.C.G. Fernandes

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE. '''


class LIBRARY_MAT:
    """Library with typical gear materials"""

    def __init__(self, MAT_NAME):

        default = 'No defined material'
        getattr(self, MAT_NAME, lambda: default)()

    def Input(self):
        self.E = float(input('Young modulus / MPa: '))
        self.v = float(input('Poisson coeficient: '))
        self.cp = float(input('Heat capacity: '))
        self.k = float(input('Heat conductivity / W/mK: '))
        self.rho = float(input('Density / kg/m3: '))

    def STEEL(self):
        self.E = 206e3
        self.v = 0.3
        self.cp = 465
        self.k = 46
        self.rho = 7830
        # Цементируемая сталь (Eh), грейд MQ по ISO 6336-5:
        #   σHlim ≈ 1300–1650 МПа, σFlim ≈ 430–500 МПа.
        # S-N кривая не задана — возвращаем предел выносливости как константу
        # (NL=1e8 в пайплайне ≈ область выносливости) callable для VDI2736.LCC.
        self.SigmaHlim = lambda temp, cycles: 1500
        self.SigmaFlim = lambda temp, cycles: 430

    def ADI(self):
        self.E = 210e3
        self.v = 0.26
        self.cp = 460.548
        self.k = 55
        self.rho = 7850
        # Изотермически закалённый чугун ADI (ausferritic SG iron) по ISO 6336-5
        # / ISO 17804: σHlim ≈ 580–800 МПа; σFlim ≈ 230–250 МПа (σFE 460–490).
        # Константа-предел выносливости, обёрнутая в callable для VDI2736.LCC.
        self.SigmaHlim = lambda temp, cycles: 700
        self.SigmaFlim = lambda temp, cycles: 250

    def POM(self):
        self.E = 3.2e3
        self.v = 0.35
        self.cp = 1465
        self.k = 0.3
        self.rho = 1415
        self.SigmaHlim = None
        def SHlimPOM(temp,cycles):
            if temp > 120: temp = 120
            return 36 - 0.0012*temp**2 + (1000 - 0.025*temp**2)*cycles**(-0.21)
        self.SigmaHlim = SHlimPOM
        def SFlimPOM(temp, cycles):
            if temp > 120: temp = 120
            SFL = 26 - 0.0025*temp**2 + 400*cycles**(-0.2)
            return SFL
        self.SigmaFlim = SFlimPOM

    def PA66(self):
        self.E = 1.85e3
        self.v = 0.3
        self.cp = 1670
        self.k = 0.26
        self.rho = 1140
        def SHlimPA66(temp,cycles):
            if temp > 120: temp = 120
            SHL = 36 - 0.0012*temp**2 + (1000 - 0.025*temp**2)*cycles**(-0.21)
            return SHL 
        self.SigmaHlim = SHlimPA66
        def SFlimPA66(temp,cycles):
            if temp > 120: temp = 120
            SFL = 30 - 0.22*temp + (4600 - 900*temp**(0.3))*cycles**(-1/3)
            return SFL
        self.SigmaFlim = SFlimPA66

    def D16T(self):
        # Алюминиевый сплав Д16Т (ГОСТ 4784-2019), закалка + естественное старение
        self.E = 72e3
        self.v = 0.33
        self.cp = 922
        self.k = 130
        self.rho = 2770
        # S-N кривая отсутствует — отдаём константу для совместимости с VDI2736.LCC
        self.SigmaHlim = lambda temp, cycles: 170
        self.SigmaFlim = lambda temp, cycles: 130

    def PA_CF(self):
        # PA12-CF FFF Печать (DIN EN ISO 1043-1), без ТО
        self.E = 3500
        self.v = 0.4
        self.cp = 1500
        self.k = 0.3
        self.rho = 1100
        # S-N кривая отсутствует — отдаём константу для совместимости с VDI2736.LCC
        self.SigmaHlim = lambda temp, cycles: 27
        self.SigmaFlim = lambda temp, cycles: 12

    def PA6_CF(self):
        # PA6-CF FFF печать (полиамид-6 с рубленым углеволокном ~20%), без отжига
        # Источники: TDS Polymaker PA6-CF, Bambu Lab PA6-CF, eSUN ePA-CF
        # E (XY) ~ 6-7 ГПа; прочность при растяжении ~100-120 МПа; изгибная ~150 МПа
        self.E = 6500
        self.v = 0.4
        self.cp = 1600
        self.k = 0.4
        self.rho = 1180
        # S-N кривая отсутствует — отдаём константу для совместимости с VDI2736.LCC
        self.SigmaHlim = lambda temp, cycles: 35
        self.SigmaFlim = lambda temp, cycles: 18

    def PETG(self):
        # PETG FFF печать. Литературные оценки (без углеволокна, типовая печать XY).
        # σt ~ 45-55 МПа, σизг ~ 60-70 МПа; для шестерён это слабый материал.
        # σHlim ≈ 22 МПа (≈ 0.6 от POM/PA6-CF — типично для аморфного PETG)
        # σFlim ≈ 12 МПа (с учётом анизотропии печати)
        # E_XY ~ 2.0 ГПа; ν ~ 0.4; ρ ~ 1270; cp ~ 1100; k ~ 0.2
        self.E = 2000
        self.v = 0.4
        self.cp = 1100
        self.k = 0.2
        self.rho = 1270
        self.SigmaHlim = lambda temp, cycles: 22
        self.SigmaFlim = lambda temp, cycles: 12

    def PA6_PRINT(self):
        # PA6 печатный (FFF, без углеволокна).
        # Источники: TDS eSUN ePA, Polymaker PolyMide CoPA, Bambu Lab PAHT.
        # σt(XY) ~ 50-65 МПа, σизг ~ 70-90 МПа; E(XY) ~ 1.4-1.7 ГПа.
        # σHlim для зубчатых ≈ 25 МПа (выше PETG за счёт пластичности),
        # σFlim ≈ 16 МПа (выше PETG из-за лучшего удлинения при разрыве).
        # ν ~ 0.4; ρ ~ 1130; cp ~ 1700; k ~ 0.25.
        # Без отжига; с отжигом параметры на ~15-20% выше.
        self.E = 1500
        self.v = 0.4
        self.cp = 1700
        self.k = 0.25
        self.rho = 1130
        self.SigmaHlim = lambda temp, cycles: 25
        self.SigmaFlim = lambda temp, cycles: 16

    def PA6_ANNEAL(self):
        # PA6 печатный (FFF) ПОСЛЕ ОТЖИГА (термообработка для снятия
        # внутренних напряжений и роста кристалличности).
        # Отжиг повышает прочность/жёсткость и теплостойкость FFF-нейлона:
        #   σt, σизг   +15...25 %; E +10...20 %; HDT существенно выше.
        # Консервативная оценка относительно PA6_PRINT (без отжига):
        #   E +13 %  (1500 -> 1700) — рост модуля чуть поднимает σH по Герцу,
        #   σHlim +16 % (25 -> 29), σFlim +19 % (16 -> 19).
        # Чистый выигрыш по SH ~ +7...8 % (рост σHlim частично съедается ростом E).
        self.E = 1700
        self.v = 0.4
        self.cp = 1700
        self.k = 0.25
        self.rho = 1130
        self.SigmaHlim = lambda temp, cycles: 29
        self.SigmaFlim = lambda temp, cycles: 19

    def POM_C(self):
        # POM-C (полиоксиметилен, кополимер) фрезерованный.
        # σt ~ 65-70 МПа, σизг ~ 85-95 МПа; E ~ 3.0-3.2 ГПа.
        # σHlim ≈ 35 МПа, σFlim ≈ 26 МПа (близко к POM-H, чуть мягче).
        # Используем как уточнённый POM-C; для совместимости с библиотекой
        # параметры близки к функции POM().
        self.E = 3000
        self.v = 0.35
        self.cp = 1465
        self.k = 0.3
        self.rho = 1410
        self.SigmaHlim = lambda temp, cycles: 35
        self.SigmaFlim = lambda temp, cycles: 26

class MATERIAL:
    """Assign a material to pinion and wheel"""

    def __init__(self, PINION_MAT, WHEEL_MAT):

        Pmaterial = LIBRARY_MAT(PINION_MAT)
        self.MAT1 = PINION_MAT 
        self.E1 = Pmaterial.E
        self.v1 = Pmaterial.v
        self.cp1 = Pmaterial.cp
        self.k1 = Pmaterial.k
        self.rho1 = Pmaterial.rho
        self.SigmaHlim1 = Pmaterial.SigmaHlim
        self.SigmaFlim1 = Pmaterial.SigmaFlim
        
        Wmaterial = LIBRARY_MAT(WHEEL_MAT)
        self.MAT2 = WHEEL_MAT
        self.E2 = Wmaterial.E
        self.v2 = Wmaterial.v
        self.cp2 = Wmaterial.cp
        self.k2 = Wmaterial.k
        self.rho2 = Wmaterial.rho
        self.SigmaHlim2 = Wmaterial.SigmaHlim
        self.SigmaFlim2 = Wmaterial.SigmaFlim