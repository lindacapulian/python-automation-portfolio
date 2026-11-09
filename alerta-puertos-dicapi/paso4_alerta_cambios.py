# =============================================================
# PASO 4 - Enviar la alerta SOLO cuando haya cambios
# Compara el estado actual de cada puerto con el de la última
# revisión (guardado en estado_anterior.json).
#   - Si algún puerto cambió de nivel (incluido volver a abierto) -> envía correo
#   - Si todo sigue igual -> no envía nada
# Usa la configuración (destinatarios, firma, MODO_PRUEBA) del paso 3.
# =============================================================
import json
import win32com.client as win32
import paso2_reporte_pdf as rep
import paso3_enviar_correo as p3

ARCHIVO_ESTADO = rep.CARPETA.parent / "estado_anterior.json"


# ---------- 1) Guardar y leer el estado ----------
def estado_actual(puertos):
    """Diccionario {portId: datos mínimos} para comparar."""
    return {str(p["portId"]): {"port": p["port"], "captaincy": p["captaincy"],
                               "levelId": p["levelId"], "level": p["level"]}
            for p in puertos}


def leer_estado_anterior():
    if not ARCHIVO_ESTADO.exists():
        return None                                   # primera ejecución
    return json.loads(ARCHIVO_ESTADO.read_text(encoding="utf-8"))


def guardar_estado(estado):
    ARCHIVO_ESTADO.write_text(json.dumps(estado, ensure_ascii=False, indent=2), encoding="utf-8")


# ---------- 2) Detectar cambios ----------
def detectar_cambios(anterior, actual):
    cambios = []
    for pid, ahora in actual.items():
        antes = anterior.get(pid)
        if antes is None:
            cambios.append({**ahora, "antes": "Nuevo", "antes_id": None})
        elif antes["levelId"] != ahora["levelId"]:
            cambios.append({**ahora, "antes": antes["level"], "antes_id": antes["levelId"]})
    for pid, antes in anterior.items():
        if pid not in actual:
            cambios.append({**antes, "antes": antes["level"], "antes_id": antes["levelId"],
                            "level": "Ya no figura", "levelId": None})
    return sorted(cambios, key=lambda c: (c["captaincy"], c["port"]))


# ---------- 3) Bloque HTML con los cambios ----------
def html_cambios(cambios, primera_vez):
    if primera_vez:
        contenido = ('<p style="margin:0;font-size:13px;color:#555;">Primer registro del monitoreo. '
                     'Desde ahora recibirán este correo solo cuando cambie el estado de algún puerto.</p>')
    else:
        filas = ""
        for c in cambios:
            c_antes = rep.COLORES.get(c["antes_id"], "#888")
            c_ahora = rep.COLORES.get(c["levelId"], "#888")
            filas += (f'<tr><td style="padding:4px 0;font-size:13px;color:#555;">'
                      f'<b>{c["port"]}</b> <span style="color:#888;">({c["captaincy"]})</span><br>'
                      f'<span style="color:{c_antes};font-weight:bold;">{c["antes"]}</span>'
                      f' &nbsp;&rarr;&nbsp; '
                      f'<span style="color:{c_ahora};font-weight:bold;">{c["level"]}</span></td></tr>')
        contenido = f'<table cellpadding="0" cellspacing="0" width="100%">{filas}</table>'

    return f"""
    <table width="100%" cellpadding="0" cellspacing="0"
           style="background:#fff4ef;border-left:4px solid #ff6441;margin-bottom:18px;">
      <tr><td style="padding:14px 18px;">
        <p style="margin:0 0 8px;font-size:13px;font-weight:bold;color:#c2410c;">CAMBIOS DETECTADOS:</p>
        {contenido}
      </td></tr>
    </table>"""


def armar_cuerpo(puertos, nombre_pdf, cambios, primera_vez):
    """Toma el cuerpo del paso 3 e inserta el bloque de cambios antes de las tarjetas."""
    cuerpo = p3.construir_cuerpo(puertos, nombre_pdf)
    pos_tarjeta = cuerpo.find('<td align="center" width="25%"')
    pos_tabla = cuerpo.rfind("<table", 0, pos_tarjeta)
    return cuerpo[:pos_tabla] + html_cambios(cambios, primera_vez) + cuerpo[pos_tabla:]


# ---------- 4) Enviar ----------
def enviar(puertos, ruta_pdf, cambios, primera_vez):
    fecha = rep.ahora_lima().strftime("%d/%m/%Y")
    if primera_vez:
        asunto = f"Estado de Puertos {fecha} - Inicio de monitoreo"
    else:
        asunto = f"⚠ Cambio en Estado de Puertos {fecha} - {len(cambios)} puerto(s)"

    correo = win32.Dispatch("Outlook.Application").CreateItem(0)
    correo.To = "; ".join(p3.DESTINATARIOS)
    correo.CC = "; ".join(p3.CON_COPIA)
    correo.Subject = asunto
    correo.HTMLBody = armar_cuerpo(puertos, ruta_pdf.name, cambios, primera_vez)
    correo.Attachments.Add(str(ruta_pdf.resolve()))
    if p3.MODO_PRUEBA:
        correo.Display()
    else:
        correo.Send()


if __name__ == "__main__":
    puertos = rep.obtener_puertos()
    actual = estado_actual(puertos)
    anterior = leer_estado_anterior()
    primera_vez = anterior is None
    cambios = [] if primera_vez else detectar_cambios(anterior, actual)

    hora = rep.ahora_lima().strftime("%d/%m/%Y %H:%M")
    if not primera_vez and not cambios:
        print(f"{hora} - Sin cambios. No se envió correo.")
    else:
        rep.CARPETA.mkdir(exist_ok=True)
        ruta = rep.CARPETA / f"estado_puertos_{rep.ahora_lima():%Y-%m-%d_%H%M}.pdf"
        rep.generar_pdf(rep.construir_html(puertos), ruta)
        enviar(puertos, ruta, cambios, primera_vez)
        if p3.MODO_PRUEBA:
            print(f"{hora} - MODO PRUEBA: correo abierto, estado NO guardado.")
        else:
            guardar_estado(actual)                    # solo se guarda si el correo salió
            print(f"{hora} - Correo enviado. Cambios: {len(cambios)}")
