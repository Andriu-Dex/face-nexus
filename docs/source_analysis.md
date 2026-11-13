# Análisis de la fuente

## Fuentes y autoridad

Fuente primaria local: `transcription.md`, clase del 12 de noviembre de 2026. Se preserva sin modificaciones. SHA-256 del original: `cee686566206891dd881bca384e6ad10b69d3e0b1c17c20d7e46158d0c40b04e`.

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

## Correcciones respecto del borrador

- Se sustituye `FaceNexus_requirements.md` por `requirements.md` como única especificación vigente.
- Se distingue lo expresado en clase, la aclaración del responsable y las decisiones técnicas del proyecto.
- La apertura física deja de ser una ampliación opcional. El simulador no satisface la aceptación final.
- Cuatro identidades, tiempo real, lista de clasificadores, rechazo y métricas complementarias son alcance del proyecto; no se atribuyen automáticamente al profesor.
- Se exige evidencia de procesamiento de imágenes y un experimento de características propias, evitando que todo se limite a invocar una biblioteca. No se asegura que una concatenación concreta sea obligatoria: se documenta la duda.
- No se exige entrenar una CNN desde cero por el anuncio de una próxima clase sobre CNN.
- No se inventan cantidades mínimas de fotografías, exactitudes, plazos, FPS ni componentes.
- TEST se reserva para evaluación final; observar resultados en TEST no habilita ajustar el sistema y presentar el mismo TEST como independiente.

No se trasladan a la especificación afirmaciones generales de clase como que un algoritmo siempre supera a otro o que igualar errores demuestra por sí solo generalización. Las decisiones se defenderán con experimentos y limitaciones.
