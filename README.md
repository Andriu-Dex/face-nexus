# FaceNexus

Proyecto académico de reconocimiento facial y control de acceso físico. Identificará cuatro personas registradas, rechazará desconocidos y comparará k-NN, MLP y SVM lineal multiclase con características HOG y particiones comunes.

**Estado:** documentación lista para implementar. En la entrega, el celular transmite el video a Windows y FaceNexus envía la decisión por USB serie al ESP-WROOM-32, que acciona el SG90 del pestillo de maqueta. La TMCAM y la extracción de referencia ya se verificaron para desarrollo local.

## Arranque en Windows

Doble clic en `FaceNexus.cmd` o, desde PowerShell en el repositorio, `.\FaceNexus.cmd`. El lanzador usa el Python de `.venv`, abre la interfaz en simulación y espera el volumen `V:\FaceNexus`. Funciona aunque la carpeta de trabajo sea otra. Si falla, monta VeraCrypt o prepara `.venv`. En **Cámara** se indican la IP del celular y el puerto (8080), `IP:puerto` o la URL completa. **Detener video** invalida la decisión de vivo. La captura, la inferencia y la vista van en hilos distintos; el estado muestra fps de vista, milisegundos de inferencia y edad local del fotograma. El puerto serie del pestillo es otro ajuste. La URL efectiva se guarda en `%LOCALAPPDATA%\FaceNexus\operator_camera.json`. Si no se puede guardar, se usa en esa sesión. Los argumentos de `python -m scripts.operator_ui` siguen valiendo para pruebas.

Un mapa opcional `V:\FaceNexus\private\identity_labels.json` muestra el código junto a una etiqueta local. Las claves son solo `K01`–`K04`; el valor es texto. Si falta en el volumen, se puede leer la correspondencia local gitignored del repositorio. Si no hay mapa, se muestra el código. No versionar nombres. Ejemplo de forma (sin nombres reales):

```json
{
  "K01": "etiqueta local",
  "K02": "etiqueta local",
  "K03": "etiqueta local",
  "K04": "etiqueta local"
}
```

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
