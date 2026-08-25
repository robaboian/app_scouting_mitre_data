from pathlib import Path

import pandas as pd
import streamlit as st


# ============================================================
# CONFIGURACIÓN
# ============================================================

st.set_page_config(
    page_title="Scouting | Club Atlético Mitre",
    page_icon="⚽",
    layout="wide",
)


# ============================================================
# ESCUDO
# ============================================================

logo_path = (
    Path(__file__).resolve().parent
    / "assets"
    / "escudo_mitre.png"
)


# ============================================================
# ENCABEZADO
# ============================================================

col_logo, col_text = st.columns(
    [1, 5],
    vertical_alignment="center",
)

with col_logo:
    if logo_path.exists():
        st.image(
            str(logo_path),
            width=170,
        )

with col_text:
    st.title(
        "Club Atlético Mitre"
    )

    st.subheader(
        "Secretaría Técnica · Departamento de Scouting"
    )

    st.caption(
        "Herramienta interna de análisis, comparación "
        "y búsqueda de perfiles de futbolistas."
    )

st.divider()


# ============================================================
# PRESENTACIÓN
# ============================================================

st.write(
    """
Esta plataforma centraliza el análisis de jugadores a partir de las bases
estadísticas del área de scouting. Permite comparar perfiles, explorar el
universo disponible, buscar futbolistas a partir de atributos específicos
y encontrar jugadores con características similares.

Las bases 2026 trabajan con los **9 perfiles definitivos del modelo de scouting**
y con una escala común de atributos de **0 a 100**.
"""
)


# ============================================================
# ACTUALIZACIÓN DE BASES POR PUESTO
# ============================================================

st.subheader(
    "📅 Actualización de bases de datos por puesto"
)

# Puestos oficiales del modelo 2026
PUESTOS = [
    "Defensor central",
    "Lateral",
    "Volante contención",
    "Interior contención",
    "Interior ofensivo",
    "Volante ofensivo",
    "Media punta",
    "Extremo",
    "Delantero",
]

# ✍️ Editá este diccionario cuando subas o actualices una base.
# Formato sugerido: DD/MM/AAAA
ACTUALIZACION_PUESTOS = {
    "Defensor central": "25/08/2026",
    "Lateral": "25/08/2026",
    "Volante contención": "25/08/2026",
    "Interior contención": "25/08/2026",
    "Interior ofensivo": "25/08/2026",
    "Volante ofensivo": "25/08/2026",
    "Media punta": "25/08/2026",
    "Extremo": "25/08/2026",
    "Delantero": "25/08/2026",
}

# Garantizamos que existan todas las claves y respetamos el orden de PUESTOS
ACTUALIZACION_PUESTOS = {
    puesto: ACTUALIZACION_PUESTOS.get(puesto, "")
    for puesto in PUESTOS
}

df_actualizacion = pd.DataFrame(
    {
        "Puesto": PUESTOS,
        "Última actualización": [
            ACTUALIZACION_PUESTOS[puesto]
            for puesto in PUESTOS
        ],
    }
)

st.dataframe(
    df_actualizacion,
    use_container_width=True,
    hide_index=True,
)


# ============================================================
# MÓDULOS
# ============================================================

st.subheader(
    "Módulos de trabajo"
)

c1, c2, c3, c4 = st.columns(4)

with c1:
    with st.container(border=True):
        st.markdown(
            "### 📊 Gráficos de radar"
        )

        st.write(
            """
Compará jugadores de un mismo perfil a través de los nueve atributos
principales del modelo, siempre sobre una escala fija de 0 a 100.
"""
        )

with c2:
    with st.container(border=True):
        st.markdown(
            "### 🔍 Explorador de jugadores"
        )

        st.write(
            """
Explorá las bases mediante filtros de puesto, liga, minutos, edad,
pasaporte, pierna y situación contractual.
"""
        )

with c3:
    with st.container(border=True):
        st.markdown(
            "### 🎯 Buscador por atributos"
        )

        st.write(
            """
Definí rangos mínimos y máximos para los atributos del modelo y encontrá
jugadores que respondan a un perfil específico.
"""
        )

with c4:
    with st.container(border=True):
        st.markdown(
            "### 🧬 Índice de similitud"
        )

        st.write(
            """
Seleccioná un jugador de referencia y buscá perfiles estadísticamente
similares dentro del universo elegido.
"""
        )


# ============================================================
# PERFILES DEL MODELO
# ============================================================

st.subheader(
    "Perfiles del modelo"
)

st.write(
    """
**Defensor central · Lateral · Volante contención · Interior contención ·
Interior ofensivo · Volante ofensivo · Media punta · Extremo · Delantero**
"""
)


# ============================================================
# FLUJO DE TRABAJO
# ============================================================

st.subheader(
    "Flujo de trabajo"
)

st.write(
    """
**1.** Seleccionar el puesto o perfil a analizar  
**2.** Delimitar el universo mediante los filtros disponibles  
**3.** Comparar rendimiento general y atributos específicos  
**4.** Profundizar sobre candidatos mediante radar, búsqueda o similitud
"""
)

st.divider()


# ============================================================
# PIE
# ============================================================

st.caption(
    "Club Atlético Mitre · Secretaría Técnica · Departamento de Scouting"
)
