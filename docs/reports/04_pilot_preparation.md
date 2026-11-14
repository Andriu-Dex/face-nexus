# Cierre de cámara y preparación del piloto

Fecha: 14-11-2026. Entrega documental, sin captura de rostros ni entrenamiento.

## Cámara: qué queda cerrado

TMCAM 8305 como única cámara, resolución oficial 1920×1080 para piloto, objetivo 30 FPS y 60 Hz previsto. Se conserva el ensayo real de 29,241 FPS medios en diez minutos; están verificadas resolución recibida, continuidad sin fallos en ese período, apertura fallida sin USB y nueva apertura tras reconexión. Ningún resultado demuestra 30 FPS constantes. El responsable informó vista fluida sin bandas.

Se recalcularon los cuatro SHA-256 y coinciden con [el registro de evidencia original](03_camera_diagnostic.md). No se cambiaron los JSON ni el código del diagnóstico. Los valores manuales pendientes en los JSON no se sobrescribieron con observaciones posteriores.

## Qué sigue pendiente

Confirmar 60 Hz en el controlador y ensayar desconexión durante read. Se preparó documentalmente un procedimiento con hijo/supervisor y límite de tiempo, sin reconexión automática. No se ejecutó hoy ni se confunde con apertura sin dispositivo. Estos puntos no bloquean la preparación del piloto; el fallo seguro durante bloqueo será necesario antes de acceso físico.

## Piloto listo para revisión

[La ficha operativa](../data_protocol.md#ficha-operativa-del-piloto--propuesta-del-14-11-2026) propone 20 PNG originales por persona registrada, 80 en total, una sesión por persona, cinco bloques (frontal, giro horizontal, inclinación vertical, distancia y expresión), dos iluminaciones moderadas y sin ráfagas persistidas. Se registra toda toma/reemplazo/exclusión. Solo TRAIN/desarrollo; no se consume VALIDATION/TEST.

No se generan imágenes, embeddings ni formularios personales en Git. Se concreta manifiesto privado, separación raw/processed/features, revisión manual y control de duplicados. Los seis voluntarios desconocidos siguen como propuesta para fases posteriores, con identidades disjuntas de calibración y TEST y consentimiento propio. Las cantidades no son garantías de suficiencia ni obligaciones docentes.

## Detector y extractor

[model_verification.md](../model_verification.md) deja YuNet y SFace como candidatos, con licencias de sus carpetas, nombres de artefactos y hashes/tamaños publicados en punteros LFS; no se descargaron binarios. Hoy se comprobó que el entorno Python 3.14.7/OpenCV 4.14.0/NumPy 2.5.4 expone FaceDetectorYN y FaceRecognizerSF. No se validó carga, salida, precisión, dimensión del embedding ni latencia. El documento especifica cómo comprobarlos tras autorizar adquisición; no instala nuevas dependencias.

## Decisiones para aprobar antes de capturar

1. Aceptar 20 fotos por cada una de las cuatro personas y la pauta de variación; el piloto no autoriza todavía captura definitiva.
2. Confirmar quién asume custodia y que data/private están bajo su cuenta, sin sincronización externa ni acceso compartido por defecto.
3. Aceptar o ajustar eliminación a 90 días después de la defensa, con retiro anticipado y gestión de derivados. No es un plazo legal afirmado.
4. Confirmar que se obtendrá y conservará localmente el consentimiento individual antes de cada captura; no enviarlo a este chat.

Se solicita aprobación porque la instrucción del responsable en instruction.md exige presentar el protocolo y recibir aprobación antes de avanzar a captura definitiva, y la preparación acordada exige consentimiento/custodia antes de persistir rostros. Por prudencia operativa se explicita también la aprobación del pequeño piloto; no procede de una regla de skill ni autoriza compartir datos.

## Archivos modificados y verificación

Se actualizaron README, requirements.md, architecture.md, data_protocol.md, implementation_plan.md, decisions.md y se añadió el cierre al informe 03 sin alterar sus mediciones. Se crearon model_verification.md y este informe 04. El diagnóstico y las dependencias no se modificaron en esta entrega. Los cambios anteriores del usuario permanecen; no se hizo commit ni se alteró el índice/remoto.

Verificaciones: hashes de los cuatro JSON originales coincidentes; hash del script conservado (`269cb425dda9b2157c3dff26709cdfaf441825e6a1ef3060b4145d2532b1eed8`); interfaces locales presentes; enlaces relativos y diferencias de formato revisados. No se repitieron tests de código ni ensayos de diez minutos porque el cambio es documental. No se han descargado pesos/datasets, implementado clasificadores, abierto la webcam ni realizado nuevas capturas en esta fase.


## Respuesta del responsable — 14-11-2026

El usuario confirmó custodia personal, eliminación a los 90 días de la defensa y compromiso de obtener consentimiento individual. Se actualizaron protocolo, plan y decisiones. La solicitud anterior queda como antecedente de revisión; no se considera probado que los consentimientos ya existan ni que el destino privado esté configurado. El próximo trabajo es preparar la herramienta de captura y sus pruebas, no iniciar automáticamente la captura de personas.
