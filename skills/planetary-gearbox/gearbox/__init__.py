"""Переносимое ядро расчёта многоступенчатой планетарной передачи (VDI 2736).

Высокоуровневый API — :func:`calculate` (вход = dict spec, выход = dict отчёт),
а также поиск по библиотеке готовых коробок (:mod:`.library`).
"""

from . import engine, catalog, spec, library


def calculate(spec_dict, use_cache=True, save=True):
    """Полный расчёт по spec. Возвращает отчёт-dict (см. SKILL.md / spec.build_report).

    use_cache — вернуть готовый результат, если такой spec уже считали;
    save      — сохранить новый расчёт в библиотеку (designs/).
    """
    stages, load, cfg, meta = spec.normalize(spec_dict)
    # авто-число саттелитов (если не задано) — ДО хэша, чтобы кэш учитывал
    # фактически использованное число саттелитов
    stages = engine.resolve_planets(stages, cfg)
    h = spec.physics_hash(stages, load, cfg)

    if use_cache:
        cached = library.load_cached(h)
        if cached is not None:
            return spec.build_report(stages, load, cfg, cached['raw'], h, meta,
                                     from_cache=True)

    raw = engine.compute(stages, load, cfg)
    if save:
        library.save_cache(spec.raw_to_cache(stages, load, cfg, raw, h, meta))
    return spec.build_report(stages, load, cfg, raw, h, meta, from_cache=False)


__all__ = ['calculate', 'engine', 'catalog', 'spec', 'library']
