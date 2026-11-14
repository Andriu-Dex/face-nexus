# Captura y auditoría inicial del piloto

Fecha: 14-11-2026. El custodio autoriza prueba sintética y posterior piloto real y declara consentimiento individual de los cuatro participantes, disponibles para la sesión. La correspondencia K01=responsable y K02–K04=compañeros se custodia localmente; no se publican nombres ni formularios.

## Código entregado y comprobado

Captura manual: scripts/pilot_capture.py; auditoría: scripts/pilot_audit.py; pruebas: tests/test_pilot.py. Veinte tests del proyecto pasan, incluidos siete iniciales de persistencia/pauta/auditoría, dos adicionales de fallo de lectura/resolución con liberación sin fallback y los once del diagnóstico anterior. Los casos parametrizados cuentan como pruebas separadas.

Se implementaron PNG original 1920×1080, JSON por toma con hash, IDs/fuente/TRAIN/pauta, guardado exclusivo, tiempo mínimo entre fotos, selección explícita de USB CAMERA y detención ante fallo sin cambio de cámara. Se trasladó la dependencia de enumeración a requirements.txt porque la captura la requiere; no se instalaron modelos. La [guía de operación](../pilot_capture.md) detalla límites y manejo de sesiones parciales.

La auditoría valida integridad, etiquetas/rutas/pauta consistentes, resolución, cantidad, partición TRAIN, huérfanos y duplicados exactos. Mide intensidad/varianza de Laplaciano sin aprobar calidad con umbrales inventados. Identidad/consentimiento documental, pose/luz, distancias reales y duplicados perceptuales siguen sujetos a revisión manual; no hay detección ni embeddings por ausencia de pesos.

## Ensayo sintético ejecutado

Se generaron patrones geométricos sin rostros, con source=synthetic, bajo `outputs/pilot_synthetic/20261114T215914Z/raw`. Resultado del reporte privado audit.json: 80/80, K01–K04 con 20 cada uno, structural_pass=True, sin incidencias y sin duplicados exactos. Los datos sintéticos están separados del dataset real y no demuestran calidad facial. También se ejecutaron pruebas negativas de corrupción, fuente/partición incorrecta, metadatos ausentes, duplicados y sobrescritura.

## Destinos privados

Se crearon data y private en la raíz del proyecto; no había archivos registrados allí. `.gitignore` los excluye. Se aplicó ACL Windows heredable solo para cuenta actual, SYSTEM y Administradores, sin cifrado. Esto no protege contra procesos de la misma cuenta ni certifica la ausencia de sincronización externa. No se modificó ACL de carpetas preexistentes ni se publicaron datos.

## Ejecución real

La sesión K01 se abrió para captura manual después de superar la prueba sintética y confirmar destino. La cámara permanece bajo control del operador; la vista muestra vídeo en vivo e instrucciones, sin una fotografía de pose de ejemplo. Cada foto exige Espacio; no se obtienen ochenta fotos automáticamente. El resultado real se documentará al cerrar las sesiones; la disponibilidad de cuatro personas no demuestra que se hayan capturado sus fotos.

No se modificaron JSON del diagnóstico previo ni se descargaron pesos/datasets. No se entrenaron clasificadores. Se conservan los cambios previos y no se publicó ni creó commit. Mensaje de commit propuesto para esta entrega: `feat: add manual pilot capture and structural audit`.
