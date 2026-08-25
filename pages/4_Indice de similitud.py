# -*- coding: utf-8 -*-

import os

import numpy as np
import pandas as pd
import streamlit as st
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import StandardScaler

# =========================
#   Configuración de página
# =========================
st.set_page_config(page_title="Jugadores similares por perfil", layout="wide")
st.title("🔍 Jugadores similares por perfil")

st.markdown("""
### 🧠 ¿Qué hace esta herramienta?

Esta página te permite **buscar jugadores con un perfil de juego similar** al que selecciones.

Para lograrlo:
- Compara los atributos del modelo del puesto.
- Normaliza los atributos usando como referencia **toda la base del puesto**, para que la similitud no cambie por aplicar filtros de liga o minutos.
- Calcula la similitud de coseno entre el jugador elegido y el resto de los jugadores.

El resultado principal es **Similitud (%)**:
- **100%** → perfil prácticamente idéntico al jugador elegido.
- **50%** → sin una orientación clara de similitud.
- **0%** → perfil opuesto dentro de esta representación.

Los filtros modifican **dónde buscamos jugadores similares**, pero no la escala con la que se calcula la similitud.
""")

# =========================
#   Configuración de puestos
# =========================
# Mapping explícito para usar exactamente las mismas bases 2026
# que el Radar, el Explorador y el Buscador por atributos.
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

# El modelo nuevo tiene los 9 atributos en todos los puestos.
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
#   Utilidades
# =========================
@st.cache_data(show_spinner=False)
def cargar_datos_xlsx(path: str) -> pd.DataFrame:
    return pd.read_excel(path)


def asegurar_col(df: pd.DataFrame, col: str, valor=np.nan):
    if col not in df.columns:
        df[col] = valor


def to_num(s):
    return pd.to_numeric(s, errors="coerce")


def parse_contract_date(s):
    """Parsea fechas tipo '31/12/2026' a datetime."""
    if pd.isna(s):
        return pd.NaT
    s = str(s).strip()
    if not s or s.lower() == "nan":
        return pd.NaT
    return pd.to_datetime(s, dayfirst=True, errors="coerce")


# =========================
#   Selección de puesto
# =========================
puesto_seleccionado = st.selectbox(
    "Seleccioná el puesto a analizar:",
    PUESTOS,
)

# =========================
#   Carga de datos
# =========================
archivo = ARCHIVOS_POR_PUESTO[puesto_seleccionado]

if not os.path.isfile(archivo):
    st.error(
        f"No se encontró el archivo esperado para {puesto_seleccionado}: "
        f"'{archivo}'."
    )
    st.stop()

try:
    df0 = cargar_datos_xlsx(archivo).copy()
except Exception as e:
    st.error(f"No se pudo leer '{archivo}': {e}")
    st.stop()

# Columnas obligatorias
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

asegurar_col(df0, "Contract expires", "")
asegurar_col(df0, "Puntaje", np.nan)

# Comprobamos que estén los 9 atributos del modelo nuevo.
faltan_modelo = [a for a in ATRIBUTOS if a not in df0.columns]
if faltan_modelo:
    st.error(
        "Faltan atributos del modelo en el Excel: " + ", ".join(faltan_modelo)
    )
    st.stop()

# Limpieza básica
df0["Player"] = df0["Player"].fillna("").astype(str).str.strip()
df0["Team within selected timeframe"] = (
    df0["Team within selected timeframe"].fillna("").astype(str).str.strip()
)
df0["Pais competencia"] = df0["Pais competencia"].fillna("").astype(str).str.strip()
df0["Competencia"] = df0["Competencia"].fillna("").astype(str).str.strip()

df0["Liga"] = df0["Pais competencia"] + " - " + df0["Competencia"]
df0["Jugador con equipo"] = (
    df0["Player"] + " (" + df0["Team within selected timeframe"] + ")"
)
df0["Minutos"] = to_num(df0["Minutes played"]).fillna(0)
df0["Puntaje"] = to_num(df0["Puntaje"])

# Todos los atributos deben ser numéricos para el modelo de similitud.
for atributo in ATRIBUTOS:
    df0[atributo] = to_num(df0[atributo])

# Contrato
df0["Contrato_dt"] = df0["Contract expires"].apply(parse_contract_date)
df0["Finalización de contrato"] = np.where(
    df0["Contrato_dt"].notna(),
    df0["Contrato_dt"].dt.strftime("%d/%m/%Y"),
    df0["Contract expires"].fillna("").astype(str),
)

# =========================
#   Filtro mínimo de minutos
# =========================
st.markdown("#### ⏱️ Minutos mínimos")
min_minutos = st.number_input(
    "Minutos mínimos para considerar:",
    min_value=0,
    value=0,
    step=50,
)

df = df0[df0["Minutos"] >= min_minutos].copy()

