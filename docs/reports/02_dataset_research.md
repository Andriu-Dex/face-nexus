# Investigación y selección de datos — FaceNexus

Fecha de consulta: 13-11-2026. Investigación documental, sin descarga de imágenes, datasets ni pesos, sin entrenamiento y sin mediciones propias. Se consultaron páginas, publicaciones y metadatos textuales; el puntero Git LFS de SFace no es el modelo binario.

## Recomendación ejecutiva

La base será una colección privada de las cuatro identidades y de voluntarios desconocidos capturados en condiciones de uso. Los datasets públicos no sustituyen esas personas ni las pruebas con nuestra cámara. No entrenaremos un extractor desde cero en esta fase.

Priorizar SFace como primer candidato a validar técnicamente, por su integración documentada con OpenCV y su licencia de carpeta explícita; InsightFace queda como alternativa de investigación. Ninguno está seleccionado definitivamente: falta comprobar el artefacto y su funcionamiento en el equipo. No descargar ahora los siete datasets. Reservar una eventual evaluación pública pequeña para una pregunta concreta y después de verificar sus condiciones.

Las valoraciones siguientes son criterio PROY, no resultados experimentales. «Página accesible» no significa «descarga comprobada». No se abrieron los archivos de imágenes para comprobar disponibilidad o tamaño; los valores ausentes se declaran pendientes en lugar de estimarlos.

## Siete candidatos únicos

WIDER FACE estaba duplicado en la propuesta local. Funciones: A = entrenar extractor; B = clasificar nuestras cuatro identidades; C = verificación por pares; D = rechazo abierto bajo un protocolo propio; E = detección; F = robustez. Ninguno aporta B sin nuestras capturas. C no equivale a D ni a apertura física.

| Dataset y origen | Escala / anotaciones verificadas | Función y valor para FaceNexus | Acceso, formato y coste de adquisición | Decisión |
| --- | --- | --- | --- | --- |
| Glint360K — proyecto InsightFace, asociado al trabajo Partial FC de An y colaboradores | 17.091.657 imágenes; 360.232 identidades | A; gran escala sin necesidad actual de reentrenar extractor | README accesible; enlaces Baidu/magnet publicados, no probados; RecordIO train.rec/train.idx y fragmentos de archivo; bytes totales no comprobados | No descargar: coste y procesamiento desproporcionados para cuatro clases [G] |
| DigiFace-1M — Bae y colaboradores, Microsoft, WACV 2023 | 1.220.000 imágenes sintéticas; 110.000 identidades, sumando dos grupos documentados | A/F; prueba sintética complementaria, no sustituto de desconocidos reales | Página accesible; ocho partes enlazadas no descargadas; carpetas por sujeto y PNG; bytes no comprobados | No descargar inicialmente; brecha entre imágenes sintéticas y cámara [D] |
| WIDER FACE — Yang, Luo, Loy y Tang, CUHK, CVPR 2016 | 32.203 imágenes y 393.703 caras; cajas y atributos, no catálogo de identidades | E/F; útil si se decide auditar detección en escenas difíciles | Ficha CUHK-CSE accesible; sitio del proyecto agotó tiempo; imágenes y anotaciones por partición; bytes no comprobados | Reserva para detección; no usar como conjunto de identidades desconocidas disjuntas [W] |
| CPLFW — Zheng y Deng, BUPT, informe de 2018 | Pares de igual/distinta identidad enfatizando cambios de pose; reutiliza identidades de LFW. Totales de imágenes/identidades no confirmados en el acceso disponible | C/F; útil solo para una pregunta sobre pose | Página y PDF devolvieron 502 al abrir; resumen indexado del PDF recuperable. Estructura exacta, bytes y descarga pendientes | No descargar: acceso y condiciones sin verificar [P] |
| LFW — Huang, Ramesh, Berg y Learned-Miller, UMass, 2007/2008 | 13.233 imágenes; 5.749 identidades, recogidas de la web | C/F; D solo con selección y protocolo propios, sin llamarlo evaluación LFW oficial | Sitio original no accesible desde la herramienta; publicación disponible. Loader mantenido por scikit-learn describe JPEG y archivos de pares; indica más de 200 MB para el conjunto. No se probó descarga | Reserva condicionada para comparación histórica; no base operativa [L] |
| CFP, protocolo CFP-FP — Sengupta y colaboradores, UMD/Rutgers, WACV 2016 | 500 personas, 10 fotos frontales y 4 de perfil por persona: 7.000 imágenes; pares FF/FP | C/F; estudia perfiles extremos | Sitio CFP devolvió 502; artículo de autores disponible. Archivo de imágenes, estructura y bytes no comprobados | Reserva si interesa pose extrema y se resuelve acceso/licencia [C] |
| VGGFace2 — Cao y colaboradores, Oxford VGG, FG 2018 | 3,31 millones de imágenes; 9.131 personas; identidad, cajas y cinco puntos estimados | A/F; no necesario para entrenar nuestras cuatro clases | Oxford informa que ya no ofrece enlaces de descarga; recortes y metadatos descritos, bytes actuales no verificables | No descargar ni buscar mirrors como sustituto automático del origen [V] |

