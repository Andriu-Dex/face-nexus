# Procedencia y protocolo del dataset definitivo

17-11-2026 · Pauta aprobada y herramienta preparada. La procedencia se auditó en solo lectura y la herramienta se probó con datos sintéticos. La captura real sigue pendiente de autorización.

## Procedencia de los 13 segmentos

Se contrastó el manifiesto activo con los archivos entregados en la raíz privada de FaceNexus. Los segmentos corresponden a carpetas de fotogramas. Cada identificador SEG es local a una identidad y la etiqueta se basa en la correspondencia confirmada por el custodio. Los segmentos de cada persona conservan la agrupación S01. La cantidad real de vídeos o encuentros queda sin verificar.

| Identidad | Segmento | PNG verificados | Resolución del PNG |
| --- | --- | ---: | --- |
| K01 | SEG01 | 963 | 848×478 |
| K01 | SEG02 | 1.006 | 848×478 |
| K01 | SEG03 | 965 | 848×478 |
| K01 | SEG04 | 917 | 848×478 |
| K02 | SEG01 | 659 | 1280×720 |
| K02 | SEG02 | 821 | 1280×720 |
| K02 | SEG03 | 586 | 1280×720 |
| K02 | SEG04 | 767 | 1280×720 |
| K03 | SEG01 | 980 | 848×478 |
| K03 | SEG02 | 915 | 848×478 |
| K04 | SEG01 | 1.006 | 848×478 |
| K04 | SEG02 | 928 | 848×478 |
| K04 | SEG03 | 900 | 848×478 |
| **Total** | **13** | **11.413** | |

Para las 13 filas se aplica el mismo estado de evidencia:

| Dato | Evidencia disponible |
| --- | --- |
| Cámara | El custodio confirmó TMCAM 8305 para la colección. El manifiesto lo registra como declaración del operador. La carpeta entregada carece de vídeos fuente o registros de dispositivo que vinculen cada segmento con esa cámara. |
| Resolución, FPS y códec originales | Pendientes. La tabla recoge dimensiones de los PNG decodificados durante la importación, cuyos hashes se volvieron a comprobar. Los PNG carecen de una referencia verificada a los parámetros del vídeo fuente. |
| Conversión, compresión y redimensionamiento | El custodio declaró extracción externa de fotogramas. Se desconoce el programa y su configuración, y si hubo compresión o redimensionamiento al grabar, editar o exportar. |
| Fecha, condiciones y marcas temporales | Fecha/hora de captura, iluminación, distancia y montaje por segmento sin ficha contemporánea disponible. Los nombres y números de fotograma sirven para ordenar; los tiempos y el hash del vídeo siguen vacíos en el manifiesto. |

Se revisó el contenido bajo la raíz privada de FaceNexus en Downloads. Allí se encontraron PNG y artefactos de inventario y análisis, sin contenedores de vídeo originales. Si el custodio localiza los vídeos y la configuración de exportación, podrá verificarse localmente resolución, FPS y códec con los metadatos del archivo y cotejar la correspondencia por segmento. La identificación de cámara requiere metadatos del dispositivo u otro registro contemporáneo que la vincule a la captura.

## Uso experimental y conservación

La colección se incorpora al desarrollo. El manifiesto histórico asigna S01 a TRAIN para mantener cada identidad agrupada. Su ingreso al entrenamiento definitivo se decidirá comparando las mismas sesiones nuevas de TRAIN con y sin S01, sobre la misma VALIDATION independiente. La procedencia incompleta, la resolución asociada a la identidad y la dependencia entre fotogramas limitan la interpretación de esta colección.

La auditoría confirmó SHA-256 del manifiesto, los 11.413 originales y las 80 copias candidatas. También comprobó cinco artefactos del lote de procesamiento contra los hashes registrados, la correspondencia entre las 80 candidatas y sus resultados, y los 73 embeddings de 128 componentes. Se conservan las siete entradas sin detección y las tomas difíciles, incluidas las borrosas y de perfil. Los [informes de importación](06_external_frames.md) y [validación facial](07_face_pipeline_validation.md) quedan como evidencia histórica. La custodia y la eliminación a los 90 días de la defensa, o antes por retiro, siguen aplicándose a los derivados.

## Adquisición y organización

