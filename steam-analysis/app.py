import sqlite3
import requests
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics.pairwise import cosine_similarity

st.set_page_config(
    page_title="Steam Value Analyzer",
    page_icon="🎮",
    layout="wide"
)

DB_PATH = "data/clean/steam.db"
STEAM_API_URL = "https://store.steampowered.com/api/appdetails"


# ================================================================
# Helpers de base de datos
# ================================================================

def query(sql, params=None):
    with sqlite3.connect(DB_PATH) as conn:
        return pd.read_sql_query(sql, conn, params=params)


@st.cache_data
def get_filter_options():
    generos = query("""
        SELECT DISTINCT genres FROM games
        WHERE genres NOT LIKE '%,%' AND genres IS NOT NULL
        ORDER BY genres
    """)["genres"].tolist()

    anios = query("""
        SELECT DISTINCT release_year FROM games
        WHERE release_year BETWEEN 2000 AND 2019
        ORDER BY release_year
    """)["release_year"].dropna().astype(int).tolist()

    return generos, anios


@st.cache_data
def load_main(generos_sel, anio_min, anio_max, precio_min, precio_max,
              score_min, min_ratings, solo_pago):
    gen_filter  = f"AND genres IN ({','.join(['?']*len(generos_sel))})" if generos_sel else ""
    precio_pago = "AND price > 0" if solo_pago else ""
    params = [*generos_sel, anio_min, anio_max, precio_min, precio_max, score_min, min_ratings]
    return query(f"""
        SELECT appid, name, developer, genres, release_year,
               ROUND(price, 2) AS price,
               average_playtime,
               ROUND(review_score, 1) AS review_score,
               total_ratings,
               ROUND(horas_por_dolar, 1) AS horas_por_dolar,
               ROUND(valor_score, 1) AS valor_score,
               categoria_precio
        FROM games
        WHERE release_year BETWEEN ? AND ?
          AND price BETWEEN ? AND ?
          AND (review_score >= ? OR review_score IS NULL)
          AND total_ratings >= ?
          {gen_filter}
          {precio_pago}
        ORDER BY valor_score DESC
    """, params)


@st.cache_data
def load_all_for_recommender():
    return query("""
        SELECT appid, name, genres, price, average_playtime,
               review_score, horas_por_dolar, valor_score, total_ratings
        FROM games
        WHERE review_score IS NOT NULL
          AND price > 0
          AND average_playtime > 0
          AND total_ratings >= 20
    """)


@st.cache_data
def load_evolucion():
    return query("""
        SELECT release_year,
               COUNT(*) AS lanzamientos,
               ROUND(AVG(review_score), 1) AS review_promedio,
               ROUND(AVG(CASE WHEN price > 0 THEN price END), 2) AS precio_promedio,
               SUM(total_ratings) AS ratings_totales
        FROM games
        WHERE release_year BETWEEN 2000 AND 2019
          AND review_score IS NOT NULL
          AND total_ratings >= 50
        GROUP BY release_year
        ORDER BY release_year
    """)


@st.cache_data
def load_generos_overview():
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


# ================================================================
# Steam API
# ================================================================

@st.cache_data(ttl=3600)
def fetch_steam_data(appid):
    """Trae datos en tiempo real de un juego desde la Steam Store API."""
    try:
        resp = requests.get(
            STEAM_API_URL,
            params={"appids": appid, "cc": "us", "l": "en"},
            timeout=8
        )
        data = resp.json().get(str(appid), {})
        if not data.get("success"):
            return None
        d = data["data"]
        price_raw = d.get("price_overview", {})
        return {
            "name":         d.get("name"),
            "description":  d.get("short_description", ""),
            "header_image": d.get("header_image", ""),
            "genres":       ", ".join(g["description"] for g in d.get("genres", [])),
            "developers":   ", ".join(d.get("developers", [])),
            "price_actual": price_raw.get("final", 0) / 100 if price_raw else 0,
            "price_fmt":    price_raw.get("final_formatted", "Gratuito"),
            "is_free":      d.get("is_free", False),
            "metacritic":   d.get("metacritic", {}).get("score"),
            "website":      d.get("website", ""),
            "steam_url":    f"https://store.steampowered.com/app/{appid}",
        }
    except Exception:
        return None


# ================================================================
# Recomendador (cosine similarity)
# ================================================================

