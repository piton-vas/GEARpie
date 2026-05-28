from CLASSES import MATERIAL_LIBRARY, I18N

I18N.set_lang('ru')

mats = ['D16T', 'PA6_CF', 'PA6_PRINT', 'PETG', 'POM_C']

L = ["Materials properties:"]
L.append("-" * 60)
L.append(f"{'Material':<15} {'SigmaFlim':<12} {'SigmaHlim':<12} {'E':<10}")
L.append("-" * 60)

for mat_name in mats:
    lib = MATERIAL_LIBRARY.LIBRARY_MAT(mat_name)

    try:
        if callable(lib.SigmaFlim):
            sigma_f = lib.SigmaFlim(25, 1e6)
        else:
            sigma_f = float(lib.SigmaFlim)
    except:
        sigma_f = 0

    try:
        if callable(lib.SigmaHlim):
            sigma_h = lib.SigmaHlim(25, 1e6)
        else:
            sigma_h = float(lib.SigmaHlim)
    except:
        sigma_h = 0

    E = lib.E

    L.append(f"{mat_name:<15} {sigma_f:<12.1f} {sigma_h:<12.1f} {E:<10.0f}")

print('\n'.join(L))
