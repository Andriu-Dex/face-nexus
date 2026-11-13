# AGENTS.md — FaceNexus

## Propósito operativo

Implementar un sistema de reconocimiento facial en tiempo real para identificar cuatro personas registradas, rechazar identidades desconocidas, comparar clasificadores y emitir decisiones de autorización desacopladas del dispositivo de acceso. Mantener una implementación comprensible, medible y defendible académicamente.

## Autoridad de documentación

1. **Requisitos expresos del profesor:** se identifican como `PROF` en `docs/requirements.md`.
2. **Convenciones y metodología de clase:** se identifican como `CLASE`; aplicar sus conceptos sin convertirlos en obligaciones inventadas.
3. **Aclaraciones del responsable:** se identifican como `CONF`; el dispositivo físico es obligatorio para la entrega final.
4. **Decisiones del proyecto:** se identifican como `PROY`; pueden refinarse con evidencia y deben quedar registradas.

Orden de lectura antes de implementar: `docs/requirements.md` → `docs/architecture.md` → `docs/evaluation_protocol.md` → secciones de la fase activa en `docs/implementation_plan.md`. Consultar `docs/data_protocol.md` o `docs/hardware_protocol.md` al tocar esos módulos. Evitar releer documentación completa si la tarea está acotada y la referencia ya se encuentra en contexto.

## Prioridad de claridad y defensa académica

Por indicación expresa del responsable, priorizar código fácil de entender, explicar y defender sobre la aplicación de patrones o buenas prácticas de programación que añadan complejidad. Elegir funciones directas, nombres descriptivos, flujo visible y comentarios en español que expliquen el motivo y las matemáticas. Usar clases, capas, tipado y abstracciones solo cuando aporten claridad o resuelvan una necesidad concreta; no crear una clase por cada módulo conceptual del diseño.

La simplicidad no permite eliminar validaciones, pruebas relevantes, protección de datos, separación de particiones ni denegación ante fallos. Las bibliotecas están permitidas: explicar sus entradas, salidas, parámetros y función, sin reimplementar algoritmos completos por obligación estética. Optimizar únicamente con mediciones y conservar una explicación comprensible de la operación.

## Principios innegociables

- Implementar por fases, con commits coherentes, pruebas y evidencias reales. No declarar funciones terminadas sin ejecutarlas y verificar los resultados.
- No modificar el repositorio remoto, crear ramas remotas ni publicar información privada sin autorización explícita.
- Reconocimiento de cuatro identidades **no equivale** a reconocer a cualquier persona; una identidad desconocida debe poder producir `UNKNOWN` y `DENIED`.
- No conectar un actuador físico durante el desarrollo inicial. La acción predeterminada es **no abrir**.
- No almacenar datos biométricos, fotos, credenciales ni artefactos personalizados en Git. No generar capturas persistentes sin necesidad y consentimiento.
- Toda transformación aprendida (PCA, normalización estadística, selección de atributos, calibración) se ajusta únicamente con TRAIN o VALIDATION según su función, nunca con TEST.
- Dividir por sesión de captura, no por fotografías casi idénticas tomadas en una misma ráfaga.
- Usar idénticas entradas y particiones para SVM, Random Forest, k-NN y ANN. Evaluar la opción de rechazo por separado.
- Reportar exactitud, macro-F1, matrices de confusión, rechazos indebidos, aceptaciones indebidas, latencias y limitaciones. Nunca inventar cifras ni elegir un modelo únicamente por mayor accuracy.
- Verificar licencias, procedencia y hashes de los pesos preentrenados. No descargar ni ejecutar código remoto arbitrario.
- Las pruebas automatizadas deben funcionar sin webcam ni cerradura reales; las pruebas de integración con dispositivos se ejecutarán solo cuando estos existan.
- Utilizar códigos y conceptos explicables: documentar entradas, salidas, umbrales, fórmula de similitud, elección de hiperparámetros y decisión de autorización.
- Mantener módulos pequeños, tipados cuando aporte, con validaciones explícitas, logging sin exposición biométrica y manejo seguro de excepciones.

## Contratos esenciales

- `FaceDetection`: posición y puntuación de detección.
- `Embedding`: vector numérico con versión del extractor registrada.
- `Prediction`: identidad candidata, puntuaciones, rechazo/aceptación, versión del modelo.
- `AccessDecision`: `GRANTED` o `DENIED` con motivo controlado.
- `AccessController`: `authorize(decision, context)` y estado de ejecución; en ausencia de hardware no puede ordenar apertura.

Todas las decisiones fallan en modo cerrado (`DENIED`) ante ausencia de rostro, varios rostros ambiguos, modelo faltante, error de cámara, identidad desconocida, permiso inactivo o excepción no controlada.

## Implementación y validación

Para cada fase: (1) verificar requisitos, (2) plan breve de archivos a tocar, (3) implementar, (4) ejecutar lint/pruebas pertinentes, (5) inspeccionar salidas, (6) registrar lo verificado y sus limitaciones, (7) preparar commit descriptivo. Usar `pytest`, pruebas de integración y análisis estático cuando estén disponibles.

No modificar objetivos académicos para justificar un resultado. Una evaluación positiva del entrenamiento no sustituye pruebas separadas con nuevas sesiones, personas desconocidas o intentos con fotografías de rostros.

## Interfaz

Diseñar una experiencia clara: cámara en vivo, estado del detector, identidad o «Desconocido», decisión de acceso, administración local de participantes, control de permisos, historial técnico sin imágenes y panel de comparación de modelos. No colocar métricas ni estados como si ya hubieran sido medidos. No prometer resistencia a ataques no verificada.

## Entrega física y fuente original

La integración física es obligatoria (`CONF-01`). El controlador simulado permite desarrollo inicial, pero no satisface la entrega final. Distinguir autorización, orden y apertura observada; documentar la ausencia de sensores de posición.

No modificar `docs/transcription.md` ni incorporarlo a Git: es la fuente local original y contiene información personal incidental. Consultar su trazabilidad en `docs/source_analysis.md`. Registrar decisiones y pendientes en `docs/decisions.md`.
