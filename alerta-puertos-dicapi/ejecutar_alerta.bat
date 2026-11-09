@echo off
REM Ajusta la ruta a la carpeta donde guardaste el proyecto
cd /d "C:\ruta\a\alerta-puertos-dicapi"
python paso4_alerta_cambios.py >> registro.txt 2>&1
