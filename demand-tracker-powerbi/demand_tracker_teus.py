# =============================================================
# Demand Tracker TEUs - captura automática de un informe público de Power BI
# Abre el informe, aplica filtros (Año, Operación, Tipo), toma capturas
# y arma un reporte PNG/PDF semanal con encabezado y secciones.
# =============================================================
from playwright.sync_api import sync_playwright
from PIL import Image, ImageDraw, ImageFont, ImageChops
from PIL import JpegImagePlugin, PdfImagePlugin  # registra los formatos que usa el PDF
from datetime import date

# ---------- CONFIGURACIÓN ----------
SUBTITULO = "EMPRESA"   # aparece en el encabezado del reporte
import re

URL = "https://app.powerbi.com/view?r=<enlace-publico-del-informe>"   # informe publicado en la web

# Texto que solo aparece en la página del gráfico de TEUs (leyenda del gráfico)
TEXTO_PAGINA = "dif 2v8"

# El informe ya abre con 2025 marcado; solo hay que AGREGAR estos años
ANIOS_AGREGAR = ["2026"]

# (Operación, Tipo) en el orden en que irán en el PDF
COMBINACIONES = [
    ("Importaciones", "DRY"),
    ("Exportaciones", "DRY"),
    ("Exportaciones", "REEFER"),
]


def esta_en_pagina(page):
    return page.get_by_text(TEXTO_PAGINA).count() > 0


def ir_a_pagina(page):
    """Avanza (y si hace falta, retrocede) página por página hasta encontrar el gráfico."""
    for flecha in ["Next Page", "Previous Page"]:
        for _ in range(12):  # límite de seguridad
            if esta_en_pagina(page):
                print("Página del gráfico encontrada")
                return
            boton = page.get_by_role("button", name=re.compile(flecha, re.I)).first
            if boton.is_disabled():
                break  # llegó al final en esa dirección
            boton.click()
            page.wait_for_timeout(4000)
    raise RuntimeError("No se encontró la página con el texto: " + TEXTO_PAGINA)


def cerrar_listas(page):
    """Cierra cualquier desplegable abierto haciendo clic en una zona vacía."""
    page.mouse.click(5, 5)
    page.wait_for_timeout(800)


def opciones(page):
    """Opciones de la lista desplegable que esté abierta."""
    return page.locator(".slicer-dropdown-popup:visible .slicerItemContainer")


def seleccionar(page, titulo_slicer, valor):
    """Elige un valor en el slicer y COMPRUEBA que quedó; si no, vuelve a intentar."""
    slicer = page.locator("visual-container").filter(has_text=titulo_slicer).first
    texto = slicer.locator(".slicer-restatement")

    for intento in range(1, 5):
        actual = texto.inner_text().strip()
        if actual.upper() == valor.upper():
            print(f"  {titulo_slicer} = {valor} (ok)")
            return
        print(f"  {titulo_slicer}: muestra '{actual}', intento {intento} de elegir '{valor}'")

        cerrar_listas(page)
        slicer.locator(".slicer-dropdown-menu").click()
        page.wait_for_timeout(1500)

        opcion = opciones(page).filter(has_text=valor).first
        if opcion.count() == 0:
            # Puede que la opción esté más abajo en la lista: bajamos con la rueda del mouse
            caja = page.locator(".slicer-dropdown-popup:visible").first.bounding_box()
            if caja:
                page.mouse.move(caja["x"] + caja["width"] / 2, caja["y"] + caja["height"] / 2)
                page.mouse.wheel(0, 400)
                page.wait_for_timeout(1000)
        if opcion.count() == 0:
            print("  Opciones que aparecen en la lista:", opciones(page).all_inner_texts())
            continue

        opcion.click()
        page.wait_for_timeout(3000)  # espera a que el gráfico se actualice
        cerrar_listas(page)

    raise RuntimeError(f"No se pudo dejar {titulo_slicer} = {valor}")


def agregar_anios(page, valores):
    """Agrega años al filtro Año con Ctrl + clic, sin tocar el que ya está marcado."""
    slicer = page.locator("visual-container").filter(has_text="Año").first
    texto = slicer.locator(".slicer-restatement")
    antes = texto.inner_text().strip()
    print(f"  Año antes: '{antes}'")

    # Si ya muestra selección múltiple, los años ya están puestos: no hacemos nada
    if "multiple" in antes.lower() or "múltiple" in antes.lower():
        return

    cerrar_listas(page)
    slicer.locator(".slicer-dropdown-menu").click()
    page.wait_for_timeout(1500)
    for valor in valores:
        opciones(page).filter(has_text=valor).first.click(modifiers=["Control"])
        page.wait_for_timeout(2000)
    cerrar_listas(page)
    page.wait_for_timeout(2000)
    print(f"  Año después: '{texto.inner_text().strip()}'")


