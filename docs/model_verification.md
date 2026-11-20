# Preparación y validación de detector y extractor facial

Antecedente del 14-11-2026, exclusivamente documental y de interfaces locales. **Actualización vigente:** el 17-11-2026 se adquirieron y verificaron los dos pesos autorizados, se cargaron y se ejecutaron sobre 80 candidatas; ver [informe 07](reports/07_face_pipeline_validation.md). Las frases siguientes sobre tareas sin ejecutar describen la preparación histórica, no el estado actual. No se descargaron binarios ONNX, datasets ni código para ejecutarlo; no se abrió cámara ni se extrajeron vectores. Se leyeron páginas y punteros LFS textuales. YuNet + SFace son candidatos a piloto, no selección definitiva.

## Responsabilidades y compatibilidad

YuNet localiza rostros y puntos faciales; SFace recibe un rostro alineado y obtiene características. El flujo previsto es imagen BGR → YuNet → validación de rostro único y landmarks → alignCrop → feature. SFace no es detector, clasificador de las cuatro personas ni detector de vida. Según el proveedor, sus pesos codifican MobileFaceNet con pérdida SFace [S].

Entorno comprobado hoy: Python 3.14.7, OpenCV 4.14.0 (paquete 4.14.0.94) y NumPy 2.5.4. `hasattr(cv2, 'FaceDetectorYN')` y `hasattr(cv2, 'FaceRecognizerSF')` devolvieron True. Es disponibilidad de API, no carga del modelo ni compatibilidad de inferencia probada. No se necesita añadir PyTorch, TensorFlow u ONNX Runtime para el primer ensayo mediante OpenCV DNN; aceleración y nuevas dependencias solo si las mediciones lo justifican.

## Artefactos candidatos y procedencia

| Función | Archivo propuesto | Metadatos publicados, no peso local verificado |
| --- | --- | --- |
| Detección | face_detection_yunet_2023mar.onnx | 232.589 bytes; SHA-256 `8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4` [YP] |
| Extracción | face_recognition_sface_2021dec.onnx | 38.696.353 bytes; SHA-256 `0ba9fbfa01b5270c96627c4ef784da859931e02f04419c829e83484087c34e79` [SP] |

Se propone FP32 sin cuantización para no mezclar esa variable en el primer piloto. El README actual de YuNet distingue una variante 2026 de entrada dinámica asociada a OpenCV 5 y la variante 2023; revisar primero 2023 para nuestro OpenCV 4 [Y]. Es una elección a comprobar, no una declaración de compatibilidad por el nombre del archivo.

El proveedor declara MIT para todos los archivos de la carpeta YuNet y Apache 2.0 para los de SFace; se consultaron los LICENSE correspondientes [YL, SL]. Conservar avisos y condiciones aplicables al artefacto adquirido. No extrapolar estas declaraciones a cualquier peso llamado YuNet/SFace o a imágenes de terceros. No se publicarán pesos ni biometría en Git.

Las URLs de ramas main/4.x son referencias móviles. Antes de adquirir, registrar commit específico, URL del artefacto, licencia/avisos de esa revisión, fecha, tamaño y hash esperado. Tras adquisición autorizada, calcular hash local y compararlo; un puntero LFS de unos bytes no es el modelo ejecutable. No usar descarga automática ni código remoto arbitrario.

## Verificación técnica posterior, aún sin ejecutar

