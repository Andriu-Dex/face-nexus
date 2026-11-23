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

## Confirmaciones — 20-11-2026

- D-47: el responsable confirma dos días de grabación, con una persona en cuadro por turno. Las carpetas con sufijo 02 corresponden a R01, el segundo día. En el experimento entre encuentros, S01 se destina a ajuste y R01 a validación exploratoria. Se conserva el registro de preparación original.
- D-48: los modelos de IoT de la transcripción son ejemplos. Está disponible una placa con ESP-WROOM-32 y un SG90 para el pestillo de maqueta. La ruta con captura directa de la TMCAM en Windows sirve para desarrollo y requiere confirmación docente si se quiere presentar como configuración final.
- D-49 / CONF-04: el responsable confirma la captura directa en Windows para la demostración. Usar TMCAM 8305, ESP-WROOM-32 y SG90. La comunicación serie USB es la primera opción de integración. D-49 actualiza la condición de captura registrada en D-43 y D-48.
- D-50 / CONF-04: para la demostración, el responsable confirma captura desde el celular, procesamiento en Windows y actuación del ESP-WROOM-32 con SG90. Sustituye la fuente de captura de D-49. Se mantiene USB serie para la primera implementación de la actuación.

## Diagnóstico en vivo — 21-11-2026

- D-51: el siguiente trabajo de reconocimiento es medir el dominio del celular, no accionar el SG90. Se registra calidad de detección por fotograma (conteo, score de YuNet, tamaño de caja, motivo de recorte) y puntuaciones de clasificador, sin persistir imágenes ni vectores HOG. Un comando `probe` elige el giro sobre los mismos fotogramas. `inspect-attempts` resume intentos aunque falten integrantes. La política de muestreo `hog-margin-5x3-v1` no cambia. Los registros previos siguen siendo válidos para comparar umbrales cuando esté el conjunto mínimo.

## Adaptación al celular — 21-11-2026

- D-52: con un solo integrante presente, se captura un lote TRAIN de K01 desde el MJPEG del celular, separado de `rejection_calibration`. Las presentaciones de calibración no se reutilizan como entrenamiento porque no conservan vectores. K02–K04 se añaden al mismo esquema cuando estén disponibles. Los lotes de otra cámara (sesión 03 de K02 y K04) no entran en este lote. El reentrenamiento HOG espera al menos K01 en dominio celular; no se declara modelo nuevo hasta extraer y evaluar.

- D-53: no se reentrena el clasificador de cuatro clases con solo K01 del celular. Mientras llegan K02–K04, se mide el dominio HOG (lote `k01_phone_v3` contra medias de S01 y modelos congelados) y se implementa permiso más autorización simulada, siempre en modo cerrado y sin apertura física.

## Clasificador humano / no humano — 21-11-2026

- D-54: se entrena una CNN propia de dos clases con LFW (humano, partición por identidad) y CIFAR-10 (no humano, objetos y animales). No identifica a K01–K04. Los pesos preentrenados siguen reservados al recorte (YuNet). El modelo se guarda fuera de Git. Un recorte de 2000 imágenes por clase en TRAIN acota la primera ejecución; se puede repetir sin recorte. LFW se usa solo como etiqueta «humano»; no se mezcla con las cuatro identidades locales.

## Identidad de un integrante — 21-11-2026

- D-55: mientras K02–K04 no estén en el celular, el reconocimiento operativo es binario: K01 frente a OTHER (LFW, partido por identidad). Positivos: HOG de S01 de K01 más `k01_phone_v3` (15 TRAIN, 5 VALIDATION del celular). No se inventan las otras tres clases. La SVM lineal se define y entrena en Keras, igual que la comparación de fase 4. El umbral de aceptación se calibra para rechazar a los OTHER de validación que el modelo etiquete como K01. K02–K04 se incorporarán después como clases nuevas, no como etiquetas ficticias. El sistema de cuatro identidades sigue incompleto hasta esas capturas (PROF-01, PROF-07).

- D-56: en el celular, la CNN LFW/CIFAR no se usa como veto de un recorte YuNet (en 20 fotos TRAIN, 1 ya salía no humano). El umbral SVM 1,46 rechazaba fotos propias (márgenes 0,58–1,41) para anular 47 falsos K01 en LFW. La demo en vivo acepta el argmax K01 (margen 0) y muestra `cnn=H/N` sin bloquear. FAR LFW de validación con esa regla: 47/2627. Un objeto sin caja YuNet sigue siendo `no_face`.

- D-57: k-NN, MLP y SVM lineal se comparan con el mismo HOG K01/OTHER (S01 + celular + LFW). Se descarta un modelo con recall K01 nulo. Gana k-NN (5/5 K01, 1/2627 LFW). La MLP colapsa a OTHER. La SVM reconoce a K01 y acepta 47 LFW. La demo en vivo no se cambia todavía: sigue la SVM ya ensayada delante de la cámara. La comparación de cuatro clases en S01/R01 (D-41 / informe 11) permanece aparte.

