# Reserva de lote y filas de calibración

22-11-2026. Correcciones de supervisión con datos sintéticos. Piloto con un operador. Sin veto CNN ni pestillo.

## Clave de lote

Antes de escribir fotogramas se crea `.pending-<run>` en exclusivo. Si esa carpeta o el destino ya existen, la segunda ejecución se rechaza y no se borra el pendiente anterior.

## Calibración

La separación de desconocidos se declara verificada solo si las identidades salen de las filas del NPZ realmente usado (`sample_ids` e `identity_ids`). Una lista externa, aunque lleve la huella de la galería, deja el estado sin verificar.
