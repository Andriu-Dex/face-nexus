# Importación de fotogramas externos y agrupación conservadora

Fecha: 17-11-2026. Se revisó la colección externa proporcionada por el custodio, quien confirmó TMCAM 8305 y la correspondencia local de las cuatro carpetas. No se grabaron nuevos vídeos, descargaron pesos ni entrenaron modelos.

## Decisión de sesión

Tras la aclaración más reciente, **todos los segmentos de cada identidad se agrupan conservadoramente en una única S01 destinada a TRAIN/desarrollo**. Se mantiene el segmento como procedencia, sin tratarlo como sesión independiente. El número de vídeos/encuentros reales no se declara comprobado. Tener cantidades diferentes de segmentos no determina por sí solo independencia; esta agrupación evita asumirla y no pretende reconstruir las condiciones reales de grabación.

No hay particiones VALIDATION/TEST independientes disponibles con esta agrupación. Se requieren nuevas sesiones antes de evaluar generalización o seleccionar/validar el sistema completo. No realizar una división aleatoria de estos fotogramas para aparentar conjuntos independientes. Los desconocidos también siguen pendientes.

## Auditoría ejecutada

| Identidad seudónima | PNG válidos | Segmentos de origen | Resolución real |
| --- | ---: | ---: | --- |
| K01 | 3.851 | 4 | 848×478 |
| K02 | 2.833 | 4 | 1280×720 |
| K03 | 1.895 | 2 | 848×478 |
| K04 | 2.834 | 3 | 848×478 |
| Total | 11.413 | 13 | Resoluciones heterogéneas |

Se decodificaron todos los PNG, se registraron SHA-256 de archivo/píxeles, dimensiones y métricas descriptivas sobre vista gris de 256×256. No hay archivos ilegibles ni grupos de duplicados exactos de archivo o píxeles. No se borró ningún original.

Se señalaron 8.259 pares consecutivos dentro de segmentos con distancia Hamming de dHash <=2. Son candidatos de similitud global (incluye fondo), no prueba de rostro repetido ni de identidad; no se eliminaron automáticamente y no constituyen búsqueda exhaustiva de similitud entre todos los archivos. Los límites no se calibraron como criterio facial. Las medidas de intensidad y Laplaciano se guardan sin umbral de aceptación.

Las resoluciones no cumplen el objetivo de captura original 1920×1080. No se reescalaron para ocultar la diferencia. No se puede determinar si la reducción ocurrió al grabar, editar o exportar sin los vídeos y parámetros originales. La confirmación de cámara no demuestra resolución de cada vídeo. La colección puede usarse para desarrollo con esta limitación explícita; su calidad facial, pose, iluminación, encuadre y etiquetas necesitan revisión visual local antes de considerarla aprobada.

## Organización realizada sin modificar fuentes

La colección original permanece en la raíz externa entregada por el responsable. Se creó `_prepared/single_session_20261117/` como colección activa:

- `manifest.jsonl`: 11.413 registros con original relativo, nombre/ordinal de frame, segmento, S01, ID y hashes. Los tiempos exactos y hash del vídeo quedan null porque no se recibieron vídeos originales en esa raíz; no se inventó una frecuencia para calcularlos.
- `candidates/K01/S01/` hasta K04: 20 PNG por identidad con nombres como `K01_S01_SEG01_F000001.png` y JSON por muestra. Las copias mantienen exactamente los bytes de origen, verificados por hash.
- `audit.json`: resumen y hash del manifiesto.

La selección de 80 es uniforme en posición y equilibrada entre segmentos, excluyendo repetición exacta de píxeles dentro de la selección por persona. Es candidata para revisión, no selección automática de las mejores poses ni garantía de suficiencia. Los 11.413 originales siguen disponibles.

El inventario intermedio `_prepared/import_20261117/` se calculó mientras estaba vigente la primera respuesta del responsable acerca de sesiones independientes. Quedó marcado SUPERSEDED para asignación de sesiones; conservarlo solo como evidencia de auditoría. `_prepared/CURRENT.json` identifica la colección activa. La colección final volvió a comprobar los hashes de todos los originales antes de agrupar, sin repetir decodificación ni alterar el inventario previo.

Los nombres personales, correspondencia, manifiestos, hashes de imágenes y métricas individuales se conservan en almacenamiento privado. La carpeta preparada se creó con ACL para cuenta actual/SYSTEM/Administradores; no se modificaron permisos de las carpetas originales. No hay cifrado ni certificación automática de ausencia de sincronización. La política de eliminación a 90 días de la defensa abarca originales, copias y derivados; el plazo no se reinicia por importar.

Las diez fotos anteriores de K01/P01 permanecen separadas en el repositorio local excluido. No se combinaron ni se contaron como otra sesión independiente de esta colección: su relación temporal requiere procedencia, no una carpeta nueva.

## Código y comprobaciones

Se añadieron scripts/import_frames.py y tests/test_import_frames.py. La importación inventaría por segmento como etapa provisional; --regroup-from crea la única sesión activa y TRAIN conservadoramente. No se sobrescriben destinos existentes ni se mueven originales. Mapping de carpetas a IDs es un JSON privado excluido de Git.

Veinticinco tests pasan: incluyen orden numérico de frames (999 antes de 1000), índices de selección únicos, integridad de originales, archivos inválidos/duplicados, rechazo de rutas fuera de raíz y agrupación de segmentos en una S01/TRAIN con IDs únicos. Se verificaron 11.413 registros canónicos y hashes de las 80 copias. No se declara detección facial ni evaluación de reconocimiento ejecutadas.

No se publicaron cambios ni se modificó el índice de Git. Mensaje de commit propuesto: `feat: audit external video frames and group development sessions`.
