# Demand Tracker semanal desde Power BI

**Herramientas:** Python · Playwright · Pillow · Microsoft Edge · Power BI

## Problema
Cada semana había que entrar a dos informes de Power BI, cambiar los filtros uno por uno (año, operación, tipo de carga), tomar capturas de cada combinación y armar a mano un reporte para la jefatura. Era una tarea repetitiva que tomaba tiempo y dependía de no olvidar ninguna combinación.

## Solución
Dos scripts que navegan los informes de Power BI como lo haría una persona y generan el reporte semanal listo para enviar.

### 1. `demand_tracker_teus.py` – Volumen de TEUs
1. Abre un informe **público** de Power BI en Edge.
2. Busca automáticamente la página del gráfico, avanzando o retrocediendo entre páginas.
3. Agrega el año actual al filtro **Año** con Ctrl + clic, sin quitar el que ya está marcado.
4. Recorre las combinaciones **Operación × Tipo** (Importaciones DRY, Exportaciones DRY, Exportaciones REEFER), verificando que cada filtro realmente quedó aplicado y reintentando si no.
5. Toma una captura de cada combinación y recorta la barra inferior y los espacios en blanco.

### 2. `demand_tracker_carga_general.py` – Carga General
1. Abre un informe **interno** de Power BI con un **perfil persistente de Edge**: se inicia sesión solo la primera vez.
2. **Lee todos los valores** del filtro **Tipo**, de modo que si aparece un tipo nuevo se incluye solo.
3. Selecciona cada tipo con **coincidencia exacta** (para que "BULK" no elija "BREAK BULK") y captura solo el lienzo del informe.

### En ambos casos
Las capturas se unen en una sola hoja con encabezado, número de semana ISO, fecha y títulos por sección, y se guardan en **PNG y PDF** (`Demand_Tracker_..._2026_W45.pdf`).

## Técnicas destacadas
- Automatización de navegador con **Playwright** sobre el Edge instalado (`channel="msedge"`).
- Selectores robustos para *slicers* de Power BI y **verificación con reintentos** de cada filtro.
- Perfil persistente del navegador para reutilizar la sesión de Microsoft sin guardar contraseñas en el código.
- Procesamiento de imágenes con **Pillow**: recorte automático de bordes en blanco y armado del reporte.
- Nombres de archivo con **semana ISO** para mantener un histórico ordenado.

## Resultado
- El reporte semanal se genera con **un solo comando**.
- [Agrega aquí el tiempo ahorrado, por ejemplo: de ~X minutos a menos de 2 minutos por semana.]
- Siempre se incluyen todas las combinaciones, sin olvidos.

## Cómo usarlo
1. Instala las dependencias: `pip install -r requirements.txt`
2. Coloca en `URL` el enlace del informe y ajusta `SUBTITULO`.
3. Ejecuta `python demand_tracker_teus.py` o `python demand_tracker_carga_general.py`.

Requisitos: Windows y Microsoft Edge.

> Versión adaptada para portafolio: los enlaces a los informes fueron reemplazados por marcadores `<...>`. La carpeta `perfil_edge` (sesión del navegador) y los reportes generados están excluidos con `.gitignore` y nunca deben publicarse.
