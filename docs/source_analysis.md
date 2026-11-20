# Análisis de la fuente

## Fuentes y autoridad

Fuentes locales preservadas: `docs/transcriptions/transcription_12-11-2026.md` y `docs/transcriptions/transcription_19-11-2026.md`. Las referencias por línea de la tabla corresponden a la primera clase. La segunda se cita por marcas de tiempo.

Las referencias siguientes usan líneas del original. La transcripción contiene errores de reconocimiento, fragmentos incompletos, ejemplos y asuntos ajenos al proyecto; no es una especificación literal ni una fuente fiable de fórmulas. La aclaración posterior del responsable exige dispositivo físico aunque la clase mencione también una aplicación.

## Trazabilidad

| Referencia local | Lectura sustentada | Tratamiento |
| --- | --- | --- |
| Líneas 60–106 | Cadena modular de adquisición, preprocesamiento, características, clasificación y postprocesamiento; datos propios y posibilidad de datasets | PROF-02 y CLASE-01 |
| Líneas 139–159 | Reconocer personas elegidas y otorgar permisos de acceso | PROF-01 |
| Líneas 216–263 | Entrenamiento, validación, test y generalización | CLASE-02; protocolo operativo PROY |
| Líneas 768–798 | Probar modelos, mostrar exactitudes y pruebas, justificar la elección y abrir un elemento | PROF-01 y PROF-03 |
| Líneas 777–781 y 820–822 | Se mencionan tres o cuatro personas, con formulación inconsistente | Cuatro identidades como alcance PROY, no cifra docente inequívoca |
| Líneas 800–818 | Permite bibliotecas; enfatiza añadir conocimientos propios sobre características de imagen | PROF-04; alcance exacto de concatenación pendiente de confirmar |
| Líneas 824–837 | Variaciones de posición y pruebas prácticas; el ejemplo de dígitos pertenece a MNIST | CLASE; no trasladar cifras del ejemplo al reconocimiento facial |
| Líneas 846–920 | Reducción, filtros, PCA y extracción aprendida | CLASE; alternativas a justificar, no obligación de aplicar todas |
| Aclaración del responsable en este chat, 12-11-2026 | El dispositivo físico es obligatorio | CONF-01, condición de entrega final |

## Aclaraciones de la clase del 19 de noviembre

| Minuto | Lectura y efecto |
| --- | --- |
| 0:00–1:19, 2:20–2:38 | Espera varias personas en cuadro y que baste reconocer a una de las que pueden activar una acción. Probar entradas y salidas del cuadro y casos mixtos. Los colores y gestos son ejemplos. |
| 1:39–2:38, 9:59–10:04 | La salida física es flexible. Una tira LED es una opción aceptada. Los efectos por identidad son opcionales. |
| 8:28–9:59 | El nodo IoT captura y envía la imagen a la computadora. La computadora procesa y devuelve una etiqueta. El nodo ejecuta una acción según la respuesta. ESP32 con cámara es un ejemplo explícito. |
| 10:41–14:40, 19:09–19:54 | Separar la clasificación humano/no humano del reconocimiento de integrantes. Combinar datos generales con los propios según la tarea. Las cuatro identidades registradas pueden seguir siendo las mismas. Incorporar ejemplos negativos al clasificador humano/no humano. |
| 14:54–16:17, 17:51–19:06 | Autoriza pesos preentrenados para recorte. Pide construir y entrenar los modelos que se presentan y permite TensorFlow/Keras para definir la arquitectura. La respuesta distingue esa opción de invocar estimadores de scikit-learn ya hechos. SFace y las pruebas actuales quedan como referencia técnica; la opción conservadora para entrega es construir la representación y entrenar los modelos propios. |
| 16:17–17:51 | Comparar modelos y reportar exactitud en el informe. Demostrar un modelo seleccionado y describir la interfaz en el informe. |
| 4:09–4:51, 6:27 | Anuncia revisión del proyecto el jueves siguiente. Tomando la fecha del archivo, la referencia corresponde al 26-11-2026. |

## Correcciones respecto del borrador

- Se sustituye `FaceNexus_requirements.md` por `requirements.md` como única especificación vigente.
- Se distingue lo expresado en clase, la aclaración del responsable y las decisiones técnicas del proyecto.
- La apertura física deja de ser una ampliación opcional. El simulador no satisface la aceptación final.
- Cuatro identidades, tiempo real, lista de clasificadores, rechazo y métricas complementarias son alcance del proyecto; no se atribuyen automáticamente al profesor.
- Se exige evidencia de procesamiento de imágenes y un experimento de características propias, evitando que todo se limite a invocar una biblioteca. No se asegura que una concatenación concreta sea obligatoria: se documenta la duda.
- La CNN es una familia posible. Si se presenta una, la clase del 19 pide construirla y entrenarla.
- No se inventan cantidades mínimas de fotografías, exactitudes, plazos, FPS ni componentes.
- TEST se reserva para evaluación final; observar resultados en TEST no habilita ajustar el sistema y presentar el mismo TEST como independiente.

No se trasladan a la especificación afirmaciones generales de clase como que un algoritmo siempre supera a otro o que igualar errores demuestra por sí solo generalización. Las decisiones se defenderán con experimentos y limitaciones.
