# Captura manual y auditoría

Usar la [herramienta del dataset definitivo](#herramienta-del-dataset-definitivo) para las nuevas rondas. El procedimiento P01 se conserva como antecedente.

## Herramienta del dataset definitivo

La [pauta de adquisición vigente](data_protocol.md#adquisición-del-dataset-definitivo--17-11-2026) define las poses, las cantidades y las particiones. La captura real requiere autorización expresa y consentimiento individual confirmado por el custodio.

### Almacenamiento cifrado

El contenedor VeraCrypt NTFS de `C:\Downloads\FaceNexus` se montó en `V:`. Los permisos y el SHA-256 del marcador se verificaron tras desmontar y volver a montar. Quedan pendientes la prueba de recuperación y la copia de datos históricos. Los [comandos de puesta en servicio](vault_and_camera_setup.md) incluyen también el ensayo de la TMCAM en una escena sin personas.

### Plan privado

Guardar `plan.json` en la carpeta aprobada del volumen. Ejemplo sintético de una sesión:

```json
[
  {
    "person_id": "K01",
    "session_id": "K01_S02",
    "round_id": "R01",
    "split": "TRAIN",
    "first_light": "diffuse",
    "consent_ref": "consent_K01",
    "setup": "Cámara a altura de ojos, fondo común y referencia a 0,8 m",
    "difficult": [
      {"label": "Perfil pronunciado", "lighting": "lateral", "distance_m": 0.8}
    ]
  }
]
```

Asignar una fila por encuentro. Cada ronda conserva la misma partición y primera luz para todos sus integrantes. Cada ID de desconocido pertenece a un único grupo VALIDATION o TEST. `difficult` es opcional. El custodio comprueba localmente que cada participante conserve su ID y que cada encuentro sea independiente. La herramienta detecta conflictos del plan y coteja las sesiones registradas con sus fichas. Se pueden incorporar filas nuevas para otros encuentros o participantes manteniendo las fichas anteriores.

### Comprobación por ronda, toma y auditoría

Estos comandos corresponden a las rondas del dataset definitivo una vez aprobada la validación operativa. Para el ensayo inicial se usa la ronda ficticia R99 de la [guía de puesta en servicio](vault_and_camera_setup.md#4-validar-la-tmcam-con-una-escena-sin-personas).

Ejemplo con unidad y comprobación ficticias. Sustituir `V:` y el índice por los que correspondan al montaje y a la TMCAM:

```powershell
.\.venv\Scripts\python.exe -m scripts.dataset_capture --vault 'V:\FaceNexus' check-vault
.\.venv\Scripts\python.exe -m scripts.dataset_capture --vault 'V:\FaceNexus' check-camera --round R01 --camera 1 --antiflicker unconfirmed
```

Verificar el ajuste de 60 Hz en el controlador y elegir `confirmed_60hz`, `other` o `unconfirmed`. Confirmar la TMCAM con la escena sin personas. Se mide la entrega real de imágenes y después se inspeccionan ambos modos de luz. Registrar con **S** si se ven bandas o **N** si la vista está libre de bandas en esa condición. La herramienta solo guarda un informe técnico. Revisar FPS y pausas frente al diagnóstico previo antes de escribir `APROBAR`. Repetir si cambian la conexión, el modo o la iluminación del ensayo.

Tras recibir autorización expresa de captura, usar el ID que imprimió `check-camera`:

```powershell
.\.venv\Scripts\python.exe -m scripts.dataset_capture --vault 'V:\FaceNexus' capture --session K01_S02 --check R01-00000000000000000000000000000000 --capture-approved
.\.venv\Scripts\python.exe -m scripts.dataset_capture --vault 'V:\FaceNexus' audit --session K01_S02
```

- **Espacio** confirma la condición en pantalla y guarda el PNG original y su SHA-256. El registro indica la luz y la distancia aproximada que confirma el operador. **D** permite ajustar la distancia. Para el ajuste y los motivos de rechazo o exclusión, escribir en la terminal y volver a la vista.
- **X** registra un intento rechazado con su motivo y mantiene la toma pendiente. **R** excluye la última foto aceptada del conjunto utilizable y vuelve a esa toma. La imagen se conserva y el reemplazo queda enlazado con el intento original. **Q** o **Esc** terminan la sesión. Usar `--resume` únicamente para continuar el mismo encuentro con el mismo plan y comprobación.
- Cada intento guarda su ficha en `sessions/<sesión>/attempts/<intento>/record.json`. La ficha de sesión contiene la partición y la comprobación de cámara. Una carpeta de intento se publica con el PNG y su ficha en una sola operación de renombrado. Si la escritura se interrumpe, la auditoría señala la carpeta `.pending-*` y el programa bloquea la continuación de esa sesión hasta su revisión local. Conservar esa carpeta en el volumen mientras se investiga.
- La auditoría comprueba secuencia, vínculos de reemplazo, completitud, decodificación y hashes. Sin `--session` cubre el plan completo y puede detectar PNG idénticos entre particiones. El custodio revisa aparte similitud visual, etiquetas, condiciones e independencia de los encuentros. Un fallo válido del futuro detector conserva su toma original y cuenta en la evaluación correspondiente.

## Piloto P01 (antecedente)

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