El enlace propuesto `wider_face_split.zip` corresponde a la separación/anotaciones; no debe asumirse que contiene el conjunto de imágenes. Su contenido y bytes no se inspeccionaron en esta fase.

La diversidad descrita por los autores no garantiza cobertura de nuestro entorno: Glint es web a gran escala; DigiFace varía condiciones sintéticas; WIDER enfatiza escala/pose/oclusión; CPLFW y CFP enfatizan pose; LFW contiene condiciones web no controladas; VGGFace2 enfatiza pose y edad. Ninguno valida por sí solo cámara, autorización o seguridad del montaje.

## Condiciones de uso y publicación

Esta es una lectura de condiciones publicadas para tomar decisiones del proyecto, no una autorización adicional. Un repositorio público con código y tablas agregadas es distinto de redistribuir imágenes o pesos.

| Fuente | Condición encontrada | Consecuencia operativa |
| --- | --- | --- |
| Glint360K | README limita datos y modelos derivados a investigación no comercial [G] | No asumir permiso de redistribución por la licencia del código; conservar fuera de Git |
| DigiFace | R-UDA v1.0: investigación computacional no comercial; redistribución condicionada a atribución y vincular al receptor a los términos; restricciones alcanzan usos comerciales de resultados [DL] | No incorporar a una oferta comercial; no publicar datos en este proyecto |
| WIDER | Ficha CUHK-CSE declara CC BY-NC-ND 4.0 [W] | Revisar términos originales antes de cualquier incorporación; no publicar recortes o derivados suponiendo permiso automático |
| CPLFW / CFP | No se verificó licencia actual de los archivos de datos | Bloqueados para adquisición hasta aclararla; la licencia o copyright del artículo no autoriza el dataset |
| LFW | No se verificó autorización vigente de redistribución de las fotografías | Accesibilidad mediante un loader no resuelve derechos; no descargar hasta revisar condiciones concretas |
| VGGFace2 | Descarga oficial retirada; condiciones actuales del archivo no verificadas | No usar mirrors como si acreditaran procedencia o permiso |

## Extractores: profundización útil

### SFace de OpenCV Zoo — candidato preferente para el piloto

El proveedor identifica un MobileFaceNet entrenado con la pérdida SFace y publica ONNX, demo Python y alineación de cinco landmarks [S]. La carpeta declara Apache 2.0 para todos sus archivos; se revisó también su LICENSE [SL]. El archivo FP32 `face_recognition_sface_2021dec.onnx` tiene un puntero LFS con 38.696.353 bytes y SHA-256 publicado `0ba9fbfa01b5270c96627c4ef784da859931e02f04419c829e83484087c34e79` [SP]. Esto es metadata del proveedor, no un hash calculado sobre un peso descargado.

El código de OpenCV alinea y prepara una entrada 112×112 [SC]. La dimensión de salida se debe verificar en el grafo y en una ejecución del artefacto antes de fijar el contrato; no se inspeccionaron pesos. El artículo/proyecto original experimenta con CASIA-WebFace, VGGFace2 y MS-Celeb-1M, pero la fuente consultada no identifica inequívocamente cuál produjo este ONNX [SO]. Registrar esa limitación; no atribuirle un dataset exacto por conjetura.

