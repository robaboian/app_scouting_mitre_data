# -*- coding: utf-8 -*-

import streamlit as st
import pandas as pd
import numpy as np
import os
from datetime import date

# =========================
#  Configuración / Título
# =========================
st.set_page_config(page_title="Explorador global de jugadores", layout="wide")
st.title("🔍 Explorador global de jugadores")

# =========================
#  Configuración de puestos
# =========================
# Cada puesto apunta de forma explícita al Excel correspondiente.
# Así evitamos inferencias por nombre y garantizamos que el Explorador
# utilice exactamente las mismas bases que la página de Radar.
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
def to_num(s):
    return pd.to_numeric(s, errors="coerce")


def asegurar_col(df: pd.DataFrame, col: str, valor=np.nan):
    if col not in df.columns:
        df[col] = valor


def parse_passports(x) -> list:
    if pd.isna(x):
        return []
    s = str(x).strip()
    if not s or s.lower() == "nan":
        return []
    return [p.strip() for p in s.split(",") if p.strip()]


def parse_contract_date(s):
    """Parsea '31/12/2026' (DD/MM/YYYY) a datetime; NaT si inválido."""
    if pd.isna(s):
        return pd.NaT
    s = str(s).strip()
    if not s or s.lower() == "nan":
        return pd.NaT
    return pd.to_datetime(s, dayfirst=True, errors="coerce")


@st.cache_data(show_spinner=False)
def cargar_xlsx(path: str) -> pd.DataFrame:
    return pd.read_excel(path)


# =========================
#  Carga de todas las tablas
# =========================
dfs = []
archivos_faltantes = []

