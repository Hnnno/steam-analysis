import sqlite3
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(
    page_title="Steam Value Analyzer",
    page_icon="🎮",
    layout="wide"
)

DB_PATH = "data/clean/steam.db"


def query(sql):
    with sqlite3.connect(DB_PATH) as conn:
        return pd.read_sql_query(sql, conn)


@st.cache_data
def load_main(price_max, score_min, min_ratings, solo_pago):
    precio_cond = "AND price > 0" if solo_pago else ""
    return query(f"""
        SELECT name, developer, genres, release_year,
               ROUND(price, 2) AS price,
               average_playtime,
               ROUND(review_score, 1) AS review_score,
               total_ratings,
               ROUND(horas_por_dolar, 1) AS horas_por_dolar,
               ROUND(valor_score, 1) AS valor_score,
               categoria_precio
        FROM games
        WHERE price <= {price_max}
          AND (review_score >= {score_min} OR review_score IS NULL)
          AND total_ratings >= {min_ratings}
          {precio_cond}
        ORDER BY valor_score DESC
    """)


@st.cache_data
def load_tendencias():
    return query("""
        SELECT release_year,
               COUNT(*) AS lanzamientos,
               ROUND(AVG(review_score), 1) AS review_promedio,
               ROUND(AVG(CASE WHEN price > 0 THEN price END), 2) AS precio_promedio
        FROM games
        WHERE release_year BETWEEN 2000 AND 2019
          AND review_score IS NOT NULL
          AND total_ratings >= 50
        GROUP BY release_year
        ORDER BY release_year
    """)


@st.cache_data
def load_generos():
    return query("""
        SELECT genres,
               COUNT(*) AS total_juegos,
               ROUND(AVG(review_score), 1) AS review_promedio,
               ROUND(AVG(CASE WHEN price > 0 THEN price END), 2) AS precio_promedio,
               ROUND(AVG(average_playtime), 0) AS playtime_promedio,
               ROUND(AVG(valor_score), 1) AS valor_promedio
        FROM games
        WHERE review_score IS NOT NULL
          AND total_ratings >= 100
          AND genres NOT LIKE '%,%'
        GROUP BY genres
        HAVING total_juegos >= 40
        ORDER BY review_promedio DESC
        LIMIT 12
    """)


@st.cache_data
def load_desarrolladoras():
    return query("""
        SELECT developer,
               COUNT(*) AS juegos_publicados,
               ROUND(AVG(review_score), 1) AS review_promedio,
               SUM(total_ratings) AS ratings_totales
        FROM games
        WHERE review_score IS NOT NULL
          AND total_ratings >= 50
          AND developer IS NOT NULL AND developer != ''
        GROUP BY developer
        HAVING juegos_publicados >= 5
        ORDER BY review_promedio DESC
        LIMIT 20
    """)


# --- Sidebar ---
st.sidebar.title("Filtros")
price_max   = st.sidebar.slider("Precio máximo (USD)", 0, 60, 30, step=1)
score_min   = st.sidebar.slider("Review score mínimo (%)", 0, 100, 60, step=5)
min_ratings = st.sidebar.slider("Mínimo de reviews", 10, 500, 50, step=10)
solo_pago   = st.sidebar.checkbox("Solo juegos de pago", value=True)

df = load_main(price_max, score_min, min_ratings, solo_pago)

# --- Header ---
st.title("¿Qué juegos en Steam valen su precio?")
st.caption("Análisis del catálogo de Steam · fuente: Kaggle — Steam Store Games")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Juegos encontrados", f"{len(df):,}")
c2.metric("Precio promedio", f"${df['price'].mean():.2f}" if len(df) else "—")
c3.metric("Review score promedio", f"{df['review_score'].mean():.1f}%" if len(df) else "—")
c4.metric("Valor score promedio",
          f"{df['valor_score'].mean():.1f}" if df['valor_score'].notna().any() else "—")

st.divider()

# ================================================================
# 1 — Exploración principal
# ================================================================
st.header("Exploración principal")

col_a, col_b = st.columns([3, 2])

with col_a:
    st.subheader("Precio vs tiempo de juego")
    df_sc = df[df["horas_por_dolar"].notna()].head(500)
    fig = px.scatter(
        df_sc, x="price", y="average_playtime",
        size="horas_por_dolar", color="review_score",
        hover_name="name",
        hover_data={"price": True, "review_score": True, "horas_por_dolar": True},
        color_continuous_scale="Viridis",
        labels={"price": "Precio (USD)", "average_playtime": "Horas promedio",
                "review_score": "Review (%)"},
        size_max=25, opacity=0.75
    )
    fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=360)
    st.plotly_chart(fig, use_container_width=True)