if df.empty:
    st.warning("No hay jugadores con esos minutos.")
    st.stop()

# =========================
#   Jugador de referencia
# =========================
st.markdown("#### 👤 Jugador de referencia")

jugadores_ref = sorted(
    df.loc[df["Jugador con equipo"].str.strip() != "", "Jugador con equipo"]
    .dropna()
    .unique()
    .tolist()
)

if not jugadores_ref:
    st.warning("No hay jugadores disponibles para seleccionar como referencia.")
    st.stop()

jugador_ref = st.selectbox("Seleccioná el jugador:", jugadores_ref)

# =========================
#   Filtro por ligas
#   (universo de comparación)
# =========================
st.markdown("#### 🌍 Ligas donde buscar similares")

opciones_ligas = ["Todas"] + sorted(
    [liga for liga in df["Liga"].dropna().unique().tolist() if str(liga).strip()]
)
ligas_sel = st.multiselect("Ligas:", opciones_ligas, default=["Todas"])

if "Todas" in ligas_sel or not ligas_sel:
    df_comp_base = df.copy()
else:
    df_comp_base = df[df["Liga"].isin(ligas_sel)].copy()

if df_comp_base.empty:
    st.warning("No hay jugadores en esas ligas.")
    st.stop()

# =========================
#   Atributos a usar para comparar
# =========================
st.markdown("#### 📊 Atributos a comparar")

opciones_atr = ["Todos (por defecto)"] + ATRIBUTOS
atr_sel = st.multiselect(
    "Atributos:",
    opciones_atr,
    default=["Todos (por defecto)"],
)

if "Todos (por defecto)" in atr_sel:
    atributos_usar = ATRIBUTOS.copy()
else:
    atributos_usar = atr_sel

if not atributos_usar:
    st.warning("Seleccioná al menos un atributo para calcular la similitud.")
    st.stop()

# =========================
#   Cálculo de similitud
#   Coseno + z-score estable
# =========================
# IMPORTANTE:
# El StandardScaler se ajusta sobre TODA la base del puesto y NO sobre los
# jugadores que sobreviven a los filtros. Así, filtrar una liga o cambiar
# los minutos mínimos no redefine la escala de similitud entre dos jugadores.

df_model_base = df0.dropna(subset=atributos_usar).copy()

if df_model_base.empty:
    st.warning("No hay jugadores con datos completos en los atributos seleccionados.")
    st.stop()

# Referencia: se toma desde la base filtrada por minutos para respetar la
# selección visible del usuario.
df_ref = df[df["Jugador con equipo"] == jugador_ref].dropna(
    subset=atributos_usar
).copy()

if df_ref.empty:
    st.warning("El jugador seleccionado no tiene datos en esos atributos.")
    st.stop()

df_ref = df_ref.head(1)

# Candidatos: se aplican minutos + ligas, pero la normalización sigue siendo
# la de toda la base del puesto.
df_comp = df_comp_base.dropna(subset=atributos_usar).copy()
df_comp = df_comp[df_comp["Jugador con equipo"] != jugador_ref]

if df_comp.empty:
    st.warning("No hay otros jugadores con datos válidos para comparar.")
    st.stop()

# Ajustamos el scaler una única vez sobre toda la población del puesto.
scaler = StandardScaler()
scaler.fit(df_model_base[atributos_usar].astype(float).values)

X_ref = scaler.transform(df_ref[atributos_usar].astype(float).values)
X_comp = scaler.transform(df_comp[atributos_usar].astype(float).values)

sim_cos = cosine_similarity(X_ref, X_comp)[0]

# El coseno puede ir matemáticamente de -1 a 1.
# Lo llevamos linealmente a una escala 0-100:
# -1 -> 0, 0 -> 50, 1 -> 100.
similitud_pct = (((sim_cos + 1) / 2) * 100).round(2)
distancias = (1 - sim_cos).round(4)

# Resultado
resultados = df_comp.copy()
resultados["Distancia (coseno-z)"] = distancias
resultados["Similitud (%)"] = similitud_pct

resultados = resultados.sort_values(
    ["Similitud (%)", "Puntaje", "Minutos"],
    ascending=[False, False, False],
    na_position="last",
)

# =========================
#   Mostrar tabla final
# =========================
st.markdown("### 🏆 Jugadores más similares (por perfil)")

cols_mostrar = [
    "Jugador con equipo",
    "Age",
    "Passport country",
    "Liga",
    "Minutos",
    "Puntaje",
    "Finalización de contrato",
    "Similitud (%)",
    "Distancia (coseno-z)",
]

cols_mostrar = [c for c in cols_mostrar if c in resultados.columns]

st.dataframe(
    resultados[cols_mostrar].reset_index(drop=True),
    use_container_width=True,
)
