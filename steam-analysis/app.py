import sqlite3
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(
    page_title="Steam Value Analyzer",
    page_icon="🎮",
    layout="wide"
)

DB_PATH = "data/clean/steam.db"


@st.cache_data
def load_data(price_max, score_min, min_ratings):
    with sqlite3.connect(DB_PATH) as conn:
        return pd.read_sql_query(f"""
            SELECT
                name, developer, genres, release_year,
                ROUND(price, 2) AS price,
                average_playtime,
                ROUND(review_score, 1) AS review_score,
                total_ratings,
                ROUND(horas_por_dolar, 1) AS horas_por_dolar,
                categoria_precio
            FROM games
            WHERE price <= {price_max}
              AND (review_score >= {score_min} OR review_score IS NULL)
              AND total_ratings >= {min_ratings}
            ORDER BY horas_por_dolar DESC
        """, conn)


@st.cache_data
def load_genre_data():
    with sqlite3.connect(DB_PATH) as conn:
        return pd.read_sql_query("""
            SELECT genres,
                   COUNT(*) AS total,
                   ROUND(AVG(review_score), 1) AS review_promedio,
                   ROUND(AVG(price), 2) AS precio_promedio
            FROM games
            WHERE review_score IS NOT NULL
              AND total_ratings >= 100
              AND genres NOT LIKE '%,%'
            GROUP BY genres
            HAVING total >= 30
            ORDER BY review_promedio DESC
            LIMIT 15
        """, conn)


# --- Sidebar ---
st.sidebar.title("Filtros")

price_max = st.sidebar.slider("Precio máximo (USD)", 0, 60, 30, step=1)
score_min = st.sidebar.slider("Review score mínimo (%)", 0, 100, 60, step=5)
min_ratings = st.sidebar.slider("Mínimo de reviews", 10, 500, 50, step=10)
solo_pago = st.sidebar.checkbox("Solo juegos de pago", value=True)

df = load_data(price_max, score_min, min_ratings)

if solo_pago:
    df = df[df["price"] > 0]

# --- Header ---
st.title("¿Qué juegos en Steam valen su precio?")
st.caption("Análisis del catálogo de Steam · fuente: Kaggle — Steam Store Games")

# --- Métricas resumen ---
col1, col2, col3, col4 = st.columns(4)
col1.metric("Juegos encontrados", f"{len(df):,}")
col2.metric("Precio promedio", f"${df['price'].mean():.2f}" if len(df) else "—")
col3.metric("Review score promedio", f"{df['review_score'].mean():.1f}%" if len(df) else "—")
col4.metric("Horas/dólar promedio",
            f"{df['horas_por_dolar'].mean():.1f}h" if df['horas_por_dolar'].notna().any() else "—")

st.divider()

# --- Scatter: precio vs playtime ---
col_a, col_b = st.columns([3, 2])

with col_a:
    st.subheader("Precio vs tiempo de juego")
    df_scatter = df[df["horas_por_dolar"].notna()].head(500)
    fig = px.scatter(
        df_scatter,
        x="price", y="average_playtime",
        size="horas_por_dolar",
        color="review_score",
        hover_name="name",
        hover_data={"price": True, "review_score": True, "horas_por_dolar": True},
        color_continuous_scale="Viridis",
        labels={
            "price": "Precio (USD)",
            "average_playtime": "Horas promedio",
            "review_score": "Review score (%)"
        },
        size_max=25,
        opacity=0.75
    )
    fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=380)
    st.plotly_chart(fig, use_container_width=True)

with col_b:
    st.subheader("Review score por género")
    df_gen = load_genre_data()
    fig2 = px.bar(
        df_gen.sort_values("review_promedio"),
        x="review_promedio", y="genres",
        orientation="h",
        color="review_promedio",
        color_continuous_scale="Blues",
        labels={"review_promedio": "Review score (%)", "genres": ""},
    )
    fig2.update_layout(margin=dict(l=0, r=0, t=0, b=0),
                       height=380, showlegend=False,
                       coloraxis_showscale=False)
    st.plotly_chart(fig2, use_container_width=True)

st.divider()

# --- Top 20 horas por dólar ---
st.subheader("Top 20 — más horas de juego por dólar")
st.caption("Juegos con review score ≥ filtro seleccionado y precio > $0")

top20 = df[df["horas_por_dolar"].notna()].head(20)
fig3 = px.bar(
    top20.sort_values("horas_por_dolar"),
    x="horas_por_dolar", y="name",
    orientation="h",
    color="review_score",
    color_continuous_scale="Greens",
    hover_data={"price": True, "genres": True},
    labels={"horas_por_dolar": "Horas por dólar", "name": "", "review_score": "Review (%)"},
)
fig3.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=480,
                   coloraxis_showscale=True)
st.plotly_chart(fig3, use_container_width=True)

st.divider()

# --- Tabla completa ---
st.subheader("Tabla completa")
st.dataframe(
    df[["name", "genres", "price", "review_score", "average_playtime",
        "horas_por_dolar", "total_ratings", "developer"]].reset_index(drop=True),
    use_container_width=True,
    height=350
)
