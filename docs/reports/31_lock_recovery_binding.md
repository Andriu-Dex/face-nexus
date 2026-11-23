# Candado, recuperación estricta y vínculo de calibración

22-11-2026. Correcciones de supervisión con datos sintéticos. Sin capturas reales, pestillo ni veto CNN.

## Índice

La actualización del manifiesto adquiere el candado antes de leer. Si la revisión en disco ya no es la esperada, se rechaza. Dos escritores que parten del mismo índice no pueden dejar solo la segunda ráfaga.

## Staging

Antes de publicar un `.pending-*` se cotejan identidad, encuentro, fase, huellas de fotogramas y filas HOG. Un NPZ corrupto o una ficha de otro encuentro no se publica y el pendiente queda para revisión.

## Disjunción

Los IDs de calibración llevan la huella de la galería del ensayo. Los extraños exigen `sample_ids` en el NPZ y en cada fila. Sin ambos vínculos, `unknowns_disjoint` queda sin verificar.
