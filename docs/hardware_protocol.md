# Protocolo de integración física

## Condición de entrega

El dispositivo físico es obligatorio (CONF-01). Su tipo, mecanismo y componentes están pendientes. El simulador inicial permite desarrollar y probar decisiones; no sustituye la demostración física final.

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
4. Ejecutar una apertura autorizada acotada y comprobar retorno al estado previsto.
5. Comprobar que desconocidos, permiso inactivo, errores y órdenes caducadas no producen apertura.
6. Probar pérdida de comunicación, reinicio y reconexión sin aperturas espontáneas.

Registrar configuración/versiones, caso, resultado esperado, observación real y limitaciones. No se exige grabar rostros como evidencia. No declarar fase completada sin ejecutar el hardware real.
