# Alerta de Estado de Puertos del Perú (DICAPI)

**Herramientas:** Python · API REST · Playwright · Outlook (pywin32) · Programador de tareas de Windows

## Problema
El estado de los puertos del Perú (abierto, cierre parcial o cierre total) se publica en la web de DICAPI. Para enterarse de un cierre había que entrar a revisar la página manualmente, y un cambio podía pasar desapercibido durante horas.

## Solución
Un sistema en Python que revisa el estado de los puertos cada hora y **envía una alerta por correo solo cuando algún puerto cambia de nivel**, incluida su reapertura.

1. **Consulta la API** pública que usa la propia web de DICAPI (`/api/ports`), identificada con las herramientas de desarrollador del navegador.
2. **Compara** el estado de cada puerto con la última revisión, guardada en `estado_anterior.json`.
3. **Si hay cambios**, genera un **reporte PDF** con diseño (tarjetas de resumen, tabla de puertos con restricción y resumen por capitanía) usando HTML + Playwright.
4. **Envía el correo** por Outlook con un cuerpo HTML que destaca los cambios (por ejemplo, *Nivel I → Nivel V*) y el PDF adjunto.
5. **Se programa** con el Programador de tareas de Windows para ejecutarse cada hora.

## Estructura
| Archivo | Qué hace |
|---|---|
| `paso1_consultar_puertos.py` | Prueba de lectura de la API y listado en consola |
| `paso2_reporte_pdf.py` | Obtiene los datos y genera el reporte PDF |
| `paso3_enviar_correo.py` | Configuración y diseño del correo; envía el estado actual |
| `paso4_alerta_cambios.py` | Detecta cambios y envía la alerta solo cuando corresponde |
| `ejecutar_alerta.bat` | Lanzador para el Programador de tareas |

## Técnicas destacadas
- Identificación de la API interna de una web con DevTools (pestaña Network → Fetch/XHR).
- Solución de errores SSL en redes corporativas con `truststore`, sin desactivar la verificación de seguridad.
- Detección de cambios comparando el estado actual con el anterior (persistencia en JSON).
- Generación de PDF desde HTML con Playwright usando el navegador Edge instalado.
- Correos HTML compatibles con Outlook (tablas y estilos en línea).
- El estado solo se actualiza si el correo se envió, para no perder alertas.

## Cómo usarlo
1. Instala las dependencias: `pip install -r requirements.txt`
2. Edita la sección **CONFIGURACIÓN** de `paso3_enviar_correo.py` (destinatarios, firma y `MODO_PRUEBA`).
3. Ejecuta `python paso4_alerta_cambios.py`. La primera vez envía un correo de "Inicio de monitoreo".
4. Programa `ejecutar_alerta.bat` en el Programador de tareas (por ejemplo, cada hora).

Requisitos: Windows, Outlook clásico de escritorio y Microsoft Edge.

> Fuente de datos: https://www.dicapi.mil.pe/estado-de-puertos (información pública). Verificar siempre la resolución oficial antes de tomar decisiones operativas.
