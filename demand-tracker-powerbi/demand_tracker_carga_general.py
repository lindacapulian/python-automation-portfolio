# =============================================================
# Demand Tracker Carga General - captura automática de un informe interno de Power BI
# Usa un perfil persistente de Edge (inicias sesión solo la primera vez),
# recorre todos los valores del filtro "Tipo" y arma un reporte PNG/PDF.
# =============================================================
from playwright.sync_api import sync_playwright
from PIL import Image, ImageDraw, ImageFont, ImageChops
from PIL import JpegImagePlugin, PdfImagePlugin  # registra los formatos que usa el PDF
from datetime import date
from pathlib import Path
import re

URL = "https://app.powerbi.com/groups/<workspace-id>/reports/<report-id>/<page-id>"   # informe interno

# Carpeta donde Edge guarda tu sesión (así solo inicias sesión la primera vez).
# No compartas esta carpeta: contiene tu sesión de Microsoft.
PERFIL = Path(__file__).parent / "perfil_edge"   # se crea junto al script (está en .gitignore)

TEXTO_ANIOS = "2025 – 2026"   # el informe ya abre con ambos años marcados
SUBTITULO = "EMPRESA"   # aparece en el encabezado del reporte


# ---------- Funciones para el filtro Tipo ----------
def buscar_slicer_tipo(page):
    """El slicer que tiene lista desplegable y cuyo título es exactamente 'Tipo'."""
    return (page.locator("visual-container")
                .filter(has=page.locator(".slicer-dropdown-menu"))
                .filter(has_text=re.compile(r"\bTipo\b"))
                .first)


def opciones(page):
    return page.locator(".slicer-dropdown-popup:visible .slicerItemContainer")


def abrir_lista(page, slicer):
    if opciones(page).count() == 0:
        slicer.locator(".slicer-dropdown-menu").click()
        page.wait_for_timeout(1500)


def cerrar_lista(page, slicer):
    if opciones(page).count() > 0:
        page.keyboard.press("Escape")
        page.wait_for_timeout(800)
    if opciones(page).count() > 0:          # si Escape no la cerró, clic otra vez en el desplegable
        slicer.locator(".slicer-dropdown-menu").click()
        page.wait_for_timeout(800)


def leer_opciones(page, slicer):
    """Lee TODOS los valores que hay en la lista (así, si aparece uno nuevo, se incluye solo)."""
    abrir_lista(page, slicer)
    textos = [t.strip() for t in opciones(page).all_inner_texts() if t.strip()]
    cerrar_lista(page, slicer)
    return [t for t in textos if t.lower() not in ("select all", "seleccionar todo")]


def seleccionar(page, slicer, valor):
    """Elige el valor y comprueba que quedó; si no, vuelve a intentar."""
    texto = slicer.locator(".slicer-restatement")
    # Coincidencia EXACTA: para que "BULK" no elija "BREAK BULK"
    exacto = re.compile(rf"^\s*{re.escape(valor)}\s*$", re.I)

    for intento in range(1, 5):
        actual = texto.inner_text().strip()
        if actual.upper() == valor.upper():
            print(f"  Tipo = {valor} (ok)")
            return
        print(f"  Tipo muestra '{actual}', intento {intento} de elegir '{valor}'")
        abrir_lista(page, slicer)
        opciones(page).filter(has_text=exacto).first.click()
        page.wait_for_timeout(3000)   # espera a que los visuales se actualicen
        cerrar_lista(page, slicer)

    raise RuntimeError(f"No se pudo dejar Tipo = {valor}")


def recortar_blanco(archivo):
    """Quita el espacio en blanco que quede debajo del contenido."""
    img = Image.open(archivo).convert("RGB")
    blanco = Image.new("RGB", img.size, (255, 255, 255))
    caja = ImageChops.difference(img, blanco).convert("L").point(lambda v: 255 if v > 25 else 0).getbbox()
    if caja:
        img = img.crop((0, 0, img.width, min(caja[3] + 30, img.height)))
    img.save(archivo)


# ---------- 1. Tomar una captura por cada Tipo ----------
capturas = []
with sync_playwright() as p:
    contexto = p.chromium.launch_persistent_context(
        PERFIL, channel="msedge", headless=False,
        viewport={"width": 1920, "height": 1080}, device_scale_factor=2)
    page = contexto.pages[0] if contexto.pages else contexto.new_page()
    page.goto(URL)

    print("Si Edge te pide iniciar sesión, hazlo en esa ventana (tienes 3 minutos).")
    page.wait_for_selector("visual-container", state="attached", timeout=180000)
    page.wait_for_timeout(8000)

    slicer = buscar_slicer_tipo(page)
    tipos = leer_opciones(page, slicer)
    print("Tipos encontrados:", tipos)

    for tipo in tipos:
        seleccionar(page, slicer, tipo)
        archivo = f"cg_{re.sub(r'[^A-Za-z0-9]+', '_', tipo)}.png"
        lienzo = page.locator(".displayArea").first   # solo el informe, sin menús de Power BI
        if lienzo.count() > 0:
            lienzo.screenshot(path=archivo)
        else:
            page.screenshot(path=archivo)
        recortar_blanco(archivo)
        capturas.append((tipo, archivo))
        print("Capturado:", archivo)

    contexto.close()

# ---------- 2. Armar el reporte: encabezado + (título y captura) por cada Tipo ----------
AZUL = (30, 41, 80)
NARANJA = (232, 90, 36)
GRIS = (110, 110, 110)


def fuente(tamano, negrita=True):
    try:
        return ImageFont.truetype("arialbd.ttf" if negrita else "arial.ttf", tamano)
    except OSError:
        return ImageFont.load_default()


imagenes = [Image.open(a).convert("RGB") for _, a in capturas]
ancho = max(img.width for img in imagenes)
margen, alto_encabezado, alto_titulo, espacio = 80, 260, 150, 70
alto_total = alto_encabezado + sum(alto_titulo + img.height + espacio for img in imagenes) + margen

hoja = Image.new("RGB", (ancho + 2 * margen, alto_total), "white")
d = ImageDraw.Draw(hoja)

hoy = date.today()
semana = hoy.isocalendar().week
d.rectangle([0, 0, hoja.width, 24], fill=NARANJA)
d.text((margen, 70), "Weekly Demand Tracker – General Cargo", fill=AZUL, font=fuente(80))
d.text((margen, 170), f"{SUBTITULO}  ·  Years {TEXTO_ANIOS}  ·  "
                      f"Generated: week {semana} – {hoy:%d/%m/%Y}",
       fill=GRIS, font=fuente(42, negrita=False))

y = alto_encabezado
for (tipo, _), img in zip(capturas, imagenes):
    d.rectangle([margen, y + 30, margen + 14, y + alto_titulo - 30], fill=NARANJA)
    d.text((margen + 40, y + 38), f"Demand Tracker · General Cargo · {tipo} · {TEXTO_ANIOS}",
           fill=AZUL, font=fuente(62))
    y += alto_titulo
    hoja.paste(img, (margen, y))
    y += img.height + espacio

nombre = f"Demand_Tracker_General_Cargo_{hoy.year}_W{semana:02d}"
hoja.save(nombre + ".png")
print("PNG generado:", nombre + ".png")
try:
    hoja.save(nombre + ".pdf", resolution=200)
    print("PDF generado:", nombre + ".pdf")
except Exception as e:
    print("No se pudo crear el PDF:", e)
