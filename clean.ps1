Get-ChildItem -Path . -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force
Get-ChildItem -Path . -Recurse -Include "*.pyc", "*.pyo", "*.pyd" | Remove-Item -Force
Write-Host "✅ Pycache cleaned."
