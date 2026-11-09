# =============================================================
# PASO 3 - Enviar el reporte por correo (Outlook)
# Reutiliza las funciones del paso 2: consulta la API, genera
# el PDF y lo envía adjunto con un resumen en el cuerpo.
# =============================================================
import win32com.client as win32
import paso2_reporte_pdf as rep          # el archivo del paso 2 (misma carpeta)

# ---------- CONFIGURACIÓN (edita aquí) ----------
DESTINATARIOS = ["correo1@empresa.com", "correo2@empresa.com"]
CON_COPIA = []                            # opcional, ej. ["jefe@empresa.com"]
MODO_PRUEBA = True                         # True = solo abre el correo para revisarlo
                                          # False = lo envía directamente
FIRMA_NOMBRE = "Tu nombre"
FIRMA_CARGO = "Cargo | Empresa"
PIE = "Reporte automático de estado de puertos"
# -------------------------------------------------


def construir_cuerpo(puertos, nombre_pdf):
    """Cuerpo HTML con el mismo estilo de tus correos (tablas + estilos en línea para Outlook)."""
    restringidos = sorted([p for p in puertos if p["levelId"] != 1],
                          key=lambda p: (-p["levelId"], p["captaincy"], p["port"]))
    abiertos = len(puertos) - len(restringidos)
    cierre_total = sum(1 for p in restringidos if p["levelId"] == 5)
    parcial = len(restringidos) - cierre_total
    fecha = rep.ahora_lima().strftime("%d/%m/%Y")
    hora = rep.ahora_lima().hour
    if hora < 12:
        saludo = "Buenos días"
    elif hora < 19:
        saludo = "Buenas tardes"
    else:
        saludo = "Buenas noches"

    # Tarjetas de resumen
    def tarjeta(numero, texto, color):
        return (f'<td align="center" width="25%" style="padding:10px 4px;border:1px solid #e6e8ee;">'
                f'<div style="font-size:22px;font-weight:bold;color:{color};">{numero}</div>'
                f'<div style="font-size:10px;color:#777;text-transform:uppercase;">{texto}</div></td>')

    tarjetas = (tarjeta(len(puertos), "Puertos", "#2b2b33")
                + tarjeta(abiertos, "Abiertos", rep.COLORES[1])
                + tarjeta(parcial, "Cierre parcial", rep.COLORES[3])
                + tarjeta(cierre_total, "Cierre total", rep.COLORES[5]))

    # Lista de puertos con restricción
    if restringidos:
        filas = ""
        for p in restringidos:
            color = rep.COLORES.get(p["levelId"], "#e3a008")
            filas += (f'<tr><td style="padding:3px 0;font-size:13px;color:#555;">'
                      f'<span style="color:{color};font-weight:bold;">&#9679; {p["level"]}</span>'
                      f' &nbsp;{p["port"]} <span style="color:#888;">({p["captaincy"]})</span></td></tr>')
        detalle = f'<table cellpadding="0" cellspacing="0" width="100%">{filas}</table>'
    else:
        detalle = '<p style="margin:0;font-size:13px;color:#2e9e4f;">Todos los puertos se encuentran abiertos.</p>'

    return f"""
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f5f7;padding:20px 0;">
<tr><td align="center">
<table width="600" cellpadding="0" cellspacing="0" style="background:#ffffff;font-family:Segoe UI,Arial,sans-serif;">
  <tr><td style="background:#3c3c46;height:60px;"></td></tr>
  <tr><td style="background:#ff6441;height:4px;font-size:0;line-height:0;">&nbsp;</td></tr>
  <tr><td style="padding:30px 32px 10px;">
    <h2 style="margin:0 0 20px;text-align:center;font-size:20px;color:#2b2b33;">Estado de Puertos</h2>
    <p style="font-size:14px;color:#555;margin:0 0 12px;">{saludo}, Equipo,</p>
    <p style="font-size:14px;color:#555;margin:0 0 18px;">Espero que tengan una excelente jornada.
       Comparto con ustedes el <b style="color:#2b2b33;">estado de puertos del Perú</b>
       actualizado al <b style="color:#2b2b33;">{fecha}</b>, según DICAPI.</p>

    <table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;margin-bottom:18px;">
      <tr>{tarjetas}</tr>
    </table>

    <table width="100%" cellpadding="0" cellspacing="0"
           style="background:#f7f8fa;border:1px solid #e6e8ee;">
      <tr><td style="padding:16px 18px;">
        <p style="margin:0 0 8px;font-size:13px;font-weight:bold;color:#1f3a5f;">PUERTOS CON RESTRICCIÓN:</p>
        {detalle}
        <p style="margin:12px 0 0;font-size:13px;color:#555;">&bull; Detalle completo: {nombre_pdf}</p>
      </td></tr>
    </table>

    <p style="font-size:14px;color:#555;margin:22px 0;">Quedo a su disposición ante cualquier duda.</p>
    <hr style="border:none;border-top:1px solid #eceef3;margin:0 0 14px;">
    <p style="margin:0;font-size:14px;font-weight:bold;color:#1f3a5f;">{FIRMA_NOMBRE}</p>
    <p style="margin:2px 0 20px;font-size:12px;color:#666;">{FIRMA_CARGO}</p>
  </td></tr>
  <tr><td align="center" style="background:#efefef;padding:16px;font-size:11px;color:#888;">{PIE}</td></tr>
</table>
</td></tr>
</table>"""


def enviar_correo(puertos, ruta_pdf):
    restringidos = sum(1 for p in puertos if p["levelId"] != 1)
    fecha = rep.ahora_lima().strftime("%d/%m/%Y")
    if restringidos:
        asunto = f"⚠ Estado de Puertos {fecha} - {restringidos} con restricción"
    else:
        asunto = f"✅ Estado de Puertos {fecha} - Todos abiertos"

    outlook = win32.Dispatch("Outlook.Application")
    correo = outlook.CreateItem(0)               # 0 = correo nuevo
    correo.To = "; ".join(DESTINATARIOS)
    correo.CC = "; ".join(CON_COPIA)
    correo.Subject = asunto
    correo.HTMLBody = construir_cuerpo(puertos, ruta_pdf.name)
    correo.Attachments.Add(str(ruta_pdf.resolve()))

    if MODO_PRUEBA:
        correo.Display()                          # lo abre para revisarlo
        print("Correo abierto en modo prueba (no se envió).")
    else:
        destinatarios = correo.To
        correo.Send()
        try:
            outlook.GetNamespace("MAPI").SendAndReceive(False)
        except Exception:
            pass                     # algunas cuentas corporativas no lo permiten; no es grave
        print(f"Correo enviado a: {destinatarios}")


if __name__ == "__main__":
    rep.CARPETA.mkdir(exist_ok=True)
    puertos = rep.obtener_puertos()
    ruta = rep.CARPETA / f"estado_puertos_{rep.ahora_lima():%Y-%m-%d}.pdf"
    rep.generar_pdf(rep.construir_html(puertos), ruta)
    enviar_correo(puertos, ruta)
