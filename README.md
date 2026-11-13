# FaceNexus

Proyecto académico de reconocimiento facial y control de acceso físico. Identificará cuatro personas registradas, rechazará desconocidos y comparará SVM, Random Forest, k-NN y ANN/MLP con las mismas particiones y representación de entrada.

**Estado:** preparación documental. No hay implementación, modelos entrenados, resultados medidos ni hardware verificado. La entrega final requiere un dispositivo físico; una simulación solo permite avanzar durante el desarrollo.

## Documentación

1. [Requisitos y criterios de aceptación](docs/requirements.md).
2. [Análisis y trazabilidad de la fuente](docs/source_analysis.md).
3. [Arquitectura propuesta](docs/architecture.md).
4. [Protocolo de datos](docs/data_protocol.md).
5. [Protocolo de evaluación](docs/evaluation_protocol.md).
6. [Integración física](docs/hardware_protocol.md).
7. [Plan de implementación](docs/implementation_plan.md).
8. [Decisiones y asuntos pendientes](docs/decisions.md).

[AGENTS.md](AGENTS.md) orienta el trabajo de agentes. La transcripción original se conserva intacta en el entorno local y se excluye de Git por contener nombres y conversación incidental. La documentación de trazabilidad permite entender los requisitos sin publicar la fuente privada. No se deben versionar imágenes, vectores biométricos ni modelos personalizados.
