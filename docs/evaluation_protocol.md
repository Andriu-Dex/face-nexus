# Protocolo de evaluación

## Diseño previo

Antes del entrenamiento principal, congelar manifiesto de particiones, representación, versiones, semillas, espacio de búsqueda y presupuesto por clasificador. Comparar k-NN, MLP y SVM lineal multiclase con las mismas muestras y características HOG. Documentar las transformaciones y ajustarlas solo en el tramo de entrenamiento.

El experimento de identidad usa S01 para TRAIN y R01 para VALIDATION exploratoria de conocidos. Para calibrar el rechazo de desconocidos, usar un grupo A grabado con el celular. El ensayo final usa el modelo congelado, la cámara del celular y un grupo B de desconocidos distintos. Contar intentos completos. Si se ensaya una quinta clase «otros», sus imágenes de entrenamiento deben estar separadas de los grupos A y B.

En un experimento aparte estudiar características propias de procesamiento de imágenes y, si corresponde, representación preentrenada y concatenación. Declarar dimensiones, escalas y coste; no atribuir al clasificador una mejora producida por cambiar el extractor.

Elegir hiperparámetros y modelo con TRAIN/VALIDATION. Si se utiliza validación cruzada, agrupar por sesión y verificar presencia de clases; no usar folds aleatorios de fotogramas. Registrar advertencias de convergencia y candidatos fallidos.

## Identificación cerrada

Desde la aclaración del 19-11-2026, evaluar por separado el clasificador humano/no humano con ejemplos positivos y negativos y la identificación de los cuatro integrantes con muestras conocidas. En la entrega, reportar la exactitud de los candidatos y justificar el modelo elegido. El mismo conjunto de evaluación se aplica a los candidatos de cada tarea.

Para cada modelo reportar exactitud, precisión/recall/F1 por identidad, macro-F1 y matriz 4×4 con ejes y soportes. Mostrar TRAIN y VALIDATION diferenciados y TEST al final. Esta evaluación mide la clasificación candidata de conocidos antes del rechazo.

## Rechazo y autorización

Definir scores por modelo y calibrarlos sin TEST. Un score alto o una softmax no garantizan que un rostro pertenezca al conjunto conocido. Documentar fórmula de distancia/similitud cuando se use, normalización, umbrales y condiciones de aceptación. Si se usa coseno: `s(x,y) = (x·y)/(||x|| ||y||)`; rechazar vectores de norma cero. Su uso no está decidido.

Para SVM y MLP con HOG se ensaya la diferencia entre las dos puntuaciones más altas. La revisión por fotograma de R01 sirve de diagnóstico. Para estimar el umbral se usan presentaciones en vivo del grupo A y de los integrantes con el mismo celular y la misma regla por intento. [Procedimiento de calibración](reports/12_hog_rejection_calibration.md)

Reportar por separado:

| Medida | Numerador / denominador |
| --- | --- |
| Aceptación de desconocidos | Intentos desconocidos aceptados como alguna identidad / intentos desconocidos válidos |
| Rechazo indebido de identidad | Intentos conocidos devueltos como UNKNOWN / intentos conocidos válidos |
| Identificación incorrecta aceptada | Intentos conocidos aceptados con otra identidad / intentos conocidos válidos |
| Autorización indebida de desconocidos | Intentos desconocidos con GRANTED / todos los intentos desconocidos |
| Denegación a autorizados | Intentos de personas con permiso activo con DENIED / todos sus intentos |

Distinguir identificación y acceso: reconocer correctamente a alguien sin permiso exige DENIED. Añadir tabla de resultados con columna UNKNOWN para las cuatro identidades y desconocidos. Contabilizar fallos de captura/detección en la evaluación de extremo a extremo, aunque se excluyan justificadamente de la clasificación condicionada a rostro válido.

Definir un intento como una presentación delimitada con inicio, fin y una decisión final. Fijar antes de medir su duración máxima, regla temporal y separación entre intentos. No tratar fotogramas consecutivos como ensayos independientes. Reportar cantidades, denominadores y resultados por sesión; si se calculan intervalos, respetar el agrupamiento. Cero errores observados no demuestra riesgo cero.

## Rendimiento y pruebas prácticas

Medir entrenamiento, inferencia del clasificador, pipeline de reconocimiento y tiempo hasta confirmación física por separado. Usar reloj monotónico; indicar equipo, cámara, resolución, versiones, calentamiento, cantidad de ensayos, mediana y p95. Reportar FPS procesados y descartes de fotogramas, no solo FPS de visualización.

Probar identidad con permiso, sin permiso, desconocido, ausencia/multiplicidad de rostros, condiciones nuevas, fallo de cámara/modelo, revocación, desconexión y repetición de órdenes. Ensayar presentaciones mediante fotografía/vídeo con consentimiento y describir resultados; si falta detección de vida, declarar la vulnerabilidad. No inferir seguridad física de la accuracy.

El responsable aprobó un ensayo en vivo con el modelo y la política congelados. Registrar un resultado por intento, con recuentos de aciertos, rechazos correctos, rechazos indebidos e identificaciones incorrectas. Para el nodo IoT, registrar también si la acción esperada se observó físicamente.

## Selección y evidencia

Antes de TEST definir metas de rechazo, calidad y latencia a partir del piloto y del dispositivo. La selección prioriza el riesgo de autorización indebida y considera macro-F1, rechazos y coste. Si ningún candidato cumple las metas, registrar el incumplimiento.

Congelar el modelo y la política elegidos antes de TEST. Evaluar también candidatos congelados para la comparación final sin cambiar retrospectivamente al ganador. Cualquier ajuste tras examinar TEST requiere declarar ese conjunto consumido y obtener nueva evaluación independiente.

Guardar configuración, versiones/hashes, cantidades por partición, métricas, matrices, tiempos, limitaciones y decisión justificada. Solo publicar reportes agregados revisados. Resultados por muestra y modelos personalizados quedan privados. Los primeros resultados corresponden a la validación exploratoria de identidades conocidas. [Comparación con HOG](reports/11_hog_classifier_comparison.md)