El [protocolo de datos](../data_protocol.md#adquisición-del-dataset-definitivo--17-11-2026) es la pauta vigente para cantidades, asignación, fichas y condiciones. El [diagnóstico previo](03_camera_diagnostic.md) observó 29,241 FPS medios a 1080p durante diez minutos. La aplicación de 60 Hz sigue pendiente de confirmación.

La planificación inicial suma 480 tomas de conocidos y 240 de desconocidos. La cobertura de personas, sesiones y condiciones determinará qué conclusiones permite el conjunto. El plan y el manifiesto conservan la partición de todos los derivados de cada encuentro. El custodio decidirá antes de iniciar la selección y calibración si añade otra ronda VALIDATION de conocidos.

## Herramienta y protección preparadas

- La herramienta de captura definitiva reutiliza la medición de cámara del diagnóstico y sigue los dos bloques nominales del protocolo. Lee un plan privado de sesiones, guarda PNG y ficha juntos, mantiene el vínculo de cada reemplazo y señala escrituras interrumpidas. El piloto P01 conserva su herramienta y datos históricos.
- El equipo informa Windows 11 Home. La consulta de BitLocker no permitió comprobar el estado de `C:`. El responsable aprobó la ubicación `C:\Downloads\FaceNexus` y el instalador oficial de VeraCrypt 1.26.31 se descargó y verificó por SHA-256 y Authenticode. La creación, recuperación y validación del contenedor están pendientes. La [guía de puesta en servicio](../vault_and_camera_setup.md) reúne los comandos del montaje, la copia histórica verificable y el ensayo sin personas.
- Se auditó un lote sintético de 80 PNG a 1920×1080 que incluyó las tres particiones y desconocidos disjuntos. Se comprobó la detección de hashes modificados, duplicados entre particiones, conflictos del plan, repeticiones y escrituras interrumpidas. Con una cámara simulada se verificó el informe sin PNG y el registro independiente de 60 Hz y bandas. El comando de verificación rechazó el directorio habitual de desarrollo por estar fuera de un montaje VeraCrypt. [Guía de la herramienta](../pilot_capture.md#herramienta-del-dataset-definitivo)
- La suite completa pasó 48 pruebas automatizadas. También se verificaron el ejemplo de plan, los enlaces locales nuevos y la compilación de los scripts.

## Comparación posterior

Conservar YuNet + SFace como referencia. Para evaluar otro extractor, acreditar procedencia, versión, licencia y restricciones del peso específico, verificar SHA-256 y documentar el preprocesamiento y coste. Usar las mismas sesiones, tomas y detecciones de partida en TRAIN/VALIDATION. Registrar cuándo falla cada etapa y reportar tanto resultados condicionados a rostro válido como de extremo a extremo. Elegir y congelar la configuración antes de abrir TEST, según el [protocolo de evaluación](../evaluation_protocol.md).

## Decisiones pendientes

1. Crear y verificar el contenedor en la ubicación aprobada. El custodio configura la credencial y su recuperación. Completar la copia histórica y comprobarla antes de decidir sobre las copias anteriores.
2. Confirmar calendario y condiciones difíciles de la primera ronda, las asignaciones de los voluntarios y la reserva de TEST. Verificar con cada participante el alcance del consentimiento.
3. Autorizar expresamente la captura real tras verificar la cámara y el destino. La primera ronda se audita antes de ampliarla y cuenta para TRAIN si cumple la pauta vigente.
4. Decidir la segunda ronda de conocidos para VALIDATION antes de seleccionar modelos o calibrar el rechazo.

## Diagnóstico operativo parcial de la TMCAM

La ronda R99 se ejecutó con la escena vacía confirmada por el custodio. DirectShow abrió `USB CAMERA` en el índice 1, con MJPG. Tras cinco segundos de calentamiento, la herramienta recibió 1.801 fotogramas de 1920×1080 en 60 segundos, a 30,002 FPS medios. Hubo cero fallos de lectura y cero pausas superiores a 250 ms. El mayor intervalo fue de 53,5 ms.

Tras cerrar la vista previa, el custodio confirmó que no observó bandas con luz frontal difusa ni con luz lateral. La observación se registra aquí como confirmación posterior. El JSON técnico original quedó pendiente de aprobación porque la herramienta no registró las respuestas durante la ejecución. El ajuste de 60 Hz sigue sin confirmar. Se verificó que la prueba no guardó PNG ni creó sesiones de captura.

Antes de la primera ronda real se requiere su propia comprobación de cámara aprobada en la herramienta, además de la autorización expresa de captura. Quedan pendientes las nuevas sesiones, la incorporación de otro extractor y el entrenamiento.
