# app.py
# -*- coding: utf-8 -*-

import streamlit as st
import pandas as pd
from mplsoccer import Radar
from matplotlib.patheffects import withStroke
import unicodedata

# =========================
# Utils
# =========================
def quitar_tildes(texto: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", str(texto))
        if unicodedata.category(c) != "Mn"
    )

@st.cache_data(show_spinner=False)
def load_excel(path: str) -> pd.DataFrame:
    return pd.read_excel(path)

def ensure_filtropais(df: pd.DataFrame) -> pd.DataFrame:
    # Crea FiltroPais = "Pais competencia | Competencia | Año"
    for c in ["Pais competencia", "Competencia", "Año"]:
        if c not in df.columns:
            df[c] = ""
    df["Pais competencia"] = df["Pais competencia"].fillna("")
    df["Competencia"] = df["Competencia"].fillna("")
    df["Año"] = df["Año"].fillna("").astype(str)

    df["FiltroPais"] = (df["Pais competencia"] + " | " + df["Competencia"] + " | " + df["Año"]).str.strip()
    return df

def ensure_jugador_con_equipo(df: pd.DataFrame) -> pd.DataFrame:
    if "Jugador con equipo" not in df.columns:
        # Requiere Player y Team within selected timeframe
        if "Player" not in df.columns:
            df["Player"] = ""
        if "Team within selected timeframe" not in df.columns:
            df["Team within selected timeframe"] = ""
        df["Jugador con equipo"] = df["Player"].astype(str) + " (" + df["Team within selected timeframe"].astype(str) + ")"
    return df

def visible_mapping_from_players(player_series: pd.Series):
    jugadores_reales = player_series.dropna().astype(str).unique().tolist()
    jugadores_visibles = [quitar_tildes(j) for j in jugadores_reales]
    # Si hay colisiones al quitar tildes, resolvemos agregando un sufijo
    seen = {}
    fixed_visibles = []
    for v, r in zip(jugadores_visibles, jugadores_reales):
        if v not in seen:
            seen[v] = 1
            fixed_visibles.append(v)
        else:
            seen[v] += 1
            fixed_visibles.append(f"{v} ({seen[v]})")
    mapa_visible_a_real = dict(zip(fixed_visibles, jugadores_reales))
    return fixed_visibles, mapa_visible_a_real

def reset_keys_on_position_change():
    if "prev_puesto" not in st.session_state:
        st.session_state.prev_puesto = st.session_state.puesto
        return

    if st.session_state.puesto != st.session_state.prev_puesto:
        # Resetea solo cosas que dependen fuerte del puesto
        for k in [
            "subpuesto",
            "pierna",
            "filtro_pais",
            "minutos",
            "jugador1",
            "jugador2",
        ]:
            st.session_state.pop(k, None)
        st.session_state.prev_puesto = st.session_state.puesto

def check_required_cols(df: pd.DataFrame, required: list[str], label: str) -> bool:
    missing = [c for c in required if c not in df.columns]
    if missing:
        st.error(
            f"En **{label}** faltan columnas necesarias: {missing}. "
            "Revisá el Excel o el nombre de las columnas."
        )
        return False
    return True

# =========================
# Config por puesto
# =========================
RADAR_COLS = [
    "Gol y Finalización",
    "Asistencias y creación de chances",
    "Juego asociado",
    "Progresion de pelota",
    "Juego aéreo",
    "Defensa",
    "1v1 en ataque",
    "1v1 en defensa",
    "Centros",
]

RENAMES_TABLA = {
    "Jugador con equipo": "Jugador",
    "Asistencias y creación de chances": "Ast. y chances",
    "Progresion de pelota": "Prog. de pelota",
}

