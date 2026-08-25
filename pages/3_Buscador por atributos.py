# -*- coding: utf-8 -*-

import streamlit as st
import pandas as pd
import numpy as np
import os
import re
from datetime import date

# =========================
#  Configuración / Título
# =========================
st.set_page_config(page_title="Buscador por perfil", layout="wide")
st.title("🎯 Buscador de jugadores por atributos")

# =========================
#  Configuración de puestos
# =========================
# Cada puesto apunta de forma explícita al Excel correspondiente.
# Así usamos exactamente las mismas bases 2026 que en Radar y Explorador.
ARCHIVOS_POR_PUESTO = {
    "Defensores centrales": "data/final_defensoresCentrales_todos2026.xlsx",
    "Laterales": "data/final_Laterales_todos2026.xlsx",
    "Volante posicional": "data/final_volanteContencion_todos2026.xlsx",
    "Interior contención": "data/final_interiorContencion_todos2026.xlsx",
    "Interior ofensivo": "data/final_interiorOfensivo_todos2026.xlsx",
    "Volante ofensivo": "data/final_volanteOfensivo_todos2026.xlsx",
    "Mediapunta": "data/final_mediapunta_todos2026.xlsx",
    "Extremos": "data/final_extremos_todos2026.xlsx",
    "Delantero centro": "data/final_delanteros_todos2026.xlsx",
}

PUESTOS = list(ARCHIVOS_POR_PUESTO.keys())

