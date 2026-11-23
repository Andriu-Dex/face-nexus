# Interfaz y arranque

22-11-2026. Rediseño de `operator_ui` y lanzador `FaceNexus.cmd`. Simulación. Datos sintéticos.

La barra muestra FaceNexus y Simulación. El visor ocupa el área principal; el estado vacío pide abrir una imagen o conectar la cámara. Cámara es el botón principal; Abrir imagen, Probar carpeta y Siguiente presentación quedan al pie del visor. El lateral prioriza la decisión (texto y color), la identidad con código y etiqueta privada, los permisos y un historial con desplazamiento. El puerto y el acuse distinguen simulación de movimiento físico.

La URL del IP Webcam y la orientación se configuran en Cámara. Un mapa opcional `V:\FaceNexus\private\identity_labels.json` usa claves `K01`–`K04` y no se versiona; si falta, se muestra el código.

Si la cámara falla después de un Autorizado, la decisión pasa a Señal perdida, el fotograma se marca como anterior y el rearme sigue a `PresentationGate.note_fault`. Abrir una imagen retiene ese resumen hasta que el operador vuelve a conectar la cámara.

`FaceNexus.cmd` localiza el repositorio, usa `.venv` y `V:\FaceNexus`, y no pasa puerto serie. Si falta el volumen o el entorno, el mensaje lo indica.