CONFIG = {
    "Defensores centrales": {
        "excel": "data/final_defensoresCentrales_todos2026.xlsx",
        "radar": RADAR_COLS,
        "subpuesto": None,
        "renames": RENAMES_TABLA,
    },
    "Laterales": {
        "excel": "data/final_Laterales_todos2026.xlsx",
        "radar": RADAR_COLS,
        "subpuesto": {
            "label": "Puesto:",
            "options": ["Sin asignar", "Lateral derecho", "Lateral izquierdo"],
            "mode": "contains_RL",
            "right": "Lateral derecho",
            "left": "Lateral izquierdo",
        },
        "renames": RENAMES_TABLA,
    },
    "Volante posicional": {
        "excel": "data/final_volanteContencion_todos2026.xlsx",
        "radar": RADAR_COLS,
        "subpuesto": None,
        "renames": RENAMES_TABLA,
    },
    "Interior contención": {
        "excel": "data/final_interiorContencion_todos2026.xlsx",
        "radar": RADAR_COLS,
        "subpuesto": None,
        "renames": RENAMES_TABLA,
    },
    "Interior ofensivo": {
        "excel": "data/final_interiorOfensivo_todos2026.xlsx",
        "radar": RADAR_COLS,
        "subpuesto": None,
        "renames": RENAMES_TABLA,
    },
    "Volante ofensivo": {
        "excel": "data/final_volanteOfensivo_todos2026.xlsx",
        "radar": RADAR_COLS,
        "subpuesto": None,
        "renames": RENAMES_TABLA,
    },
    "Mediapunta": {
        "excel": "data/final_mediapunta_todos2026.xlsx",
        "radar": RADAR_COLS,
        "subpuesto": None,
        "renames": RENAMES_TABLA,
    },
    "Extremos": {
        "excel": "data/final_extremos_todos2026.xlsx",
        "radar": RADAR_COLS,
        "subpuesto": {
            "label": "Puesto:",
            "options": ["Sin asignar", "Extremo por derecha", "Extremo por izquierda"],
            "mode": "contains_RL",
            "right": "Extremo por derecha",
            "left": "Extremo por izquierda",
        },
        "renames": RENAMES_TABLA,
    },
    "Delantero centro": {
        "excel": "data/final_delanteros_todos2026.xlsx",
        "radar": RADAR_COLS,
        "subpuesto": None,
        "renames": RENAMES_TABLA,
    },
}

# =========================
# App
# =========================
st.set_page_config(page_title="Gráficos de radar", layout="wide")

st.title("📌 Buscador por puesto")



st.selectbox(
    "Seleccioná el puesto a explorar",
    options=list(CONFIG.keys()),
    key="puesto",
)

reset_keys_on_position_change()

cfg = CONFIG[st.session_state.puesto]
df = load_excel(cfg["excel"]).copy()

# Columnas auxiliares
df = ensure_filtropais(df)
df = ensure_jugador_con_equipo(df)

# Validaciones base
base_required = ["Minutes played", "Foot", "FiltroPais", "Jugador con equipo", "Puntaje"]
if not check_required_cols(df, base_required, st.session_state.puesto):
    st.stop()

# Layout
col1, col2, col3 = st.columns([1, 2.5, 1])

