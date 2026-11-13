# Revisión profesional previa a implementación

Fecha: 12-11-2026. Alcance: opinión técnica sobre `instruction.md`, contraste con materiales locales y registro de la prioridad expresa de claridad. No se ha iniciado implementación de FaceNexus ni ejecutado los talleres. Las recomendaciones siguientes no son requisitos nuevos del profesor ni cambios ya aprobados al experimento.

## Dictamen

La propuesta mejora la precisión experimental, especialmente en SVM y características. No conviene aceptar literalmente todas sus «correcciones obligatorias»: ese rótulo pertenece a la propuesta del compañero y no sustituye las instrucciones del responsable. Varias condiciones ya estaban resueltas. Mantener la documentación y hacer cambios puntuales es adecuado.

| Observación | Criterio y recomendación |
| --- | --- |
| Acceso desacoplado del dispositivo | Correcto para desarrollar y probar. No sustituye CONF-01: dispositivo físico obligatorio al cierre. La compra no debe bloquear contratos, datos ni experimentos. |
| A: preentrenado; B: propio; C: combinación | Comparación valiosa como decisión del proyecto. Recomiendo un experimento acotado A/B/C, con una representación propia sencilla y justificada. No probar todas las técnicas enumeradas ni convertirlas en requisitos docentes. |
| Combinar características | Es una hipótesis, no una mejora garantizada. Normalizar bloques, declarar dimensiones y fijar sus pesos sin TEST. Un resultado peor también es evidencia útil. |
| Detección, alineación y segmentación como características | Distinguir etapas: localizar y preparar un rostro no produce necesariamente el descriptor usado para identificarlo. Solo contar como característica el valor numérico que realmente entra al clasificador. |
| SVM OvO/OvR | Correcto: cuatro clases implican seis problemas binarios OvO y cuatro OvR. Comparación razonable dentro de SVM, manteniendo representación, kernel y presupuesto comparables. No se puede anticipar un ganador. |
| Árbol de decisión adicional | Está respaldado por el taller MNIST y aporta una referencia fácil de explicar. Recomiendo incluirlo como baseline si el presupuesto lo permite; RF no es un árbol individual. Los cuatro candidatos vigentes se mantienen hasta adoptar la ampliación. |
| CNN posterior | Correcto no exigir entrenamiento de CNN propia. Un extractor preentrenado puede contener una CNN sin convertirla en un quinto clasificador entrenado por el proyecto. |
| Privacidad y Git | Correcto; la transcripción ya está excluida y se conserva intacta. Evitar movimientos innecesarios. `.gitignore` no elimina archivos ya registrados ni detecta información sensible dentro de documentos. |
| Nuevas etiquetas de autoridad | Conservar PROF, CLASE, CONF y PROY evita cambios cosméticos. Marcar propuestas y pendientes en texto sin renombrar todos los identificadores. |
| Todas las métricas y particiones | Mantener. No copiar el reparto de MNIST a ráfagas faciales ni elegir por TEST. |

## Material académico contrastado

Se inspeccionaron los README de las cinco carpetas y secciones de `procesamiento.py`; para Taller 4 se leyó su módulo completo, y para Taller 3 y MNIST se revisaron los bloques de procesamiento y modelos relevantes. Fue una revisión documental y de código seleccionada, no una auditoría completa de todos los informes o cuadernos. No se modificaron los materiales externos ni se copiaron imágenes o nombres personales al proyecto.

| Trabajo local | Evidencia disponible | Aplicación razonable y límite |
| --- | --- | --- |
| Taller 1-ProcesamientoDigitalImagenes-Hoja | RGB, conteo de histogramas y redistribución de intensidades | Explicar intensidades y contraste. Redistribuir colores de un paisaje no demuestra mejor identificación facial. |
| Taller 2-Configuración de histogramas | Histogramas manuales/NumPy, conservación de píxeles y separación entre cálculo e interfaz | Descriptor de histogramas por regiones del rostro como hipótesis simple; el histograma global pierde ubicación espacial. |
| Taller 3-Reduccion-de-una-Imagen | Máscaras, convolución, suavizado, reducción, filtros estadísticos y de frecuencia, Laplaciano | Preparación y experimento controlado de bordes o reducción. No aplicar todos los filtros; podrían eliminar información útil. |
| Taller 4 - Delimitación y extracción de objetos | Binarización global, conectividad de ocho vecinos, área, centroide, caja y recorte | Reutilizar conceptos de regiones y coordenadas. Sus componentes por intensidad no reconocen semánticamente un rostro; área y centroide dependen del encuadre. |
| Taller_APE_MNIST_Arbol_RandomForest_KNN | Árbol, RF y k-NN, normalización de píxeles, métricas y semilla | Apoya esos clasificadores. Sus cantidades e hiperparámetros corresponden a MNIST, no son obligaciones para FaceNexus. |

