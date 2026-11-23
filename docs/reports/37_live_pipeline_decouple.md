# Pipeline de vivo

22-11-2026. Simulación. T ≈ 0,530 y G ≈ 0,057 sin cambio.

La captura y la inferencia corren fuera de Tkinter. Cada uno lee solo el último fotograma; si llega otro, el anterior se descarta. La vista se pinta aunque la predicción vaya tarde; las cajas se dibujan solo si coinciden con ese fotograma. Detener o reconectar borra la autorización de cámara. Un archivo abierto se marca «Predicción de archivo».

Prueba sintética con inferencia de 120 ms: la vista siguió actualizándose y Detener video respondió. No se comparó el retraso extremo a extremo con la página de IP Webcam. No hubo presentación nueva de K01 en el celular; el rechazo de supervisión no se reconstituyó.

El estado muestra fps de vista, milisegundos de inferencia y edad local al pintar. Eso no es latencia de red.
