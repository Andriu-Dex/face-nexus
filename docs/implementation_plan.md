# Plan de implementación

Actualizado el 13-11-2026 con las siete fases acordadas. La preparación documental inicial se conserva como antecedente. Actualmente la fase 1 tiene investigación y protocolos redactados; no hay dataset capturado. Se incorpora la herramienta de diagnóstico de cámara; su validación física se registra por separado.

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

La cámara es apta para el piloto bajo las condiciones medidas; pendientes acotados en [informe 03](reports/03_camera_diagnostic.md). No repetir el ensayo continuo solo para cerrar documentación.

Aplicar la [ficha operativa al final del protocolo de datos](data_protocol.md#ficha-operativa-del-piloto--propuesta-del-14-11-2026): 20 fotos por persona. El responsable confirmó custodia, eliminación a 90 días de la defensa y consentimiento individual ya obtenido. Se prepararon y probaron con 80 imágenes sintéticas la captura manual y auditoría estructural; ver [guía operativa](pilot_capture.md). Los destinos privados fueron creados y se verificó su exclusión de Git y ACL local. Ejecutar el piloto manual con cada participante y auditar resultados; las pruebas sintéticas no sustituyen las capturas reales. La captura definitiva requiere revisión de sus resultados y aprobación posterior.

La [preparación de YuNet y SFace](model_verification.md) distingue documentación/API local de carga de pesos pendiente. No hay descargas autorizadas por esta fase ni entrenamiento. Mantener sesiones de TEST fuera de cualquier depuración.