YuNet es el detector empleado en la demo, no el extractor. Su versión y licencia requieren registro separado. Probar CPU antes de considerar aceleración; no hay todavía medidas de RAM, FPS o latencia en nuestro equipo. Los umbrales y aciertos del tutorial de OpenCV son de benchmarks, no resultados ni umbrales adoptados para FaceNexus [OT].

### InsightFace / ArcFace — alternativa

InsightFace es un proyecto y ArcFace una función de pérdida, no un archivo único de pesos. El model zoo distingue, por ejemplo, antelopev2 (ResNet100/Glint360K) y buffalo_l (ResNet50/WebFace600K), y publica paquetes de 407 MB y 326 MB respectivamente; son tamaños del paquete, no solo del extractor [IZ]. Python/ONNX Runtime permite inferencia; la arquitectura iResNet consultada usa por defecto 512 características, sin que esto certifique todo paquete [IC].

El código se declara MIT, mientras datos y pesos publicados se limitan a investigación no comercial; el README también remite a contacto para licencias de modelos de reconocimiento [I]. No redistribuirlos como si fueran MIT. Si se adopta, elegir un paquete y versión explícitos, revisar condiciones y registrar solo módulos necesarios. No activar descargas automáticas ni estimación de edad/género o detección de vida por conveniencia.

No añadir un tercer extractor ahora: no se identificó una carencia que justifique más dependencias y experimentos. La selección final depende de licencia concreta, trazabilidad y piloto, no de la mayor cifra publicada en un benchmark.

## Independencia de evaluación

Separar dos problemas: nuestros clasificadores no ven TEST, pero el extractor puede haber visto identidades públicas durante su entrenamiento. LFW/CPLFW comparten identidades; conjuntos con nombres distintos no son automáticamente independientes. Si se usan dos fuentes públicas, comprobar solapamientos de personas y duplicados entre ambas. Si no se puede verificar el entrenamiento del extractor, declarar «independencia del extractor no demostrada» y no afirmar evaluación completamente inédita.

Los desconocidos locales tendrán dos grupos de personas disjuntas para VALIDATION y TEST. No convertirlos por defecto en una quinta clase. Las pruebas de pares de un benchmark mantienen su protocolo si se informa un resultado oficial; cualquier selección para rechazo se presenta como experimento propio.

## Tres configuraciones

| Configuración | Datos y modelos propuestos | Qué se obtiene / límite |
| --- | --- | --- |
| Mínima | Capturas propias de cuatro personas y voluntarios desconocidos; representación propia; detector revisado cuando toque implementarlo | Evaluar clases y rechazo local; no cubre todavía comparación con embeddings |
| Recomendada | Mínima más un extractor preentrenado trazable, comenzando la revisión técnica por SFace | Comparar A/B/C sin adquirir grandes datasets; es la ruta recomendada para el proyecto completo |
| Ampliada | Recomendada más un benchmark de pose o detección elegido por una pregunta concreta, con licencia y acceso resueltos | Evidencia complementaria de robustez; no sustituye evaluación local ni acción física |

La configuración mínima es un arranque, no la aceptación final. No descargar Glint/DigiFace/VGGFace2, no combinar todos los datasets y no adquirir todavía LFW/CFP/CPLFW/WIDER. En una fase posterior, descargar solo el detector y extractor concretos que superen la revisión; esta investigación no los instala.

## Registro de fuentes y adopción

| ID | Estado actual | Uso autorizado por el plan | Artefacto/versionado pendiente |
| --- | --- | --- | --- |
| LOCAL-K | Planificado, sin capturas | Cuatro identidades; TRAIN/VALIDATION/TEST por sesión | Consentimiento, equipo, manifiesto privado y hashes |
| LOCAL-U | Planificado, sin capturas | Desconocidos locales disjuntos VALIDATION/TEST | Voluntarios, consentimiento y grupos privados |
| PUBLIC-G/D/W/P/L/C/V | Investigados; ninguno adquirido ni adoptado | Referencia documental | Versión, condiciones y checksum si se decide adquirir uno |
| MODEL-S | Candidato preferente, no adquirido | Piloto posterior de embeddings | Commit del proveedor, licencia conservada, hash local y salida verificada |
| MODEL-I | Alternativa, no adquirido | Ninguna ejecución actual | Paquete exacto, condiciones y hash |