- D-58: la demo en vivo usa k-NN por defecto, con la galería TRAIN del ensayo `identity_k01_compare_v1`. La SVM queda como `--backend svm`. No se añade umbral de distancia en este paso. La CNN LFW/CIFAR sigue siendo diagnóstico.

- D-59: se ajusta `human_cnn_full` con recortes YuNet y parches de fondo de `k01_phone_v3` (peso 20). Las 5 caras de validación del celular pasan a humano. YuNet sigue decidiendo si hay cara; la CNN no veta ese recorte. En ausencia de caja se muestra `cnn=` sobre el fotograma. No es liveness.

- D-60: se compara HOG 1764-D con el híbrido landmarks YuNet (12-D L2) + HOG completo (1776-D), mismas filas K01/OTHER. k-NN empata en 5/5 y 0 LFW colados; gana HOG por latencia. SVM empeora con landmarks (54 vs 225 LFW). La demo sigue en k-NN HOG. No se recorta el HOG.

- D-61: la calidad de recorte se mide en `k01_phone_v3` y S01 K01 (Laplaciano y colas 10/245). El umbral copiado de Laplaciano 85 rechazaría 8/20 fotos del celular que ya sirven en TRAIN/demo; no se adopta. Los avisos, si se usan, son por debajo del mínimo del mismo montaje (celular ≈ 8,8). No se borra TRAIN ni se veta el vivo. No se comparte umbral de tamaño de caja entre TMCAM y el teléfono.

- D-62: el vivo clasifica cada recorte YuNet y autoriza la escena si al menos un K01 pasa k-NN con T=0,456 (máximo d de VALIDATION × 1,1). El falso K01 de LFW (1/2627) queda fuera. Varios rostros ya no se rechazan en bloque. K02–K04 siguen sin clase. El simulador no abre el pestillo.

- D-63: se entrena una galería de cuatro IDs con encuentros distintos en el volumen privado (TRAIN: encuentro A de cada ID más un segundo encuentro de K02–K04; VALIDATION: encuentro B de K01 y sesión 03 de K02–K04). Exactitud 31/39; K02 5/9 se confunde con K03. T=0,770. El vivo autoriza a cualquiera de K01–K04 con permiso. Firmware `latch` (GPIO 18) para el SG90; el banco SIMULATED no mueve el servo. Interfaz `operator_ui`. El celular de la demostración sigue siendo el dominio de entrega.

- D-64: el 22-11-2026, con el micro-USB conectado, Windows mostró Silicon Labs CP210x en COM5. `PING` a 115200 recibió `PONG FACENEXUS BENCH 1`. No se grabó `latch`, no había `arduino-cli` en el PATH y no se observó el SG90. Queda pendiente la decisión de flashear.

- D-65: archivos e interfaz no emiten serie. Una orden por presentación de cámara (`PresentationGate`). Solo firmware `LATCH` habilita envío. Galería y T del mismo ensayo con SHA-256; si faltan, `model_unavailable`. El mapa de carpetas de Downloads sale del código Git. No se flasheó el pestillo ni se vetó con la CNN.

- D-66: el rearme exige cuadro vacío (`no_face`); denegaciones ambiguas bloquean. El acuse serie es la línea completa; `pulse_confirmed` no afirma la posición. Un error de transporte invalida el puerto. T JSON solo numérico real; `bind_threshold` comprueba `summary.json` si existe. Informes 14/16/18/22 y D-52/D-63 sin nombres de carpeta ni IP de ensayo.

- D-67: `no_face` de YuNet no rearma el pestillo; el operador pulsa «Siguiente presentación». `load_verified_knn` trata zip corrupto como `model_unavailable` y exige las cuatro identidades. `bind_threshold` no escribe sin `summary.json` con huella coincidente.

- D-68: la interfaz no envía el pestillo desde el reconocimiento. Extraños = LFW OTHER contra la galería de cuatro con T. Humano/no humano se mide aparte y no veta YuNet. Banco LATCH: órdenes `CHECK` con `--servo-disconnected`; no se flashea ni se engrana el SG90 en esta ronda.

- D-69: rechazo abierto: aceptar solo si el ganador es K01–K04, `d ≤ T` y `d_otra − d ≥ G`. T=0,530 y G=0,057 se eligen para FAR ≤ 1 % en LFW TRAIN OTHER (60/6537). El T anterior 0,770 queda como `previous_max_distance`. El recall LOO de TRAIN baja a 78/120. No es TEST ni el celular del aula.