for puesto, path in ARCHIVOS_POR_PUESTO.items():
    if not os.path.isfile(path):
        archivos_faltantes.append(path)
        continue

    try:
        df_i = cargar_xlsx(path).copy()
    except Exception as e:
        st.warning(f"No se pudo leer {os.path.basename(path)}: {e}")
        continue

    # Columnas mínimas
    oblig = [
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

    for c in oblig:
        asegurar_col(
            df_i,
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
    asegurar_col(df_i, "Contract expires", "")

    # Atributos del modelo nuevo
    for atributo in ATRIBUTOS:
        asegurar_col(df_i, atributo, np.nan)
        df_i[atributo] = to_num(df_i[atributo])

    # Derivadas base
    df_i["Player"] = df_i["Player"].fillna("").astype(str)
    df_i["Team within selected timeframe"] = (
        df_i["Team within selected timeframe"].fillna("").astype(str)
    )
    df_i["Pais competencia"] = df_i["Pais competencia"].fillna("").astype(str)
    df_i["Competencia"] = df_i["Competencia"].fillna("").astype(str)

    df_i["Liga"] = df_i["Pais competencia"] + " - " + df_i["Competencia"]
    df_i["Jugador con equipo"] = (
        df_i["Player"] + " (" + df_i["Team within selected timeframe"] + ")"
    )
    df_i["Minutos"] = to_num(df_i["Minutes played"]).fillna(0)

    # Puntaje oficial del modelo nuevo
    asegurar_col(df_i, "Puntaje", np.nan)
    df_i["Puntaje"] = to_num(df_i["Puntaje"])

    # Pasaportes
    df_i["Pasaportes_list"] = df_i["Passport country"].apply(parse_passports)

    # Contrato: parse + visible
    df_i["Contrato_dt"] = df_i["Contract expires"].apply(parse_contract_date)
    df_i["Finalización de contrato"] = np.where(
        df_i["Contrato_dt"].notna(),
        df_i["Contrato_dt"].dt.strftime("%d/%m/%Y"),
        df_i["Contract expires"].fillna("").astype(str),
    )

    # Puesto de origen: sale del mapping explícito del archivo.
    df_i["Puesto"] = puesto

    dfs.append(df_i)

if archivos_faltantes:
    st.warning(
        "No se encontraron algunos Excel esperados:\n\n"
        + "\n".join(f"- {path}" for path in archivos_faltantes)
    )

if not dfs:
    st.error("No se pudo cargar ninguna tabla del modelo 2026.")
    st.stop()

# Concat (outer) sin sumar minutos por nombre.
# Cada fila conserva el puesto/modelo del Excel del que proviene.
df0 = pd.concat(dfs, ignore_index=True, sort=False)

# =========================
#  Filtros globales
# =========================
st.markdown("### 🧰 Filtros")
colA, colB, colC, colD = st.columns(4)

# 1) Minutos (por FILA, NO acumulados)
with colA:
    vmins = to_num(df0["Minutos"]).dropna()
    if vmins.empty:
        st.info("No hay minutos válidos para establecer rango.")
        df = df0.copy()
    else:
        lo = int(np.floor(vmins.min()))
        hi = int(np.ceil(vmins.max()))
        step_val = 50 if (hi - lo) >= 50 else 1
        rango_min = st.slider(
            "Rango de minutos (por fila):",
            min_value=lo,
            max_value=hi,
            value=(lo, hi),
            step=step_val,
            key="rango_min_global",
        )
        df = df0[
            df0["Minutos"].between(rango_min[0], rango_min[1], inclusive="both")
        ].copy()

# 2) Liga
with colB:
    opciones_ligas = ["Todas"] + sorted(df["Liga"].dropna().unique().tolist())
    ligas_sel = st.multiselect("Liga:", opciones_ligas, default=["Todas"], key="ligas")
    if ligas_sel and "Todas" not in ligas_sel:
        df = df[df["Liga"].isin(ligas_sel)]

# 3) Pasaporte
with colC:
    all_passports = sorted(
        set(
            p
            for lst in df["Pasaportes_list"]
            for p in (lst if isinstance(lst, list) else [])
        )
    )
    opciones_pas = ["Todos"] + all_passports
    pas_sel = st.multiselect(
        "Pasaporte(s):", opciones_pas, default=["Todos"], key="pasaportes"
    )
    if pas_sel and "Todos" not in pas_sel:
        sel = set(pas_sel)
        mask = df["Pasaportes_list"].apply(
            lambda lst: any(p in sel for p in (lst if isinstance(lst, list) else []))
        )
        df = df[mask]

# 4) Pie
with colD:
    opciones_pie = ["Cualquiera"] + sorted(
        [x for x in df["Foot"].dropna().unique().tolist() if x != ""]
    )
    pie_sel = st.selectbox("Pierna hábil:", opciones_pie, key="pie")
    if pie_sel != "Cualquiera":
        df = df[df["Foot"] == pie_sel]

# 5) Puesto de origen
colP1, colP2 = st.columns([1, 3])
with colP1:
    puestos_disponibles = ["Todos"] + [p for p in PUESTOS if p in df["Puesto"].unique()]
    puestos_sel = st.multiselect(
        "Puesto (origen):",
        puestos_disponibles,
        default=["Todos"],
        key="puestos_origen",
    )
    if puestos_sel and "Todos" not in puestos_sel:
        df = df[df["Puesto"].isin(puestos_sel)]

# --- 📅 Finalización de contrato: ANULAR (por defecto True) o aplicar filtro ---
st.markdown("#### 📅 Finalización de contrato")
anular_filtro_contrato = st.checkbox(
    "Anular filtro de fecha de contrato (incluir a todos)",
    value=True,
    key="anular_filtro_contrato_global",
)

if not anular_filtro_contrato:
    fechas_validas = df["Contrato_dt"].dropna()

    if fechas_validas.empty:
        st.caption("No hay fechas válidas en el subconjunto actual.")
        incluir_nan = st.checkbox(
            "Agregar a la tabla a los jugadores que no tengan una fecha de finalización asignada",
            value=True,
            key="incluir_nan_contrato_empty_global",
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
            key="fecha_contrato_limite_global",
        )

        incluir_nan = st.checkbox(
            "Agregar a la tabla a los jugadores que no tengan una fecha de finalización asignada",
            value=False,
            key="incluir_nan_contrato_global",
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
#  Tabla final
# =========================
st.markdown("### 🧾 Jugadores que cumplen con los criterios")

df_tabla = df.copy()

# Renombres únicamente visuales.
df_tabla = df_tabla.rename(
    columns={
        "Age": "Edad",
        "Passport country": "Pasaporte",
        "Jugador con equipo": "Jugador",
        "Asistencias y creación de chances": "Ast. y chances",
        "Progresion de pelota": "Prog. de pelota",
    }
)

ATRIBUTOS_VISTA = [
    "Gol y Finalización",
    "Ast. y chances",
    "Juego asociado",
    "Prog. de pelota",
    "Juego aéreo",
    "Defensa",
    "1v1 en ataque",
    "1v1 en defensa",
    "Centros",
]

columnas_resultado = [
    "Jugador",
    "Puntaje",
    "Edad",
    "Puesto",
    "Minutos",
    "Pasaporte",
    "Liga",
    "Finalización de contrato",
] + ATRIBUTOS_VISTA

# Ordenar por Puntaje oficial; Minutos desempatan.
df_tabla = df_tabla.sort_values(
    by=["Puntaje", "Minutos"],
    ascending=[False, False],
    na_position="last",
)

if df_tabla.empty:
    st.warning("No hay jugadores que cumplan con los filtros seleccionados.")
else:
    columnas_visibles = [c for c in columnas_resultado if c in df_tabla.columns]
    st.dataframe(
        df_tabla[columnas_visibles],
        use_container_width=True,
        hide_index=True,
    )
