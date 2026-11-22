# Piloto de calibración del rechazo con HOG

## Diagnóstico con R01

Se cargaron los modelos SVM y MLP de la comparación anterior y se verificaron el manifiesto y los vectores de R01. Se midió el margen entre las dos puntuaciones más altas en los 72 fotogramas utilizables del segundo día.

| Modelo | Aciertos / confusiones | Margen mediano en aciertos | Margen mediano en confusiones | Mayor margen de una confusión |
| --- | ---: | ---: | ---: | ---: |
| SVM | 57 / 15 | 0,422 | 0,127 | 0,628 |
| MLP | 57 / 15 | 2,567 | 1,208 | 3,362 |

Para ambos modelos hubo aciertos con márgenes inferiores a los de varias confusiones. Cada modelo usa su propia escala de puntuación. R01 contiene rostros conocidos y permite estudiar ese solapamiento por fotograma. La estimación del rechazo de desconocidos se hace por intento en vivo.

El muestreo recibió cinco fotogramas de una transmisión MJPEG sintética sin rostros. Registró cero rostros usables, por lo que ninguno de los modelos emitió un candidato.

## Presentaciones con el celular

1. Participa una persona a la vez con el celular en la misma red que Windows, en la posición prevista para la demostración. Asignar `K01` a `K04` a los integrantes y `A01`, `A02`, etc. a voluntarios con consentimiento que no sean integrantes. Reservar voluntarios diferentes para el ensayo final.
2. El operador inicia el comando con la persona en cuadro. Se toman cinco fotogramas separados por al menos 0,3 s, dentro de una ventana de 2,5 s después de abrir el video. Se usa YuNet y HOG de la comparación. Una lectura interrumpida, una ventana incompleta o menos de tres fotogramas con rostro único usable invalidan el intento y se registran.
3. Si un modelo coincide en una identidad en al menos tres fotogramas, se toma el tercer margen más alto de esa identidad. El umbral del modelo se compara con ese margen. Entre intentos, la persona sale del cuadro durante al menos dos segundos antes de volver a presentarse. Un piloto inicial puede usar tres presentaciones por persona.
4. El programa guarda únicamente el código, el estado y los márgenes del intento en VeraCrypt. Los fotogramas y los vectores se procesan en memoria. El ensayo se ejecuta sin accionar el ESP32 ni el SG90.

El ejemplo registra una presentación. La dirección es ilustrativa y el número cambia en cada repetición para conservar el registro anterior.

```powershell
python -m scripts.calibrate_hog probe --url http://192.168.1.20:8080/video
python -m scripts.calibrate_hog --vault V:\FaceNexus attempt --url http://192.168.1.20:8080/video --participant A01 --number 1 --rotation 90
python -m scripts.calibrate_hog --vault V:\FaceNexus inspect-attempts
python -m scripts.calibrate_hog --vault V:\FaceNexus compare-attempts
```

`probe` lee tres fotogramas y prueba los giros 0°, 90°, 180° y 270° sobre las mismas imágenes. No evalúa identidad ni escribe en el volumen. Usar el `suggested_rotation` si hay recortes usables y repetir `probe` si se mueve el celular.

Si el celular entrega la imagen de lado, `--rotation 90` aplica un giro horario antes de YuNet. Conservar la orientación física del celular entre presentaciones y usar la corrección que deje el rostro derecho. El registro del intento conserva el giro aplicado, el recuento de rostros, la puntuación de YuNet y el tamaño de caja por fotograma. No guarda imágenes ni vectores HOG.

`inspect-attempts` resume aciertos y confusiones aunque falten K02–K04. `compare-attempts` solo estima umbral cuando hay presentaciones usables de los cuatro integrantes y de al menos un voluntario A.

Con intentos utilizables de los cuatro integrantes y del grupo A, el comparador busca para cada modelo el menor umbral que rechaza las aceptaciones indebidas observadas. Reporta cuántos intentos conocidos reconoce y cuántos rechaza con ese umbral. La estimación es exploratoria y se valida después con el modelo congelado y un grupo distinto.

## Primera sesión del grupo A

Se registraron cinco presentaciones de un voluntario, con el celular transmitiendo el video en 1920 × 1080. Las dos primeras recibieron cinco fotogramas cada una y produjeron cero recortes usables. En un diagnóstico en memoria, YuNet detectó un único rostro en los cuatro fotogramas con giro horario de 90° y el umbral de detección original de 0,90. Se aplicó esa corrección a las tres presentaciones siguientes y todas resultaron usables, con cinco fotogramas válidos por presentación.

Antes de calibrar el rechazo, SVM y MLP propusieron alguna identidad conocida en las tres presentaciones usables. Los resultados corresponden a un solo voluntario. Se conservaron los cinco registros en VeraCrypt y el comparador mantuvo el estado `insufficient_live_data` mientras faltan las presentaciones de los cuatro integrantes con el celular.

## Primera sesión de un integrante

Se registraron cuatro presentaciones de K01. La primera recibió cinco fotogramas y no produjo un recorte usable. Una comprobación en memoria confirmó un rostro usable en cuatro de cuatro fotogramas con el giro horario de 90°. Las siguientes tres presentaciones mantuvieron ese giro y produjeron cinco fotogramas usables cada una.

Antes de aplicar un umbral, la SVM acertó una de las tres presentaciones usables y MLP cero de tres. El comparador registró seis presentaciones usables de nueve en total, sumando K01 y el voluntario. El cálculo del umbral requiere las presentaciones de K02, K03 y K04.

## Continuación operativa — 21-11-2026

El software de calibración ahora registra, por fotograma y sin imágenes, si falló la detección, si hubo varios rostros o si el recorte HOG fue usable, junto con las puntuaciones de SVM y MLP. El comando `probe` elige el giro del celular antes de gastar números de intento. El comando `inspect-attempts` permite leer el dominio del celular con los registros ya guardados.

Pendiente de ejecución con el celular en la posición de demostración:

1. `probe` hasta confirmar un giro con recortes usables.
2. Tres presentaciones usables nuevas de K02, K03 y K04, y repetir K01 con el mismo giro. No reutilizar números de intento ya escritos.
3. Completar o repetir voluntarios del grupo A distintos del grupo B final.
4. `inspect-attempts` para separar fallo de recorte y fallo de clasificación; después `compare-attempts` cuando estén los cuatro conocidos.

No se conecta el SG90 en esta etapa. Los intentos previos de K01 y A01 se conservan como antecedente; si el giro o la distancia cambian de forma material, registrar los nuevos con el siguiente número libre y no mezclar interpretaciones sin decirlo.