with col2:
    st.subheader(st.session_state.puesto)

    # Minutos (slider)
    min_minutos = int(pd.to_numeric(df["Minutes played"], errors="coerce").fillna(0).min())
    max_minutos = int(pd.to_numeric(df["Minutes played"], errors="coerce").fillna(0).max())
    if max_minutos < min_minutos:
        min_minutos, max_minutos = 0, 0

    st.slider(
        "Filtrar por minutos jugados:",
        min_value=min_minutos,
        max_value=max_minutos,
        value=(min_minutos, max_minutos),
        key="minutos",
    )

    # Subpuesto opcional (Extremos/Laterales)
    if cfg["subpuesto"] is not None:
        sp = cfg["subpuesto"]
        # si falta Position, no frenamos toda la app, solo avisamos y no filtramos
        if "Position" not in df.columns:
            st.warning("Este puesto tiene filtro de subpuesto, pero no existe la columna 'Position' en el Excel.")
            st.selectbox(sp["label"], sp["options"], key="subpuesto")
        else:
            st.selectbox(sp["label"], sp["options"], key="subpuesto")

            if st.session_state.subpuesto == sp["right"]:
                df = df[df["Position"].astype(str).str.contains("R", na=False)]
            elif st.session_state.subpuesto == sp["left"]:
                df = df[df["Position"].astype(str).str.contains("L", na=False)]
    else:
        # por si quedó de otro puesto
        st.session_state.pop("subpuesto", None)

    # Pierna hábil
    opciones_pierna = ["Sin aclarar"] + sorted(df["Foot"].dropna().astype(str).unique().tolist())
    st.selectbox("Filtrar por pierna hábil:", opciones_pierna, key="pierna")

    # Ligas (FiltroPais)
    opciones_filtro_pais = sorted(df["FiltroPais"].dropna().astype(str).unique().tolist())
    st.multiselect(
        "Filtrar por ligas (puedes seleccionar múltiples):",
        opciones_filtro_pais,
        default=st.session_state.get("filtro_pais", []),
        key="filtro_pais",
    )

    # Aplicar filtros
    a, b = st.session_state.minutos
    df = df[(df["Minutes played"] >= a) & (df["Minutes played"] <= b)]

    if st.session_state.pierna != "Sin aclarar":
        df = df[df["Foot"].isin([st.session_state.pierna, "both", "unknown"])]

    if st.session_state.filtro_pais:
        df = df[df["FiltroPais"].isin(st.session_state.filtro_pais)]

    if df.empty:
        st.warning("No quedaron jugadores con los filtros actuales.")
        st.stop()

    # Validación radar cols
    radar_cols = cfg["radar"]
    if not check_required_cols(df, radar_cols, f"{st.session_state.puesto} (radar)"):
        st.stop()

    # Select jugadores (con mapping sin tildes)
    jugadores_visibles, mapa_visible_a_real = visible_mapping_from_players(df["Jugador con equipo"])

    # Si hay 0/1 jugadores por filtros
    if len(jugadores_visibles) == 0:
        st.warning("No hay jugadores disponibles con estos filtros.")
        st.stop()

    st.selectbox("Selecciona el primer jugador:", jugadores_visibles, key="jugador1")
    jugador_1 = mapa_visible_a_real[st.session_state.jugador1]

    jugadores_opcionales = ["Ninguno"] + [j for j in jugadores_visibles if j != st.session_state.jugador1]
    st.selectbox("Selecciona el segundo jugador (opcional):", jugadores_opcionales, key="jugador2")
    jugador_2 = mapa_visible_a_real[st.session_state.jugador2] if st.session_state.jugador2 != "Ninguno" else None

    data_j1 = df[df["Jugador con equipo"] == jugador_1]
    data_j2 = df[df["Jugador con equipo"] == jugador_2] if jugador_2 else None

    # Radar
    # Los atributos ya están expresados en una escala 0-100.
    # La escala del radar queda fija para que un 72 siempre se vea en 72,
    # independientemente de los filtros aplicados.
    radar = Radar(
        params=radar_cols,
        min_range=[0.0] * len(radar_cols),
        max_range=[100.0] * len(radar_cols),
    )

    fig, ax = radar.setup_axis(figsize=(15, 15), facecolor="#f2f2f2")
    fig.patch.set_facecolor("#f2f2f2")
    radar.draw_circles(ax=ax, facecolor="#f2f2f2", edgecolor="#4C4545", lw=3)

    values_1 = list(
        pd.to_numeric(data_j1[radar_cols].iloc[0], errors="coerce")
        .fillna(0)
        .clip(0, 100)
        .astype(float)
        .values
    )
    minutos_j1 = int(data_j1["Minutes played"].iloc[0])

    color_j1 = "#0D3E8A"
    color_j2 = "#FB0B0E"

    if data_j2 is not None and not data_j2.empty:
        values_2 = list(
            pd.to_numeric(data_j2[radar_cols].iloc[0], errors="coerce")
            .fillna(0)
            .clip(0, 100)
            .astype(float)
            .values
        )
        minutos_j2 = int(data_j2["Minutes played"].iloc[0])

        radar.draw_radar_compare(
            ax=ax,
            values=values_1,
            compare_values=values_2,
            kwargs_compare={"facecolor": color_j2, "alpha": 0.6, "edgecolor": "yellow", "lw": 2, "linestyle": "-"},
            kwargs_radar={"facecolor": color_j1, "alpha": 0.8, "edgecolor": "white", "lw": 2, "linestyle": "-"},
        )
    else:
        radar.draw_radar(
            ax=ax,
            values=values_1,
            kwargs_radar={"facecolor": color_j1, "alpha": 0.8, "edgecolor": "white", "lw": 2, "linestyle": "-"},
        )
        minutos_j2 = None

    radar.draw_range_labels(
        ax=ax,
        fontsize=13,
        weight="bold",
        color="black",
        fontfamily="Verdana",
        path_effects=[withStroke(linewidth=6, foreground="white")],
    )

    radar.draw_param_labels(
        ax=ax,
        fontsize=14,
        color="black",
        fontfamily="Verdana",
        weight="bold",
        offset=0.6,
        path_effects=[withStroke(linewidth=0, foreground="white")],
    )

    texto_jugador_1 = f"{jugador_1} ({minutos_j1} min)"
    ax.text(
        0.05,
        0.01,
        texto_jugador_1,
        weight="bold",
        fontsize=14,
        fontfamily="Verdana",
        color=color_j1,
        transform=ax.transAxes,
        bbox=dict(facecolor="white", edgecolor="black", boxstyle="round,pad=0.4"),
    )

    if minutos_j2 is not None and jugador_2 is not None:
        texto_jugador_2 = f"{jugador_2} ({minutos_j2} min)"
        ax.text(
            0.95,
            0.01,
            texto_jugador_2,
            weight="bold",
            fontsize=14,
            fontfamily="Verdana",
            color=color_j2,
            transform=ax.transAxes,
            ha="right",
            bbox=dict(facecolor="white", edgecolor="black", boxstyle="round,pad=0.4"),
        )

    st.pyplot(fig, use_container_width=False)

