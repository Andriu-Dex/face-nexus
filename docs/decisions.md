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

## Agrupación de colección externa — 17-11-2026

- D-28: prevalece la última aclaración del responsable: todos los segmentos de cada identidad se agrupan en S01/TRAIN por criterio conservador. La respuesta anterior acerca de segmentos independientes no se usa para particiones; no se afirma cantidad de vídeos reales comprobada.
- D-29: originales externos intactos; manifiesto de 11.413 frames y selección candidata de 80 copias con IDs, segmento y hashes privados. Colección activa identificada por _prepared/CURRENT.json; inventario intermedio sustituido para sesiones.
- D-30: resoluciones reales inferiores y diferentes de la configuración objetivo; no reescalar ni afirmar 1080p. No hay TEST/VALIDATION independientes, desconocidos o detección facial evaluados. Revisar candidatas antes de desarrollar extracción; planificar nuevas sesiones para evaluación.

Evidencia y limitaciones en [06_external_frames.md](reports/06_external_frames.md). No se movieron ni borraron originales, ni se mezclaron automáticamente las diez fotos manuales previas.

## Validación facial — 17-11-2026

- D-31: el responsable aprueba instruction.md junto a las precisiones profesionales: licencia/hash de dos pesos concretos, revisión visual, separación de etapas, resultados exploratorios sin umbral ni generalización. Se autoriza adquisición/ejecución únicamente para este alcance; sin commits ni publicación.
- D-32: pesos fijados a revisión OpenCV Zoo 48b10fa505aeb51fbd127fc60a5c660040e823b7; verificación local contra punteros LFS. Licencias de carpetas MIT (YuNet) y Apache 2.0 (SFace), avisos conservados en models/verified excluido.
- D-33: CPU/un hilo, lado máximo de detector 640 sin ampliar, score 0,9/NMS 0,3; geometría devuelta al original, alignCrop 112×112, SFace 128 float32 observado. Parámetros no ajustados para ocultar fallos.
- D-34: 73/80 embeddings válidos; siete sin detección y ningún caso múltiple en la colección. Revisión de láminas local realizada, sin sustituir ni eliminar. Check real controlado con dos caras produjo multiple_faces y sin vector.
- D-35: coseno intra/inter exploratorio con solapamiento, sin umbral final ni accuracy. Mantener baseline técnico y planificar nuevas sesiones/unknown; las resoluciones están confundidas con identidad/condiciones y no permiten inferencia causal.

Resultados, tiempos, pruebas y archivos en [07_face_pipeline_validation.md](reports/07_face_pipeline_validation.md). No se conectó webcam/actuador ni se entrenó durante esta etapa. El primer lote es antecedente; el resultado privado principal se identifica con sufijo verified y conserva los originales.

## Preparación del dataset definitivo — 17-11-2026

- D-36: la TMCAM 8305 es la fuente declarada por el custodio para los 13 segmentos. La evidencia disponible verifica los PNG y su agrupación por identidad, con resolución de grabación y exportación pendientes. S01 conserva su etiqueta histórica TRAIN en desarrollo exploratorio, fuera del dataset definitivo.
- D-37: el responsable aprobó preparar el protocolo y revisar la procedencia. La pauta operativa, el calendario, una posible segunda ronda VALIDATION y la asignación de desconocidos se presentan para aprobación antes de iniciar capturas. La primera ronda se auditará antes de ampliar y solo podrá contarse como TRAIN si cumple la pauta definitiva.
- D-38: se mantiene YuNet + SFace como baseline. La comparación futura exige verificar el peso exacto del segundo extractor y usar las mismas particiones; TEST queda reservado hasta congelar la configuración. Ver [informe 08](reports/08_dataset_acquisition.md).
- D-39: pauta de adquisición aprobada para preparación técnica. El protocolo de datos es la referencia operativa única. La segunda ronda VALIDATION para conocidos se decide antes de la selección y calibración. Guardar fotos nuevas requiere autorización expresa.
- D-40: VeraCrypt con NTFS es la solución de almacenamiento preparada para el entorno Windows 11 Home. El cifrado de C: permanece sin verificar. Ubicación, credenciales, montaje y posible migración histórica quedan pendientes de comprobación y acuerdo con el custodio.
- D-41: la nueva herramienta valida sesiones y rondas preasignadas y registra intentos en carpetas que publican foto y ficha juntas. La comprobación de cámara de cada ronda se ejecuta sin guardar fotogramas. La prueba sintética preserva los datos y las herramientas históricas.
- D-42: el responsable aprobó preparar VeraCrypt en `C:\Downloads\FaceNexus` y conservar la credencial en privado. Instalador 1.26.31 descargado y verificado. La [guía operativa](vault_and_camera_setup.md) documenta el estado de montaje, verificación histórica y validación sin personas. El resultado operativo y la autorización de captura real siguen pendientes.

## Aclaraciones de clase — 19-11-2026

- D-43: el IoT de la demostración captura, envía a la computadora y actúa según la etiqueta devuelta. La TMCAM sigue siendo la referencia de desarrollo. Se propone ESP32 con cámara y una tira LED, pendientes de confirmar según disponibilidad.
- D-44: tratar cada rostro en escenas grupales. Una identidad autorizada confirmada basta para actuar; la ambigüedad que impida confirmar autorización produce denegación.
- D-45: separar humano/no humano del reconocimiento de los cuatro integrantes. Construir y entrenar los modelos de entrega. Conservar SFace y los clasificadores de biblioteca actuales como referencias de desarrollo. Demostrar un modelo, con la comparación y la interfaz descritas en el informe.
- D-46: con las imágenes disponibles, considerar S01 para ajuste y R01 para validación entre encuentros si se verifica su independencia. La asignación de los archivos privados queda pendiente de esa comprobación. Un ensayo en vivo congelado puede completar la evidencia práctica.