@st.cache_data
def build_recommender_matrix():
    df_r = load_all_for_recommender().copy()

    # Encode géneros como dummies
    genre_dummies = df_r["genres"].str.get_dummies(sep=";")

    # Normalizar métricas numéricas
    num_cols = ["price", "average_playtime", "review_score",
                "horas_por_dolar", "valor_score", "total_ratings"]
    scaler = MinMaxScaler()
    num_scaled = pd.DataFrame(
        scaler.fit_transform(df_r[num_cols].fillna(0)),
        columns=num_cols,
        index=df_r.index
    )

    # Pesos: géneros 40%, métricas 60%
    feature_matrix = pd.concat([
        genre_dummies * 0.4,
        num_scaled * 0.6
    ], axis=1)

    similarity = cosine_similarity(feature_matrix)
    return df_r.reset_index(drop=True), similarity


def get_recommendations(nombre, n=10):
    df_r, sim = build_recommender_matrix()
    matches = df_r[df_r["name"] == nombre]
    if matches.empty:
        return pd.DataFrame()
    idx = matches.index[0]
    scores = list(enumerate(sim[idx]))
    scores = sorted(scores, key=lambda x: x[1], reverse=True)[1:n+1]
    indices = [i for i, _ in scores]
    sim_scores = [round(s * 100, 1) for _, s in scores]
    result = df_r.iloc[indices].copy()
    result["similitud (%)"] = sim_scores
    return result[["name", "genres", "price", "review_score",
                   "horas_por_dolar", "valor_score", "similitud (%)"]].reset_index(drop=True)


# ================================================================
# Sidebar
# ================================================================
st.sidebar.title("🎮 Filtros")

generos_opts, anios_opts = get_filter_options()

with st.sidebar.expander("Género", expanded=True):
    generos_sel = st.multiselect("Seleccionar géneros", generos_opts, placeholder="Todos")

with st.sidebar.expander("Año de lanzamiento", expanded=True):
    anio_min, anio_max = st.select_slider(
        "Rango de años",
        options=anios_opts,
        value=(anios_opts[0], anios_opts[-1])
    )

with st.sidebar.expander("Precio", expanded=True):
    precio_min, precio_max = st.slider("Rango de precio (USD)", 0, 60, (0, 30), step=1)

with st.sidebar.expander("Calidad", expanded=False):
    score_min   = st.slider("Review score mínimo (%)", 0, 100, 60, step=5)
    min_ratings = st.slider("Mínimo de reviews", 10, 500, 50, step=10)
    solo_pago   = st.checkbox("Solo juegos de pago", value=True)

df = load_main(generos_sel, anio_min, anio_max, precio_min, precio_max,
               score_min, min_ratings, solo_pago)

# ================================================================
# Header y tabs
# ================================================================
st.title("Steam Value Analyzer")
st.caption("¿Qué juegos realmente valen su precio? · fuente: Kaggle + Steam API")

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "Exploración",
    "Detalle de juego",
    "Recomendador",
    "Evolución histórica",
    "Géneros",
    "Desarrolladoras",
])

# ================================================================
# TAB 1 — Exploración
# ================================================================
with tab1:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Juegos encontrados", f"{len(df):,}")
    c2.metric("Precio promedio", f"${df['price'].mean():.2f}" if len(df) else "—")
    c3.metric("Review score promedio", f"{df['review_score'].mean():.1f}%" if len(df) else "—")
    c4.metric("Valor score promedio",
              f"{df['valor_score'].mean():.1f}" if df['valor_score'].notna().any() else "—")

    st.divider()
    col_a, col_b = st.columns([3, 2])

    with col_a:
        st.subheader("Precio vs tiempo de juego")
        df_sc = df[df["horas_por_dolar"].notna()].head(500)
        fig = px.scatter(
            df_sc, x="price", y="average_playtime",
            size="horas_por_dolar", color="review_score",
            hover_name="name",
            hover_data={"price": True, "review_score": True,
                        "horas_por_dolar": True, "genres": True},
            color_continuous_scale="Viridis",
            labels={"price": "Precio (USD)", "average_playtime": "Horas promedio",
                    "review_score": "Review (%)"},
            size_max=25, opacity=0.75
        )
        fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=380)
        st.plotly_chart(fig, use_container_width=True)

    with col_b:
        st.subheader("Top 20 — valor score")
        top20 = df[df["valor_score"].notna()].head(20)
        fig2 = px.bar(
            top20.sort_values("valor_score"),
            x="valor_score", y="name", orientation="h",
            color="valor_score", color_continuous_scale="Oranges",
            labels={"valor_score": "Valor", "name": ""},
            hover_data={"price": True, "review_score": True, "horas_por_dolar": True}
        )
        fig2.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=380,
                           coloraxis_showscale=False)
        st.plotly_chart(fig2, use_container_width=True)

    st.subheader("Tabla completa")
    st.dataframe(
        df[["name", "genres", "price", "review_score", "average_playtime",
            "horas_por_dolar", "valor_score", "total_ratings", "developer",
            "release_year"]].reset_index(drop=True),
        use_container_width=True, height=320
    )

