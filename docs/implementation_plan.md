# Plan de implementación

Actualizado el 19-11-2026 con las [aclaraciones de clase](source_analysis.md#aclaraciones-de-la-clase-del-19-de-noviembre). El volumen cifrado y la TMCAM ya se verificaron. Están auditados S01 y R01, y el código de comparación de referencia se probó con datos sintéticos. El nodo IoT, los modelos propios y la demostración con varias personas pasan a ser prioridades.

Cada fase requiere plan breve de archivos, trabajo acotado, comprobaciones disponibles, inspección de resultados y registro de evidencia antes de preparar un commit. No publicar ramas ni cambios remotos sin autorización. Priorizar claridad y defensa del código (CONF-02).

| Fase | Trabajo previsto | Condición de salida |
| --- | --- | --- |
| 1. Preparación y auditoría del dataset | Investigación de fuentes, consentimiento, captura piloto, manifiesto y particiones; protocolo en data_protocol.md | Datos propios autorizados, grupos de desconocidos disjuntos y auditoría ejecutada sin fugas pendientes |
| 2. Detección y procesamiento facial | Detector, recortes, alineación y calidad; comprobar piloto antes de captura definitiva | Configuración explicada, archivos/rostros utilizables y fallos registrados |
| 3. Extracción y comparación de características | Representación propia, preentrenada y combinación bajo experimento acotado; entrenamiento preliminar con referencia fija | Comparación en VALIDATION, versiones/dimensiones y procedencia verificadas |
| 4. Entrenamiento y evaluación de clasificadores | Comparación principal SVM/RF/k-NN/MLP con entradas comunes; candidatos adicionales solo si se justifica | Configuraciones elegidas con TRAIN/VALIDATION; TEST aún reservado |
| 5. Reconocimiento en tiempo real y rechazo | Calibración offline con VALIDATION, regla temporal, cámara y latencias | Modelo, preparación y rechazo congelados; evaluación TEST offline y en vivo con sesiones/intentos reservados, sin ajustes posteriores |
| 6. Sistema de autorización | Integrar identidad, permisos e interfaz con controlador simulado | Revocación sin reentrenar, denegaciones y estados de ejecución comprobados |
| 7. Integración y pruebas con dispositivo físico | Adaptador y pruebas de apertura, denegación, repetición, desconexión y reconexión; cierre de informe | Orden transmitida y acción efectiva comprobada; limitaciones y todos los resultados reales documentados |

La fase 1 empieza con protocolo y piloto; se coordina con fase 2 antes de capturar el dataset definitivo. No requiere agotar toda la adquisición antes de comprobar el detector. La comparación de características de fase 3 permite entrenamiento preliminar sin consumir TEST; la selección completa corresponde a fase 4.

La lógica sencilla de permisos y el contrato de controlador se definen y prueban desde el inicio con datos simulados, aunque su integración completa sea fase 6. Los casos de acceso físico se ensayan en fase 7 con intentos reservados; no sustituyen la evaluación del reconocimiento ni justifican retocar un TEST ya consumido. Si se necesitan cambios tras TEST, declarar la evaluación de desarrollo y obtener nuevas sesiones para una evaluación final independiente.

La selección del dispositivo avanza en paralelo desde las primeras fases; el montaje con actuador queda para fase 7. Sigue pendiente el dispositivo concreto. CONF-01 exige reconocer las cuatro personas, verificar permisos, transmitir una orden válida y comprobar su ejecución física. No basta un mensaje de recepción.

## Registro de evidencias

Anotar fecha, requisito, versión/configuración, comando o procedimiento, resultado observado, ubicación privada o pública del reporte y limitaciones. No convertir resultados esperados en observados. Las pruebas de lógica usan datos sintéticos y dobles de cámara/controlador; las de dispositivos se separan y las no ejecutadas quedan pendientes. Si se adopta Python, utilizar pytest y análisis estático proporcionales al cambio.

## Siguiente paso concreto

### Prioridades para la demostración

1. Confirmar qué nodo con cámara tiene disponible el equipo y comprobar pronto el ciclo captura → computadora → respuesta → acción observable. La tira LED es una opción de salida física aceptada en clase.
2. Preparar la clasificación humano/no humano con ejemplos adecuados para esa tarea y entrenar los modelos de entrega. Usar una representación facial explicable para comparar candidatos. Conservar YuNet para localización/recorte y usar SFace y el código actual como referencia interna.
3. Confirmar que S01 y R01 son encuentros distintos para cada integrante. Si se confirma, usar S01 para ajuste y considerar R01 para una evaluación entre encuentros con los datos disponibles. Mantener asignaciones y resultados explícitos. Un ensayo en vivo con el modelo congelado aporta evidencia adicional sin requerir otro lote de fotografías almacenadas.
4. Ensayar una persona autorizada, varias autorizadas, una autorizada con desconocidos, solo desconocidos y la salida de la última persona autorizada. Presentar el modelo elegido y documentar en el informe la exactitud de los candidatos y la interfaz.

### Preparación técnica ya realizada

La [preparación de la comparación](reports/09_classifier_preparation.md) permite verificar los cuatro clasificadores con datos sintéticos y preparar los lotes de fotogramas de las nuevas grabaciones. La comparación real sigue pendiente de sesiones independientes.

Completar la [evaluación de impacto](biometric_impact_assessment.md) para el único flujo de acceso por reconocimiento facial y verificar localmente el alcance del consentimiento verbal grabado antes de la adquisición. Confirmar los datos de contacto del responsable. Los [formularios](consent_templates.md) quedan disponibles como apoyo opcional.

La revisión local y el primer pipeline de las 80 candidatas se ejecutaron; ver [informe 07](reports/07_face_pipeline_validation.md): 73 embeddings válidos y siete sin detección, con fallos preservados y similitudes exploratorias solapadas. Se autorizaron únicamente los pesos concretos de YuNet y SFace y permanecen privados/verificados.

El volumen VeraCrypt superó el remontaje y la comprobación del SHA-256 de prueba. La TMCAM superó el diagnóstico operativo de R01. El [primer lote de TRAIN](reports/09_classifier_preparation.md#primer-lote-de-train) produjo 72 embeddings válidos. Los resultados de R01 se conservan con su asignación histórica mientras se confirma el plan de evaluación entre encuentros.
