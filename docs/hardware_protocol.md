# Protocolo de integración física

## Condición de entrega

El responsable confirmó la configuración de entrega (CONF-04). El celular captura y envía video a Windows por una red local. FaceNexus devuelve la etiqueta y la decisión por USB serie al ESP-WROOM-32, que controla el SG90 del pestillo de maqueta. La TMCAM queda disponible para desarrollo local. Verificar en banco el acceso al stream desde Windows, el puerto serie, la alimentación externa del servo, la variante del SG90 y el esfuerzo del pestillo.

## Selección antes de comprar o conectar

Registrar elemento a abrir, controlador, actuador, alimentación, tensiones/corrientes, aislamiento necesario, interfaz, sensores disponibles, mecanismo de cierre y forma de parada o desconexión. Revisar especificaciones reales de los componentes elegidos. No fijar un cableado genérico ni energizar una carga sin conocer sus requisitos.

La lógica de autorización falla cerrada. El estado mecánico seguro y cualquier necesidad de salida de emergencia se definen para el montaje concreto; DENIED en software no demuestra que un mecanismo permanezca cerrado tras perder alimentación.

## Contrato de órdenes

Cada orden se asocia a un evento autorizado, con caducidad, duración acotada y control de repetición. Establecer valores después de elegir el mecanismo y antes de ensayarlo. Permitir solo un estado de ejecución coherente; invalidar pendientes al desconectar. Reconectar no abre ni reproduce órdenes anteriores.

Distinguir orden enviada, recepción confirmada y posición física confirmada. Si no hay sensor de posición, declarar esa limitación y verificar el efecto mediante observación práctica; no presentar un acuse del microcontrolador como prueba de apertura.

## Secuencia y evidencia

1. Probar contrato con controlador simulado y errores inyectados, sin actuador.
2. Revisar montaje y probar comunicación sin carga de apertura.
3. Verificar alimentación y mecanismo en banco supervisado.
4. Recibir en Windows la imagen del celular, reconocer y enviar la etiqueta y la decisión por USB serie al ESP32. Observar la apertura y el retorno del pestillo.
5. Comprobar escenas con varios integrantes y escenas mixtas, así como denegación cuando falte una identidad autorizada, haya un error o caduque la orden.
6. Probar pérdida de comunicación, reinicio y reconexión sin aperturas espontáneas.

Registrar configuración/versiones, caso, resultado esperado, observación real y limitaciones. No se exige grabar rostros como evidencia. No declarar fase completada sin ejecutar el hardware real.

## Verificación USB serie

El 20-11-2026 se conectó la placa ESP-WROOM-32 a Windows 11 mediante un cable USB-A a micro-USB de datos. En las capturas del responsable, el Administrador de dispositivos mostró primero el CP2102 con advertencia y después el controlador Silicon Labs CP210x en **COM5**, sin advertencia. Windows confirmó el mismo nombre y puerto durante la comprobación. COM3 y COM4 correspondían a enlaces Bluetooth.

Con esptool 5.6.0 se ejecutó `python -m esptool --port COM5 --no-stub flash-id`. El cargador de arranque respondió por COM5. Identificó un **ESP32-D0WD-V3, revisión 3.1**, y memoria flash de **4 MB**. La herramienta reinició la placa al terminar. Esta prueba verificó el enlace serie con el cargador de arranque. [Comandos de esptool](https://docs.espressif.com/projects/esptool/en/latest/esp32/esptool/basic-commands.html)

## Ensayo de banco del protocolo FaceNexus

El firmware de banco se compiló con Arduino CLI 1.5.1 y el núcleo Arduino-ESP32 2.0.17 para la placa genérica ESP32. El puerto serie opera a 115200 baudios. `PING` comprueba la comunicación. Cada trama `CHECK` lleva el identificador del intento, la etiqueta y la decisión. El ESP32 devuelve el acuse `SIMULATED` para las decisiones válidas y un error para las tramas inválidas. El firmware carece de salidas de accionamiento y el SG90 permanece desconectado durante el ensayo.

En la prueba de escritorio, el código del firmware devolvió las once respuestas esperadas. Los casos cubrieron comunicación, decisiones sobre identidades conocidas y desconocidas, concesión inválida a `UNKNOWN`, entradas malformadas, campos sin separador, desbordamiento y recuperación de la comunicación.

El 20-11-2026 se guardó en el volumen VeraCrypt una copia de los 4 MiB de la memoria original del ESP32. La copia se verificó contra el resumen MD5 calculado por la placa antes de grabar el firmware. Los intentos de lectura continua tuvieron errores de transferencia. La lectura por bloques a 115200 baudios permitió completar y verificar el respaldo. Se cargó el firmware por COM5 en modo ROM, sin borrado global, y esptool verificó los datos escritos antes de reiniciar la placa.

Desde Windows se ejecutó `python -m scripts.serial_bench --port COM5` dos veces. Pasaron las **11 tramas en cada ronda** con una apertura independiente del puerto. Las respuestas comprobaron la recepción y validación de decisiones de prueba en el ESP32. La verificación del recorrido desde el celular y la observación del pestillo se realizan en los ensayos de integración.

### Video local y decisión de banco

Con el SG90 desconectado, habilitar MJPEG en el celular en la misma red local que Windows, con la cámara apuntada a una escena sin personas y sin grabación ni nube. Ejecutar desde la raíz del proyecto con el entorno virtual activo y las dependencias de `requirements.txt` y `requirements-hardware.txt` instaladas. Sustituir la IP y el puerto del ejemplo por los que muestre el celular. En IP Webcam, la ruta MJPEG es `/video`.

```powershell
python -m scripts.phone_serial_bench --url http://192.168.1.20:8080/video --port COM5
```

Windows comprueba primero la versión del firmware de banco con `PING`, abre el video con OpenCV y procesa cinco fotogramas con YuNet. Emite un único `CHECK <id> UNKNOWN DENIED` y exige el acuse con el mismo identificador. El programa reporta la resolución y el motivo de denegación, y mantiene los fotogramas en memoria. El ensayo cubre detección y transporte de la decisión. El reconocimiento de identidades y la autorización quedan para sus pruebas específicas.

El 20-11-2026 se probó con un servidor MJPEG sintético en Windows y el ESP32 real en COM5. YuNet procesó 5/5 fotogramas de 320 × 240 y devolvió `NO_FACE`. Una segunda ejecución con el servidor inaccesible produjo `STREAM_UNAVAILABLE` y terminó con código 2. En ambos casos el ESP32 contestó `UNKNOWN DENIED SIMULATED` con el identificador esperado.

El mismo día se ejecutó la prueba con el celular real por la red local. En dos rondas, OpenCV recibió cinco fotogramas de 1920 × 1080 por ronda y YuNet informó `NO_FACE` en la escena despejada. En 2/2 rondas, el ESP32 confirmó `UNKNOWN DENIED SIMULATED` por COM5 con el identificador correspondiente. El SG90 permaneció desconectado.
