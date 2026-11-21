# Ensayo de banco con ESP32 y video del celular

Pruebas realizadas el 20-11-2026. La configuración acordada usa el celular como fuente de video, FaceNexus en Windows para procesarlo y el ESP-WROOM-32 conectado por USB serie. La TMCAM 8305 queda disponible para desarrollo y adquisición de datos.

## Identificación y preparación de la placa

Windows 11 reconoció el puente Silicon Labs CP210x en COM5. El cargador de arranque identificó un ESP32-D0WD-V3 revisión 3.1 con 4 MiB de memoria flash. Antes de grabar el firmware, se respaldó la memoria original en VeraCrypt. La lectura continua falló y la lectura por bloques a 115200 baudios permitió completar el respaldo y verificarlo contra el resumen calculado por la placa.

El firmware de banco se compiló con Arduino CLI 1.5.1 y Arduino-ESP32 2.0.17. Se grabó en modo ROM y esptool verificó los datos escritos. El firmware valida tramas y devuelve el identificador del intento en su acuse. El SG90 permaneció desconectado.

## Resultados

| Prueba | Resultado observado |
| --- | --- |
| Protocolo en escritorio | 11 respuestas esperadas. |
| Protocolo por COM5 | 11 de 11 tramas en cada una de dos rondas. Incluyeron denegaciones, entradas inválidas y recuperación tras un desbordamiento. |
| MJPEG sintético | Cinco fotogramas de 320 × 240. YuNet informó `NO_FACE` y el ESP32 confirmó `UNKNOWN DENIED SIMULATED`. |
| Fuente de video inaccesible | `STREAM_UNAVAILABLE`, código de salida 2 y denegación confirmada por el ESP32. |
| Celular real en la red local | Dos rondas de cinco fotogramas de 1920 × 1080. YuNet informó `NO_FACE` y COM5 confirmó la denegación con el identificador esperado en 2 de 2 rondas. |

El acuse confirma que la placa recibió y validó una decisión de banco. La identificación y el rechazo se ensayan en el [informe 12](12_hog_rejection_calibration.md). La apertura y el retorno del pestillo requieren el ensayo físico con el SG90. [Procedimiento y comandos de integración](../hardware_protocol.md#ensayo-de-banco-del-protocolo-facenexus)
