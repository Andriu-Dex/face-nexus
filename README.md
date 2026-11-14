# FaceNexus

Proyecto académico de reconocimiento facial y control de acceso físico. Identificará cuatro personas registradas, rechazará desconocidos y comparará SVM, Random Forest, k-NN y ANN/MLP con las mismas particiones y representación de entrada.

**Estado:** preparación del dataset y herramienta de diagnóstico de cámara. No hay reconocimiento implementado ni modelos entrenados; la TMCAM completó diez minutos a 1080p y 29,24 FPS medios; la comprobación de 60 Hz y el fallo de lectura por desconexión en caliente siguen pendientes. La entrega final requiere un dispositivo físico; una simulación solo permite avanzar durante el desarrollo.

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
