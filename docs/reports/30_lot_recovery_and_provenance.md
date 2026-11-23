# Recuperación de lotes y procedencia de evaluación

22-11-2026. Correcciones de supervisión sobre captura sintética. Sin capturas reales ni pestillo.

## Lotes existentes

`recover_unpublished_lot` ya no borra una carpeta final ausente del manifiesto. Si el destino existe y no está listado, se deja intacto y se informa el conflicto. Solo se publica un `.pending-*` cuya ficha acredita la identidad y contiene HOG.

## Fallo de publicación

Si el manifiesto ya registró el lote y falla el renombrado, el staging se conserva. La recuperación puede publicarlo. El índice usa un candado; un segundo escritor no pisa la revisión.

## Procedencia

`--encounter-id` es obligatorio y no puede derivarse del papel y el `run-name`. Los extraños y los inscritos se atan al NPZ por SHA-256 y por fila (`sample_id`, etiqueta `OTHER` en desconocidos). Coincidir en cantidad no acredita la disjunción.

El veto CNN sigue apagado. No hubo ensayo de puerto.