def recortar(archivo):
    """Quita la barra inferior de Power BI y el espacio en blanco debajo del gráfico."""
    img = Image.open(archivo).convert("RGB")
    img = img.crop((0, 0, img.width, img.height - 140))          # barra inferior (zoom y páginas)
    blanco = Image.new("RGB", img.size, (255, 255, 255))
    diferencia = ImageChops.difference(img, blanco).convert("L").point(lambda v: 255 if v > 25 else 0)
    caja = diferencia.getbbox()                                    # zona que no es blanca
    if caja:
        img = img.crop((0, 0, img.width, min(caja[3] + 30, img.height)))
    img.save(archivo)


# ---------- 1. Tomar las 3 capturas ----------
capturas = []
with sync_playwright() as p:
    browser = p.chromium.launch(channel="msedge", headless=False)
    page = browser.new_page(viewport={"width": 1920, "height": 1080}, device_scale_factor=2)
    page.goto(URL)
    page.wait_for_selector("visual-container", state="attached", timeout=60000)
    page.wait_for_timeout(6000)
    ir_a_pagina(page)
    agregar_anios(page, ANIOS_AGREGAR)

    for operacion, tipo in COMBINACIONES:
        seleccionar(page, "OPERACION", operacion)
        seleccionar(page, "TIPO", tipo)
        archivo = f"captura_{operacion}_{tipo}.png"
        page.screenshot(path=archivo)
        recortar(archivo)
        capturas.append((operacion, tipo, archivo))
        print("Capturado:", archivo)

    browser.close()

# ---------- 2. Armar el PDF: encabezado + (título y captura) x 3, uno debajo del otro ----------
AZUL = (30, 41, 80)
NARANJA = (232, 90, 36)
GRIS = (110, 110, 110)
TEXTO_ANIOS = "2025 – 2026"
EN_INGLES = {"Importaciones": "Imports", "Exportaciones": "Exports"}  # solo para los títulos


def fuente(tamano, negrita=True):
    try:
        return ImageFont.truetype("arialbd.ttf" if negrita else "arial.ttf", tamano)
    except OSError:
        return ImageFont.load_default()


imagenes = [Image.open(a).convert("RGB") for _, _, a in capturas]
ancho = max(img.width for img in imagenes)
margen = 80
alto_encabezado = 260
alto_titulo = 150
espacio = 70

alto_total = alto_encabezado + sum(alto_titulo + img.height + espacio for img in imagenes) + margen
hoja = Image.new("RGB", (ancho + 2 * margen, alto_total), "white")
d = ImageDraw.Draw(hoja)

# Encabezado general
hoy = date.today()
semana = hoy.isocalendar().week
d.rectangle([0, 0, hoja.width, 24], fill=NARANJA)
d.text((margen, 70), "Weekly Demand Tracker (TEUs)", fill=AZUL, font=fuente(80))
d.text((margen, 170), f"{SUBTITULO}  ·  2, 4 & 8-week moving averages  ·  "
                      f"Years {TEXTO_ANIOS}  ·  Generated: week {semana} – {hoy:%d/%m/%Y}",
       fill=GRIS, font=fuente(42, negrita=False))

# Secciones
y = alto_encabezado
for (operacion, tipo, _), img in zip(capturas, imagenes):
    d.rectangle([margen, y + 30, margen + 14, y + alto_titulo - 30], fill=NARANJA)  # barrita naranja
    d.text((margen + 40, y + 38), f"Demand Tracker · {EN_INGLES.get(operacion, operacion)} · {tipo} · {TEXTO_ANIOS}",
           fill=AZUL, font=fuente(62))
    y += alto_titulo
    hoja.paste(img, (margen, y))
    y += img.height + espacio

nombre = f"Demand_Tracker_TEUs_{hoy.year}_W{semana:02d}"

# 1) Siempre guardamos la hoja completa en PNG
hoja.save(nombre + ".png")
print("PNG generado:", nombre + ".png")

# 2) Y la convertimos a PDF
try:
    hoja.save(nombre + ".pdf", resolution=200)
    print("PDF generado:", nombre + ".pdf")
except Exception as e:
    print("No se pudo crear el PDF:", e)