- D-70: T y G se conservan como candidatos. VALIDATION de Downloads con ambos: 13/39, K02 0/9, 26 UNKNOWN. El reconocimiento no acciona el pestillo. Extraños disjuntos del aula, celular de demostración, ensayo K01–K04+externos y el papel de la CNN en la decisión siguen pendientes. El banco LATCH puede avanzar en paralelo con el SG90 desconectado.

- D-71: el calibrador T/G maximiza aciertos de identidad y penaliza confusiones aceptadas, no el recuento bruto de aceptados. Ensayo exploratorio K01–K04+OTHER (LFW por identidad): gana k-NN (19/39 inscritos, 2/2627 LFW). MLP/SVM cuelan extraños. El vivo sigue en la política de cuatro clases. Banco LATCH exige `--v5-unplugged`; no se grabó firmware.

- D-72: lotes del celular usan manifiesto privado `tune`/`eval`, ráfaga en una partición y aviso si falta una clase o hay hash cruzado. El candidato four+OTHER espera esos lotes; la UI sigue en simulación. Ensayo CNN-veto en el mismo cuarto: 0/20 caras vetadas, 1/60 parches se cuelan; el vivo no activa el veto.

- D-73: `phone_eval_ready` exige manifiesto válido, recortes usables de las cuatro clases, encuentros `tune`/`eval` distintos y HOG cotejado. La disjunción de extraños queda sin verificar si no hay listas de IDs. Los informes de dominio usan `domain_<nombre>.json` sin sobrescribir. La captura valida huellas, publica en staging y recupera huérfanos. La CNN 0/20 y 1/60 es diagnóstico del lote de adaptación; el veto sigue apagado.

- D-74: no se borra un lote en disco ausente del manifiesto. Un rename fallido conserva el staging registrado. El índice del celular lleva candado. El encuentro se nombra de forma explícita. Extraños e inscritos se cotejan por huella de archivo y por fila; el recuento no acredita disjunción. CNN y pestillo sin cambio.

- D-75: el candado cubre lectura, validación y escritura; una revisión desactualizada se rechaza. Un pendiente registrado solo se publica si ficha, encuentro, fase, huellas y HOG coinciden; si no, se conserva. La disjunción se verifica solo con IDs de calibración atados a la galería del ensayo y extraños con sample_ids por fila.

- D-76: la clave `(person_id, run_name)` se reserva creando el staging sin borrar un pendiente ajeno. La disjunción verificada exige filas de calibración leídas del NPZ usado (`sample_ids` e `identity_ids`); una lista externa con huella de galería no basta.

- D-77: la procedencia de calibración se escribe al consumir LFW (NPZ con vectores, `sample_ids` e `identity_ids`, huella en `summary.json` ligada a la galería). El evaluador solo verifica disjunción si esa huella coincide y hay vectores. Un NPZ de otro ensayo o sin vectores queda sin verificar.

- D-78: `--phone-tune` arma el ensayo K01–K04+OTHER con vectores `tune` del celular y OTHER de LFW. Exige las cuatro clases. Los lotes `eval` se cargan aparte y no entran al ajuste. El vivo sigue en simulación.

- D-79: la interfaz Tkinter prioriza el visor y la decisión; Cámara configura URL y giro. FaceNexus.cmd arranca en simulación con `.venv` y `V:\FaceNexus`. El mapa de nombres es privado. El pestillo no se acciona desde el reconocimiento.

- D-80: un fallo de lectura de cámara no conserva Autorizado. La decisión visible es Señal perdida, el último fotograma se marca como anterior y `note_fault` impide una orden física hasta el rearme del operador. Un archivo abierto no lo pisa el vivo hasta conectar de nuevo la cámara. El mapa `private/identity_labels.json` vive solo en el volumen.

- D-81: la cámara se configura por IP y puerto 8080, distintos del puerto serie. Un YuNet rechazado muestra identidad no confirmada y el vecino k-NN como diagnóstico; T y G de `identity_four_v2` no se relajan. El historial agrupa fotogramas repetidos. La aprobación de K01 exige un encuentro nuevo, no la ráfaga previa.

- D-82: detener o reconectar invalida la autorización de cámara. Un archivo se etiqueta como predicción de archivo. La URL efectiva (ruta incluida) se conserva; un fallo al guardar no impide conectar. Captura, inferencia y vista usan el fotograma más reciente, sin cola. Tkinter no abre el stream. T y G no cambian. El pestillo sigue en simulación.

- D-83: cada resultado fresco se publica una vez con edad máxima y sesión activa, aunque la vista haya avanzado. El recuadro es una capa de Canvas con vigencia breve; no alarga la autorización. Se borra si el análisis siguiente no ve rostro, caduca o cambia la sesión. El FPS cuenta fotogramas distintos.
