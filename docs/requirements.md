# Requisitos de FaceNexus

## Autoridad y alcance

`PROF`: instrucción explícita identificable en la transcripción. `CLASE`: concepto o metodología explicada, sin convertir cada ejemplo en obligación. `CONF`: aclaración expresa del responsable. `PROY`: decisión del proyecto revisable con evidencia y registro en `decisions.md`.

Las referencias de origen se encuentran en [source_analysis.md](source_analysis.md). Solo hay mediciones de captura de cámara (informe 03); no existen resultados de reconocimiento, rechazo o acceso físico.

## Requisitos trazables

| ID | Requisito | Evidencia de aceptación prevista |
| --- | --- | --- |
| PROF-01 | Reconocer personas concretas y usar su identidad para habilitar acceso a un elemento | Demostración completa de identidad, permiso y acción |
| PROF-02 | Adquirir datos propios de participantes; se pueden usar datasets auxiliares | Inventario privado de capturas y procedencia |
| PROF-03 | Probar varios clasificadores, mostrar exactitudes y pruebas y justificar la elección | Informe reproducible de comparación |
| PROF-04 | Explicar y aplicar conocimientos de características y procesamiento de imágenes, pudiendo usar bibliotecas | Pipeline explicado y experimento de representación propia |
| CONF-03 | Usar exclusivamente TMCAM 8305 para captura y operación; verificar objetivo 1080p/30 FPS antes de captura definitiva | Resolución recibida, frecuencia de entrega y estabilidad medidas; 60 Hz y parpadeo comprobados por separado |
| CONF-02 | Priorizar código sencillo de entender, explicar y defender sobre patrones y convenciones que compliquen la solución | Revisión del flujo y explicación de cada operación; conservar corrección experimental y denegación ante fallos |
| CONF-01 | Integrar obligatoriamente un dispositivo físico de acceso en la entrega final | Apertura real autorizada y denegación verificadas con el hardware |
| CLASE-01 | Organizar y explicar las etapas de adquisición a postprocesamiento | Correspondencia entre módulos y memoria técnica |
| CLASE-02 | Distinguir entrenamiento, validación y prueba; estudiar generalización | Particiones y resultados separados |
| PROY-01 | Identificar cuatro participantes mediante cámara en tiempo real | Ensayos en sesiones nuevas para cada identidad |
| PROY-02 | Comparar SVM, Random Forest, k-NN y ANN/MLP | Mismas muestras y particiones para los cuatro |
| PROY-03 | Rechazar desconocidos e incertidumbre mediante política calibrada | Pruebas con desconocidos reservados y rechazos medidos |
| PROY-04 | Separar identidad, permiso, autorización y ejecución física | Revocar permiso sin reentrenar; registrar resultado real |
| PROY-05 | Denegar ante ausencia de rostro, múltiples rostros, fallo de cámara/modelo o excepción | Pruebas automatizadas y prácticas según corresponda |
| PROY-06 | Mantener biometría y credenciales fuera de Git y procesar localmente por defecto | Revisión de archivos, registros y configuración |
| PROY-07 | Ofrecer cámara, estado, identidad, permiso, eventos sin imágenes y comparación de modelos | Verificación de interfaz con datos y resultados reales |
| PROY-08 | Evitar órdenes repetidas, antiguas o sin confirmación de estado | Pruebas de temporización, desconexión y reconexión |

## Flujo esperado

Cámara → detección de un rostro → preparación → vector de características → clasificación candidata → aceptación o `UNKNOWN` → consulta de permiso → `GRANTED` o `DENIED` → ejecución del controlador → resultado confirmado o fallo.

`GRANTED` expresa autorización; no prueba que el dispositivo se abrió. La interfaz debe distinguir ambos estados. Un fallo nunca genera una orden de apertura.

## Alcance de entrega

Se requieren cuatro identidades, comparación experimental, rechazo de desconocidos, inferencia en vivo y acceso físico verificado. El dispositivo y el mecanismo concreto siguen pendientes de selección. Un simulador permite probar el contrato durante las fases iniciales, pero no completa CONF-01.

No se exige identificar a cualquier persona, resistencia a fotografías o vídeo, despliegue público, entrenamiento desde cero ni operación como cerradura de alta seguridad. Se documentará y ensayará la suplantación como limitación; no se declarará detección de vida sin evaluación específica.

## Cierre de aceptación

La entrega necesita evidencia de todos los requisitos aplicables: métricas sobre sesiones reservadas, comparación y selección previas a TEST, pruebas de errores y permisos, y demostración física autorizada y denegada. No basta con exactitud de entrenamiento, una animación de apertura o una orden enviada sin verificar el efecto. No hay umbrales numéricos de aprobación establecidos: se fijarán metas técnicas antes de la evaluación final y se reportarán los incumplimientos.