1. Registrar y autorizar los artefactos concretos. Descargar solo esos pesos y avisos en models privado, nunca grandes datasets para obtenerlos. Bloquear si el hash o formato no coincide.
2. Cargar YuNet con FaceDetectorYN y SFace con FaceRecognizerSF usando CPU/OpenCV DNN inicialmente. Registrar errores explícitos y versiones; no sustituir modelos silenciosamente.
3. Probar detección con entradas autorizadas de desarrollo, sin rostro, un rostro y varios. Medir detecciones/cobertura, no inferir identidad desde el score del detector. Verificar cajas dentro de imagen y cinco puntos finitos.
4. Alinear con alignCrop. El código oficial prepara 112×112 y conversión de canales para la red [SC]; no convertir ni normalizar dos veces por añadir pasos propios. Documentar canales, escala y cada transformación real.
5. Ejecutar feature: registrar dimensión y dtype reales; exigir vector finito, de norma no nula y longitud estable. No fijar dimensión por recuerdo de otro modelo sin inspeccionar el grafo/ejecución. Probar persistencia privada y recarga solo cuando se implemente ese módulo.
6. Medir latencias de detección, alineación y extracción por separado, con calentamiento y cantidad de ensayos declarados. Comparar repetibilidad de entradas y sensibilidad a condiciones; no publicar vectores. No hay métricas todavía.
7. No trasladar umbrales publicados a UNKNOWN/acceso: calibrarlos posteriormente con VALIDATION y mantener TEST reservado. Ninguna inferencia en esta fase da permiso de apertura.

La procedencia exacta del dataset de entrenamiento de este ONNX SFace no está acreditada por el nombre ni por los datasets ensayados en el artículo. Mantener esa limitación ya registrada en [02_dataset_research.md](reports/02_dataset_research.md), incluida independencia no demostrada de identidades públicas.

## Comparación proporcionada

Mantener un descriptor propio sencillo de histogramas por regiones como alternativa experimental propuesta, seguido de A=embeddings, B=características propias y C=concatenación escalada, con muestras comunes y referencia fija. No afirmar que los histogramas identifican bien sin evaluarlos. Si la calidad de alineación cambia entre alternativas, declarar el factor en lugar de atribuir todo al descriptor.

InsightFace sigue como alternativa de extractor si SFace no satisface necesidades; revisión de paquete, dependencias y licencia específica antes de adquirir. No añadirlo a la instalación ahora. Un detector alternativo solo se elige si el piloto revela un problema concreto; no hace falta comparar varios detectores para cumplir la comparación académica de clasificadores. Fuentes y límites de InsightFace ya figuran en el informe 02.

## Fuentes primarias consultadas

- [S: README de SFace](https://raw.githubusercontent.com/opencv/opencv_zoo/main/models/face_recognition_sface/README.md) y [SL: LICENSE de carpeta](https://raw.githubusercontent.com/opencv/opencv_zoo/main/models/face_recognition_sface/LICENSE).
- [Y: README de YuNet](https://raw.githubusercontent.com/opencv/opencv_zoo/main/models/face_detection_yunet/README.md) y [YL: LICENSE de carpeta](https://raw.githubusercontent.com/opencv/opencv_zoo/main/models/face_detection_yunet/LICENSE).
- [YP: puntero LFS YuNet](https://raw.githubusercontent.com/opencv/opencv_zoo/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx); [SP: puntero LFS SFace](https://raw.githubusercontent.com/opencv/opencv_zoo/main/models/face_recognition_sface/face_recognition_sface_2021dec.onnx).
- [SC: implementación OpenCV de alineación y extracción](https://raw.githubusercontent.com/opencv/opencv/4.x/modules/objdetect/src/face_recognize.cpp).


## Verificación ejecutada — 17-11-2026

Se completaron procedencia/licencia/tamaño/hash contra revisión oficial fija, carga y ejecución CPU/OpenCV. YuNet detectó un rostro en 73/80 candidatas con score 0,9; en siete no hubo detección, conservadas sin sustituir. Alineación efectiva 112×112 BGR uint8 y salida SFace (1,128) float32, finita y de norma no nula. No hubo múltiples en la colección; un check controlado con dos rostros sí produjo multiple_faces sin extraer vector. La presencia de API dejó de ser la única evidencia.

La exploración de cosenos muestra separación preliminar con solapamiento, sin umbral final ni accuracy independiente. Los modelos permanecen como baseline técnico, no selección final de reconocimiento. Descargar otros modelos, entrenar clasificadores o ajustar SFace queda fuera de esta autorización. Detalles reproducibles, tiempos y límites en el informe 07; no duplicar aquí los resultados por muestra.