La ubicación de consulta es la carpeta Deberes indicada por el responsable. Esos trabajos acreditan que se practicaron técnicas, pero sus README no convierten toda afirmación en requisito docente. Por ejemplo, no se trasladará la afirmación del Taller 1 de que tiempo real siempre significa menos de 300 ms: FaceNexus necesita un presupuesto de tiempo definido para su operación concreta.

No se verificó en estos cinco trabajos que LBP, HOG, landmarks o alineación facial especializada se hayan estudiado. Si se proponen, etiquetarlos como técnicas nuevas del proyecto. Tampoco se corroboró ANN con un taller en esa carpeta; su tratamiento sí aparece en la transcripción. CNN figura como tema anunciado.

## Experimento recomendado, aún no adoptado

1. Crear una representación propia pequeña y explicable: por ejemplo, histogramas normalizados en una cuadrícula fija del recorte facial. Fijar tamaño, cuadrícula y bins con TRAIN/VALIDATION. Incorporar bordes solo si hay hipótesis y presupuesto.
2. Comparar A/B/C sobre las mismas muestras con un clasificador de referencia fijado previamente. Usar C como concatenación de bloques escalados y documentar la contribución de cada bloque. No retocar TEST.
3. Seleccionar representación con VALIDATION y comparar los cuatro clasificadores vigentes; considerar árbol como referencia adicional y OvO/OvR como variantes de SVM. Este diseño evita imponer de entrada todas las combinaciones. Su conclusión sobre representaciones queda condicionada al clasificador de referencia; no afirmar que se halló la mejor combinación global.
4. Congelar todo antes de TEST y conservar las variantes que se decida evaluar. Mantener calibración de rechazo, latencias e integración física.

En scikit-learn, `SVC` entrena internamente OvO incluso con `decision_function_shape='ovr'`; ese parámetro cambia la presentación de scores. Un OvR real puede construirse con `OneVsRestClassifier(SVC(...))`. Comparar SVC con LinearSVC introduciría también diferencias de implementación/optimización y posiblemente de kernel; no aislaría únicamente la estrategia multiclase. Fuentes oficiales: [SVC](https://scikit-learn.org/stable/modules/generated/sklearn.svm.SVC.html) y [OneVsRestClassifier](https://scikit-learn.org/stable/modules/generated/sklearn.multiclass.OneVsRestClassifier.html).

## Cambios realizados y pendientes

Se modificaron únicamente AGENTS.md, requirements.md, architecture.md y decisions.md para incorporar CONF-02 y enlazar este informe. Se creó este reporte. No se cambiaron los requisitos experimentales, no se renombraron identificadores y no se eliminó la propuesta local.

Se revisaron además README, análisis de fuente, protocolos de datos/evaluación/hardware, plan, `.gitignore` y estado de Git. Siguen pendientes la adopción del experimento acotado A/B/C, la variante OvR real, el árbol adicional y las decisiones de hardware, datos y herramientas ya registradas. No se afirma ningún resultado de reconocimiento.

## Validación

La revisión del índice de Git encontró únicamente documentación y `.gitignore`; no hay fotos, vectores, pesos ni transcripción registrados. Hay archivos preparados en el índice por el usuario y todavía no existen commits en la rama actual: no se modificó el índice ni se creó un commit. No existe historial local de commits que auditar por filtraciones anteriores; esto no certifica otros repositorios o remotos.

Se comprobaron los enlaces locales de la documentación, los identificadores CONF-01/CONF-02, la exclusión de `instruction.md` y `docs/transcription.md`, y el hash de la transcripción contra el original documentado. El inventario local solo contiene documentación, los dos textos locales excluidos y metadatos de Git. Esta revisión no es un escáner exhaustivo de secretos ni valida un futuro archivo colocado fuera de las carpetas privadas excluidas.

No se ejecutaron pytest ni entrenamiento porque no existe implementación de FaceNexus. No se descargaron pesos, no se conectó hardware y no se publicaron cambios.
