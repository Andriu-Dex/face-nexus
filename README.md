# FaceNexus

Proyecto académico de reconocimiento facial y control de acceso físico. Identificará cuatro personas registradas, rechazará desconocidos y comparará k-NN, MLP y SVM lineal multiclase con características HOG y particiones comunes.

**Estado:** documentación lista para implementar. En la entrega, el celular transmite el video a Windows y FaceNexus envía la decisión por USB serie al ESP-WROOM-32, que acciona el SG90 del pestillo de maqueta. La TMCAM y la extracción de referencia ya se verificaron para desarrollo local.

## Documentación

1. [Requisitos y criterios de aceptación](docs/requirements.md).
2. [Análisis y trazabilidad de la fuente](docs/source_analysis.md).
3. [Arquitectura propuesta](docs/architecture.md).
4. [Protocolo de datos](docs/data_protocol.md).
5. [Protocolo de evaluación](docs/evaluation_protocol.md).
6. [Integración física](docs/hardware_protocol.md).
7. [Plan de implementación](docs/implementation_plan.md).
8. [Decisiones y asuntos pendientes](docs/decisions.md).
9. [Investigación y selección de datasets](docs/reports/02_dataset_research.md).

[AGENTS.md](AGENTS.md) orienta el trabajo de agentes. La transcripción original se conserva intacta en el entorno local y se excluye de Git por contener nombres y conversación incidental. La documentación de trazabilidad permite entender los requisitos sin publicar la fuente privada. No se deben versionar imágenes, vectores biométricos ni modelos personalizados.


## Diagnóstico inicial

Ver [instrucciones de instalación y prueba de la TMCAM](docs/camera_diagnostic.md). El script no guarda imágenes ni abre ninguna cámara al ejecutar pruebas automatizadas.


## Preparación del piloto

La cámara es apta para el piloto con las condiciones medidas. La [ficha de captura](docs/data_protocol.md#ficha-operativa-del-piloto--propuesta-del-14-11-2026) fue aceptada para el piloto y el custodio declara consentimiento de los cuatro. La captura manual y su auditoría estructural pasaron pruebas sintéticas; ver la [guía de captura](docs/pilot_capture.md). El estado de capturas reales se registra por separado. La [revisión de detector y extractor](docs/model_verification.md) es documental, sin pesos descargados. Ver [cierre y pendientes de esta fase](docs/reports/04_pilot_preparation.md).


## Datos externos de desarrollo

El [informe 06](docs/reports/06_external_frames.md) registra 11.413 fotogramas auditados. Los segmentos históricos se agrupan en S01 por identidad. El responsable confirmó que R01 se grabó otro día. El experimento usará S01 para entrenar y R01 para validar entre encuentros.


## Primera validación facial

[Informe 07](docs/reports/07_face_pipeline_validation.md): YuNet/SFace con pesos y licencias verificados, 73/80 embeddings válidos y siete casos sin detección preservados. Revisión visual local y exploración de similitud realizadas; hay solapamiento y no se estableció un umbral. No son resultados finales de reconocimiento o acceso.
