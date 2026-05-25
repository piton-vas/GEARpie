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

from CLASSES import I18N
from CLASSES.I18N import t


class PRINTING:
    """Create a text report with output results"""

    def __init__(self, GTYPE, GMAT, GLUB, GEO, GFS, GCONTACT, GLCC):

        # Russian labels are longer; widen the label column when LANG is 'ru'.
        label_w = 52 if I18N.LANG == 'ru' else 35
        total_w = label_w + 30  # value(20) + unit(10)

        def row(label, value, unit=''):
            return '{:<{w}s}{:^20s}{:<10s}'.format(label, value, unit, w=label_w)

        file = 'REPORT/' + GTYPE.GEAR_NAME + '.txt'
        dash = '-' * total_w
        dots = '.' * total_w
        f = open(file, "w", encoding="utf-8")
        print(dash, file=f)
        # gear type
        print('{:^{w}s}'.format(GTYPE.GEAR_NAME + t('rep_suffix_gear'),
                                w=total_w), file=f)
        print(dots, file=f)
        print(row(t('fld_pressure_angle'), "%.1f" % GTYPE.alpha, '°'),
              file=f)
        print(row(t('fld_helix_angle'), "%.1f" % GTYPE.beta, '°'), file=f)
        print(row(t('fld_module'), "%.1f" % GTYPE.m, 'mm'), file=f)
        print(row(t('fld_z1'), "%.1f" % GTYPE.z[0], ''), file=f)
        print(row(t('fld_z2'), "%.1f" % GTYPE.z[1], ''), file=f)
        print(row(t('fld_x1'), "%.4f" % GTYPE.x[0], ''), file=f)
        print(row(t('fld_x2'), "%.4f" % GTYPE.x[1], ''), file=f)
        print(dash, file=f)
        # gear materials
        print('{:^{w}s}'.format(t('header_gear_materials'), w=total_w), file=f)
        print(dots, file=f)
        print(t('sub_pinion'), file=f)
        print(row(t('fld_E1'), "%.0f" % (GMAT.E1/1e3), 'GPa'), file=f)
        print(row(t('fld_v1'), "%.2f" % GMAT.v1, ''), file=f)
        print(row(t('fld_cp1'), "%.2f" % GMAT.cp1, 'J/kg.K'), file=f)
        print(row(t('fld_k1'), "%.2f" % GMAT.k1, 'W/m.K'), file=f)
        print(row(t('fld_rho1'), "%.2f" % GMAT.rho1, 'kg/m3'), file=f)
        print(t('sub_wheel'), file=f)
        print(row(t('fld_E2'), "%.0f" % (GMAT.E2/1e3), 'GPa'), file=f)
        print(row(t('fld_v2'), "%.2f" % GMAT.v2, ''), file=f)
        print(row(t('fld_cp2'), "%.2f" % GMAT.cp2, 'J/kg.K'), file=f)
        print(row(t('fld_k2'), "%.2f" % GMAT.k2, 'W/m.K'), file=f)
        print(row(t('fld_rho2'), "%.2f" % GMAT.rho2, 'kg/m3'), file=f)
        print(dash, file=f)
        # lubricant
        if GLUB is None:
            pass
        else:
            print('{:^{w}s}'.format(GLUB.NAME + t('rep_suffix_lubricant'),
                                    w=total_w), file=f)
            print(dots, file=f)
            print(row(t('fld_lub_temp'), "%.0f" % GLUB.TL, '°C'), file=f)
            print(row(t('fld_kin_visc'), "%.2f" % GLUB.niu, 'cSt'), file=f)
            print(row(t('fld_dyn_visc'), "%.2f" % GLUB.miu, 'mPa.s'), file=f)
            print(row(t('fld_density_15'), "%.2f" % GLUB.rho0, 'g/cm3'),
                  file=f)
            print(row(t('fld_density_at').format(temp=GLUB.TL),
                      "%.2f" % GLUB.rho, 'g/cm3'), file=f)
            print(row(t('fld_piezo'), "%.2f" % (GLUB.piezo/1e-9), '1/GPa'),
                  file=f)
            print(row(t('fld_thermo'), "%.3f" % GLUB.beta, '1/°C'),
                  file=f)
            print(row(t('fld_xl'), "%.2f" % GLUB.xl, ''), file=f)
            print(dash, file=f)
        # gear geometry
        print('{:^{w}s}'.format(t('header_gear_geometry'), w=total_w), file=f)
        print(dots, file=f)
        print(row(t('fld_axis_distance'), "%.1f" % GEO.al, 'mm'), file=f)
        print(row(t('fld_base_pitch_n'), "%.3f" % GEO.pb, 'mm'), file=f)
        print(row(t('fld_base_pitch_t'), "%.3f" % GEO.pbt, 'mm'), file=f)
        print(row(t('fld_root_radius'),
                  "%.3f" % GEO.rf1 + ' / ' + "%.3f" % GEO.rf2, 'mm'), file=f)
        print(row(t('fld_base_radius'),
                  "%.3f" % GEO.rb1 + ' / ' + "%.3f" % GEO.rb2, 'mm'), file=f)
        print(row(t('fld_reference_radius'),
                  "%.3f" % GEO.r1 + ' / ' + "%.3f" % GEO.r2, 'mm'), file=f)
        print(row(t('fld_pitch_radius'),
                  "%.3f" % GEO.rl1 + ' / ' + "%.3f" % GEO.rl2, 'mm'), file=f)
        print(row(t('fld_tip_radius'),
                  "%.3f" % GEO.ra1 + ' / ' + "%.3f" % GEO.ra2, 'mm'), file=f)
        print(dash, file=f)
        # contact ratio
        print('{:^{w}s}'.format(t('header_contact_ratio'), w=total_w), file=f)
        print(dots, file=f)
        print(row(t('fld_eps_alpha'), "%.2f" % GEO.epslon_alpha, ''), file=f)
        print(row(t('fld_eps_beta'), "%.2f" % GEO.epslon_beta, ''), file=f)
        print(row(t('fld_eps_gama'), "%.2f" % GEO.epslon_gama, ''), file=f)
        print(dash, file=f)
        print('{:^{w}s}'.format(t('header_path_dims'), w=total_w), file=f)
        print(dots, file=f)
        print(row('T1T2:', "%.2f" % GEO.T1T2, 'mm'), file=f)
        print(row('AB:', "%.2f" % GEO.AB, 'mm'), file=f)
        print(row('AC:', "%.2f" % GEO.AC, 'mm'), file=f)
        print(row('AD:', "%.2f" % GEO.AD, 'mm'), file=f)
        print(row('AE:', "%.2f" % GEO.AE, 'mm'), file=f)
        print(dash, file=f)
        # operating conditions
        print('{:^{w}s}'.format(t('header_operating'), w=total_w), file=f)
        print(dots, file=f)
        print(row(t('fld_pin'), "%.1f" % GFS.Pin, 'W'), file=f)
        print(row(t('fld_torque'),
                  "%.1f" % GFS.torque1 + ' / ' + "%.1f" % GFS.torque2, 'N.m'),
              file=f)
        print(row(t('fld_speed'),
                  "%.1f" % GFS.speed1 + ' / ' + "%.1f" % GFS.speed2, 'rpm'),
              file=f)
        print(row(t('fld_omega'),
                  "%.1f" % GFS.omega1 + ' / ' + "%.1f" % GFS.omega2, 'rad/s'),
              file=f)
        print(row(t('fld_vt'), "%.2f" % GFS.vt, 'm/s'), file=f)
        print(row(t('fld_vtb'), "%.2f" % GFS.vtb, 'm/s'), file=f)
        print(row(t('fld_gs_max'),
                  "%.1f" % GFS.gs1.max() + ' / ' + "%.1f" % GFS.gs2.max(), ''),
              file=f)
        print(row(t('fld_ft'), "%.1f" % GFS.ft, 'N'), file=f)
        print(row(t('fld_fr'), "%.1f" % GFS.fr, 'N'), file=f)
        print(row(t('fld_fn'), "%.1f" % GFS.fn, 'N'), file=f)
        print(row(t('fld_fa'), "%.1f" % GFS.fa, 'N'), file=f)
        print(row(t('fld_fbt'), "%.1f" % GFS.fbt, 'N'), file=f)
        print(row(t('fld_fbn'), "%.1f" % GFS.fbn, 'N'), file=f)
        print(dash, file=f)
        # contact results
        print('{:^{w}s}'.format(t('header_contact_results'), w=total_w),
              file=f)
        print(dots, file=f)
        print(t('sub_max_pressure'), file=f)
        print(row(t('sub_at_pitch_point'), "%.1f" % GCONTACT.p0I, 'MPa'),
              file=f)
        print(row(t('sub_max_along_ae'),
                  "%.1f" % GCONTACT.p0.max(), 'MPa'), file=f)
        print(row(t('sub_min_along_ae'),
                  "%.1f" % GCONTACT.p0.min(), 'MPa'), file=f)
        print(t('sub_mean_pressure'), file=f)
        print(row(t('sub_at_pitch_point'), "%.1f" % GCONTACT.pmI, 'MPa'),
              file=f)
        print(row(t('sub_max_along_ae'),
                  "%.1f" % GCONTACT.pm.max(), 'MPa'), file=f)
        print(row(t('sub_min_along_ae'),
                  "%.1f" % GCONTACT.pm.min(), 'MPa'), file=f)
        print(t('sub_contact_half_width'), file=f)
        print(row(t('sub_at_pitch_point'),
                  "%.3f" % (GCONTACT.aHI*1e3), 'μm'), file=f)
        print(row(t('sub_max_along_ae'),
                  "%.3f" % (GCONTACT.aH.max()*1e3), 'μm'), file=f)
        print(row(t('sub_min_along_ae'),
                  "%.3f" % (GCONTACT.aH.min()*1e3), 'μm'), file=f)
        print(row(t('fld_mises'),
                  "%.1f" % GCONTACT.SMises.max(), 'MPa'), file=f)
        print(row(t('fld_tau_max'),
                  "%.1f" % GCONTACT.Tmax.max(), 'MPa'), file=f)
        print(row(t('fld_tau_oct'),
                  "%.1f" % GCONTACT.Toct.max(), 'MPa'), file=f)
        print(dash, file=f)
        # film thickness
        if GLUB is None:
            pass
        else:
            print('{:^{w}s}'.format(t('header_film_thickness'), w=total_w),
                  file=f)
            print(dots, file=f)
            print(row(t('fld_inlet_shear'),
                      "%.3f" % GCONTACT.phiT.mean(), ''), file=f)
            print(t('sub_central_film'), file=f)
            print(row(t('sub_max_along_ae'),
                      "%.2f" % GCONTACT.h0C.max(), 'μm'), file=f)
            print(row(t('sub_min_along_ae'),
                      "%.2f" % GCONTACT.h0C.min(), 'μm'), file=f)
            print(row(t('sub_avg_along_ae'),
                      "%.2f" % GCONTACT.h0C.mean(), 'μm'), file=f)
            print(row(t('fld_lambda_central'),
                      "%.2f" % GCONTACT.Lambda0C.min(), ''), file=f)
            print(t('sub_min_film'), file=f)
            print(row(t('sub_max_along_ae'),
                      "%.2f" % GCONTACT.hmC.max(), 'μm'), file=f)
            print(row(t('sub_min_along_ae'),
                      "%.2f" % GCONTACT.hmC.min(), 'μm'), file=f)
            print(row(t('sub_avg_along_ae'),
                      "%.2f" % GCONTACT.hmC.mean(), 'μm'), file=f)
            print(row(t('fld_lambda_min'),
                      "%.2f" % GCONTACT.LambdamC.min(), ''), file=f)
            print(dash, file=f)
        # power loss
        print('{:^{w}s}'.format(t('header_power_loss'), w=total_w), file=f)
        print(dots, file=f)
        print(row(t('fld_hvl_wimmer'),
                  "%.4f" % GCONTACT.HVL, 'Wimmer'), file=f)
        print(row(t('fld_hv_ohlendorf'),
                  "%.4f" % GEO.HV, 'Ohlendorf'), file=f)
        if GLUB is None:
            print(row(t('fld_cof'),
                      "%.4f" % GCONTACT.CoF, 'VDI 2736'), file=f)
        else:
            print(row(t('fld_cof'),
                      "%.4f" % GCONTACT.CoF, 'Schlenk'), file=f)
            print(row(t('fld_cof'),
                      "%.4f" % GCONTACT.CoFF, 'Fernandes'), file=f)
            print(row(t('fld_cof'),
                      "%.4f" % GCONTACT.CoFM.mean(), 'Matsumoto'), file=f)
        print(row(t('fld_pvzp_avg'),
                  "%.2f" % GCONTACT.Pvzp, 'W'), file=f)
        print(row(t('fld_pvzp_max'),
                  "%.2f" % GCONTACT.PvzpL.max(), 'W/mm'), file=f)
        print(row(t('fld_pvzp_min'),
                  "%.2f" % GCONTACT.PvzpL.min(), 'W/mm'), file=f)
        print(dash, file=f)
        # load carrying capacity
        print('{:^{w}s}'.format(t('header_lcc'), w=total_w), file=f)
        print(dots, file=f)
        if GMAT.MAT1 == ('STEEL' or 'ADI') and GMAT.MAT2 == ('STEEL' or 'ADI'):
            print(t('sub_influence_factors'), file=f)
            print(row(t('fld_ka'), ' %.2f' % GLCC.KA, ''), file=f)
            print(row(t('fld_kv'), ' %.2f' % GLCC.KV, ''), file=f)
            print(row(t('fld_khb'), ' %.2f' % GLCC.KHB, ''), file=f)
            print(row(t('fld_kfb'), ' %.2f' % GLCC.KFB, ''), file=f)
            print(row(t('fld_kha'), ' %.2f' % GLCC.KHA, ''), file=f)
            print(row(t('fld_kfa'), ' %.2f' % GLCC.KFA, ''), file=f)
            print(t('sub_contact_factors'), file=f)
            print(row(t('fld_ze'), ' %.3f' % GLCC.ZE, ''), file=f)
            print(row(t('fld_zh'), ' %.3f' % GLCC.ZH, ''), file=f)
            print(row(t('fld_zeps'), ' %.3f' % GLCC.ZEPS, ''), file=f)
            print(row(t('fld_zbeta'), ' %.3f' % GLCC.ZBETA, ''), file=f)
            print(row(t('fld_zl'), ' %.3f' % GLCC.ZL, ''), file=f)
            print(row(t('fld_zv'), ' %.3f' % GLCC.ZV, ''), file=f)
            print(row(t('fld_sigmaH0'), ' %.2f' % GLCC.SigmaH0, 'MPa'),
                  file=f)
            print(row(t('fld_sigmaH'),
                      ' %.2f' % GLCC.SigmaH1 + ' / ' + ' %.2f' % GLCC.SigmaH2,
                      'MPa'), file=f)
            print(row(t('fld_sigmaHP'),
                      ' %.2f' % GLCC.SigmaHP1 + ' / ' + ' %.2f' % GLCC.SigmaHP2,
                      'MPa'), file=f)
            print(row(t('fld_sh'),
                      ' %.2f' % GLCC.SH1 + ' / ' + ' %.2f' % GLCC.SH2, ''),
                  file=f)
            print(t('sub_bending_factors'), file=f)
            print(row(t('fld_yf'),
                      ' %.3f' % GLCC.YF1 + ' / ' + ' %.3f' % GLCC.YF2, ''),
                  file=f)
            print(row(t('fld_ys'),
                      ' %.3f' % GLCC.YS1 + ' / ' + ' %.3f' % GLCC.YS2, ''),
                  file=f)
            print(row(t('fld_yb'), ' %.3f' % GLCC.YB, ''), file=f)
            print(row(t('fld_ydelt'),
                      ' %.3f' % GLCC.YdelT1 + ' / ' + ' %.3f' % GLCC.YdelT2,
                      ''), file=f)
            print(row(t('fld_yrt'),
                      ' %.3f' % GLCC.YRrelT1 + ' / ' + ' %.3f' % GLCC.YRrelT2,
                      ''), file=f)
            print(row(t('fld_sigmaF0'),
                      ' %.2f' % GLCC.SigmaF01 + ' / ' + ' %.2f' % GLCC.SigmaF02,
                      'MPa'), file=f)
            print(row(t('fld_sigmaF'),
                      ' %.2f' % GLCC.SigmaF1 + ' / ' + ' %.2f' % GLCC.SigmaF2,
                      'MPa'), file=f)
            print(row(t('fld_sigmaFG'),
                      ' %.2f' % GLCC.SigmaFG1 + ' / ' + ' %.2f' % GLCC.SigmaFG2,
                      'MPa'), file=f)
            print(row(t('fld_sigmaFP'),
                      ' %.2f' % GLCC.SigmaFP1 + ' / ' + ' %.2f' % GLCC.SigmaFP2,
                      'MPa'), file=f)
            print(row(t('fld_sf'),
                      ' %.2f' % GLCC.SF1 + ' / ' + ' %.2f' % GLCC.SF2, ''),
                  file=f)
        else:
            print(t('sub_influence_factors'), file=f)
            print(row(t('fld_ambient_temp'), "%.1f" % GLCC.TO, '°C'),
                  file=f)
            print(row(t('fld_root_temp'),
                      "%.1f" % GLCC.TR1 + ' / ' + "%.1f" % GLCC.TR2,
                      '°C'), file=f)
            print(row(t('fld_flank_temp'),
                      "%.1f" % GLCC.TF1 + ' / ' + "%.1f" % GLCC.TF2,
                      '°C'), file=f)
            print(t('sub_influence_factors'), file=f)
            print(row(t('fld_ka_combined'), ' %.2f' % GLCC.KA, ''), file=f)
            print(t('sub_contact_factors_pa66'), file=f)
            print(row(t('fld_ze'), ' %.3f' % GLCC.ZE, ''), file=f)
            print(row(t('fld_zh'), ' %.3f' % GLCC.ZH, ''), file=f)
            print(row(t('fld_zeps'), ' %.3f' % GLCC.ZEPS, ''), file=f)
            print(row(t('fld_zbeta'), ' %.3f' % GLCC.ZBETA, ''), file=f)
            print(row(t('fld_sigmaH'), ' %.2f' % GLCC.SigmaH, 'MPa'), file=f)
            print(row(t('fld_sigmaHP'),
                      ' %.2f' % GLCC.SigmaHP1 + ' / ' + ' %.2f' % GLCC.SigmaHP2,
                      'MPa'), file=f)
            print(row(t('fld_sh'),
                      ' %.2f' % GLCC.SH1 + ' / ' + ' %.2f' % GLCC.SH2, ''),
                  file=f)
            print(t('sub_bending_factors'), file=f)
            print(row(t('fld_yfa'),
                      ' %.3f' % GLCC.YFa1 + ' / ' + ' %.3f' % GLCC.YFa2, ''),
                  file=f)
            print(row(t('fld_ysa'),
                      ' %.3f' % GLCC.YSa1 + ' / ' + ' %.3f' % GLCC.YSa2, ''),
                  file=f)
            print(row(t('fld_yeps'), ' %.3f' % GLCC.Yeps, ''), file=f)
            print(row(t('fld_ybeta'), ' %.3f' % GLCC.Ybeta, ''), file=f)
            print(row(t('fld_sigmaF'),
                      ' %.2f' % GLCC.SigmaF1 + ' / ' + ' %.2f' % GLCC.SigmaF2,
                      'MPa'), file=f)
            print(row(t('fld_sigmaFG'),
                      ' %.2f' % GLCC.SigmaFG1 + ' / ' + ' %.2f' % GLCC.SigmaFG2,
                      'MPa'), file=f)
            print(row(t('fld_sigmaFP'),
                      ' %.2f' % GLCC.SigmaFP1 + ' / ' + ' %.2f' % GLCC.SigmaFP2,
                      'MPa'), file=f)
            print(row(t('fld_sf'),
                      ' %.2f' % GLCC.SF1 + ' / ' + ' %.2f' % GLCC.SF2, ''),
                  file=f)
        print(dash, file=f)
        f.close()
