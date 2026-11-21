# Arquitectura propuesta

**Estado:** TMCAM 8305 y YuNet/SFace verificados como referencias de desarrollo. En la demostración el celular entrega la imagen por red local, Windows reconoce y el ESP-WROOM-32 acciona el SG90 según la decisión recibida por USB serie.

## Criterio de implementación

Conforme a CONF-02, esta tabla separa responsabilidades conceptuales; no impone una clase, carpeta, servicio ni capa por fila. Empezar con funciones y archivos sencillos, compartir estructuras de datos comprensibles y añadir abstracciones solo cuando una necesidad real las justifique. Poder explicar el recorrido desde el fotograma hasta la orden física es un criterio de revisión. Mantener las comprobaciones de datos, permisos y fallos aunque requieran código adicional.

## Módulos

| Módulo | Entrada → salida | Responsabilidad |
| --- | --- | --- |
| Captura | Stream del celular → fotograma y referencia de la solicitud | Procesar el fotograma más reciente y denegar si la entrada se interrumpe |
| Detección | Fotograma → lista de `FaceDetection` | Localizar candidatos para clasificar y reconocer por región |
| Clasificación inicial | Región o imagen → humano/no humano | Modelo propio entrenado; sus negativos se preparan por separado |
| Preparación | Región facial → imagen normalizada | Tamaño, canales, alineación y calidad documentados |
| Características | Imagen → `Embedding` | Vector finito de dimensión fija y versión del extractor |
| Clasificación | Vector → candidato y puntuaciones | Adaptador de entrega para SVM lineal, k-NN y MLP |
| Rechazo | Candidato, scores y evidencia → `Prediction` | Aplicar política y umbrales versionados |
| Permisos | ID local → permiso vigente | Administración independiente del entrenamiento |
| Autorización | Predicción, permiso y contexto → `AccessDecision` | Denegar por defecto, comprobar frescura y ambigüedad |
| Controlador | Etiqueta y decisión de Windows → estado de ejecución | Simulación inicial y después ESP-WROOM-32 con SG90 |
| Evaluación | Manifiesto y configuración → resultados | Experimentos reproducibles fuera de la interfaz en vivo |
| Interfaz/eventos | Estados y resultados → vista/historial | Mostrar el modelo elegido, identidades y acción. Comparar candidatos en el informe |

## Contratos

- `FaceDetection`: caja en coordenadas del fotograma, score, versión de detector.
- `Embedding`: vector, dimensión y versión completa de preparación/extractor. No se registra el vector en logs.
- `Prediction`: candidato opcional, scores con semántica declarada, aceptación/rechazo, motivo y versiones de modelo/política. `UNKNOWN` no es una quinta persona entrenada por defecto.
- `AccessDecision`: `GRANTED` o `DENIED`, motivo controlado, ID de evento y referencia temporal. Permiso inactivo siempre deniega.
- `AccessController.authorize(decision, context)`: devuelve estado (`SIMULATED`, `PENDING`, `SUCCEEDED`, `FAILED` o `UNAVAILABLE`) y correlación con la orden. El controlador simulado no tiene capacidad de apertura física.

Antes de emitir una orden se vuelven a comprobar permiso y vigencia. Una desconexión invalida órdenes pendientes; no se reenvían automáticamente al reconectar. La lógica de seguridad no depende de que la interfaz continúe funcionando.

La detección múltiple produce decisiones por región. Actuar cuando al menos una identidad autorizada esté confirmada y la decisión sea inequívoca. Si sale del cuadro la última identidad con permiso, la siguiente decisión deniega. La computadora devuelve la etiqueta y decisión al nodo IoT, que controla la salida y permite observar su efecto.

## Opciones iniciales

Usar Python y una ventana OpenCV para la interfaz. YuNet localiza y recorta rostros. El clasificador humano/no humano evalúa imágenes o regiones candidatas antes de que el recorte facial pueda descartar las entradas negativas. En una escena grupal, el resultado de una región se aplica a esa región. Calcular HOG para k-NN propio en NumPy, MLP y SVM lineal multiclase en Keras.

La entrega prioriza características calculadas por el equipo y clasificadores construidos y entrenados por el grupo. La comparación principal fija representación y muestras. SFace y los estimadores ya probados de scikit-learn quedan como referencias internas mientras se desarrolla esa ruta.

Preparación documental de detección/alineación/extracción: [model_verification.md](model_verification.md). La adquisición y carga ya se comprobaron en el [informe 07](reports/07_face_pipeline_validation.md); la comparación de representaciones y clasificadores sigue pendiente.
