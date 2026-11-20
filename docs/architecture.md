# Arquitectura propuesta

**Estado:** TMCAM 8305 y el flujo con YuNet/SFace verificados para desarrollo. La demostración debe incorporar un nodo IoT con cámara y una salida física. La selección del equipo y los modelos de entrega siguen pendientes.

## Criterio de implementación

Conforme a CONF-02, esta tabla separa responsabilidades conceptuales; no impone una clase, carpeta, servicio ni capa por fila. Empezar con funciones y archivos sencillos, compartir estructuras de datos comprensibles y añadir abstracciones solo cuando una necesidad real las justifique. Poder explicar el recorrido desde el fotograma hasta la orden física es un criterio de revisión. Mantener las comprobaciones de datos, permisos y fallos aunque requieran código adicional.

## Módulos

| Módulo | Entrada → salida | Responsabilidad |
| --- | --- | --- |
| Captura | Cámara del nodo IoT → fotograma y referencia de la solicitud | Enviar a la computadora y comprobar frescura; TMCAM para desarrollo local |
| Detección | Fotograma → lista de `FaceDetection` | Localizar candidatos para clasificar y reconocer por región |
| Clasificación inicial | Región o imagen → humano/no humano | Modelo propio entrenado; sus negativos se preparan por separado |
| Preparación | Región facial → imagen normalizada | Tamaño, canales, alineación y calidad documentados |
| Características | Imagen → `Embedding` | Vector finito de dimensión fija y versión del extractor |
| Clasificación | Vector → candidato y scores | Adaptador intercambiable SVM/RF/k-NN/MLP |
| Rechazo | Candidato, scores y evidencia → `Prediction` | Aplicar política y umbrales versionados |
| Permisos | ID local → permiso vigente | Administración independiente del entrenamiento |
| Autorización | Predicción, permiso y contexto → `AccessDecision` | Denegar por defecto, comprobar frescura y ambigüedad |
| Controlador | Decisión y contexto → estado de ejecución | Simulación inicial e integración física posterior |
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

Python y OpenCV ya se utilizan en el diagnóstico; la inferencia YuNet/SFace se validó sobre 80 candidatas y el stack de entrenamiento sigue pendiente. Framework de interfaz, detector, extractor y transporte al dispositivo se elegirán después de revisar compatibilidad, licencias y rendimiento. No se descargan pesos ni se fijan versiones sin esa revisión.

La entrega prioriza características calculadas por el equipo y clasificadores construidos y entrenados por el grupo. La comparación principal fija representación y muestras. SFace y los estimadores ya probados de scikit-learn quedan como referencias internas mientras se desarrolla esa ruta.

Preparación documental de detección/alineación/extracción: [model_verification.md](model_verification.md). La adquisición y carga ya se comprobaron en el [informe 07](reports/07_face_pipeline_validation.md); la comparación de representaciones y clasificadores sigue pendiente.
