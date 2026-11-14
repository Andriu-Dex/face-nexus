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
- Se revisó la propuesta local `instruction.md` y una selección de README y código de procesamiento de los cinco talleres anteriores. Las ampliaciones sugeridas se evalúan en [el informe de revisión](reports/01_preimplementation_review.md); aún no se adoptan como obligaciones del plan.
- CONF-01 sigue vigente: las pruebas sin dispositivo permiten avanzar, pero no completan la entrega física.

## Preparación de datos — 13-11-2026

- D-10: se adopta la investigación acotada aprobada por el responsable: siete datasets públicos únicos, profundización en extractores candidatos y protocolo principal consolidado en data_protocol.md. No se descargan datasets ni pesos, ni se entrena.
- D-11: las fuentes principales planificadas son cuatro identidades propias y voluntarios desconocidos locales, con identidades separadas entre VALIDATION y TEST. Los datos públicos son auxiliares y necesitan una función justificada.
- D-12: SFace pasa a candidato preferente para revisión/piloto; InsightFace queda como alternativa. No se declara extractor seleccionado ni licencia de un binario local verificada: no hay peso descargado. Revisar el artefacto y su procedencia antes de adoptarlo.
- D-13: los volúmenes del protocolo son propuestas iniciales de planificación, ajustables tras piloto. Aún no se ha confirmado disponibilidad de participantes, cámara ni plazo de conservación.
- D-14: se sincroniza implementation_plan.md con las siete fases acordadas, empezando por datos; permisos se prueban temprano y el dispositivo se selecciona en paralelo. No altera identificadores de requisitos ni convierte el hardware en opcional.
- D-15: se amplía el mismo protocolo de datos con captura, auditoría y almacenamiento. El registro público de fuentes queda en [dataset_research.md](reports/02_dataset_research.md); los manifiestos personales nunca van a docs.

Pendiente antes de capturar: ubicación/custodio y plazo de eliminación, consentimiento y disponibilidad de voluntarios y equipo. Pendiente antes de inferencia: versiones exactas de detector/extractor, licencia conservada, hashes locales y dimensión de salida verificada. La captura y auditoría reales siguen sin ejecutar.

## Diagnóstico de cámara — 13-11-2026

- D-16 / CONF-03: TMCAM 8305 como única cámara oficial. Objetivo 1920×1080/30 FPS, 60 Hz previsto y OpenCV; los valores efectivos no están certificados por la selección en Windows.
- D-17: diagnóstico inicial de 600 segundos después de 5 segundos de calentamiento, sin persistencia de fotogramas. JSON técnico local en outputs; fallos terminan el ensayo sin cambiar de cámara ni reconectar automáticamente.
- D-18: elección de índice verificada por el operador, porque Windows solo informa USB CAMERA y no acredita el modelo exacto. No abrir automáticamente la cámara integrada. Prueba visual de parpadeo y reconexión requieren intervención del operador.

Plan de archivos de esta entrega: scripts/camera_diagnostic.py, pruebas sin hardware, dependencias, protocolo de diagnóstico y referencias documentales. El informe de verificación distingue pruebas simuladas de funcionamiento físico.

## Evidencia inicial de cámara — 13-11-2026

La TMCAM confirmada por el responsable se ensayó por DirectShow/índice 1, vista activa: 600,046 s, 17.547 matrices 1920×1080, 29,241 FPS medios, cero fallos y ninguna pausa >250 ms. Se conserva el objetivo 1080p/30; no se afirma que 30 FPS sean constantes ni se cambia a menor resolución. El operador informó fluidez y ausencia de bandas, sin confirmar 60 Hz. Apertura con USB desconectada produjo open_failed sin fallback. El informe 03 separa estos hechos de la desconexión durante lectura, aún no comprobada.

Después de reconectar se confirmó nuevamente el índice 1 y se completó un ensayo de 30 s a 1080p/30,001 FPS medios, sin fallos. La recuperación por nueva apertura está comprobada; la desconexión durante read y el ajuste 60 Hz permanecen pendientes. Ver informe 03 para cronología y hashes de los JSON originales.

## Preparación del piloto — 14-11-2026

- D-19: cámara apta para piloto con resolución oficial 1920×1080 y objetivo 30 FPS. Se conserva 29,241 FPS como media real del ensayo principal; 60 Hz previsto sin confirmar y desconexión durante read pendientes. Hashes de los cuatro JSON revalidados sin cambios.
- D-20 (propuesta pendiente de aprobación): una sesión piloto de 20 fotos por cada K01–K04, solo TRAIN/desarrollo, con cinco bloques de variación. La pauta concreta está al final de data_protocol.md; no duplica el protocolo general ni valida automáticamente las sesiones definitivas.
- D-21 (propuesta pendiente de aprobación): custodio único responsable del proyecto, almacenamiento local bajo cuenta privada sin sincronización/respaldos adicionales por defecto, y eliminación a 90 días de la defensa o antes por retiro. Falta confirmar custodio concreto, ubicación efectiva y consentimientos; esta propuesta no autoriza capturas.
- D-22: revisión documental de YuNet como detector y SFace como extractor, separados. APIs presentes en OpenCV, pesos no adquiridos ni ejecutados. El plan está en model_verification.md y no autoriza descargas en esta fase.
- D-23: sin cambios al script de diagnóstico ni nuevas pruebas de cámara para esta entrega documental. La prueba de desconexión bloqueante se propone en proceso hijo con supervisor y tiempo máximo; no se declara implementada.

La aprobación del protocolo piloto es una decisión diferente del consentimiento individual, la autorización de publicar rostros, la descarga de pesos y el permiso de acceso físico.

## Confirmación de custodia — 14-11-2026

- D-24: el responsable confirma que custodiará los datos, acepta eliminarlos a los 90 días después de la defensa y obtendrá el consentimiento individual. La fecha de defensa y los consentimientos efectivos aún no están registrados.
- Siguiente trabajo: herramienta sencilla de captura del piloto y pruebas sin webcam real, manteniendo 20 fotografías por persona como pauta. Antes de guardar rostros, verificar destino privado y consentimiento de cada participante; no se solicita repetir las decisiones de custodia/conservación ya confirmadas.

## Herramienta de piloto — 14-11-2026

- D-25: el usuario confirma consentimiento ya obtenido de los cuatro y disponibilidad conjunta. Autoriza primero prueba sintética y luego piloto manual de 80 fotos.
- D-26: data y private creadas en raíz local, excluidas de Git, con ACL explícita para cuenta actual/SYSTEM/Administradores; sin cifrado ni certificación automática de ausencia de nube.
- D-27: piloto con guardado manual, manifestado JSON por toma, sin sobrescritura ni reanudación automática. Auditoría estructural separada de revisión visual y detección. Imágenes sintéticas separadas en outputs, nunca en dataset real.
- Plan de esta entrega: scripts/pilot_capture.py, scripts/pilot_audit.py, tests/test_pilot.py, dependencia de enumeración en requirements y guía pilot_capture.md. No se modifica el diagnóstico ni se descargan pesos.

## Cambio de método propuesto — 14-11-2026

El responsable propone grabar vídeos por participante y seleccionar fotogramas mediante software local, con destino privado C:/Downloads/FaceNexus/data. La alternativa está en revisión; no se han movido datos ni adoptado automáticamente un protocolo nuevo. La sesión manual se detuvo preservando 10 fotos K01/P01, verificadas estructuralmente, y cero de K02–K04. No se borran ni se consideran una sesión completa. Si se repite vídeo en el mismo encuentro, fotos y vídeo pertenecen al mismo grupo de sesión; no se dividen entre TRAIN/VALIDATION/TEST.
