# Protocolo de datos

## Captura y custodia

Obtener autorización de cada participante antes de capturar. Documentar propósito, acceso, almacenamiento local, conservación y procedimiento de retiro; no guardar consentimientos con nombres en Git. Emplear IDs seudónimos y mantener la correspondencia identificativa en almacenamiento privado.

Capturar las cuatro identidades en sesiones independientes con variación real de iluminación, distancia, posición y orientación moderada. Revisar etiquetas, archivos ilegibles, duplicados, ausencia de rostro, oclusión y rostros múltiples. Registrar exclusiones con motivo y cantidades; no descartar fallos difíciles solo para mejorar resultados.

Se propone al menos una sesión independiente por identidad para cada partición como punto de partida técnico, no como suficiencia estadística ni exigencia docente. La cantidad final de sesiones e imágenes se definirá tras un piloto y se congelará antes del experimento principal.

## Manifiesto privado

Cada muestra tendrá `sample_id`, `person_id`, `session_id`, fuente, fecha de captura, condiciones, ruta privada, hash del archivo, partición y estado de calidad. No se publican rutas identificativas, imágenes, embeddings ni este manifiesto personalizado. En Git solo se conservan esquemas y ejemplos sintéticos.

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