Este registro es público y describe fuentes. El inventario de personas, imágenes, rutas y autorizaciones permanece privado. Revalidar URL, versión y licencia en la adquisición: las referencias a ramas main/master son móviles, no versiones congeladas.

## Fuentes consultadas

- [G: Partial FC / Glint360K, README del proveedor](https://raw.githubusercontent.com/deepinsight/insightface/master/recognition/partial_fc/README.md).
- [D: DigiFace-1M, datos y publicación original enlazada](https://github.com/microsoft/DigiFace1M); [DL: R-UDA](https://raw.githubusercontent.com/microsoft/DigiFace1M/main/LICENSE).
- [W: ficha CUHK-CSE WIDER FACE](https://huggingface.co/datasets/CUHK-CSE/wider_face); [publicación de los autores](https://arxiv.org/abs/1511.06523).
- [P: CPLFW, publicación de Zheng y Deng](https://www.whdeng.cn/CPLFW/Cross-Pose-LFW.pdf), resumen indexado consultado; apertura directa fallida.
- [L: publicación LFW de los autores](https://people.cs.umass.edu/~elm/papers/Huang_eccv2008-lfw.pdf); [loader de scikit-learn](https://scikit-learn.org/stable/datasets/real_world.html#the-labeled-faces-in-the-wild-face-recognition-dataset).
- [C: CFP, artículo de los autores](https://engineering.jhu.edu/vpatel36/wp-content/uploads/2018/08/WACV2016_CFP.pdf).
- [V: página Oxford con aviso de retirada](https://www.robots.ox.ac.uk/~vgg/data/vgg_face2/); [publicación VGGFace2](https://arxiv.org/abs/1710.08092).
- [S: SFace OpenCV Zoo](https://raw.githubusercontent.com/opencv/opencv_zoo/main/models/face_recognition_sface/README.md); [SL: licencia de carpeta](https://raw.githubusercontent.com/opencv/opencv_zoo/main/models/face_recognition_sface/LICENSE); [SP: puntero LFS](https://raw.githubusercontent.com/opencv/opencv_zoo/main/models/face_recognition_sface/face_recognition_sface_2021dec.onnx).
- [SC: implementación OpenCV](https://raw.githubusercontent.com/opencv/opencv/4.x/modules/objdetect/src/face_recognize.cpp); [SO: proyecto original SFace](https://raw.githubusercontent.com/zhongyy/SFace/master/README.md); [OT: tutorial OpenCV](https://docs.opencv.org/4.x/d0/dd4/tutorial_dnn_face.html).
- [I: licencia y alcance InsightFace](https://github.com/deepinsight/insightface); [IZ: model zoo](https://raw.githubusercontent.com/deepinsight/insightface/master/model_zoo/README.md); [IC: definición iResNet](https://raw.githubusercontent.com/deepinsight/insightface/master/recognition/arcface_torch/backbones/iresnet.py).

## Cierre de investigación

La selección operativa de datos propios queda definida; el extractor y las cifras de captura son recomendaciones ajustables tras piloto. Falta concretar cámara/equipo, voluntarios, custodia y conservación antes de capturar. No se midió suficiencia, calidad, rendimiento ni apertura física. La selección del dispositivo sigue pendiente y su integración es obligatoria. Ver [protocolo operativo de datos](../data_protocol.md) y [plan de fases](../implementation_plan.md).

## Comprobaciones documentales ejecutadas

Se verificaron enlaces relativos y `git diff --check`; se corrigió en decisions.md la referencia al informe previo, que ahora se llama `01_preimplementation_review.md`. Se comprobó mediante rutas sintéticas que `.gitignore` excluye data, private, models, instruction.md y la ruta prevista de la transcripción. No se crearon archivos biométricos de prueba.

El índice de Git contiene documentación y `.gitignore`, sin imágenes, modelos ni transcripción. En el árbol local actual no existe `docs/transcription.md`; no se modificó ni se recreó y no fue posible recalcular su hash. El hash de referencia de source_analysis.md procede de la revisión anterior, no de una verificación actual.

La investigación leyó páginas y metadatos del proveedor sin descargar recursos binarios. No se ejecutaron pruebas del sistema ni auditoría de un dataset inexistente. Solo se modificaron README, data_protocol.md, implementation_plan.md y decisions.md y se creó este informe. No se alteró el índice de Git, no se creó commit y no se publicaron cambios.
