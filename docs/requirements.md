# Requisitos de FaceNexus

## Autoridad y alcance

`PROF`: instrucción explícita identificable en la transcripción. `CLASE`: concepto o metodología explicada, sin convertir cada ejemplo en obligación. `CONF`: aclaración expresa del responsable. `PROY`: decisión del proyecto revisable con evidencia y registro en `decisions.md`.

Las referencias de origen se encuentran en [source_analysis.md](source_analysis.md). Hay mediciones de captura (informe 03) y detección/alineación/embeddings en desarrollo (informe 07). No existen resultados independientes de reconocimiento, rechazo o acceso físico.

## Requisitos trazables

| ID | Requisito | Evidencia de aceptación prevista |
| --- | --- | --- |
| PROF-01 | Reconocer personas concretas y usar su identidad para habilitar acceso a un elemento | Demostración completa de identidad, permiso y acción |
| PROF-02 | Adquirir datos propios de participantes; se pueden usar datasets auxiliares | Inventario privado de capturas y procedencia |
| PROF-03 | Probar varios clasificadores, mostrar exactitudes y pruebas y justificar la elección | Informe reproducible de comparación |
| PROF-04 | Construir y entrenar los modelos presentados. Se permiten bibliotecas para definir el modelo y herramientas preentrenadas para el recorte | Explicación de características propias, arquitectura y entrenamiento |
| PROF-05 | Distinguir humano/no humano antes de reconocer a los integrantes | Pruebas con ejemplos positivos y negativos distintos de los usados para entrenar |
| PROF-06 | El nodo IoT captura, envía la imagen a la computadora, recibe la etiqueta y actúa | Demostración de la cadena completa en hardware |
| PROF-07 | Reconocer en escenas con varias personas y actuar cuando haya al menos una identidad autorizada confirmada | Casos individuales, varios integrantes, desconocidos y mezcla |
| CONF-03 | Usar TMCAM 8305 como referencia de captura del dataset y desarrollo local | Resolución, entrega efectiva y parpadeo documentados. La entrada de la demostración se valida con la cámara del nodo IoT según PROF-06. |
| CONF-02 | Priorizar código sencillo de entender, explicar y defender sobre patrones y convenciones que compliquen la solución | Revisión del flujo y explicación de cada operación; conservar corrección experimental y denegación ante fallos |
| CONF-01 | Integrar obligatoriamente un dispositivo físico de acceso en la entrega final | Apertura real autorizada y denegación verificadas con el hardware |
| CLASE-01 | Organizar y explicar las etapas de adquisición a postprocesamiento | Correspondencia entre módulos y memoria técnica |
| CLASE-02 | Distinguir entrenamiento, validación y prueba; estudiar generalización | Particiones y resultados separados |
| PROY-01 | Identificar cuatro participantes mediante cámara en tiempo real | Ensayos en sesiones nuevas para cada identidad |
| PROY-02 | Comparar SVM, Random Forest, k-NN y ANN/MLP | Mismas muestras y particiones para los cuatro |
| PROY-03 | Rechazar desconocidos e incertidumbre mediante política calibrada | Pruebas con desconocidos reservados y rechazos medidos |
| PROY-04 | Separar identidad, permiso, autorización y ejecución física | Revocar permiso sin reentrenar; registrar resultado real |
| PROY-05 | Denegar ante ausencia de una identidad autorizada confirmada, ambigüedad que impida decidir, fallo de cámara/modelo o excepción | Incluir escenas mixtas y grupos sin ninguna identidad autorizada |
| PROY-06 | Mantener biometría y credenciales fuera de Git y procesar localmente por defecto | Revisión de archivos, registros y configuración |
| PROY-07 | Mostrar cámara, identidades y decisión del modelo elegido. Documentar la interfaz y comparar los candidatos en el informe | Verificación de interfaz y tabla de exactitud |
| PROY-08 | Evitar órdenes repetidas, antiguas o sin confirmación de estado | Pruebas de temporización, desconexión y reconexión |

## Flujo esperado

Nodo IoT con cámara → computadora → detección y clasificación humano/no humano → características propias y reconocimiento por rostro → consulta de permiso → etiqueta y decisión de vuelta al nodo → acción física observada o fallo.

`GRANTED` expresa autorización; no prueba que el dispositivo se abrió. La interfaz debe distinguir ambos estados. Un fallo nunca genera una orden de apertura.

## Alcance de entrega

Se requieren cuatro identidades, comparación experimental, rechazo de desconocidos, inferencia en vivo y acceso físico verificado. El dispositivo y el mecanismo concreto siguen pendientes de selección. Un simulador permite probar el contrato durante las fases iniciales, pero no completa CONF-01.

La entrega demuestra un modelo elegido y una acción física en un entorno controlado. Probar ejemplos presentados en cámara sin atribuir detección de vida al clasificador humano/no humano.

## Cierre de aceptación

La entrega necesita evidencia de todos los requisitos aplicables: métricas sobre sesiones reservadas, comparación y selección previas a TEST, pruebas de errores y permisos, y demostración física autorizada y denegada. No basta con exactitud de entrenamiento, una animación de apertura o una orden enviada sin verificar el efecto. No hay umbrales numéricos de aprobación establecidos: se fijarán metas técnicas antes de la evaluación final y se reportarán los incumplimientos.
