# Protocolo de integración física

## Condición de entrega

El dispositivo físico es obligatorio (CONF-01). En la demostración, el nodo IoT captura una imagen, la envía a la computadora, recibe la etiqueta y actúa según la respuesta (PROF-06). Se propone probar un ESP32 con cámara y una salida observable como una tira LED. El equipo y la salida siguen pendientes de confirmación. El simulador sirve para probar decisiones.

El responsable propuso también un SG90 para mover un pestillo de maqueta. Es una salida candidata. La placa exacta, la cámara, la alimentación y el esfuerzo del pestillo se comprobarán en banco.

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
4. Capturar en el nodo, enviar a la computadora, recibir la etiqueta y ejecutar una acción autorizada acotada. Comprobar el efecto y el retorno al estado previsto.
5. Comprobar escenas con varios integrantes y escenas mixtas, así como denegación cuando falte una identidad autorizada, haya un error o caduque la orden.
6. Probar pérdida de comunicación, reinicio y reconexión sin aperturas espontáneas.

Registrar configuración/versiones, caso, resultado esperado, observación real y limitaciones. No se exige grabar rostros como evidencia. No declarar fase completada sin ejecutar el hardware real.
