# Proyecto Office Max

Proyecto de analisis de elasticidad promocional para Office Max.

## Contenido

- `index.html`: simulador interactivo de PromoIntel AI para cargar bases CSV, filtrar SKUs y visualizar graficas.
- `scripts/`: scripts de procesamiento, modelado y generacion de reportes.
- `Promociones/`: documentos fuente de promociones.
- `output/`: resultados, reportes y archivos generados.
- `PROGRESO.md`: avance del proyecto, metricas e informacion de seguimiento.
- `requirements.txt`: dependencias necesarias para ejecutar los scripts.

## Simulador Interactivo

El front del proyecto esta en `index.html`.

- En local: abre `index.html` en el navegador.
- En GitHub Pages: `https://landin2312.github.io/Proyecto-Office-Max/`

Para publicar el simulador desde GitHub, activa Pages en `Settings > Pages` y selecciona `GitHub Actions` como fuente. Cada push a `main` publicara automaticamente el front.

## Archivos Para Revision

- [elasticidad_visualizaciones_v2.pdf](elasticidad_visualizaciones_v2.pdf): representacion grafica de los hallazgos.
- [modelo1_betas_loglog.csv](output/modelo1_betas_loglog.csv): resultados del modelo log-log.
- [modelo2_betas_con_controles.csv](output/modelo2_betas_con_controles.csv): resultados del modelo con controles.

## Estado

El detalle del avance y hallazgos esta documentado en `PROGRESO.md`.
