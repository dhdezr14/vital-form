
# Registra una tarea programada que inicia Streamlit al arrancar Windows.
# Ejecutar UNA VEZ como administrador:
#   Right-click > "Ejecutar como administrador"

$taskName  = "VitalForm-Streamlit"
$batPath   = "C:\vital-form-streamlit\run_app.bat"

# Eliminar si ya existe
Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue

$action  = New-ScheduledTaskAction -Execute "cmd.exe" -Argument "/c `"$batPath`""
$trigger = New-ScheduledTaskTrigger -AtLogOn
$settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Hours 0) -AllowStartIfOnBatteries

Register-ScheduledTask -TaskName $taskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -RunLevel Highest `
    -Description "Inicia el dashboard VitalForm Streamlit al iniciar sesion"

Write-Host ""
Write-Host "Tarea '$taskName' registrada. Streamlit arrancara automaticamente al iniciar sesion."
Write-Host "Para iniciarla ahora sin reiniciar:"
Write-Host "  Start-ScheduledTask -TaskName '$taskName'"
