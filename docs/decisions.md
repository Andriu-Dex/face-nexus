# Decisiones y pendientes

## Decisiones iniciales — 12-11-2026

| ID | Decisión | Motivo / revisión |
| --- | --- | --- |
| D-01 | Dispositivo físico obligatorio al cierre | Aclaración explícita del responsable; cambia cualquier lectura de hardware opcional |
| D-02 | Cuatro identidades | Alcance del borrador y AGENTS; dentro de las cantidades mencionadas en clase |
| D-03 | SVM, RF, k-NN y ANN/MLP | Comparación inicial del proyecto; no lista docente cerrada |
| D-04 | Cámara en vivo, procesamiento local y rechazo de desconocidos | Alcance funcional y control de riesgo |
| D-05 | Separación por sesiones, TEST reservado y calibración sin TEST | Evitar fuga y sesgo de selección |
| D-06 | Simulador durante desarrollo, adaptador físico obligatorio después | Permite pruebas sin actuador y mantiene condición de entrega |
| D-07 | Transcripción local intacta, excluida de Git | Contiene nombres y conversación incidental; publicar documentación derivada sin esos datos |
| D-08 | Evaluar características propias y posible combinación con extractor | Responder al énfasis docente sin concatenar atributos arbitrariamente |

## Pendientes que no impiden crear el esqueleto

- Dispositivo y elemento físico; componentes, presupuesto, alimentación y transporte.
- Equipo de cómputo, cámara, participantes, disponibilidad de sesiones y fecha de entrega.
- Detector/extractor, licencia concreta de pesos, dimensiones y herramientas de interfaz.
- Consentimiento, responsables, plazo de conservación y almacenamiento privado.
- Cantidades de datos, búsquedas de hiperparámetros, metas de latencia/rechazo y regla temporal: fijar tras piloto y antes de TEST.
- Confirmar con el profesor si la formulación sobre características propias exige concatenación con una biblioteca o acepta comparación experimental. Hasta aclararlo, conservar el experimento y documentar su justificación.

No se presenta ninguno de estos puntos como resuelto ni medido. Los cambios posteriores registrarán motivo, evidencia y efecto en requisitos, experimentos y criterios de aceptación.

## Revisión previa a implementación — 12-11-2026

- D-09 / CONF-02: el responsable prioriza comprensión y defensa del código sobre patrones y convenciones que añadan complejidad. Se mantienen validaciones, pruebas relevantes y rigor experimental.
- Se revisó la propuesta local `instruction.md` y una selección de README y código de procesamiento de los cinco talleres anteriores. Las ampliaciones sugeridas se evalúan en [el informe de revisión](reports/preimplementation_review.md); aún no se adoptan como obligaciones del plan.
- CONF-01 sigue vigente: las pruebas sin dispositivo permiten avanzar, pero no completan la entrega física.