# =========================
# Tablas (fuera del col2 a propósito, como tus páginas)
# =========================
# (recalculamos jugadores seleccionados con los "reales")
jugador_1_real = jugador_1
jugador_2_real = jugador_2

columnas_tabla = ["Jugador con equipo", "Puntaje"] + radar_cols
if not check_required_cols(df, columnas_tabla, f"{st.session_state.puesto} (tabla)"):
    st.stop()

df_tabla = df[columnas_tabla].copy()
df_tabla = df_tabla.sort_values(by="Puntaje", ascending=False).reset_index(drop=True)
df_tabla["Ranking"] = df_tabla.index + 1

columnas_finales = ["Ranking", "Jugador con equipo", "Puntaje"] + radar_cols
df_tabla = df_tabla[columnas_finales]

# Renombres por puesto (incluye "Jugador con equipo"->"Jugador")
df_tabla.rename(columns=cfg["renames"], inplace=True)

# Seleccionados
jugadores_seleccionados = [jugador_1_real]
if jugador_2_real is not None:
    jugadores_seleccionados.append(jugador_2_real)

# Ojo: tras renombrar, la col "Jugador" existe
col_jugador = "Jugador" if "Jugador" in df_tabla.columns else "Jugador con equipo"

df_seleccionados = df_tabla[df_tabla[col_jugador].isin(jugadores_seleccionados)]

st.subheader("Jugadores seleccionados")
st.dataframe(df_seleccionados, use_container_width=True, hide_index=True)

def resaltar_fila(row):
    if row[col_jugador] in jugadores_seleccionados:
        return ["background-color: #FFD700; color: black"] * len(row)
    return [""] * len(row)

st.subheader("Ranking de jugadores filtrados")
st.dataframe(
    df_tabla.style.apply(resaltar_fila, axis=1).format(precision=2),
    use_container_width=True,
    hide_index=True,
)
