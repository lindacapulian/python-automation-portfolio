# =============================================================
# PASO 2 - Generar un reporte PDF con el estado de los puertos
# Lee la API de DICAPI, arma un reporte en HTML con diseño
# y lo convierte a PDF con Playwright.
# Aún NO envía correos (eso es el paso 3).
# =============================================================
import requests
import truststore
truststore.inject_into_ssl()
from datetime import datetime, timedelta, timezone
from pathlib import Path
from playwright.sync_api import sync_playwright

URL = "https://www.dicapi.mil.pe/api/ports"
CARPETA = Path(__file__).parent / "reportes"   # se crea junto a este script

# Color de cada nivel (levelId)
COLORES = {1: "#2e9e4f", 3: "#e3a008", 5: "#d64545"}


def ahora_lima():
    return datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=5)


def a_hora_lima(fecha_utc):
    if not fecha_utc:
        return "—"
    dt = datetime.strptime(fecha_utc[:19], "%Y-%m-%dT%H:%M:%S") - timedelta(hours=5)
    return dt.strftime("%d/%m/%Y %H:%M")


# ---------- 1) Datos ----------
def obtener_puertos():
    r = requests.get(URL, timeout=30)
    r.raise_for_status()
    return r.json()["data"]


def resumen_por_capitania(puertos):
    """Devuelve {capitania: {'abiertos': n, 'parcial': n, 'total': n}}"""
    res = {}
    for p in puertos:
        c = res.setdefault(p["captaincy"], {"abiertos": 0, "parcial": 0, "total": 0})
        if p["levelId"] == 1:
            c["abiertos"] += 1
        elif p["levelId"] == 5:
            c["total"] += 1
        else:
            c["parcial"] += 1
    return dict(sorted(res.items()))


# ---------- 2) HTML ----------
def construir_html(puertos):
    fecha = ahora_lima().strftime("%d/%m/%Y %H:%M")
    abiertos = sum(1 for p in puertos if p["levelId"] == 1)
    cierre_total = sum(1 for p in puertos if p["levelId"] == 5)
    parcial = len(puertos) - abiertos - cierre_total

    restringidos = sorted([p for p in puertos if p["levelId"] != 1],
                          key=lambda p: (-p["levelId"], p["captaincy"], p["port"]))

    filas_restr = ""
    for p in restringidos:
        color = COLORES.get(p["levelId"], "#e3a008")
        enlace = (f'<a href="{p["resolution_url"]}">{p["resolution_number"]}</a>'
                  if p.get("resolution_url") else (p.get("resolution_number") or "—"))
        filas_restr += f"""
        <tr>
          <td><span class="badge" style="background:{color}">{p['level']}</span></td>
          <td><b>{p['port']}</b></td>
          <td>{p['captaincy']}</td>
          <td>{p['levelName']}</td>
          <td>{enlace}</td>
          <td>{a_hora_lima(p['publication_date'])}</td>
        </tr>"""
    if not filas_restr:
        filas_restr = '<tr><td colspan="6" class="ok">Todos los puertos están abiertos.</td></tr>'

    filas_cap = ""
    for cap, c in resumen_por_capitania(puertos).items():
        alerta = ' class="alerta"' if (c["parcial"] or c["total"]) else ""
        filas_cap += f"""
        <tr{alerta}><td>{cap}</td><td>{c['abiertos']}</td>
        <td>{c['parcial'] or ''}</td><td>{c['total'] or ''}</td></tr>"""

    return f"""<!DOCTYPE html>
<html lang="es"><head><meta charset="utf-8">
<style>
  body {{ font-family: 'Segoe UI', Arial, sans-serif; color:#2b2b33; margin:0; }}
  .header {{ background:#1f2a44; color:#fff; padding:22px 28px; }}
  .header h1 {{ margin:0; font-size:22px; }}
  .header p {{ margin:4px 0 0; font-size:12px; opacity:.85; }}
  .wrap {{ padding:20px 28px; }}
  .kpis {{ display:flex; gap:12px; margin-bottom:22px; }}
  .kpi {{ flex:1; border-radius:8px; padding:14px; text-align:center; border:1px solid #e2e4ea; }}
  .kpi .n {{ font-size:30px; font-weight:700; }}
  .kpi .t {{ font-size:11px; text-transform:uppercase; letter-spacing:.5px; color:#666; }}
  h2 {{ font-size:15px; margin:18px 0 8px; border-left:4px solid #1f2a44; padding-left:8px; }}
  table {{ width:100%; border-collapse:collapse; font-size:11px; }}
  th {{ background:#f1f3f7; text-align:left; padding:7px; border-bottom:2px solid #d5d9e2; }}
  td {{ padding:6px 7px; border-bottom:1px solid #eceef3; vertical-align:top; }}
  .badge {{ color:#fff; border-radius:10px; padding:2px 8px; font-size:10px; white-space:nowrap; }}
  tr.alerta td {{ background:#fff6e5; }}
  .ok {{ color:#2e9e4f; text-align:center; padding:12px; }}
  a {{ color:#1f5fbf; text-decoration:none; }}
  .pie {{ font-size:9px; color:#888; margin-top:18px; }}
</style></head>
<body>
  <div class="header">
    <h1>Estado de Puertos del Perú</h1>
    <p>Reporte generado el {fecha} (hora de Lima) · Fuente: DICAPI</p>
  </div>
  <div class="wrap">
    <div class="kpis">
      <div class="kpi"><div class="n">{len(puertos)}</div><div class="t">Puertos</div></div>
      <div class="kpi"><div class="n" style="color:{COLORES[1]}">{abiertos}</div><div class="t">Abiertos</div></div>
      <div class="kpi"><div class="n" style="color:{COLORES[3]}">{parcial}</div><div class="t">Cierre parcial</div></div>
      <div class="kpi"><div class="n" style="color:{COLORES[5]}">{cierre_total}</div><div class="t">Cierre total</div></div>
    </div>

    <h2>Puertos con restricción</h2>
    <table>
      <tr><th>Nivel</th><th>Puerto</th><th>Capitanía</th><th>Estado</th><th>Resolución</th><th>Vigente desde</th></tr>
      {filas_restr}
    </table>

    <h2>Resumen por capitanía</h2>
    <table>
      <tr><th>Capitanía</th><th>Abiertos</th><th>Cierre parcial</th><th>Cierre total</th></tr>
      {filas_cap}
    </table>

    <p class="pie">Información obtenida de https://www.dicapi.mil.pe/estado-de-puertos.
    Verificar siempre la resolución oficial antes de tomar decisiones operativas.</p>
  </div>
</body></html>"""


# ---------- 3) PDF ----------
def generar_pdf(html, ruta_pdf):
    with sync_playwright() as p:
        navegador = p.chromium.launch(channel="msedge")   # usa el Edge instalado
        pagina = navegador.new_page()
        pagina.set_content(html, wait_until="load")
        pagina.pdf(path=str(ruta_pdf), format="A4", print_background=True,
                   margin={"top": "0", "bottom": "12mm", "left": "0", "right": "0"})
        navegador.close()


if __name__ == "__main__":
    CARPETA.mkdir(exist_ok=True)
    puertos = obtener_puertos()
    html = construir_html(puertos)
    ruta = CARPETA / f"estado_puertos_{ahora_lima():%Y-%m-%d}.pdf"
    generar_pdf(html, ruta)
    print(f"PDF generado: {ruta}")