# ================================================================
# TAB 2 — Detalle de juego + Steam API + comparativa de precio
# ================================================================
with tab2:
    st.subheader("Vista de detalle por juego")

    if len(df) == 0:
        st.warning("No hay juegos con los filtros actuales.")
    else:
        juego_sel = st.selectbox("Seleccioná un juego", df["name"].tolist(), index=0)
        row = df[df["name"] == juego_sel].iloc[0]

        # --- Métricas del dataset ---
        col1, col2, col3 = st.columns(3)
        col1.metric("Precio (dataset)", f"${row['price']:.2f}")
        col2.metric("Review score", f"{row['review_score']:.1f}%" if pd.notna(row['review_score']) else "—")
        col3.metric("Valor score", f"{row['valor_score']:.1f}" if pd.notna(row['valor_score']) else "—")

        col4, col5, col6 = st.columns(3)
        col4.metric("Playtime promedio", f"{int(row['average_playtime'])}h" if pd.notna(row['average_playtime']) else "—")
        col5.metric("Horas por dólar", f"{row['horas_por_dolar']}" if pd.notna(row['horas_por_dolar']) else "—")
        col6.metric("Total reviews", f"{int(row['total_ratings']):,}" if pd.notna(row['total_ratings']) else "—")

        st.divider()

        # --- Steam API: datos en tiempo real ---
        col_info, col_api = st.columns([1, 1])

        with col_info:
            st.markdown(f"""
            | Campo | Valor |
            |---|---|
            | Desarrolladora | {row['developer']} |
            | Género | {row['genres']} |
            | Año de lanzamiento | {int(row['release_year']) if pd.notna(row['release_year']) else '—'} |
            | Categoría de precio | {row['categoria_precio']} |
            | AppID | {int(row['appid']) if pd.notna(row['appid']) else '—'} |
            """)

        with col_api:
            st.subheader("Datos en tiempo real (Steam API)")
            appid = row.get("appid")

            if appid and not pd.isna(appid):
                with st.spinner("Consultando Steam API..."):
                    steam = fetch_steam_data(int(appid))

                if steam:
                    if steam["header_image"]:
                        st.image(steam["header_image"], use_container_width=True)

                    st.markdown(f"**{steam['name']}**")
                    if steam["description"]:
                        st.caption(steam["description"][:300] + "...")

                    m1, m2 = st.columns(2)
                    m1.metric("Precio actual (Steam)", steam["price_fmt"])
                    if steam["metacritic"]:
                        m2.metric("Metacritic", f"{steam['metacritic']}/100")

                    # Comparativa: precio dataset vs precio actual
                    precio_dataset = row["price"]
                    precio_actual  = steam["price_actual"]

                    if precio_dataset > 0 and precio_actual > 0:
                        diff     = precio_actual - precio_dataset
                        diff_pct = (diff / precio_dataset) * 100
                        st.divider()
                        st.subheader("Comparativa de precio")
                        fig_precio = go.Figure(go.Bar(
                            x=["Precio en dataset\n(Kaggle ~2019)", "Precio actual\n(Steam hoy)"],
                            y=[precio_dataset, precio_actual],
                            marker_color=["#5b8db8", "#e07b39"],
                            text=[f"${precio_dataset:.2f}", f"${precio_actual:.2f}"],
                            textposition="outside"
                        ))
                        fig_precio.update_layout(
                            height=300,
                            margin=dict(l=0, r=0, t=10, b=0),
                            yaxis_title="Precio (USD)",
                            showlegend=False
                        )
                        st.plotly_chart(fig_precio, use_container_width=True)
                        delta_str = f"+${diff:.2f} (+{diff_pct:.1f}%)" if diff >= 0 else f"-${abs(diff):.2f} ({diff_pct:.1f}%)"
                        st.caption(f"Variación de precio: {delta_str} desde el dataset")

                    st.link_button("Ver en Steam →", steam["steam_url"])
                else:
                    st.info("No se pudo obtener datos de Steam API para este juego.")
            else:
                st.info("Este juego no tiene AppID disponible.")

        st.divider()

        # --- Radar chart ---
        st.subheader("¿Cómo se compara con el resto?")
        df_norm = df[["review_score", "horas_por_dolar", "valor_score", "total_ratings"]].copy()
        df_norm = df_norm.apply(lambda x: (x - x.min()) / (x.max() - x.min()) * 100)

        idx        = df[df["name"] == juego_sel].index[0]
        vals_juego = df_norm.loc[idx]
        vals_prom  = df_norm.mean()
        categorias = ["Review score", "Horas/$", "Valor score", "Popularidad"]

        fig_radar = go.Figure()
        fig_radar.add_trace(go.Scatterpolar(
            r=[vals_juego["review_score"], vals_juego["horas_por_dolar"],
               vals_juego["valor_score"], vals_juego["total_ratings"]],
            theta=categorias, fill="toself",
            name=juego_sel[:30], line_color="#e07b39"
        ))
        fig_radar.add_trace(go.Scatterpolar(
            r=[vals_prom["review_score"], vals_prom["horas_por_dolar"],
               vals_prom["valor_score"], vals_prom["total_ratings"]],
            theta=categorias, fill="toself", opacity=0.4,
            name="Promedio del catálogo", line_color="#5b8db8"
        ))
        fig_radar.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
            height=400, margin=dict(l=40, r=40, t=40, b=40)
        )
        st.plotly_chart(fig_radar, use_container_width=True)