with col_b:
    st.subheader("Top 20 — horas por dólar")
    top20 = df[df["horas_por_dolar"].notna()].head(20)
    fig2 = px.bar(
        top20.sort_values("horas_por_dolar"),
        x="horas_por_dolar", y="name", orientation="h",
        color="review_score", color_continuous_scale="Greens",
        labels={"horas_por_dolar": "Horas/$", "name": "", "review_score": "Review (%)"},
    )
    fig2.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=360)
    st.plotly_chart(fig2, use_container_width=True)

st.divider()

# ================================================================
# 2 — Métrica compuesta de valor
# ================================================================
st.header("Métrica compuesta de valor")
st.caption("valor_score combina: review score (50%) + horas por dólar (35%) + popularidad (15%)")

df_valor = df[df["valor_score"].notna()].head(25)
fig3 = px.bar(
    df_valor.sort_values("valor_score"),
    x="valor_score", y="name", orientation="h",
    color="valor_score", color_continuous_scale="Oranges",
    hover_data={"price": True, "review_score": True, "horas_por_dolar": True},
    labels={"valor_score": "Valor score", "name": ""},
)
fig3.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=520,
                   coloraxis_showscale=False)
st.plotly_chart(fig3, use_container_width=True)

st.divider()

# ================================================================
# 3 — Tendencias por año
# ================================================================
st.header("Tendencias por año de lanzamiento")

df_anio = load_tendencias()
col_c, col_d = st.columns(2)

with col_c:
    fig4 = px.bar(df_anio, x="release_year", y="lanzamientos",
                  labels={"release_year": "Año", "lanzamientos": "Juegos lanzados"},
                  title="Lanzamientos por año",
                  color_discrete_sequence=["#5b8db8"])
    fig4.update_layout(margin=dict(l=0, r=0, t=40, b=0), height=300)
    st.plotly_chart(fig4, use_container_width=True)

with col_d:
    fig5 = px.line(
        df_anio, x="release_year",
        y=["review_promedio", "precio_promedio"],
        labels={"release_year": "Año", "value": "Valor", "variable": "Métrica"},
        title="Review score y precio promedio por año",
        color_discrete_map={"review_promedio": "#4a9e6b", "precio_promedio": "#e07b39"}
    )
    fig5.update_layout(margin=dict(l=0, r=0, t=40, b=0), height=300)
    st.plotly_chart(fig5, use_container_width=True)

st.divider()

# ================================================================
# 4 — Comparativa de géneros
# ================================================================
st.header("Comparativa entre géneros")

df_gen = load_generos()
metrica = st.radio(
    "Ver por",
    ["review_promedio", "precio_promedio", "playtime_promedio", "valor_promedio"],
    horizontal=True,
    format_func=lambda x: {
        "review_promedio": "Review score",
        "precio_promedio": "Precio promedio",
        "playtime_promedio": "Playtime promedio",
        "valor_promedio": "Valor score"
    }[x]
)

fig6 = px.bar(
    df_gen.sort_values(metrica),
    x=metrica, y="genres", orientation="h",
    color=metrica, color_continuous_scale="Blues",
    labels={"genres": "", metrica: metrica.replace("_", " ").title()},
    hover_data={"total_juegos": True}
)
fig6.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=420,
                   coloraxis_showscale=False)
st.plotly_chart(fig6, use_container_width=True)

st.divider()

# ================================================================
# 5 — Ranking de desarrolladoras
# ================================================================
st.header("Ranking de desarrolladoras")
st.caption("Mínimo 5 juegos publicados · al menos 50 reviews por juego")

df_dev = load_desarrolladoras()
fig7 = px.bar(
    df_dev.sort_values("review_promedio"),
    x="review_promedio", y="developer", orientation="h",
    color="juegos_publicados", color_continuous_scale="Purples",
    labels={"review_promedio": "Review score promedio (%)",
            "developer": "", "juegos_publicados": "Juegos"},
    hover_data={"juegos_publicados": True, "ratings_totales": True}
)
fig7.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=560)
st.plotly_chart(fig7, use_container_width=True)

st.divider()

# ================================================================
# Tabla completa
# ================================================================
st.subheader("Tabla completa")
st.dataframe(
    df[["name", "genres", "price", "review_score", "average_playtime",
        "horas_por_dolar", "valor_score", "total_ratings", "developer"]].reset_index(drop=True),
    use_container_width=True,
    height=350
)