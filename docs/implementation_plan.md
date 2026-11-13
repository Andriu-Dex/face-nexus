# Plan de implementación

Estado inicial: fase 0 preparada documentalmente; fases de software y hardware pendientes. Cada fase requiere plan breve de archivos, implementación, ejecución de comprobaciones disponibles, inspección de salidas y registro de evidencia antes de preparar un commit descriptivo. No se publican ramas ni cambios remotos sin autorización.

| Fase | Trabajo y archivos previstos | Condición de salida |
| --- | --- | --- |
| 0. Base documental | README, AGENTS y docs | Trazabilidad, alcance físico y pendientes explícitos; enlaces válidos |
| 1. Esqueleto y contratos | Configuración de proyecto, módulos de dominio, autorización, controlador simulado y pruebas | Casos de permiso/fallo/repetición comprobados sin cámara ni hardware |
| 2. Datos y piloto | Herramientas de captura, validación de manifiestos y preparación | Consentimientos privados, sesiones separadas, controles de fugas y viabilidad de cámara |
| 3. Características | Preparación, extractor, representación propia y experimento separado | Dimensiones/versiones verificadas y procedencia de pesos revisada; características justificadas |
| 4. Comparación | Entrenamiento, evaluación y reportes | Cuatro clasificadores con entradas comunes; selección y rechazo calibrados sin TEST |
| 5. Inferencia e interfaz | Captura en vivo, estados, permisos y eventos | Flujo completo simulado, tiempos medidos y fallos cerrados verificados |
| 6. Dispositivo físico | Adaptador, configuración privada y pruebas de integración | Apertura real y denegación observadas; desconexión y repetición controladas |
| 7. Evaluación final y defensa | Configuración congelada, reporte agregado y guía de demostración | TEST reservado ejecutado; límites y cumplimiento documentados, incluida CONF-01 |

La selección del dispositivo y la disponibilidad de participantes pueden avanzar desde la fase 1; la conexión del actuador corresponde a fase 6. No asignar fechas sin conocer entrega, equipo y disponibilidad.

Las rutas de código se concretarán al crear el esqueleto. Usar pytest y análisis estático si se adopta Python; las pruebas lógicas usan muestras sintéticas y dobles de cámara/controlador. Separar las pruebas que requieren equipos y marcar las no ejecutadas como pendientes.

## Registro de evidencias por fase

Anotar fecha, requisito, versión/configuración, comando o procedimiento, resultado observado, ubicación privada o pública del reporte y limitaciones. No convertir un resultado esperado en observado. La preparación documental no acredita funcionamiento.

## Primer trabajo de implementación

Comprobar entorno y definir estructura mínima; crear contratos, política de permisos y controlador simulado con pruebas de denegación. Antes de capturar datos: resolver consentimiento, almacenamiento y disponibilidad de sesiones. Antes de elegir pesos: verificar licencia del artefacto concreto.
