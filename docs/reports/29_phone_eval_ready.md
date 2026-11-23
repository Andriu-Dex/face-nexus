# Evaluación del celular: listo, extraños y captura

22-11-2026. Correcciones de supervisión. Sin capturas nuevas ni pestillo.

## Evaluación lista

`phone_eval_ready` es verdadero solo si el manifiesto no tiene errores, hay recortes usables de K01–K04 en `eval`, ajuste y evaluación no comparten `encounter_id`, y los HOG publicados coinciden en huella y etiqueta. Un manifiesto con errores o `usable_frames = 0` no pasa aunque figuren los cuatro códigos.

## Extraños

Sin JSON de `identity_ids` de calibración y de evaluación, `unknowns_disjoint` queda sin verificar. Un resultado se guarda como `domain_<nombre>.json` y no reutiliza `demo_domain.json`.

## Captura

Las huellas se comprueban contra el manifiesto antes de publicar. El lote sale de un directorio `.pending-*` y el índice se reemplaza de forma atómica. Un lote no listado se borra. Pruebas: dos capturas sucesivas y un duplicado rechazado sin huérfano.

## CNN

0/20 y 1/60 siguen siendo diagnóstico del lote con que se adaptó la red, con K01 forzado. El vivo no veta YuNet hasta un ensayo independiente del mismo montaje.
