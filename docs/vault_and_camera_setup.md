# Puesta en servicio del volumen cifrado y la cámara

## Estado al 17-11-2026

| Hito | Estado |
| --- | --- |
| Herramienta preparada | Sí. Captura, auditoría y comprobación previa probadas con datos sintéticos. |
| Almacenamiento cifrado | Contenedor en `C:\Downloads\FaceNexus\FaceNexusVault.hc`. El custodio observó que `V:` desapareció al desmontar y volvió a montar el volumen. Se verificaron NTFS, permisos y SHA-256 del marcador tras el remontaje normal. La prueba con la cabecera de respaldo sigue pendiente. El cifrado de `C:` sigue sin confirmar. |
| Validación operativa con la TMCAM | R99 completó la medición automática. El custodio confirmó después que no vio bandas con luz frontal difusa ni lateral. El JSON original conserva su estado pendiente. La primera ronda real necesita su propia comprobación aprobada. |
| Captura real autorizada | Pendiente de confirmación expresa del responsable. |

## 1. Instalar y crear el contenedor

El instalador de VeraCrypt 1.26.31 se descargó desde la publicación oficial. Su SHA-256 coincidió con el listado del fabricante y Windows validó la firma de IDRIX SARL. El equipo informa Windows 11 Home y el estado del cifrado de `C:` sigue sin verificarse. Ejecutar en PowerShell. [Publicación oficial de VeraCrypt](https://veracrypt.io/en/Downloads.html)

```powershell
$setup = 'C:\Downloads\FaceNexus\_setup\VeraCrypt.Setup.1.26.31.exe'
$expectedSetup = '9D7B4C294A353EFD45855205133286C04F07308218877F29EE881F686268A615'
$signature = Get-AuthenticodeSignature -LiteralPath $setup
if ((Get-FileHash -LiteralPath $setup -Algorithm SHA256).Hash -ne $expectedSetup -or
    $signature.Status -ne 'Valid' -or $signature.SignerCertificate.Subject -notmatch '^CN=IDRIX SARL,') {
    throw 'El instalador no superó la comprobación.'
}
Start-Process -FilePath $setup -Verb RunAs -Wait
```

1. En el instalador seleccionar **Install** y confirmar el aviso de Windows. Abrir VeraCrypt y elegir **Create Volume → Create an encrypted file container → Standard VeraCrypt volume**.
2. Indicar el archivo nuevo `C:\Downloads\FaceNexus\FaceNexusVault.hc`. Confirmar que ese archivo no existe y que la carpeta está fuera de cualquier sincronización. La ubicación coincide con la aprobada. Mantener las opciones criptográficas predeterminadas.
3. Usar **16 GiB** como tamaño inicial, aproximadamente 16.384 MiB. El inventario actual ocupa unos 4,24 GB. El margen contempla las nuevas tomas y sus derivados. Elegir **NTFS** y completar el asistente de formato del contenedor. Escribir la contraseña tú mismo en la ventana de VeraCrypt y guardarla en un lugar privado.
4. Si `Get-PSDrive -Name V -ErrorAction SilentlyContinue` no muestra una unidad existente, seleccionar **V:** en VeraCrypt. Usar **Select File**, elegir el contenedor y pulsar **Mount**. Introducir la credencial en VeraCrypt. Si V: está ocupada, elegir otra letra y usarla en todos los comandos. [Asistente oficial de creación](https://veracrypt.io/en/Beginner%27s%20Tutorial.html)

## 2. Restringir la carpeta y comprobar recuperación

Usar PowerShell con la cuenta que custodia los datos. En el primer montaje, crear la carpeta y aplicar permisos heredables para esa cuenta, SYSTEM y Administradores.

```powershell
Set-Location -LiteralPath 'C:\Documentos\D-Proyectos\Git\FaceNexus'
$vault = 'V:\FaceNexus'
if ([IO.DriveInfo]::new('V').DriveFormat -ne 'NTFS') {
    throw 'El volumen debe estar montado y formateado como NTFS.'
}
if (Test-Path -LiteralPath $vault) { throw 'La carpeta ya existe; comprueba su contenido.' }
New-Item -ItemType Directory -Path $vault -ErrorAction Stop | Out-Null
$sid = [System.Security.Principal.WindowsIdentity]::GetCurrent().User.Value
icacls.exe $vault /inheritance:r /grant:r "*${sid}:(OI)(CI)F" '*S-1-5-18:(OI)(CI)F' '*S-1-5-32-544:(OI)(CI)F'
if ($LASTEXITCODE -ne 0) { throw 'No se pudieron establecer los permisos.' }
.\.venv\Scripts\python.exe -m scripts.dataset_capture --vault $vault check-vault
if ($LASTEXITCODE -ne 0) { throw 'El destino no pasó la comprobación.' }
```

Con el volumen montado, escribir y verificar únicamente un marcador sintético. Mantener abierta esta ventana de PowerShell para conservar el hash mientras se maneja la interfaz de VeraCrypt.

```powershell
$smoke = Join-Path $vault '_smoke'
New-Item -ItemType Directory -Path $smoke -ErrorAction Stop | Out-Null
$marker = Join-Path $smoke 'mount-check.txt'
Set-Content -LiteralPath $marker -Value 'FaceNexus prueba sintetica de montaje' -Encoding ASCII -NoNewline
$expectedMarker = (Get-FileHash -LiteralPath $marker -Algorithm SHA256).Hash
```

1. Pulsar **Dismount** en VeraCrypt. Ejecutar `Test-Path -LiteralPath $marker` y comprobar que devuelve `False`.
2. Con el contenedor desmontado y seleccionado, usar **Tools → Backup Volume Header** para generar el respaldo de cabecera. Guardarlo en una ubicación privada distinta del contenedor. La cabecera externa requiere la credencial vigente al crearla. Si cambia la contraseña o el PIM, actualizar el respaldo.
3. Volver a montar con la credencial normal y ejecutar `(Get-FileHash -LiteralPath $marker -Algorithm SHA256).Hash -eq $expectedMarker`. Debe devolver `True`.
4. Para probar la vía de recuperación sin escribir en el contenedor, desmontar y montar con **Mount Options → Mount volume as read-only** y **Use backup header embedded in volume if available**. Repetir la comparación del marcador. Después desmontar y volver a montar en modo normal. Este ensayo verifica la cabecera integrada. Una cabecera externa permite reparar una cabecera dañada mediante **Tools → Restore Volume Header**. Probar una restauración que escriba solo sobre una copia desechable del volumen cuando contenga únicamente datos sintéticos. La cabecera no sustituye una copia de los archivos ni recupera una credencial perdida. [Menú de recuperación](https://veracrypt.io/en/Program%20Menu.html) · [Opciones de montaje](https://veracrypt.io/en/Mounting%20VeraCrypt%20Volumes.html)

## 3. Copiar y verificar el archivo histórico

El inventario de solo lectura identificó estas ubicaciones. Los 12.096 archivos suman 4.235.187.322 bytes. Los vídeos originales y los formularios de consentimiento no aparecieron dentro de estas raíces. El custodio debe localizar cualquier archivo adicional en privado y aplicar la misma comparación de alcance, ruta, tamaño y SHA-256.

| Origen | Contenido | Archivos |
| --- | --- | ---: |
| `C:\Downloads\FaceNexus\data` | Fotogramas externos, candidatos, recortes, embeddings, manifiestos y evidencia de ambos análisis | 12.075 |
| `data/raw/pilot/` del repositorio local | Diez fotos del piloto P01 y sus diez fichas | 20 |
| `private/` del repositorio local | Correspondencia privada entre carpetas e IDs | 1 |

`outputs/camera/` contiene informes técnicos y `outputs/pilot_synthetic/` corresponde al piloto sintético. El archivo histórico queda en `history/` dentro del volumen, separado del plan del dataset definitivo. Los permisos del destino se heredan de la carpeta cifrada.

La utilidad se probó con un árbol sintético. Verificó la copia y la segunda lectura, rechazó sobrescrituras y detectó cambios tanto en origen como en destino. También se comprobó el rechazo de `C:\Downloads\FaceNexus` como destino sin montar y se ensayaron los permisos en una carpeta temporal. La copia real y la comprobación de montaje siguen pendientes.

Tras validar el montaje, cerrar cualquier programa que escriba en los orígenes. Ejecutar desde la raíz del repositorio.

```powershell
.\.venv\Scripts\python.exe -m scripts.history_copy --vault 'V:\FaceNexus' copy
```

La utilidad escribe primero un inventario privado dentro de `V:\FaceNexus\history`. Luego copia los archivos a tres subcarpetas nuevas y compara sus rutas relativas, tamaños y SHA-256 con el inventario, volviendo a leer también los orígenes. La operación devuelve un código distinto de cero si algo difiere. Una copia incompleta queda en el volumen para revisión. El comando de copia rechaza un destino `history` preexistente.

Desmontar y volver a montar el contenedor. Ejecutar de nuevo la comprobación independiente.

```powershell
.\.venv\Scripts\python.exe -m scripts.history_copy --vault 'V:\FaceNexus' verify
```

El custodio debe confirmar que coinciden las tres categorías, que puede abrir localmente una muestra del archivo histórico tras volver a montar el volumen y que ha revisado si existen originales o respaldos adicionales. Retirar copias anteriores será una decisión posterior. Estos comandos solo leen el origen y carecen de operaciones de borrado.

## 4. Validar la TMCAM con una escena sin personas

Mantener el volumen montado y conectar la TMCAM 8305. Confirmar de forma presencial que el objetivo apunta a una escena sin personas. El diagnóstico utiliza una ronda ficticia en la carpeta de pruebas y guarda exclusivamente un informe JSON. Desde la misma terminal de PowerShell:

```powershell
$smoke = 'V:\FaceNexus\_smoke'
$row = @{
    person_id = 'K99'
    session_id = 'K99_S02'
    round_id = 'R99'
    split = 'TRAIN'
    first_light = 'diffuse'
    consent_ref = 'synthetic'
    setup = 'Escena sin personas'
}
ConvertTo-Json -InputObject @($row) | Set-Content -LiteralPath (Join-Path $smoke 'plan.json') -Encoding UTF8
.\.venv\Scripts\python.exe -c "import cv2; from cv2_enumerate_cameras import enumerate_cameras; print([(d.index,d.name) for d in enumerate_cameras(cv2.CAP_DSHOW)])"
$cameraIndex = [int](Read-Host 'Índice de la USB CAMERA que corresponde físicamente a la TMCAM')
$hz = 'unconfirmed'
.\.venv\Scripts\python.exe -m scripts.dataset_capture --vault $smoke check-camera --round R99 --camera $cameraIndex --antiflicker $hz
```

1. Revisar el ajuste de antiparpadeo en el controlador. Si confirma 60 Hz, usar `$hz = 'confirmed_60hz'` antes de ejecutar el diagnóstico. Si muestra otro valor, usar `other`. Si no se puede confirmar, mantener `unconfirmed`.
2. Confirmar **TMCAM** en la terminal. El programa calienta cinco segundos y mide durante un minuto. Revisar las dos condiciones de luz, marcando **N** si no se ven bandas o **S** si se ven.
3. Comprobar 1920×1080 efectivos, cero fallos y una entrega estable y comparable con los 29,241 FPS del diagnóstico previo. Revisar las pausas informadas. Escribir **APROBAR** solo si la comprobación es satisfactoria. Si falla, conservar el JSON técnico y repetir tras corregir la incidencia.
4. Verificar que la carpeta temporal carece de PNG y sesiones. Conservar el ID del informe y comunicar el resultado al responsable. Esta aprobación documenta el ensayo operativo. La ronda real tendrá su propia comprobación y requerirá la autorización expresa de captura.

```powershell
@(Get-ChildItem -LiteralPath $smoke -Recurse -File -Filter '*.png').Count
Test-Path -LiteralPath (Join-Path $smoke 'sessions')
```

Los resultados esperados son `0` y `False`.