# ================================================================
# TAB 3 — Recomendador
# ================================================================
with tab3:
    st.subheader("Recomendador de juegos")
    st.caption("Basado en similitud de género, precio, playtime y review score (cosine similarity)")

    df_all = load_all_for_recommender()

    juego_base = st.selectbox(
        "Seleccioná un juego como base",
        sorted(df_all["name"].tolist()),
        key="rec_select"
    )

    n_recs = st.slider("Cantidad de recomendaciones", 5, 20, 10)

    if st.button("Buscar juegos similares"):
        with st.spinner("Calculando similitudes..."):
            recs = get_recommendations(juego_base, n=n_recs)

        if recs.empty:
            st.warning("No se encontraron recomendaciones.")
        else:
            # Mostrar el juego base
            base_row = df_all[df_all["name"] == juego_base].iloc[0]
            st.markdown(f"**Juego base:** {juego_base} · Género: `{base_row['genres']}` · "
                        f"Precio: ${base_row['price']:.2f} · "
                        f"Review: {base_row['review_score']:.1f}%")
            st.divider()

            # Gráfico de similitud
            fig_rec = px.bar(
                recs.sort_values("similitud (%)"),
                x="similitud (%)", y="name", orientation="h",
                color="valor_score", color_continuous_scale="Greens",
                labels={"name": "", "similitud (%)": "Similitud (%)"},
                hover_data={"price": True, "review_score": True, "genres": True}
            )
            fig_rec.update_layout(height=400, margin=dict(l=0, r=0, t=0, b=0),
                                  coloraxis_showscale=True)
            st.plotly_chart(fig_rec, use_container_width=True)

            st.dataframe(recs, use_container_width=True)

    # Sección: recomendaciones por preferencias del usuario
    st.divider()
    st.subheader("Recomendaciones por preferencias")
    st.caption("No tenés un juego en mente — describí lo que buscás")

    p1, p2, p3 = st.columns(3)
    pref_genero  = p1.selectbox("Género preferido", ["Cualquiera"] + generos_opts)
    pref_precio  = p2.slider("Precio máximo (USD)", 0, 60, 20)
    pref_playtime = p3.slider("Mínimo de horas promedio", 0, 500, 50)

    if st.button("Buscar por preferencias"):
        gen_f = f"AND genres = '{pref_genero}'" if pref_genero != "Cualquiera" else ""
        df_pref = query(f"""
            SELECT name, genres, ROUND(price, 2) AS price,
                   ROUND(review_score, 1) AS review_score,
                   average_playtime,
                   ROUND(horas_por_dolar, 1) AS horas_por_dolar,
                   ROUND(valor_score, 1) AS valor_score
            FROM games
            WHERE price <= {pref_precio}
              AND average_playtime >= {pref_playtime}
              AND review_score IS NOT NULL
              AND valor_score IS NOT NULL
              {gen_f}
            ORDER BY valor_score DESC
            LIMIT 15
        """)

        if df_pref.empty:
            st.info("No hay juegos con esas preferencias. Probá relajar los filtros.")
        else:
            st.dataframe(df_pref, use_container_width=True)

