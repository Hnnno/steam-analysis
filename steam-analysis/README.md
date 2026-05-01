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
- [x] Análisis de tendencias por año de lanzamiento
- [x] Comparativa entre géneros: precio, playtime y reviews
- [x] Ranking de desarrolladoras por review score histórico
- [x] Métrica compuesta de "valor": combina precio, playtime y reviews

### v3 — Dashboard completo
- [x] Filtros por género, año y rango de precio
- [x] Vista de detalle por juego individual
- [x] Gráfico de evolución histórica de lanzamientos
- [x] Deploy en Streamlit Cloud con URL pública

### v4 — Extensiones futuras
- [x] Integrar datos en tiempo real desde la Steam API (precio actual, imagen, descripción)
- [x] Modelo de recomendación basado en géneros, playtime y review score (cosine similarity)
- [x] Comparativa de precio del dataset vs precio actual en Steam

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

## Deploy en Streamlit Cloud

1. Subí el repositorio a GitHub (sin `data/` — está en `.gitignore`)
2. Entrá a [share.streamlit.io](https://share.streamlit.io) e iniciá sesión con GitHub
3. **New app** → seleccioná el repo → `app.py` como archivo principal
4. En **Advanced settings → Secrets**, agregá la ruta de la base de datos si es necesario
5. Click en **Deploy** — en 2 minutos tenés la URL pública

> **Nota:** Streamlit Cloud no puede generar `steam.db` en el servidor porque el dataset no está en el repo. Opciones:
> - Subir `steam.db` a Google Drive y descargarlo al inicio del app con `gdown`
> - Usar [Supabase](https://supabase.com) (PostgreSQL gratuito) como base de datos en la nube
> - Subir el CSV a GitHub LFS y adaptar el notebook para correr en el servidor

---

## Tecnologías

- Python 3.10+
- pandas · numpy · matplotlib · seaborn · plotly
- SQLite (via `sqlite3`)
- Streamlit

---

## Autor

Proyecto de portafolio personal. Datos públicos de [Kaggle](https://www.kaggle.com).