# El modelo nuevo contiene los 9 atributos en todos los puestos.
ATRIBUTOS = [
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

# =========================
#  Utilidades
# =========================
def normalizar_basico(s: str) -> str:
    if not isinstance(s, str):
        return ""
    s = s.lower().strip()
    s = re.sub(r"\s+", "", s)
    reemplazos = str.maketrans("áéíóúüñ", "aeiouun")
    return s.translate(reemplazos)


def asegurar_col(df: pd.DataFrame, col: str, valor=np.nan):
    if col not in df.columns:
        df[col] = valor


def to_num(s):
    return pd.to_numeric(s, errors="coerce")


def parse_passports(x) -> list:
    if pd.isna(x):
        return []
    s = str(x).strip()
    if not s or s.lower() == "nan":
        return []
    return [p.strip() for p in s.split(",") if p.strip()]


def parse_contract_date(s):
    """Parsea '31/12/2026' (DD/MM/YYYY) a datetime; NaT si no es válido."""
    if pd.isna(s):
        return pd.NaT
    s = str(s).strip()
    if not s or s.lower() == "nan":
        return pd.NaT
    return pd.to_datetime(s, dayfirst=True, errors="coerce")


@st.cache_data(show_spinner=False)
def cargar_datos_xlsx(path: str) -> pd.DataFrame:
    return pd.read_excel(path)


# =========================
#  Selección y carga
# =========================
puesto_seleccionado = st.selectbox(
    "Seleccioná el puesto a analizar:",
    PUESTOS,
)

archivo = ARCHIVOS_POR_PUESTO[puesto_seleccionado]

if not os.path.isfile(archivo):
    st.error(
        f"No se encontró el archivo correspondiente a **{puesto_seleccionado}**:\n\n"
        f"`{archivo}`"
    )
    st.stop()

try:
    df0 = cargar_datos_xlsx(archivo).copy()
except Exception as e:
    st.error(f"No se pudo leer `{archivo}`: {e}")
    st.stop()

# =========================
#  Preparación de datos
# =========================
obligatorias = [
    "Player",
    "Team within selected timeframe",
    "Minutes played",
    "Pais competencia",
    "Competencia",
    "Position",
    "Foot",
    "Age",
    "Passport country",
]

for c in obligatorias:
    asegurar_col(
        df0,
        c,
        ""
        if c
        in [
            "Player",
            "Team within selected timeframe",
            "Pais competencia",
            "Competencia",
            "Position",
            "Foot",
            "Passport country",
        ]
        else np.nan,
    )

# Contrato
asegurar_col(df0, "Contract expires", "")

# Atributos del modelo nuevo: están presentes en todos los puestos.
for atributo in ATRIBUTOS:
    asegurar_col(df0, atributo, np.nan)
    df0[atributo] = to_num(df0[atributo])

# Puntaje oficial del modelo nuevo.
asegurar_col(df0, "Puntaje", np.nan)
df0["Puntaje"] = to_num(df0["Puntaje"])

# Limpieza básica y derivadas
df0["Player"] = df0["Player"].fillna("").astype(str)
df0["Team within selected timeframe"] = (
    df0["Team within selected timeframe"].fillna("").astype(str)
)
df0["Pais competencia"] = df0["Pais competencia"].fillna("").astype(str)
df0["Competencia"] = df0["Competencia"].fillna("").astype(str)
df0["Position"] = df0["Position"].fillna("").astype(str)
df0["Foot"] = df0["Foot"].fillna("").astype(str)

df0["Liga"] = df0["Pais competencia"] + " - " + df0["Competencia"]
df0["Jugador con equipo"] = (
    df0["Player"] + " (" + df0["Team within selected timeframe"] + ")"
)
df0["Minutos"] = to_num(df0["Minutes played"]).fillna(0)

# Pasaportes
df0["Pasaportes_list"] = df0["Passport country"].apply(parse_passports)
all_passports = sorted(
    set(p for lista in df0["Pasaportes_list"] for p in lista)
)

# Contrato: parse + valor visible
df0["Contrato_dt"] = df0["Contract expires"].apply(parse_contract_date)
df0["Finalización de contrato"] = np.where(
    df0["Contrato_dt"].notna(),
    df0["Contrato_dt"].dt.strftime("%d/%m/%Y"),
    df0["Contract expires"].fillna("").astype(str),
)

# =========================
#  Jugador de referencia
# =========================
st.markdown("#### 👤 Jugador de referencia")
col_ref1, col_ref2 = st.columns([1, 2])

with col_ref1:
    min_min_ref = st.number_input(
        "Minutos mínimos para poder elegirlo:",
        min_value=0,
        value=0,
        step=50,
        key=f"min_ref_{normalizar_basico(puesto_seleccionado)}",
    )

df_ref = df0[df0["Minutos"] >= min_min_ref].copy()
jugadores_filtrados_ref = sorted(
    df_ref["Jugador con equipo"].dropna().unique().tolist()
)

with col_ref2:
    jugador_ref = st.selectbox(
        "Jugador de referencia:",
        ["Sin referencia"] + jugadores_filtrados_ref,
        key=f"jug_ref_{normalizar_basico(puesto_seleccionado)}",
    )

if jugador_ref != "Sin referencia":
    jugador_info = df_ref[
        df_ref["Jugador con equipo"] == jugador_ref
    ].copy()

    jugador_info = jugador_info.rename(
        columns={
            "Age": "Edad",
            "Passport country": "Pasaporte",
            "Jugador con equipo": "Jugador",
            "Asistencias y creación de chances": "Ast. y chances",
        }
    )

    atributos_display = [
        "Ast. y chances"
        if a == "Asistencias y creación de chances"
        else a
        for a in ATRIBUTOS
    ]

    cols = [
        "Jugador",
        "Edad",
        "Pasaporte",
        "Liga",
        "Puntaje",
        "Minutos",
        "Finalización de contrato",
    ] + atributos_display

    cols = [c for c in cols if c in jugador_info.columns]
    st.dataframe(jugador_info[cols], use_container_width=True)

# =========================
#  Filtros globales
# =========================
st.markdown("### 🧰 Filtros generales")
colA, colB, colC, colD = st.columns(4)

# 1) Minutos
with colA:
    validos_min = to_num(df0["Minutos"]).dropna()

    if validos_min.empty:
        st.info("No hay valores numéricos de minutos para establecer el rango.")
        df = df0.copy()
    else:
        lo = int(np.floor(validos_min.min()))
        hi = int(np.ceil(validos_min.max()))

        if lo >= hi:
            st.caption(f"Rango de minutos (global): {lo} – {hi} (sin variación)")
            df = df0[df0["Minutos"] == lo].copy()
        else:
            step_val = 50 if (hi - lo) >= 50 else 1
            rango_minutos = st.slider(
                "Rango de minutos (global):",
                min_value=lo,
                max_value=hi,
                value=(lo, hi),
                step=step_val,
                key=f"rango_min_gen_{normalizar_basico(puesto_seleccionado)}",
            )
            df = df0[
                df0["Minutos"].between(
                    rango_minutos[0],
                    rango_minutos[1],
                    inclusive="both",
                )
            ].copy()

# 2) Liga
with colB:
    opciones_ligas = ["Todas"] + sorted(
        [x for x in df["Liga"].dropna().unique().tolist() if x]
    )
    ligas_sel = st.multiselect(
        "Liga (puede seleccionar varias):",
        opciones_ligas,
        default=["Todas"],
        key=f"ligas_{normalizar_basico(puesto_seleccionado)}",
    )

    if ligas_sel and "Todas" not in ligas_sel:
        df = df[df["Liga"].isin(ligas_sel)].copy()

# 3) Pasaporte
with colC:
    opciones_pas = ["Todos"] + all_passports
    pas_sel = st.multiselect(
        "Pasaporte (uno o más):",
        opciones_pas,
        default=["Todos"],
        key=f"pasaportes_{normalizar_basico(puesto_seleccionado)}",
    )

    if pas_sel and "Todos" not in pas_sel:
        seleccion = set(pas_sel)
        mask = df["Pasaportes_list"].apply(
            lambda lista: any(p in seleccion for p in lista)
            if isinstance(lista, list)
            else False
        )
        df = df[mask].copy()

# 4) Puesto / pierna
with colD:
    if puesto_seleccionado not in ["Laterales", "Extremos"]:
        opciones_pie = ["Cualquiera"] + sorted(
            [x for x in df["Foot"].dropna().unique().tolist() if x]
        )
        pierna = st.selectbox(
            "Pierna hábil:",
            opciones_pie,
            key=f"pie_general_{normalizar_basico(puesto_seleccionado)}",
        )
        if pierna != "Cualquiera":
            df = df[df["Foot"] == pierna].copy()

    elif puesto_seleccionado == "Laterales":
        lateral = st.selectbox(
            "Puesto:",
            ["Cualquiera", "Lateral derecho (RB)", "Lateral izquierdo (LB)"],
            key="lat_busqueda_atributos",
        )
        if lateral == "Lateral derecho (RB)":
            df = df[df["Position"].str.contains("R", na=False)].copy()
        elif lateral == "Lateral izquierdo (LB)":
            df = df[df["Position"].str.contains("L", na=False)].copy()

        opciones_pie = ["Cualquiera"] + sorted(
            [x for x in df["Foot"].dropna().unique().tolist() if x]
        )
        pierna_lat = st.selectbox(
            "Pierna hábil:",
            opciones_pie,
            key="pie_laterales_busqueda_atributos",
        )
        if pierna_lat != "Cualquiera":
            df = df[df["Foot"] == pierna_lat].copy()

    elif puesto_seleccionado == "Extremos":
        extremo = st.selectbox(
            "Puesto:",
            ["Cualquiera", "Extremo por derecha", "Extremo por izquierda"],
            key="extremo_busqueda_atributos",
        )
        if extremo == "Extremo por derecha":
            df = df[df["Position"].str.contains("R", na=False)].copy()
        elif extremo == "Extremo por izquierda":
            df = df[df["Position"].str.contains("L", na=False)].copy()

        opciones_pie = ["Cualquiera"] + sorted(
            [x for x in df["Foot"].dropna().unique().tolist() if x]
        )
        pierna_ext = st.selectbox(
            "Pierna hábil:",
            opciones_pie,
            key="pie_extremos_busqueda_atributos",
        )
        if pierna_ext != "Cualquiera":
            df = df[df["Foot"] == pierna_ext].copy()

# =========================
#  Finalización de contrato
# =========================
st.markdown("#### 📅 Finalización de contrato")
anular_filtro_contrato = st.checkbox(
    "Anular filtro de fecha de contrato",
    value=True,
    key=f"anular_filtro_contrato_{normalizar_basico(puesto_seleccionado)}",
)

if not anular_filtro_contrato:
    fechas_validas = df["Contrato_dt"].dropna()

    if fechas_validas.empty:
        st.caption("No hay fechas válidas en el subconjunto actual.")
        incluir_nan = st.checkbox(
            "Agregar a la tabla a los jugadores que no tengan una fecha de finalización asignada",
            value=True,
            key=f"incluir_nan_contrato_empty_{normalizar_basico(puesto_seleccionado)}",
        )
        if not incluir_nan:
            df = df[df["Contrato_dt"].notna()].copy()
    else:
        min_f = fechas_validas.min().date()
        max_f = fechas_validas.max().date()
        hoy = date.today()
        def_date = min(max(hoy, min_f), max_f)

        fecha_limite = st.date_input(
            "Mostrar jugadores cuyo contrato vence hasta el día elegido (incluido):",
            value=def_date,
            min_value=min_f,
            max_value=max_f,
            key=f"fecha_contrato_limite_{normalizar_basico(puesto_seleccionado)}",
        )

        incluir_nan = st.checkbox(
            "Agregar a la tabla a los jugadores que no tengan una fecha de finalización asignada",
            value=False,
            key=f"incluir_nan_contrato_{normalizar_basico(puesto_seleccionado)}",
        )

        if incluir_nan:
            mask_fecha = df["Contrato_dt"].isna() | (
                df["Contrato_dt"] <= pd.Timestamp(fecha_limite)
            )
        else:
            mask_fecha = df["Contrato_dt"].notna() & (
                df["Contrato_dt"] <= pd.Timestamp(fecha_limite)
            )

        df = df[mask_fecha].copy()
else:
    st.caption(
        "🔓 Filtro de contrato desactivado: se incluyen jugadores con y sin fecha."
    )

# =========================
#  Filtros por atributo
# =========================
st.markdown("### 📊 Filtros por atributos del puesto")

# Todos los atributos del modelo están en escala 0–100.
# Mantener el rango fijo conserva el significado del filtro aunque cambien
# los filtros generales o el subconjunto de jugadores.
sliders = {}

for atributo in ATRIBUTOS:
    if atributo not in df.columns:
        st.warning(f"Falta la columna: **{atributo}** en el dataset.")
        continue

    rango = st.slider(
        f"{atributo}:",
        min_value=0.0,
        max_value=100.0,
        value=(0.0, 100.0),
        step=0.5,
        key=(
            f"sl_{normalizar_basico(puesto_seleccionado)}_"
            f"{normalizar_basico(atributo)}"
        ),
    )
    sliders[atributo] = rango

for atributo, (lo_val, hi_val) in sliders.items():
    serie = to_num(df[atributo])
    df = df[serie.between(lo_val, hi_val, inclusive="both")].copy()

# =========================
#  Exclusión manual
# =========================
st.markdown("### 🚫 Excluir jugadores manualmente")
opciones_excluir = sorted(
    df["Jugador con equipo"].dropna().unique().tolist()
)

key_excluir = f"excluir_sel_{normalizar_basico(puesto_seleccionado)}"
seleccion_previa = [
    j for j in st.session_state.get(key_excluir, []) if j in opciones_excluir
]

excluir_sel = st.multiselect(
    "Seleccioná jugadores a excluir de los resultados:",
    options=opciones_excluir,
    default=seleccion_previa,
    key=key_excluir,
    help="Los seleccionados se eliminarán de la tabla principal y de los TOP 10 por atributo.",
)

if excluir_sel:
    df = df[~df["Jugador con equipo"].isin(excluir_sel)].copy()
    st.caption(
        f"🔎 Excluidos: {len(excluir_sel)}  •  Resultados actuales: {len(df)} jugadores"
    )

# =========================
#  Tabla principal
# =========================
st.markdown("### 🧾 Jugadores que cumplen con los criterios")

df_tabla = df.copy()
df_tabla = df_tabla.rename(
    columns={
        "Age": "Edad",
        "Passport country": "Pasaporte",
        "Jugador con equipo": "Jugador",
        "Asistencias y creación de chances": "Ast. y chances",
    }
)

atributos_vista = [
    "Ast. y chances"
    if a == "Asistencias y creación de chances"
    else a
    for a in ATRIBUTOS
]

columnas_resultado = [
    "Jugador",
    "Edad",
    "Pasaporte",
    "Liga",
    "Puntaje",
    "Minutos",
    "Finalización de contrato",
] + atributos_vista

columnas_resultado = [
    c for c in columnas_resultado if c in df_tabla.columns
]

df_tabla = df_tabla.sort_values(
    by=["Puntaje", "Minutos"],
    ascending=[False, False],
    na_position="last",
)

if not df_tabla.empty:
    st.dataframe(df_tabla[columnas_resultado], use_container_width=True)
else:
    st.warning("No hay jugadores que cumplan con los filtros seleccionados.")

# =========================
#  Top 10 por atributo
# =========================
st.markdown("### 🏆 Top 10 por atributo (según filtros aplicados)")
mapa_atributos = {
    "Asistencias y creación de chances": "Ast. y chances"
}

if df.empty:
    st.info("No se pueden calcular Top 10 porque no hay datos tras los filtros.")
else:
    for atributo in ATRIBUTOS:
        nombre_mostrar = mapa_atributos.get(atributo, atributo)

        if atributo not in df.columns:
            st.warning(f"No hay datos para el atributo: {atributo}")
            continue

        serie = to_num(df[atributo])
        if serie.dropna().empty:
            st.info(f"Sin valores numéricos para **{nombre_mostrar}**.")
            continue

        top10 = (
            df.assign(_atributo_num=serie)
            .sort_values(
                by=["_atributo_num", "Puntaje", "Minutos"],
                ascending=[False, False, False],
                na_position="last",
            )
            .head(10)
            .copy()
        )

        top10 = top10.rename(
            columns={
                "Jugador con equipo": "Jugador",
                "Age": "Edad",
                "Passport country": "Pasaporte",
                "Asistencias y creación de chances": "Ast. y chances",
            }
        )

        cols_top = [
            "Jugador",
            "Edad",
            "Pasaporte",
            "Liga",
            "Puntaje",
            "Minutos",
            "Finalización de contrato",
            nombre_mostrar,
        ]
        cols_top = [c for c in cols_top if c in top10.columns]

        st.markdown(f"#### 🔹 {nombre_mostrar}")
        st.dataframe(top10[cols_top], use_container_width=True)