# ================================================================
# TAB 4 — Evolución histórica
# ================================================================
with tab4:
    st.subheader("Evolución histórica del catálogo de Steam")

    df_evol = load_evolucion()

    fig_evol1 = px.area(
        df_evol, x="release_year", y="lanzamientos",
        labels={"release_year": "Año", "lanzamientos": "Juegos lanzados"},
        title="Crecimiento del catálogo de Steam por año",
        color_discrete_sequence=["#5b8db8"]
    )
    fig_evol1.update_traces(line_width=2)
    fig_evol1.update_layout(height=300, margin=dict(l=0, r=0, t=40, b=0))
    st.plotly_chart(fig_evol1, use_container_width=True)

    col_e1, col_e2 = st.columns(2)

    with col_e1:
        fig_evol2 = px.line(
            df_evol, x="release_year", y="review_promedio",
            labels={"release_year": "Año", "review_promedio": "Review score (%)"},
            title="Review score promedio por año",
            markers=True, color_discrete_sequence=["#4a9e6b"]
        )
        fig_evol2.add_hline(
            y=df_evol["review_promedio"].mean(),
            line_dash="dash", line_color="gray", annotation_text="Promedio"
        )
        fig_evol2.update_layout(height=300, margin=dict(l=0, r=0, t=40, b=0))
        st.plotly_chart(fig_evol2, use_container_width=True)

    with col_e2:
        fig_evol3 = px.line(
            df_evol, x="release_year", y="precio_promedio",
            labels={"release_year": "Año", "precio_promedio": "Precio promedio (USD)"},
            title="Precio promedio de juegos de pago por año",
            markers=True, color_discrete_sequence=["#e07b39"]
        )
        fig_evol3.update_layout(height=300, margin=dict(l=0, r=0, t=40, b=0))
        st.plotly_chart(fig_evol3, use_container_width=True)

    st.subheader("Tabla de evolución")
    st.dataframe(df_evol.rename(columns={
        "release_year": "Año", "lanzamientos": "Lanzamientos",
        "review_promedio": "Review promedio (%)",
        "precio_promedio": "Precio promedio (USD)",
        "ratings_totales": "Reviews totales"
    }), use_container_width=True, height=300)

# ================================================================
# TAB 5 — Géneros
# ================================================================
with tab5:
    st.subheader("Comparativa entre géneros")

    df_gen = load_generos_overview()
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

    fig_gen = px.bar(
        df_gen.sort_values(metrica),
        x=metrica, y="genres", orientation="h",
        color=metrica, color_continuous_scale="Blues",
        labels={"genres": "", metrica: metrica.replace("_", " ").title()},
        hover_data={"total_juegos": True}
    )
    fig_gen.update_layout(margin=dict(l=0, r=0, t=10, b=0),
                          height=440, coloraxis_showscale=False)
    st.plotly_chart(fig_gen, use_container_width=True)

    st.subheader("Tabla comparativa completa")
    st.dataframe(df_gen.rename(columns={
        "genres": "Género", "total_juegos": "Juegos",
        "review_promedio": "Review (%)", "precio_promedio": "Precio (USD)",
        "playtime_promedio": "Playtime (min)", "valor_promedio": "Valor score"
    }), use_container_width=True)

# ================================================================
# TAB 6 — Desarrolladoras
# ================================================================
with tab6:
    st.subheader("Ranking de desarrolladoras")
    st.caption("Mínimo 5 juegos publicados · al menos 50 reviews por juego")

    df_dev = load_desarrolladoras()
    fig_dev = px.bar(
        df_dev.sort_values("review_promedio"),
        x="review_promedio", y="developer", orientation="h",
        color="juegos_publicados", color_continuous_scale="Purples",
        labels={"review_promedio": "Review score promedio (%)",
                "developer": "", "juegos_publicados": "Juegos"},
        hover_data={"juegos_publicados": True, "ratings_totales": True}
    )
    fig_dev.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=580)
    st.plotly_chart(fig_dev, use_container_width=True)

    st.dataframe(df_dev.rename(columns={
        "developer": "Desarrolladora", "juegos_publicados": "Juegos",
        "review_promedio": "Review promedio (%)", "ratings_totales": "Reviews totales"
    }), use_container_width=True)