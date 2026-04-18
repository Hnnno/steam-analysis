# Steam Value Analyzer

Proyecto end-to-end de análisis de datos sobre el catálogo de Steam. Responde una pregunta concreta: **¿qué juegos realmente valen su precio?**

Forma parte de un portafolio de Data Analyst. Cubre el pipeline completo: obtención de datos → SQL → análisis en Python → dashboard interactivo.

---

## Metas del proyecto

### v1 — Pipeline base (estado actual)
- [x] Estructura del repositorio definida
- [x] Script de limpieza y carga a SQLite (`01_cleaning.ipynb`)
- [x] Análisis exploratorio con SQL + Python (`02_analysis.ipynb`)
- [x] Dashboard básico funcional en Streamlit (`app.py`)

### v2 — Análisis más profundo
- [ ] Análisis de tendencias por año de lanzamiento
- [ ] Comparativa entre géneros: precio, playtime y reviews
- [ ] Ranking de desarrolladoras por review score histórico
- [ ] Métrica compuesta de "valor": combina precio, playtime y reviews

### v3 — Dashboard completo
- [ ] Filtros por género, año y rango de precio
- [ ] Vista de detalle por juego individual
- [ ] Gráfico de evolución histórica de lanzamientos
- [ ] Deploy en Streamlit Cloud con URL pública

### v4 — Extensiones futuras
- [ ] Integrar datos en tiempo real desde la Steam API
- [ ] Modelo de recomendación simple basado en géneros y playtime
- [ ] Comparar precios históricos usando SteamDB

---

## Dataset

- **Fuente:** [Kaggle — Steam Store Games](https://www.kaggle.com/datasets/nikdavis/steam-store-games)
- **Archivo:** `steam.csv` (~27.000 juegos)
- **Columnas clave:** `name`, `price`, `genres`, `positive_ratings`, `negative_ratings`, `average_playtime`, `release_date`

> Descargar `steam.csv` y colocarlo en `data/raw/` antes de ejecutar los notebooks.

---

## Estructura

```
steam-analysis/
├── data/
│   ├── raw/            # steam.csv (descargar desde Kaggle)
│   └── clean/          # steam.db (generado por 01_cleaning.ipynb)
├── notebooks/
│   ├── 01_cleaning.ipynb
│   └── 02_analysis.ipynb
├── img/                # gráficos exportados
├── app.py              # dashboard Streamlit
├── requirements.txt
└── README.md
```

---

## Cómo ejecutar

```bash
# 1. Instalar dependencias
pip install -r requirements.txt

# 2. Colocar steam.csv en data/raw/

# 3. Ejecutar notebooks en orden
jupyter notebook notebooks/01_cleaning.ipynb
jupyter notebook notebooks/02_analysis.ipynb

# 4. Lanzar el dashboard
streamlit run app.py
```

---

## Preguntas que responde el proyecto

- ¿Qué géneros tienen mejor review score promedio?
- ¿Cuáles son los juegos con más horas de juego por dólar?
- ¿Hay correlación entre precio y calidad percibida?
- ¿Qué año tuvo los mejores lanzamientos?
- ¿Los juegos gratuitos tienen peores reviews que los de pago?
- ¿Qué desarrolladora tiene el mejor promedio histórico?

---

## Tecnologías

- Python 3.10+
- pandas · numpy · matplotlib · seaborn · plotly
- SQLite (via `sqlite3`)
- Streamlit

---

## Autor

Proyecto de portafolio personal. Datos públicos de [Kaggle](https://www.kaggle.com).
