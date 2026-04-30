# clean.ps1 — purge Python bytecode and test-cache directories on Windows
# Usage: pwsh ./clean.ps1

Get-ChildItem -Recurse -Filter "__pycache__" -Directory | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
Get-ChildItem -Recurse -Include "*.pyc", "*.pyo" | Remove-Item -Force -ErrorAction SilentlyContinue
Get-ChildItem -Recurse -Filter ".pytest_cache" -Directory | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
Get-ChildItem -Recurse -Filter ".ruff_cache" -Directory | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
Get-ChildItem -Recurse -Filter ".mypy_cache" -Directory | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

Write-Host "Clean complete."
