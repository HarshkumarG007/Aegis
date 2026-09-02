$env:DATABASE_URL="sqlite:///aegis_eval.db"
$env:USE_SQLITE="1"
$env:PYTHONPATH="src"

Remove-Item -Force aegis_eval.db -ErrorAction SilentlyContinue

Write-Host "Starting Positive Target..."
$positive_job = Start-Process -FilePath ".\.venv\Scripts\uvicorn.exe" -ArgumentList "src.aegis_eval.targets.known_positive_target:app", "--port", "8001" -PassThru -NoNewWindow
Start-Sleep -Seconds 3

Write-Host "Running Positive Calibration..."
.\.venv\Scripts\python scripts\aegis_cli.py run --target http://127.0.0.1:8001/query --queries reports/benchmark-v2.2.0/adversarial-v2.2.0.json

Stop-Process -Id $positive_job.Id -Force

Write-Host "Starting Negative Target..."
$negative_job = Start-Process -FilePath ".\.venv\Scripts\uvicorn.exe" -ArgumentList "src.aegis_eval.targets.known_negative_target:app", "--port", "8002" -PassThru -NoNewWindow
Start-Sleep -Seconds 3

Write-Host "Running Negative Calibration..."
.\.venv\Scripts\python scripts\aegis_cli.py run --target http://127.0.0.1:8002/query --queries reports/benchmark-v2.2.0/adversarial-v2.2.0.json

Stop-Process -Id $negative_job.Id -Force

Write-Host "Starting Mixed Target..."
$mixed_job = Start-Process -FilePath ".\.venv\Scripts\uvicorn.exe" -ArgumentList "src.aegis_eval.targets.known_mixed_target:app", "--port", "8003" -PassThru -NoNewWindow
Start-Sleep -Seconds 3

Write-Host "Running Mixed Calibration..."
.\.venv\Scripts\python scripts\aegis_cli.py run --target http://127.0.0.1:8003/query --queries reports/benchmark-v2.2.0/adversarial-v2.2.0.json

Stop-Process -Id $mixed_job.Id -Force

Write-Host "Calibrations complete!"
