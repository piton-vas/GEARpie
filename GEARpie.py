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

# AVOID CREATION OF PYCACHE FOLDER ============================================
import sys
sys.dont_write_bytecode = True

# IMPORT LIBRARIES ============================================================
from CLASSES import (GEAR_LIBRARY, MATERIAL_LIBRARY, LUBRICANT_LIBRARY,
                     LOAD_STAGES, CALC_GEOMETRY, LOAD_SHARING,
                     FORCES_SPEEDS, CONTACT, INVOLUTE_GEOMETRY, DIN3990,
                     VDI2736, MESH_GENERATOR, OUTPUT_PRINT, PLOTTING, I18N)
from CLASSES.I18N import t

# LANGUAGE SELECTION ==========================================================
_lang = input(I18N.t('prompt_lang')).strip().lower() or 'en'
I18N.set_lang(_lang)

# GEAR GEOMETRY, MATERIAL AND FINISHING =======================================
# name of gear on library (includes geometry and surface finishing)
print('='*65)
print('{:^65s}'.format('GEARpie'))
print('.'*65)
print('{:^65s}'.format('MIT License, Carlos M.C.G. Fernandes, 2022'))
print('='*65)
print('\n')
print(t('cli_geom_list'))
print('C14, S30, H501, H701, H951')
print(t('cli_geom_new'))
GEAR_TYPE = str(input(t('prompt_gear_type'))).upper()
# GEAR SELECTION ==============================================================
GTYPE = GEAR_LIBRARY.GEAR(GEAR_TYPE)
# GEAR MATERIALS ==============================================================
# pinion and wheel material
print(t('cli_mat_list'))
print('STEEL, ADI, POM, PA66')
MAT_PINION = str(input(t('prompt_pinion_mat')) or 'STEEL').upper()
MAT_WHEEL = str(input(t('prompt_wheel_mat')) or 'STEEL').upper()
# LUBRICANT ===================================================================
# lubricant
BASE_NAME = str(input(t('prompt_base_oil'))).upper()
if BASE_NAME == 'D':
    GLUB = None
    T0 = float(input(t('prompt_ambient_temp')))
else:
    LUB_NAME = str(input(t('prompt_iso_vg'))).upper()
    Tlub = float(input(t('prompt_lub_temp')))
    GLUB = LUBRICANT_LIBRARY.LUBRICANT(BASE_NAME, LUB_NAME, Tlub)
# select element where is applied speed and torque (P - pinion, W - wheel)
element = str(input(t('prompt_pw_select'))).upper()
if element == 'F':
    STAGE = LOAD_STAGES.FZG()
    torque = STAGE.torque
    speed = float(input(t('prompt_fzg_speed')))
else:
    # torque Nm
    torque = float(input(t('prompt_torque')))
    # speed rpm
    speed = float(input(t('prompt_speed')))
# discretization of path of contact
size = 1000
# discretization of involute geometry
DISCRETIZATION = 1000
# LOAD-SHARING MODEL?
ANSWER_LS = str(input(t('prompt_load_sharing'))).upper()
# stress field position
POST = str(input(t('prompt_stress_pos'))).upper()
POSAE = 'A' + POST
# graphics
ANSWER_GRAPHICS = str(input(t('prompt_graphics'))).upper()

if ANSWER_GRAPHICS == 'Y':
    GRAPHICS = True
else:
    GRAPHICS = False

# element order
ANSWER_MESH = str(input(t('prompt_mesh'))).upper()

if ANSWER_MESH == 'Y':
    MESH = True
    DIM_MESH = int(input(t('prompt_mesh_dim')))
    DIM = str(DIM_MESH)+'D'
    ORDER = int(input(t('prompt_elem_order')))
    PTOOTH = int(input(t('prompt_pinion_teeth')))
    NODEP = int(input(t('prompt_pinion_nodes')))
    WTOOTH = int(input(t('prompt_wheel_teeth')))
    NODEW = int(input(t('prompt_wheel_nodes')))
else:
    MESH = False

# ASSIGN GEAR MATERIALS =======================================================
GMAT = MATERIAL_LIBRARY.MATERIAL(MAT_PINION, MAT_WHEEL)
# GEAR GEOMETRY ACCORDING TO MAAG BOOK ========================================
GEO = CALC_GEOMETRY.MAAG(GTYPE)
# INVOLUTE PROFILE GEOMETRY ===================================================
Pprofile = INVOLUTE_GEOMETRY.LITVIN('P', GEO, DISCRETIZATION)
Wprofile = INVOLUTE_GEOMETRY.LITVIN('W', GEO, DISCRETIZATION)
# LINES OF CONTACT ASSUMING A RIGID LOAD SHARING (SPUR AND HELICAL) ===========
GPATH = LOAD_SHARING.LINES(size, GEO, GMAT, Pprofile, Wprofile)
# FORCES AND SPEEDS ===========================================================
GFS = FORCES_SPEEDS.OPERATION(element, torque, speed, GEO, GPATH, ANSWER_LS)
# GEAR CONTACT QUANTITIES (PRESSURE, FILM THICKNESS, POWER LOSS) ==============
GCONTACT = CONTACT.HERTZ(GMAT, GLUB, GEO, GPATH, GFS, POSAE)
# LOAD CARRYING CAPACITY ======================================================
KA = 1.25
if MAT_PINION == ('STEEL' or 'ADI') and MAT_WHEEL == ('STEEL' or 'ADI')\
    and GLUB is not None:
    GL40 = LUBRICANT_LIBRARY.LUBRICANT(BASE_NAME, LUB_NAME, 40)
    GLCC = DIN3990.LCC(GMAT, GEO, GFS, KA, GL40)
else:
    try:
        GLCC = VDI2736.LCC(GMAT, GEO, GFS, GPATH, GCONTACT, T0, KA)
    except:
        GLCC = VDI2736.LCC(GMAT, GEO, GFS, GPATH, GCONTACT, Tlub, KA)
# INVOLUTE PROFILE GEOMETRY ===================================================
if MESH:
    MESH_GENERATOR.MESHING('P', GTYPE, GEO, Pprofile, PTOOTH, ORDER, NODEP, DIM)
    MESH_GENERATOR.MESHING('W', GTYPE, GEO, Wprofile, WTOOTH, ORDER, NODEW, DIM)
# OUTPUT PRINT ================================================================
OUTPUT_PRINT.PRINTING(GTYPE, GMAT, GLUB, GEO, GFS, GCONTACT, GLCC)
# OUTPUT GRAPHICS =============================================================
if GRAPHICS:
    PLOTTING.GRAPHICS(GPATH, GFS, GCONTACT)
# CLOSE PROGRAM ===============================================================
input(t('prompt_exit'))
