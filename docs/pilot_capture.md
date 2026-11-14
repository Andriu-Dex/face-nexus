# Captura manual y auditoría del piloto

Herramientas iniciales comprobadas con imágenes sintéticas el 14-11-2026. No hay detector, clasificación ni embeddings en esta herramienta.

## Carpetas y privacidad

`data/raw/pilot/` contiene originales y metadatos seudónimos; `private/` contiene consentimientos y correspondencia de nombres/IDs que custodia el responsable. Ambas raíces están excluidas de Git. Se crearon con permisos Windows para la cuenta actual, SYSTEM y Administradores (heredables por sus archivos), sin acceso general a otras cuentas. No están cifradas y no se ha certificado la ausencia de software de sincronización: el custodio debe mantenerlas fuera de sus copias externas. SYSTEM/Administradores y procesos de la misma cuenta pueden acceder; esto no es anonimización.

No enviar fotos ni formularios al chat. El responsable declaró que ya tiene consentimiento de las cuatro personas y autorizó el piloto. La herramienta registra esa declaración por ID; no verifica firmas ni contenido del consentimiento. La eliminación a 90 días de la defensa sigue vigente; la fecha concreta depende de cuándo ocurra la defensa.

## Operación

Desde la raíz con el entorno instalado, por cada persona:

```powershell
.\.venv\Scripts\python.exe -m scripts.pilot_capture --person K01 --camera 1 --consent-confirmed
```

K01 se asigna al responsable; K02–K04 a sus compañeros en orden estable acordado localmente. Antes de ejecutar por otro participante, cambiar --person. La herramienta verifica que el índice DirectShow corresponda a USB CAMERA; el operador confirma que es la TMCAM. No prueba otros índices ni cambia a cámara integrada. La confirmación CAPTURAR autoriza guardar imágenes reales de esa sesión. No ejecutar varios procesos simultáneamente.

Espacio guarda una sola toma después de confirmar persona, pose, luz y encuadre; Q/Esc o cerrar ventana termina sin borrar lo capturado. No hay captura automática. Esperar calentamiento de cinco segundos y al menos dos segundos entre tomas. La vista se reduce y tiene instrucciones; se guarda el PNG original 1920×1080, sin marcas, recortes ni filtros.

Hay veinte pasos agrupados según la ficha en [data_protocol.md](data_protocol.md). Luz diffuse = frontal/difusa, lateral = lateral moderada. Los objetivos de pose y distancia son aproximados y no medidos por software. La distancia real permanece sin medir en metadata: revisarla localmente si se necesita para análisis. El operador confirma las condiciones al pulsar Espacio; la auditoría visual debe corroborarlas.

La sesión P01 solo pertenece a TRAIN/desarrollo. Existe límite de quince minutos por ejecución; read nativo bloqueado puede impedir que se compruebe el temporizador. No reabrir ni reconectar automáticamente. Ante un fallo, se conservan originales y metadatos ya escritos. Una carpeta P01 existente impide iniciar otra sesión del mismo ID: no borrar imágenes para reintentar; revisar incidencias antes de habilitar una continuación controlada. No se implementó reanudación automática en esta primera versión.

## Datos y auditoría

Por toma se guarda `K01_P01_0001.png` junto a JSON con SHA-256, ID/sesión, fuente, TRAIN, tiempo UTC, pauta, configuración y revisión pendiente. El registro por toma constituye el manifiesto distribuido; no hay CSV agregado duplicado. Un error de escritura elimina solo una imagen nueva cuyo registro falló; un JSON incompleto puede quedar como incidencia detectable. No sobrescribe originales ni reportes.

Al terminar los cuatro:

```powershell
.\.venv\Scripts\python.exe -m scripts.pilot_audit --output outputs/pilot_audit_01.json
```

El reporte privado valida cantidad por identidad, pautas, etiquetas/rutas consistentes, TRAIN, hashes, decodificación y resolución, archivos huérfanos y duplicados exactos. Calcula varianza de Laplaciano e intensidad media sin umbrales de descarte. Revisión de identidad, pose, luz, distancias, duplicados perceptuales, consentimiento documental y calidad real sigue siendo manual. La detección facial necesita otra fase y pesos autorizados. `structural_pass` no acredita que el dataset esté plenamente aprobado ni que identifique correctamente a nadie.

Las pruebas usan entradas sintéticas y archivos temporales; el ensayo integrado sintético adicional está separado bajo outputs/pilot_synthetic con source=synthetic. Jamás mezclarlo con data/raw/pilot ni presentar sus resultados como rostros capturados.
