# Arquitectura propuesta

**Estado:** diseño inicial; cámara de captura TMCAM 8305 elegida, OpenCV incorporado para diagnóstico. Extractor y dispositivo de acceso pendientes. Los contratos son conceptuales; se concretarán al implementar.

## Criterio de implementación

Conforme a CONF-02, esta tabla separa responsabilidades conceptuales; no impone una clase, carpeta, servicio ni capa por fila. Empezar con funciones y archivos sencillos, compartir estructuras de datos comprensibles y añadir abstracciones solo cuando una necesidad real las justifique. Poder explicar el recorrido desde el fotograma hasta la orden física es un criterio de revisión. Mantener las comprobaciones de datos, permisos y fallos aunque requieran código adicional.

## Módulos

| Módulo | Entrada → salida | Responsabilidad |
| --- | --- | --- |
| Captura | Cámara → fotograma y tiempo monotónico | Lectura, frescura y errores; sin persistencia por defecto |
| Detección | Fotograma → `FaceDetection` | Caja, score y validación de presencia única |
| Preparación | Región facial → imagen normalizada | Tamaño, canales, alineación y calidad documentados |
| Características | Imagen → `Embedding` | Vector finito de dimensión fija y versión del extractor |
| Clasificación | Vector → candidato y scores | Adaptador intercambiable SVM/RF/k-NN/MLP |
| Rechazo | Candidato, scores y evidencia → `Prediction` | Aplicar política y umbrales versionados |
| Permisos | ID local → permiso vigente | Administración independiente del entrenamiento |
| Autorización | Predicción, permiso y contexto → `AccessDecision` | Denegar por defecto, comprobar frescura y ambigüedad |
| Controlador | Decisión y contexto → estado de ejecución | Simulación inicial e integración física posterior |
| Evaluación | Manifiesto y configuración → resultados | Experimentos reproducibles fuera de la interfaz en vivo |
| Interfaz/eventos | Estados y resultados → vista/historial | No confundir scores con probabilidades ni autorización con apertura |

## Contratos

- `FaceDetection`: caja en coordenadas del fotograma, score, versión de detector.
- `Embedding`: vector, dimensión y versión completa de preparación/extractor. No se registra el vector en logs.
- `Prediction`: candidato opcional, scores con semántica declarada, aceptación/rechazo, motivo y versiones de modelo/política. `UNKNOWN` no es una quinta persona entrenada por defecto.
- `AccessDecision`: `GRANTED` o `DENIED`, motivo controlado, ID de evento y referencia temporal. Permiso inactivo siempre deniega.
- `AccessController.authorize(decision, context)`: devuelve estado (`SIMULATED`, `PENDING`, `SUCCEEDED`, `FAILED` o `UNAVAILABLE`) y correlación con la orden. El controlador simulado no tiene capacidad de apertura física.

Antes de emitir una orden se vuelven a comprobar permiso y vigencia. Una desconexión invalida órdenes pendientes; no se reenvían automáticamente al reconectar. La lógica de seguridad no depende de que la interfaz continúe funcionando.

## Opciones iniciales

Python y OpenCV ya se utilizan en el diagnóstico; el stack de entrenamiento y la inferencia con pesos siguen pendientes de validación. Framework de interfaz, detector, extractor y transporte al dispositivo se elegirán después de revisar compatibilidad, licencias y rendimiento. No se descargan pesos ni se fijan versiones sin esa revisión.

Se explorará una representación de características de imagen explicable y, si se elige un extractor preentrenado, su comparación o combinación controlada. La comparación principal de clasificadores fija la representación y las muestras. Los cambios de representación constituyen otro experimento.

Preparación documental de detección/alineación/extracción: [model_verification.md](model_verification.md). La presencia de APIs locales no acredita que los pesos se hayan cargado.
