# Validación de procesamiento facial con YuNet y SFace

Fecha: 17-11-2026. Alcance autorizado en instruction.md y confirmado en chat: dos pesos concretos, detección/alineación/extracción y exploración sobre 80 candidatas TRAIN. No se implementaron clasificadores, rechazo de desconocidos, cámara en vivo ni autorización física. No se ajustó el extractor.

## Dictamen

**YuNet + SFace es técnicamente viable para continuar el desarrollo**, con limitaciones claras: 73/80 candidatas produjeron un único rostro y embedding válido; siete no tuvieron detección bajo la configuración inicial. Hay separación preliminar en las distribuciones de similitud, pero se solapan. No se acredita accuracy, generalización, rechazo de desconocidos o seguridad de acceso. El criterio de aceptación permite reportar fallos: no exige fabricar una separación perfecta.

La colección activa se obtuvo exclusivamente desde `_prepared/CURRENT.json`. Las cuatro identidades mantienen una sola S01 conservadora en TRAIN. Los 11.413 frames siguen en desarrollo; no se crearon VALIDATION/TEST aleatorios ni se modificó la selección para ocultar fallos.

## Modelos y verificación de procedencia

Repositorio oficial: [OpenCV Zoo](https://github.com/opencv/opencv_zoo/tree/48b10fa505aeb51fbd127fc60a5c660040e823b7). Revisión fijada: `48b10fa505aeb51fbd127fc60a5c660040e823b7`.

| Función | Artefacto | Bytes comprobados | SHA-256 publicado y local coincidente |
| --- | --- | ---: | --- |
| Detección | face_detection_yunet_2023mar.onnx | 232.589 | `8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4` |
| Extracción | face_recognition_sface_2021dec.onnx | 38.696.353 | `0ba9fbfa01b5270c96627c4ef784da859931e02f04419c829e83484087c34e79` |

Se consultaron los README/LICENSE de esa revisión antes de descargar: [YuNet declara MIT para todos los archivos de su carpeta](https://github.com/opencv/opencv_zoo/blob/48b10fa505aeb51fbd127fc60a5c660040e823b7/models/face_detection_yunet/README.md); [SFace declara Apache 2.0 para todos los de su carpeta](https://github.com/opencv/opencv_zoo/blob/48b10fa505aeb51fbd127fc60a5c660040e823b7/models/face_recognition_sface/README.md). Se conservaron ambos LICENSE y README en models/verified, excluido de Git. No extrapolar esto a otros pesos, datasets o publicaciones de rostros. SFace del proveedor utiliza MobileFaceNet con pérdida SFace; el dataset exacto de entrenamiento del ONNX sigue sin acreditarse inequívocamente.

Los hashes de referencia se comprobaron en punteros Git LFS de la revisión fija y después contra los binarios descargados por HTTPS desde media.githubusercontent.com. Solo se adquirieron esos dos ONNX y sus avisos; no se ejecutó código descargado ni se incorporó un dataset público. El cargador vuelve a verificar ambos archivos antes de inferencia. Registro privado: models/verified/registry.json.

## Pipeline y configuración

Código directo en scripts/face_pipeline.py: imagen BGR uint8 → reducir solo para detección a lado máximo 640 manteniendo proporción → YuNet → devolver coordenadas al original → validar rostro único y cinco puntos → alignCrop de OpenCV → SFace.feature → validar vector. No se amplían originales ni se reemplazan capturas.

YuNet usa CPU/OpenCV DNN, score mínimo 0,9, NMS 0,3 y topK 5000. Son parámetros iniciales documentados, no umbrales de identidad ni valores escogidos para maximizar éxitos. No se cambiaron tras ver los siete fallos. Entradas originales observadas: 848×478 y 1280×720; entradas de detector: 640×361 y 640×360. La normalización interna del DNN es de OpenCV; no se añadió conversión/normalización duplicada a la interfaz FaceRecognizerSF.

En los 73 casos únicos, la salida YuNet registrada tiene 1×15 valores (caja de cuatro, cinco puntos de dos coordenadas y score); los siete restantes no devolvieron detecciones. La alineación observada es 112×112×3 uint8. SFace devolvió (1,128) float32; almacenamiento conjunto (73,128), todos finitos, norma no nula. Las normas crudas variaron de 7,133 a 14,320 (mediana 11,891): no son probabilidades ni un score de calidad. La normalización L2 se usa únicamente para calcular coseno. No se ajustó PCA ni transformación aprendida.

Cero detecciones, varias detecciones, geometría inválida o embedding inválido no producen vector aceptado. No hay elección del rostro mayor. Se conservan registros de todos los fallos y no se emite ninguna decisión de acceso.

## Resultados de las 80 candidatas

| Identidad | Extracciones válidas | Sin detección | Caja facial mediana, píxeles originales | Intensidad gris mediana en ROI | Varianza Laplaciano mediana en ROI |
| --- | ---: | ---: | --- | ---: | ---: |
| K01 | 18/20 | 2 | 139.5 × 177.9 | 107.3 | 405.2 |
| K02 | 19/20 | 1 | 242.1 × 313.0 | 111.4 | 126.7 |
| K03 | 18/20 | 2 | 164.0 × 218.5 | 111.0 | 247.2 |
| K04 | 18/20 | 2 | 157.3 × 207.8 | 133.0 | 526.4 |

Total: 73 válidas y siete sin detección (cobertura de extracción 91,25% de estas 80 entradas), cero casos múltiples en la colección real y cero embeddings inválidos entre las detecciones únicas procesadas. No denominar esa cobertura exactitud ni recall de benchmark: no hay anotaciones exhaustivas independientes de detección. El estado interno no_face significa **sin detección del modelo**, no ausencia humana de un rostro en la imagen.

Las medidas de ROI son descriptivas, incluyen variación de pose/escala/contenido y no están calibradas para descartar. K02 tiene mayor resolución y rostro aparente mayor, pero su identidad, condiciones y vídeo también cambian: no se puede atribuir causalmente su comportamiento a resolución. La alineación redimensiona a 112×112 para el modelo; no recupera información perdida ni convierte los originales a 1080p.

## Revisión visual y fallos

Se generaron cuatro láminas privadas con las 80 vistas detectadas y 73 recortes, y se revisaron localmente. Los siete fallos muestran cabeza muy elevada o baja; existen rostros reales difíciles, no se sustituyeron por otras imágenes. Los cuadros detectados revisados corresponden visualmente a rostros, sin falsos positivos evidentes de fondo en las láminas. Esta observación no es una certificación cuantitativa de detección o identidad.

Se observan perfiles/autooclusiones, variaciones con/sin gafas, iluminación cambiante, cuadros de encuadre cercano y movimiento. Hay desenfoque visible en parte del último segmento de K02, incluida una candidata atípica según su similitud interna. Un cuadro detectado en K03 queda recortado por el borde; se marca. Algunos alineados de perfil contienen relleno negro y partes menos visibles: la alineación es geométrica 2D, no reconstrucción de pose.

No se borraron ni se aceptaron automáticamente estos casos como datos definitivos. Las observaciones individuales, imágenes anotadas, recortes y revisión están en almacenamiento privado. Las etiquetas siguen sustentadas por la correspondencia del custodio, no por verificación independiente de identidad. Las láminas permiten revisión global, no sustituyen examen pixel a pixel ni anotaciones expertas.

## Exploración de embeddings en desarrollo

Fórmula utilizada: `cos(x,y) = (x·y)/(||x|| ||y||)`, normalizando copias para análisis. Se usaron todos los 73 vectores válidos, sin diagonal y con pares no ordenados contados una vez.

| Pares | Cantidad | Mínimo | p05 | Mediana | p95 | Máximo |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Misma identidad | 630 | 0.346 | 0.451 | 0.663 | 0.867 | 0.959 |
| Identidades distintas | 1998 | -0.095 | 0.022 | 0.188 | 0.363 | 0.453 |

La mediana intraidentidad es mayor, pero el mínimo intra (0,346) es menor que el máximo inter (0,453): hay solapamiento y no un corte global que separe perfectamente todos estos pares. No se seleccionó un umbral. Las comparaciones comparten imágenes y sesión; 2.628 pares no son 2.628 ensayos independientes. Estos resultados tampoco evalúan un clasificador de cuatro clases ni personas desconocidas.

Medianas intra por identidad: K01 0,653; K02 0,610; K03 0,690; K04 0,672. Se generaron resúmenes por segmento sin tratarlos como sesiones independientes. Entre 53 pares de candidatas adyacentes válidas dentro de segmentos, el máximo coseno fue 0,953; su similitud sugiere redundancia posible, no duplicación exacta. Los pares originales se encuentran espaciados en selección: no son todos los fotogramas consecutivos del vídeo.

Se priorizaron para revisión ocho candidatas con menor mediana de similitud a su grupo; esto no prueba error de etiqueta ni justifica eliminarlas. Las gráficas de distribuciones, pares individuales y matriz están únicamente en almacenamiento privado. No se entrenó una proyección ni se mostraron imágenes/vectores en el repositorio.

## Tiempos observados

Windows, Intel Core i7-13700H, Python 3.14.7, OpenCV 4.14.0 (opencv-python 4.14.0.94), NumPy 2.5.4, CPU DNN y un hilo OpenCV. Tres calentamientos del pipeline y tres llamadas sintéticas adicionales a SFace antes de medir. Reloj perf_counter. Medidas de la ejecución final conservada; no son promedios de ensayos repetidos bajo carga controlada.

| Etapa | n | Mediana ms | p95 ms | Máximo ms |
| --- | ---: | ---: | ---: | ---: |
| Detección | 80 | 16.188 | 24.741 | 42.014 |
| Alineación | 73 | 0.109 | 0.256 | 0.511 |
| Extracción | 73 | 27.242 | 44.014 | 66.865 |
| Procesamiento total, todos los casos | 80 | 45.400 | 74.274 | 108.621 |

El total con éxito, solo 73 casos, tuvo mediana 47.023 ms y p95 74.946 ms. El total incluye reducción, control geométrico y medidas ROI, pero excluye lectura/decodificación, escritura, cámara y revisión. Las etapas condicionadas a éxito no tienen el mismo denominador que detección. La suma de medianas no es la mediana de la suma. No extrapolar un FPS de reconocimiento en cámara a partir de estos tiempos.

## Pruebas y evidencia

- 40 tests automatizados pasaron en la ejecución final. Incluyen el trabajo previo y 15 casos de pipeline: entradas inválidas, cero/múltiples rostros con dobles, embeddings de forma/tipo/norma inválidos o no finitos, geometría, error de detector, modelos ausentes/alterados, rutas fuera del destino permitido, conservación de matriz y contabilidad de pares. No requieren pesos descargados ni webcam.
- Checks reales separados: YuNet sobre imagen negra → cero detecciones; composición controlada con dos recortes privados → dos detecciones/multiple_faces sin vector. No equivalen a una prueba de cámara con dos personas presentes.
- Dos ejecuciones del lote produjeron 73 vectores exactamente iguales; los tiempos varían. La segunda incorpora la validación final de coherencia ID/sesión/segmento. No se ocultó la primera ni se sobrescribió.
- Los 80 originales seleccionados y las 80 candidatas conservaron sus hashes antes/después. Se recargó NPZ sin pickle, con forma (73,128), valores finitos y normas válidas. No se alteraron los 11.413 originales ni la auditoría previa.
- Compilación de scripts/tests y git diff --check ejecutados; revisión de exclusión de modelos/biometría y enlaces. No se creó commit ni se publicó información.

Resultado privado principal: `_prepared/face_pipeline_20261117_verified/`, con records.json, summary.json, embeddings.npz, similarity.npy, detections/, aligned/, analysis/ (gráficos/láminas/resúmenes), visual_review.json e integration_checks/. El primer ensayo está en face_pipeline_20261117, como antecedente, no como colección activa alternativa. CURRENT.json de la colección de entrada permanece intacto.

Hash del summary.json principal: `803ba27c537d5737acdea15c9bb158145d971815af8ce4084218d01fa5fa91f7`. Registry y todos los derivados personalizados se mantienen fuera de Git.

## Recomendación siguiente y límites

Continuar con YuNet + SFace como baseline técnico provisional, sin declararlo ganador de reconocimiento. Mantener los siete casos extremos para medir fallos; obtener capturas nominales nuevas con giros moderados y pausas de movimiento, conservando también un conjunto de casos difíciles marcado. Revisar con el custodio las candidatas borrosas/de perfil/encuadre y la calidad de alineación antes de elegir muestras de entrenamiento.

Registrar vídeos/configuración de exportación y preservar resolución nativa; no ampliar los frames existentes para simular recuperación. Capturar sesiones nuevas por identidad para VALIDATION y TEST, con iluminación/distancia/pose comparables entre participantes y sin usar esta S01 en esos conjuntos. Incorporar voluntarios desconocidos distintos para calibración y evaluación. La comparación futura de características propias/embeddings/concatenación y de clasificadores conserva entradas/particiones comunes y selección sin TEST.

No se ha probado generalización, resistencia a fotografías/vídeo, liveness, rechazo abierto, permisos o hardware. Los benchmarks publicados del modelo no son resultados de FaceNexus. El dataset exacto del peso SFace y su posible solapamiento con personas públicas permanecen como limitación de procedencia; esta etapa usa exclusivamente nuestras imágenes privadas de desarrollo.

## Reproducción y archivos

Comandos: `python -m scripts.download_face_models` (solo adquisición autorizada, no sobrescribe registro); `python -m scripts.face_pipeline --prepared <raíz privada _prepared> --output <nuevo subdirectorio privado>`; `python -m scripts.analyze_face_pipeline --root <resultado> --allowed-root <raíz privada _prepared>`; `python -m pytest -q`.

Las nuevas salidas deben usar directorios inexistentes. Para gráficos instalar requirements-analysis.txt. Nuevos archivos: scripts/download_face_models.py, scripts/face_pipeline.py, scripts/analyze_face_pipeline.py, tests/test_face_pipeline.py, requirements-analysis.txt y este informe. Documentos de arquitectura, modelos, datos, plan, decisiones, requisitos y README se actualizaron para reflejar lo ejecutado. Los cambios anteriores se conservaron.
