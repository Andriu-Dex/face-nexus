# Protocolo de datos

## Captura y custodia

Obtener autorización de cada participante antes de capturar. Documentar propósito, acceso, almacenamiento local, conservación y procedimiento de retiro; no guardar consentimientos con nombres en Git. Emplear IDs seudónimos y mantener la correspondencia identificativa en almacenamiento privado.

Capturar las cuatro identidades en sesiones independientes con variación real de iluminación, distancia, posición y orientación moderada. Revisar etiquetas, archivos ilegibles, duplicados, ausencia de rostro, oclusión y rostros múltiples. Registrar exclusiones con motivo y cantidades; no descartar fallos difíciles solo para mejorar resultados.

La única pauta vigente para las nuevas capturas está en [Adquisición del dataset definitivo](#adquisición-del-dataset-definitivo--17-11-2026). Los procedimientos fechados del piloto y sus volúmenes anteriores se conservan como antecedentes.

## Manifiesto privado

Cada muestra tendrá `sample_id`, `person_id`, `session_id`, fuente, fecha de captura, condiciones, ruta privada, hash del archivo, partición y estado de calidad. No se publican rutas identificativas, imágenes, embeddings ni este manifiesto personalizado. En Git solo se conservan esquemas y ejemplos sintéticos.

Los lotes del celular de demostración (K01–K04) se registran en un manifiesto privado `tune` (ajuste) / `eval` (evaluación): cada ráfaga lleva un `--encounter-id` del encuentro real, no un nombre derivado del papel. Fecha, orientación y SHA-256 van en el índice. Una ráfaga completa permanece en una sola partición. El software avisa si falta una identidad o si una imagen se duplica entre particiones. Un lote ya publicado no se borra aunque falte en un manifiesto nuevo. Los extraños se vinculan al NPZ por huella, `sample_id` y etiqueta OTHER. Los IDs de calibración salen del NPZ escrito al entrenar, con vectores, `sample_ids` e `identity_ids`, y su huella queda en el `summary.json` del ensayo junto a la galería. Un archivo de otro ensayo o sin vectores no verifica la disjunción. Comprobar el esquema con un manifiesto sintético antes de capturar.

Toda sesión pertenece a una sola partición. También se agrupan duplicados y muestras derivadas de un mismo origen aunque tengan nombres o sesiones diferentes. Validar que las cuatro identidades aparecen en TRAIN, VALIDATION y TEST. La adquisición de una nueva ráfaga no acredita una sesión independiente por sí sola.

## Particiones

- TRAIN: ajuste de clasificadores y transformaciones aprendidas.
- VALIDATION: hiperparámetros, selección, calibración y umbrales; reservar subgrupos internos si el ajuste repetido lo requiere.
- TEST: evaluación final con pipeline congelado.

Los desconocidos de calibración y TEST deben tener identidades disjuntas entre sí y no pertenecer a las cuatro registradas. El aumento artificial solo se aplica a TRAIN después de dividir; sus derivados heredan la partición. No mezclar aumentos con diversidad de captura real.

PCA, escalado estadístico y selección de atributos se ajustan en TRAIN; dentro de validación cruzada, únicamente en el tramo de entrenamiento de cada fold. La calibración usa datos reservados para esa función sin tocar TEST. La normalización por norma de cada vector no estima estadísticas de otras muestras y debe documentarse por separado.

Antes de incorporar datasets o pesos externos, registrar origen, versión, licencia aplicable al artefacto concreto, restricciones y hash. La licencia del código no garantiza la de los pesos o datos.

## Retiro y conservación

Definir plazo y responsable antes de capturar. Un retiro implica localizar y eliminar datos, vectores y artefactos derivados según lo acordado, revisar copias de respaldo y reentrenar cuando corresponda. Mantener solo un registro técnico no identificativo del procedimiento. No publicar biometría para demostrar reproducibilidad.

## Selección de fuentes — 13-11-2026

Se adopta como base planificada LOCAL-K (las cuatro personas registradas) y LOCAL-U (voluntarios externos con consentimiento). Una persona registrada puede tener permiso activo o inactivo: el permiso no es la etiqueta de entrenamiento. Los IDs son seudónimos, no anonimizan fotografías o vectores faciales.

La comparación HOG de las cuatro identidades usa las capturas propias de S01 y R01. HOG calcula características directamente y carece de una etapa de preentrenamiento. Los datasets públicos a gran escala tendrían sentido en un experimento aparte para entrenar un extractor profundo general. FaceNexus ya dispone de SFace preentrenado y verificado como referencia para ese experimento.

Para la tarea humano/no humano, se puede evaluar un conjunto público acotado con ejemplos pertinentes y condiciones de uso verificadas. Los recuentos de desconocidos para calibración y prueba se obtendrán con personas distintas y la cámara de la demostración. [Fuentes estudiadas](reports/02_dataset_research.md) · [Pesos verificados](model_verification.md)

## Captura piloto y volumen inicial propuesto (antecedente)

Antes de capturar, definir por escrito quién custodia los datos, quién accede, ubicación privada, plazo o evento de eliminación y procedimiento de retiro. El consentimiento debe cubrir captura, procesamiento local y demostración; publicar imágenes o grabar una presentación requiere autorización específica. No comenzar capturas persistentes con esos puntos sin resolver.

Como piloto logístico se propone una sesión de **20 fotografías por persona registrada (80 en total)**, con autorización y aprobación previa del protocolo. La ficha operativa y la distribución se concretan al final de este documento. No es un conjunto de TEST. Revisar encuadre, iluminación, resolución real y variación antes de repetir a escala. Si se conserva para desarrollo, asignarlo exclusivamente a TRAIN; no trasladarlo después a TEST. No es necesario implementar aún la herramienta de captura para aprobar este protocolo.

Para el experimento principal se propone inicialmente **seis sesiones por persona, de 20–30 fotografías cada una**: tres sesiones TRAIN, una VALIDATION y dos TEST. Representa 480–720 imágenes para las cuatro personas, antes de descartes. El motivo es disponer de varias condiciones de entrenamiento y dos sesiones finales independientes sin acumular miles de fotogramas redundantes. No es un cálculo de potencia ni prueba de suficiencia. El piloto puede justificar otro volumen; si VALIDATION se usa para muchas decisiones o calibración, añadir sesiones de desarrollo separadas antes de TEST. Si se conserva el piloto como una sesión TRAIN, cuenta dentro de las seis y debe cumplir el protocolo final.

Una sesión es un encuentro de captura separado, preferiblemente en distintos días o momentos con cambios reales de condiciones. Reiniciar la cámara o renombrar una ráfaga no crea independencia. El registro indica cuándo y qué cambió. Mantener distribución de condiciones comparable entre personas; no capturar cada identidad siempre con un fondo propio.

Para desconocidos se propone reclutar inicialmente **al menos seis voluntarios externos**, tres asignados solo a VALIDATION y tres solo a TEST, con dos sesiones de 10–20 fotos por voluntario. Es una escala inicial viable, no una muestra suficiente para afirmar seguridad general. Ampliar el número de personas antes que añadir ráfagas de las mismas. Si no hay voluntarios suficientes, registrar la limitación y dejar la evaluación abierta pendiente; no reutilizar identidades entre grupos para aparentar independencia. El piloto puede usar los desconocidos de VALIDATION, nunca los de TEST.

## Procedimiento por sesión (antecedente del piloto)

1. Comprobar consentimiento y grupo asignado; cerrar sincronizaciones externas no autorizadas. Usar una sola persona en las capturas destinadas a identificación.
2. Usar exclusivamente la webcam USB TMCAM 8305, con objetivo 1920×1080 a 30 FPS y antiparpadeo previsto de 60 Hz. Verificar resolución y FPS efectivos antes de fijar la configuración; si no es estable, presentar resultados antes de adoptar otra resolución. Registrar resolución efectiva, modelo de cámara y distancia aproximada. La resolución del fotograma no es el tamaño del rostro ni la entrada del extractor.
3. Distribuir 20–30 fotos entre rostro frontal, giros moderados izquierda/derecha y leves cambios verticales, expresión neutra/sonrisa y distancias cercana/normal/alejada dentro del uso previsto. Como guía inicial, 0,5–1,5 m, ajustable según óptica y montaje; no forzar distancias que produzcan un rostro ilegible.
4. Variar iluminación difusa y lateral, fondo y momento entre sesiones. Repetir condiciones relevantes en varias identidades. Reservar perfiles extremos, oclusiones fuertes y contraluz para ensayos difíciles identificados; no prometer identificarlos.
5. Tomar fotos espaciadas mientras cambia pose o posición. No conservar vídeo continuo por defecto. Preferir PNG o JPEG de alta calidad fijada para todas las sesiones; documentar formato y evitar recompresión repetida. No mejorar ni reducir los originales guardados.
6. Revisar archivos y etiquetas de la sesión. Repetir inmediatamente una captura accidentalmente movida o mal encuadrada, conservando el motivo del reemplazo en el manifiesto. Los ensayos difíciles previstos se mantienen como tales, aunque el sistema falle.

El recorte y la alineación definitivos se verifican en fase 2. No derivar un requisito de cámara solo de la entrada 112×112 de un modelo. Anotar resolución aparente del rostro en el piloto para definir un criterio de calidad antes del experimento principal.

## Almacenamiento y manifiestos privados (antecedente del piloto)

Usar `/data/` como raíz local excluida, con `raw/`, `processed/`, `features/` y `manifests/`; consentimientos y correspondencia de IDs en `/private/`, con acceso más restringido. Estos nombres son una propuesta de organización, no carpetas creadas con datos. No guardar originales en docs, notebooks ni informes públicos.

Ejemplo sintético de nomenclatura: `K01_S03_0007.png` y `U04_S02_0005.png`. El manifiesto relaciona muestra, identidad, sesión, grupo conocido/desconocido, partición y derivación. No codificar nombres personales ni permiso de acceso en el nombre. Para cada derivado registrar `parent_sample_id`, versión de preparación/extractor, dimensión, dtype y hash; los vectores también son biometría privada.

Mantener originales inmutables y generar recortes aparte. Conservar copias de seguridad solo en ubicaciones autorizadas, con los mismos plazos y acceso; Git no es respaldo biométrico. El responsable confirmó el 14-11-2026 la eliminación a los 90 días después de la defensa. Registrar la fecha de defensa y su vencimiento cuando se conozcan; no conservar indefinidamente ni ignorar retiros anticipados.

## Auditoría previa al entrenamiento

La herramienta definitiva comprueba estructura, integridad, duplicados exactos de PNG y coherencia de sesiones. La auditoría del dataset real incluye además los controles manuales y las comprobaciones de representaciones descritas aquí.

| Control | Comprobación propuesta | Acción ante problema |
| --- | --- | --- |
| Integridad | Abrir/decodificar, dimensiones y canales; calcular SHA-256 y comparar con inventario o checksum de proveedor | Aislar ilegibles; no interpretar hash local sin referencia como prueba de autenticidad |
| Identidad y consentimiento | Revisar manualmente todas las etiquetas de la colección local pequeña y el permiso de uso de cada fuente | Corregir antes de congelar y registrar cambios; desconocidos nunca se etiquetan K01–K04 |
| Duplicados exactos | Igualdad de hashes en todo el inventario, incluidos originales/derivados | Agrupar origen y descendientes en una sola partición; evitar contar copias como muestras nuevas |
| Similitud perceptual | Generar candidatos con hashes perceptuales o comparación equivalente; revisar visualmente en local | No borrar automáticamente: similitud no prueba duplicación y rostros distintos pueden parecerse |
| Sesiones y fugas | Una sesión y grupo de duplicados por partición; cuatro conocidos presentes en los tres conjuntos; desconocidos disjuntos por identidad | Bloquear congelación hasta resolver; revisar también solapamiento entre fuentes públicas |
| Rostros y calidad | Contar detecciones, medir nitidez/exposición/tamaño de rostro con configuración registrada; revisión manual de discrepancias | Marcar métricas y motivos. Los límites se fijan con desarrollo; fallo del detector no autoriza descartar todo TEST difícil |
| Balance | Cantidades por persona, sesión, partición y condición, antes/después de filtros | Reportar desbalance; corregir captura si procede sin seleccionar por aciertos del modelo |
| Compatibilidad | Canales, escala, alineación, dimensión y valores finitos; mismas muestras para cada representación | Fallos explícitos; no excluir muestras distintas por modelo sin reportarlo |
| Procedencia | URL/versión, fecha, licencia de archivo/peso y hash esperado/observado por separado | No incorporar recurso con condiciones pendientes |

En un benchmark opcional, respetar anotaciones/protocolo oficiales, validar lectura e integridad y revisar una muestra y anomalías; no corregir silenciosamente el benchmark para favorecer el resultado. Para comparar representaciones registrar cobertura de detección/extracción y fallos; reportar tanto el subconjunto común válido como el resultado extremo a extremo, sin ocultar exclusiones.

Una primera auditoría estructural de TEST puede verificar formato, consentimiento, partición y duplicados. No usar sus scores, etiquetas asociadas a errores o desempeño para ajustar calidad, preprocesamiento, parámetros o rechazo. Aplicar filtros congelados y contar sus fallos en el resultado operativo. Separar este inventario estructural del análisis final del modelo.

## Salida de la fase de datos

Antes de declarar el dataset preparado, deben existir consentimientos y custodia definidos, inventario privado versionado, particiones por sesión, ausencia de fugas sin resolver y reporte agregado de cantidades/exclusiones. Registrar el hash del manifiesto congelado sin publicar el manifiesto. La captura y auditoría real del dataset definitivo siguen pendientes.


## Cámara oficial y validación previa — 13-11-2026

La TMCAM 8305 es la cámara de las capturas históricas y del desarrollo local. La demostración y el ensayo en vivo usan el celular. Registrar la fuente de cada ensayo para interpretar el cambio de cámara.

La configuración objetivo es 1920×1080 a 30 FPS mediante OpenCV; el ajuste previsto antiparpadeo es 60 Hz, sujeto al soporte del controlador y revisión visual. La cámara y 1920×1080 quedan fijados para el piloto: el ensayo del 13-11-2026 midió 29,241 FPS medios, sin fallos durante diez minutos. El objetivo sigue siendo 30 FPS, sin afirmar constancia. Falta confirmar 60 Hz y ensayar desconexión durante lectura activa; no impiden preparar el piloto. La herramienta inicial está en [camera_diagnostic.md](camera_diagnostic.md).

Conservar diversidad de iluminación, distancia, pose y sesiones. Los resultados solo acreditarán el entorno y cámara ensayados. La evidencia técnica permite preparar el piloto; no comenzar captura masiva sin revisar el piloto y obtener la aprobación correspondiente.


## Ficha operativa del piloto — propuesta del 14-11-2026

**Estado: condiciones de custodia y conservación confirmadas el 14-11-2026; herramienta verificada con datos sintéticos; el responsable declara consentimiento de los cuatro y autoriza ejecutar el piloto. La auditoría de capturas reales sigue pendiente.** Objetivo: comprobar adquisición, diversidad y viabilidad de preparación facial; no medir accuracy ni entrenar clasificadores. La captura definitiva necesita una decisión posterior al resultado del piloto.

### Participantes, sesión y fotografías

Cuatro personas registradas K01–K04; una sesión independiente P01 por persona. Veinte fotos por persona permiten revisar cinco bloques pequeños sin acumular ráfagas; 80 imágenes siguen siendo auditables manualmente. Es un presupuesto inicial de trabajo, no suficiencia estadística ni exigencia del profesor. No repetir automáticamente hasta conseguir 20 detecciones exitosas: se cuentan intentos, originales y reemplazos por separado.

Usar TMCAM 8305, fotograma original 1920×1080, objetivo 30 FPS, backend/formato documentados en el ensayo. Índice USB verificado en cada conexión, sin fallback. PNG para el piloto evita recomprimir originales. Esperar al menos 2 s entre fotos y cambiar deliberadamente pose/posición; el espaciado no convierte fotos en observaciones independientes.

| Bloque | Fotos por persona | Condición propuesta |
| --- | --- | --- |
| Frontal de referencia | 4 | Rostro centrado, expresión neutra, leve reposicionamiento entre tomas |
| Giro horizontal | 4 | Aproximadamente 15° y 30° a cada lado; no son ángulos instrumentados |
| Inclinación vertical | 4 | Arriba/abajo leves, aproximadamente 10°; repetir con reposicionamiento |
| Distancia | 4 | Aproximadamente 0,6; 0,8; 1,0 y 1,2 m; registrar distancia real aproximada y ajustar si el montaje no permite encuadre |
| Expresión | 4 | Dos neutras y dos con sonrisa natural, conservando rostro visible |

Repartir 10 tomas con luz frontal/difusa y 10 con luz lateral moderada, usando la misma pauta para las cuatro personas. Registrar luz por muestra y evitar que una identidad tenga siempre un fondo o iluminación exclusivos. El piloto es una comprobación de viabilidad, no un diseño factorial que permita aislar cada efecto. No incluir perfiles extremos o contraluz intenso como condición nominal; se podrán ensayar aparte, sin afirmar robustez no medida.

### Consentimiento y conservación a aprobar

Propuesta concreta: el responsable del proyecto actúa como custodio único; almacenamiento local bajo su cuenta personal, dentro de data y private, sin sincronización a nube ni acceso de compañeros por defecto. El usuario responsable del proyecto confirmó que será el custodio. Falta comprobar la ubicación privada efectiva antes de capturar. Si el equipo/carpeta es compartido, resolver permisos efectivos primero; .gitignore no es un control de acceso ni cifrado.

Proponer eliminar las imágenes y derivados **90 días después de la defensa final**, o antes si el participante retira su autorización. El responsable aceptó este plazo el 14-11-2026; es una decisión del proyecto, no un plazo legal atribuido a una norma. Registrar fecha real de defensa y fecha límite cuando se conozcan; no trasladar el vencimiento silenciosamente. No crear respaldos adicionales del piloto por defecto; si se necesitan, acordar ubicación y borrado junto al original.

Cada participante debe conocer propósito académico, tipos de datos (originales, recortes y futuros vectores), destinatarios, acceso local, duración, contacto de retiro y ausencia de publicación de rostros por defecto. Separar consentimiento para participar del permiso de acceso al dispositivo. Exhibir imágenes en defensa, grabarlas o publicarlas requiere un alcance de consentimiento explícito, no se presume al aceptar la captura.

La aprobación del responsable del protocolo no sustituye el consentimiento individual. No es necesario enviar nombres, formularios firmados ni fotos a este chat: guardar esa documentación en private.

### Organización y auditoría inmediata

Usar `data/raw/pilot/K01/P01/K01_P01_0001.png`, con la misma estructura para K02–K04. Los recortes irán después en processed y los vectores en features; no se generan en esta entrega. Manifiesto privado con sample_id, person_id, session_id, block, lighting, distance_approx_m, camera_config, captured_at, consent_ref, relative_path, sha256, split, quality_status y exclusion_reason. Las rutas son ejemplos sintéticos y no contienen datos reales.

1. Verificar consentimiento, etiqueta, que haya una persona y que el rostro completo quede visible en las tomas nominales; revisar exposición, movimiento y foco visualmente.
2. Archivos ilegibles, etiquetas erróneas o capturas accidentales se aíslan y se registra la causa. No borrar ni reemplazar silenciosamente; una corrección de etiqueta no altera el original.
3. Fallo del detector futuro, mala calidad deliberada o un caso difícil válido se conserva y se marca: no eliminarlo para favorecer métricas. Auditar cobertura por condición.
4. Calcular hashes para integridad y duplicados exactos; candidatos a duplicado perceptual se revisan en local. No asumir que un hash diferente demuestra una toma independiente.
5. Después de aprobar la adquisición de modelos y verificarlos, medir caja/tamaño de rostro, detecciones y nitidez/exposición. No fijar un umbral numérico de desenfoque sin observar su escala en desarrollo; documentar cualquier decisión antes del experimento principal.

Asignar el piloto conocido solo a TRAIN/desarrollo, nunca a VALIDATION o TEST. Si cumple el protocolo principal puede contar como una de sus sesiones TRAIN; si se modifican las condiciones después, registrar la incompatibilidad y no incorporarlo automáticamente. Mantener la propuesta principal de seis sesiones por identidad (3 TRAIN, 1 VALIDATION, 2 TEST), ampliando desarrollo si requiere calibración separada. No repartir una sesión ni sus derivados entre particiones.

### Incorporación de desconocidos

El primer piloto puede limitarse a las cuatro personas. Antes de evaluar rechazo, reclutar seis voluntarios externos como propuesta inicial: tres solo VALIDATION/desarrollo y tres solo TEST, dos sesiones de 10–20 fotos por persona según el protocolo principal. Registrar disponibilidad real, consentimiento y asignación antes de capturar. No inventar participantes si no hay disponibilidad; reportar la limitación.

Los voluntarios de TEST no participan en depuración ni calibración. No guardar a todos como una única persona UNKNOWN entrenable: sus IDs U01–U06 permiten controlar disjunción, aunque la salida del sistema sea UNKNOWN. No otorgarles acceso por participar. Son distintas las pruebas de fotos reservadas y las presentaciones en vivo posteriores.

### Puerta de aprobación y salida

Antes de capturar, el responsable confirma: (a) 20 fotos por persona y distribución anterior; (b) identidad del custodio y que la ubicación privada está disponible sin sincronización; (c) conservación propuesta y acceso; (d) consentimiento de cada participante, custodiado localmente. La aprobación del piloto no autoriza todavía captura definitiva, publicación ni adquisición de pesos.

Al cerrar el piloto, entregar cantidades intentadas/válidas/excluidas por persona/condición, motivos, integridad/duplicados, incidencias y ajustes recomendados. No habrá métricas de identificación hasta fases posteriores. El diagnóstico sigue sin guardar fotos. La nueva herramienta manual y su auditoría estructural se describen en [pilot_capture.md](pilot_capture.md).


Confirmación del responsable — 14-11-2026: asume la custodia, acepta la eliminación a los 90 días de la defensa y obtendrá el consentimiento individual. Este último es un compromiso futuro, no evidencia de consentimientos ya obtenidos. No se capturaron imágenes con esta actualización. El siguiente trabajo es preparar y probar la herramienta de captura con entradas sintéticas; antes de usarla con personas se verifica consentimiento y destino privado.


Actualización — 14-11-2026: el custodio declara que ya obtuvo consentimiento individual de los cuatro participantes y que están disponibles para el piloto. Se crearon data/private con permisos Windows restringidos a su cuenta, SYSTEM y Administradores, y se verificó exclusión de Git; no se cifraron. La herramienta de captura/auditoría superó la prueba sintética de 80 imágenes, sin acreditar aún calidad de fotos reales. La revisión de consentimientos es responsabilidad local del custodio, no se suben documentos al chat.


## Colección externa activa — 17-11-2026

El custodio entregó 11.413 fotogramas de vídeo en almacenamiento externo y confirmó TMCAM 8305 y etiquetas locales. Por su última instrucción se agrupan todos los segmentos de cada persona en una sola S01 de TRAIN/desarrollo, sin certificar cuántos vídeos reales hubo. Se preservan originales y segmento/número de frame. La selección candidata contiene 20 copias por persona. No dividir aleatoriamente en VALIDATION/TEST; hacen falta nuevas sesiones.

Hay resolución real 848×478 para tres IDs y 1280×720 para otro: desviación documentada respecto de 1080p, sin ampliación artificial ni aprobación de calidad facial. Las diez fotos manuales previas siguen separadas. El inventario intermedio por segmentos queda sustituido para asignación de sesiones. Ver [informe 06](reports/06_external_frames.md) para evidencia, ubicación activa y límites. Esta actualización reemplaza el plan de continuar ahora la captura manual de 80 fotos; la guía manual se conserva como herramienta disponible, no como procedencia de la colección externa.


## Detección y extracción inicial — 17-11-2026

El responsable autorizó la adquisición exclusiva de YuNet/SFace tras revisión de condiciones y su validación técnica. Se procesaron las 80 candidatas de CURRENT.json sin modificar originales: 73 vectores válidos, siete sin detección con configuración inicial conservada. No se creó VALIDATION/TEST ni se reemplazaron imágenes difíciles. Pesos, detecciones, recortes, embeddings, gráficas y resultados por muestra quedan en almacenamiento privado. El [informe 07](reports/07_face_pipeline_validation.md) registra resultados agregados y revisión visual local; no equivale a aprobación definitiva de etiquetas/calidad, entrenamiento o seguridad de acceso.

## Adquisición del dataset definitivo — 17-11-2026

La revisión del 19-11-2026 conserva esta pauta para las capturas propias. La clasificación humano/no humano necesita ejemplos de esa tarea, y estos se organizan aparte de las cuatro identidades. El 20-11-2026 el responsable confirmó que S01 y R01 corresponden a dos días distintos y que en cada jornada se grabó a cada integrante por separado. Las carpetas con sufijo 02 corresponden al segundo día. Para la comparación entre encuentros usar S01 para entrenar y R01 como validación exploratoria. Mantener el registro original de R01 como lote preparado para TRAIN y registrar la nueva asignación en el manifiesto del experimento.

El responsable declara que los cuatro integrantes aceptaron verbalmente en una reunión de Zoom grabada. Antes de las capturas definitivas y de entrenar con fotos anteriores, revisar localmente qué finalidades cubre ese consentimiento. Los [formularios](consent_templates.md) son un apoyo opcional. S01 entra al desarrollo y se podrá incorporar solo a TRAIN según la comparación descrita abajo. P01 continúa como piloto histórico. Los voluntarios requieren su propio consentimiento previo.

**Experimento de entrega.** El [informe 08](reports/08_dataset_acquisition.md) recoge la procedencia y las pruebas de la herramienta. Usar S01 para ajustar los modelos de identidad y R01 para validación exploratoria entre días. El lote auditado de 80 candidatas sirve para seleccionar fotos de S01. Para el ensayo en vivo, congelar el modelo y registrar el celular como fuente. La clasificación humano/no humano usa su propia colección de positivos y negativos.

### Cámara y ensayo operativo

1. Antes de cada ronda y de guardar imágenes, confirmar el alcance del consentimiento, la asignación y el destino privado cifrado. Reidentificar la TMCAM 8305 al conectarla y registrar modelo, nombre de dispositivo y backend. Solicitar DirectShow/MJPG, 1920×1080 y 30 FPS. Medir la entrega durante un minuto tras cinco segundos de calentamiento, con una escena sin personas y sin guardar fotogramas. Registrar modo solicitado y informado, tamaño recibido, FPS efectivos y errores. El [diagnóstico previo](reports/03_camera_diagnostic.md) obtuvo 29,241 FPS medios en diez minutos a 1080p.
2. Si llega una resolución distinta, aparecen fallos de lectura o la entrega cae de forma sostenida frente al diagnóstico previo, detener la adquisición y registrar la incidencia. Confirmar el ajuste de 60 Hz en el controlador si está disponible y revisar bandas visibles bajo cada luz prevista. Registrar ambos resultados por separado, con estado pendiente cuando el controlador no permita verificarlo. Repetir la comprobación si cambia la conexión o el modo.
3. Tras recibir autorización expresa de captura, hacer una primera sesión guiada de 20 tomas nominales por integrante y revisar el resultado antes de continuar con las demás. Puede contar como la primera sesión TRAIN de cada persona si se mantiene la pauta, hay trazabilidad completa y pasa la auditoría. Si se cambia la pauta o falla la auditoría, conservar la sesión como desarrollo exploratorio y programar otra TRAIN. Usar la [herramienta definitiva](pilot_capture.md#herramienta-del-dataset-definitivo) con su propio plan y destino.

### Pauta común de captura

Montar la cámara aproximadamente a la altura de los ojos, con una sola persona en cuadro y un punto de referencia a 0,8 m. Usar dos bloques de diez tomas, uno con luz frontal difusa y otro con luz lateral moderada. Usar condiciones comparables en las cuatro personas y cambiar el orden de los bloques entre rondas. Evitar un fondo exclusivo por identidad. Tras cada toma, dejar al menos dos segundos y cambiar la pose o recolocarse. Guardar PNG del fotograma recibido, sin recortar ni reescalar el original. Registrar cualquier ajuste que se deba hacer por encuadre u óptica.

| Tomas por bloque | Pauta orientativa |
| --- | --- |
| 2 | Frontal neutra y frontal con sonrisa natural a la distancia de referencia |
| 2 | Giro horizontal aproximado de 20° a izquierda y derecha |
| 2 | Inclinación vertical leve, unos 10° arriba y abajo |
| 2 | Frontal a distancias aproximadas de 0,6 y 1,2 m, con rostro completo |
| 2 | Giro lento y recolocación natural, con una captura por movimiento |

Definir antes de cada ronda los casos difíciles que se quieran ensayar, por ejemplo perfil pronunciado o contraluz. Marcarlos como `difficult`, fuera de las 20 tomas nominales y dentro de la misma partición que su sesión. Conservar los fallos válidos del detector tanto en condiciones nominales como difíciles. Si una toma se repite por una incidencia de captura, registrar original, motivo y reemplazo, y contabilizar el intento. Reportar cantidades por persona, sesión, condición y resultado.

### Asignación y reserva de sesiones

Una ronda reúne un encuentro por integrante. Asignar la misma partición a toda la ronda y programar rondas en días o momentos separados, con cambio real de hora, entorno o montaje documentado. Un nuevo archivo, una pausa breve o reiniciar la cámara durante el mismo encuentro conserva el ID de sesión. Las nuevas capturas pueden hacerse con vídeos de la TMCAM a 1920×1080 y objetivo de 30 FPS. Guardar por integrante y encuentro en carpetas nuevas del volumen cifrado, conservar el archivo fuente y registrar su hash, el modo de captura y la exportación. Seleccionar tomas variadas, sin redimensionar el original. Todo derivado y toda toma del encuentro heredan su partición.

| Grupo | TRAIN | VALIDATION | TEST | Tomas nominales previstas |
| --- | --- | --- | --- | ---: |
| K01–K04 | 3 sesiones por persona | 1 sesión por persona | 2 sesiones por persona | 480 con 6 sesiones por persona |
| U01–U03 | — | 2 sesiones por persona | — | 120 |
| U04–U06 | — | — | 2 sesiones por persona | 120 |

La planificación inicial suma 720 tomas nominales. Se priorizan diversidad de personas, sesiones independientes y cobertura de condiciones. La cantidad de fotogramas por sí sola no acredita suficiencia. Antes de iniciar la selección y calibración de modelos, el custodio decidirá si añadir una segunda ronda VALIDATION para conocidos. Si se aprueba, añadiría 80 tomas nominales y permitiría dedicar rondas distintas a selección y calibración.

Usar con los voluntarios la misma cámara y pauta nominal, con consentimiento individual y seudónimos estables. Los IDs U son independientes de las cuatro identidades registradas y están asignados a un solo grupo antes de capturar. Si faltan voluntarios, registrar los grupos realmente disponibles y dejar pendiente la evaluación abierta que no pueda ejecutarse. Reservar TEST bajo custodia, con auditoría de inventario e integridad antes de su uso y acceso para evaluación solo al congelar el pipeline y la política de rechazo.

### Nombres, ficha y auditoría

- Usar un ID de sesión por encuentro, por ejemplo `K01_S02`, y un ID por intento, por ejemplo `K01_S02_A000001.png`. El plan preasigna ronda, identidad y partición. Cada sesión guarda una copia de su asignación. Mantener rutas, correspondencias y referencias a consentimientos en almacenamiento privado.
- **Ficha de sesión:** ID de sesión, ronda, seudónimo, partición, fecha y hora con zona, montaje y cambios respecto de otras sesiones, fondo, luces, cámara y backend/formato, resolución y FPS solicitados/medidos, duración del diagnóstico, fallos, estado de 60 Hz y referencia privada al consentimiento.
- **Ficha de toma:** ID, sesión, instante, número de intento, luz, distancia aproximada, pose, expresión, movimiento, condición nominal o difícil, origen foto/vídeo, ruta relativa privada, SHA-256, calidad, estado y motivo de repetición/exclusión. Usar campos vacíos explícitos si un valor no se midió.
- Auditar archivos, hashes, cobertura por persona y condición, duplicados y procedencia compartida. Detener la congelación del manifiesto si hay una sesión o fuente compartida entre particiones. Separar las incidencias de adquisición de los fallos válidos de detección; estos últimos cuentan en evaluación de extremo a extremo.

### Protección del almacenamiento definitivo

Usar una carpeta NTFS restringida dentro de un contenedor VeraCrypt local. El custodio controla el montaje y conserva las credenciales de recuperación fuera del contenedor, de Git y del chat. El volumen protege en reposo originales, recortes, embeddings, manifiestos, consentimientos y sus respaldos autorizados. Mientras está montado, se aplican permisos de la cuenta del custodio, SYSTEM y Administradores. Mantener archivos temporales y derivados dentro del volumen. Desmontar tras el uso y conservar el plazo de eliminación acordado. La [guía de preparación y verificación](vault_and_camera_setup.md) describe la instalación, el ensayo sin personas y la copia verificable. La captura real requiere autorización expresa posterior.
