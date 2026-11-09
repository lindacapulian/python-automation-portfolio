# =============================================================
# PASO 1 - Consultar el estado de los puertos (DICAPI)
# Objetivo: comprobar que podemos leer la API y ver los datos.
# Aún NO envía correos ni guarda nada.
# =============================================================
import requests
import truststore
truststore.inject_into_ssl()   # usa los certificados de Windows (redes corporativas)
from datetime import datetime, timedelta

URL = "https://www.dicapi.mil.pe/api/ports"


def a_hora_lima(fecha_utc):
    """Convierte '2026-10-31T14:00:00.000Z' (UTC) a hora de Lima (UTC-5)."""
    if not fecha_utc:
        return "sin fecha"
    dt = datetime.strptime(fecha_utc[:19], "%Y-%m-%dT%H:%M:%S") - timedelta(hours=5)
    return dt.strftime("%d/%m/%Y %H:%M")


# 1) Pedir los datos a la API
respuesta = requests.get(URL, timeout=30)
respuesta.raise_for_status()            # si la web falla, se detiene con un error claro
puertos = respuesta.json()["data"]      # lista con un diccionario por puerto

# 2) Contar puertos por estado
conteo = {}
for p in puertos:
    estado = p["levelName"]
    conteo[estado] = conteo.get(estado, 0) + 1

print(f"Total de puertos: {len(puertos)}")
for estado, cantidad in conteo.items():
    print(f"  {estado}: {cantidad}")

# 3) Listar los que NO están abiertos (levelId distinto de 1)
no_abiertos = [p for p in puertos if p["levelId"] != 1]
no_abiertos.sort(key=lambda p: (p["captaincy"], p["port"]))

print("\nPuertos con restricción:")
for p in no_abiertos:
    print(f"- [{p['level']}] {p['port']} ({p['captaincy']})")
    print(f"    {p['levelName']} | {p['resolution_number']} | desde {a_hora_lima(p['publication_date'])}")
