# ===============================================================
# SIMULADOR DE EMISIONES – METODOLOGÍA IPCC
# Versión web con Streamlit + Plotly
#
# Ejecutar localmente:
#   pip install streamlit pandas plotly matplotlib
#   streamlit run app_streamlit_emisiones_ipcc.py
#
# Para publicar:
#   subir este archivo a GitHub y desplegarlo en Streamlit Community Cloud
# ===============================================================

from datetime import datetime
from io import BytesIO

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages


# ---------------- Configuración de página ----------------

st.set_page_config(
    page_title="Simulador IPCC de emisiones",
    page_icon="🚛",
    layout="wide"
)


# ---------------- Parámetros IPCC y conversión energética ----------------

FE_IPCC_TJ = {
    "diesel":    {"CO2": 74100.0, "CH4": 3.9,   "N2O": 3.9},
    "biodiesel": {"CO2": 0.0,     "CH4": 3.9,   "N2O": 3.9},
    "gnl":       {"CO2": 56100.0, "CH4": 16.0,  "N2O": 3.2},
    "eléctrico": {"CO2": 0.0,     "CH4": 0.0,   "N2O": 0.0},
}

TJ_POR_L_DIESEL = 43.0 / 1e6
GWP_CH4 = 28.0
GWP_N2O = 265.0


# ---------------- Funciones de cálculo ----------------

def calcular_emisiones_ipcc(consumo_total_l: float, combustible: str):
    """Calcula emisiones por base combustible según factores IPCC."""
    if combustible not in FE_IPCC_TJ:
        combustible = "diesel"

    fe = FE_IPCC_TJ[combustible]

    if combustible in ("diesel", "biodiesel", "gnl"):
        energia_tj = consumo_total_l * TJ_POR_L_DIESEL
    else:
        energia_tj = 0.0

    co2 = energia_tj * fe["CO2"]
    ch4 = energia_tj * fe["CH4"]
    n2o = energia_tj * fe["N2O"]
    co2e = co2 + ch4 * GWP_CH4 + n2o * GWP_N2O

    return co2, ch4, n2o, co2e, energia_tj


def clasificar(emis_tkm: float):
    """Clasifica la eficiencia según t CO2e por t·km."""
    if emis_tkm < 0.0006:
        return "A eficiencia alta", "Mantener prácticas y combustibles de bajo azufre"
    if emis_tkm < 0.0010:
        return "B eficiencia media", "Optimizar carga útil y reducir marcha lenta"
    return "C eficiencia baja", "Revisar consumo, neumáticos y evaluar biodiésel o nuevas tecnologías"


def validar(grupo, integrantes, distancia_ida, cons_cargado, cons_vacio, carga, llenado):
    errores = []

    if not grupo.strip():
        errores.append("El nombre del grupo es obligatorio.")

    if len(integrantes) == 0:
        errores.append("Debe informar al menos 1 integrante del grupo.")

    if len(integrantes) > 6:
        errores.append("El máximo permitido es 6 integrantes.")

    if distancia_ida <= 0:
        errores.append("La distancia de ida debe ser positiva.")

    if cons_cargado < 0 or cons_vacio < 0:
        errores.append("Los consumos no pueden ser negativos.")

    if carga <= 0:
        errores.append("La carga útil debe ser positiva.")

    if llenado <= 0:
        errores.append("El factor de llenado debe ser mayor que cero.")

    return errores


def crear_dataframe_resultados(resumen: dict) -> pd.DataFrame:
    return pd.DataFrame([{
        "grupo": resumen["grupo"],
        "integrantes": resumen["integrantes"],
        "pais": resumen["pais"],
        "vehiculo": resumen["vehiculo"],
        "euro": resumen["euro"],
        "combustible": resumen["comb"],
        "dist_ida_km": resumen["dist_ida_km"],
        "dist_total_km": resumen["dist_total"],
        "retorno_vacio": resumen["retorno_vacio"],
        "cons_total_L": resumen["cons_total_L"],
        "energia_TJ": resumen["energia_TJ"],
        "CO2_kg": resumen["CO2"],
        "CH4_kg": resumen["CH4_kg"],
        "N2O_kg": resumen["N2O_kg"],
        "CO2e_kg": resumen["CO2e"],
        "emis_kg_CO2e_tkm": resumen["emis_kg_tkm"],
        "llenado_pct": resumen["fill_pct"],
        "carga_t": resumen["carga_t"],
        "urbano_pct": resumen["urb_pct"],
        "marcha_lenta_min_h": resumen["idle_min_h"],
        "velocidad_km_h": resumen["vel_kmh"],
        "reflexion": resumen["reflexion"]
    }])


def crear_grafico_plotly(resumen: dict):
    etiquetas = ["CO₂ kg", "CH₄ g", "N₂O g", "CO₂e kg"]
    valores = [
        resumen["CO2"],
        resumen["CH4_kg"] * 1000.0,
        resumen["N2O_kg"] * 1000.0,
        resumen["CO2e"],
    ]

    fig = go.Figure(
        data=[
            go.Bar(
                x=etiquetas,
                y=valores,
                text=[f"{v:.2f}" for v in valores],
                textposition="outside",
                hovertemplate="<b>%{x}</b><br>Valor: %{y:.4f}<extra></extra>",
            )
        ]
    )

    fig.update_layout(
        title="Perfil de emisiones por viaje",
        xaxis_title="Indicador",
        yaxis_title="Valor calculado",
        template="plotly_white",
        height=460,
        margin=dict(l=30, r=30, t=70, b=40),
    )

    return fig


def generar_pdf(resumen: dict) -> bytes:
    """Genera un PDF en memoria y devuelve bytes."""
    buffer = BytesIO()

    with PdfPages(buffer) as pdf:
        # Página 1: resumen vertical
        fig1 = plt.figure(figsize=(8.3, 11.7))
        plt.axis("off")

        ts = datetime.now().strftime("%Y-%m-%d %H:%M")

        plt.text(0.5, 0.96, "Simulador de emisiones – Metodología IPCC", ha="center", va="top", fontsize=16)
        plt.text(0.5, 0.93, "Versión educativa MERCOSUR – IPCC 2019 – GWP AR5", ha="center", va="top", fontsize=10)

        y = 0.88
        pares = [
            ("Nombre del grupo", resumen["grupo"]),
            ("Integrantes", resumen["integrantes"] if resumen["integrantes"] else "—"),
            ("País", resumen["pais"]),
            ("Vehículo", resumen["vehiculo"]),
            ("Clase Euro", resumen["euro"]),
            ("Combustible", resumen["comb"]),
            ("Distancia total (km)", f"{resumen['dist_total']:.1f}"),
            ("Consumo total (L)", f"{resumen['cons_total_L']:.2f}"),
            ("Energía consumida (TJ)", f"{resumen['energia_TJ']:.6f}"),
            ("CO₂ (kg)", f"{resumen['CO2']:.2f}"),
            ("CH₄ (g)", f"{resumen['CH4_kg'] * 1000.0:.3f}"),
            ("N₂O (g)", f"{resumen['N2O_kg'] * 1000.0:.3f}"),
            ("CO₂e total (kg)", f"{resumen['CO2e']:.2f}"),
            ("Emisión específica (kg CO₂e por t·km)", f"{resumen['emis_kg_tkm']:.3f}"),
            ("Clasificación", resumen["clas"]),
            ("Recomendación", resumen["reco"]),
            ("Fecha y hora", ts),
        ]

        for k, v in pares:
            plt.text(0.08, y, k, fontsize=12, ha="left")
            plt.text(0.55, y, str(v), fontsize=12, ha="left")
            y -= 0.045

        pdf.savefig(fig1)
        plt.close(fig1)

        # Página 2: gráfico con Matplotlib para PDF
        fig2 = plt.figure(figsize=(8.3, 5.0))
        etiquetas = ["CO2 kg", "CH4 g", "N2O g", "CO2e kg"]
        valores = [
            resumen["CO2"],
            resumen["CH4_kg"] * 1000.0,
            resumen["N2O_kg"] * 1000.0,
            resumen["CO2e"],
        ]

        bars = plt.bar(etiquetas, valores)
        plt.title("Perfil de emisiones por viaje")
        plt.grid(axis="y", linestyle=":", alpha=0.5)

        for b in bars:
            h = b.get_height()
            plt.text(
                b.get_x() + b.get_width() / 2,
                h,
                f"{h:.2f}",
                ha="center",
                va="bottom",
                fontsize=9
            )

        plt.tight_layout()
        pdf.savefig(fig2)
        plt.close(fig2)

        # Página 3: reflexión
        fig3 = plt.figure(figsize=(8.3, 11.7))
        plt.axis("off")

        plt.text(0.5, 0.96, "Reflexión del estudiante", ha="center", va="top", fontsize=16)
        plt.text(0.08, 0.92, f"Grupo: {resumen['grupo']}", fontsize=12)
        plt.text(0.08, 0.88, f"Integrantes: {resumen['integrantes'] if resumen['integrantes'] else '—'}", fontsize=12)

        y = 0.84
        lineas = [l.strip() for l in resumen["reflexion"].splitlines() if l.strip()]
        if not lineas:
            lineas = ["Sin respuesta"]

        for linea in lineas:
            plt.text(0.10, y, f"• {linea}", fontsize=12, ha="left")
            y -= 0.045

        pdf.savefig(fig3)
        plt.close(fig3)

        # Página 4: guía técnica
        fig4 = plt.figure(figsize=(8.3, 11.7))
        plt.axis("off")

        plt.text(0.5, 0.96, "Guía técnica IPCC", ha="center", va="top", fontsize=16)

        guion = [
            "Emisiones = Actividad × Factor de emisión.",
            "La actividad corresponde al consumo energético del combustible.",
            "Diésel: 43 TJ por 10^6 L. Por tanto, 1 L = 43/10^6 TJ.",
            "Factores IPCC 2019: CO2 74100 kg/TJ, CH4 3,9 kg/TJ, N2O 3,9 kg/TJ.",
            "GWP AR5: CH4 28 y N2O 265.",
            "Emisión específica: kg CO2e por t·km.",
            "La clase Euro y el entorno operativo registran condiciones, pero no alteran el cómputo IPCC si el consumo es el mismo.",
        ]

        y = 0.90
        for item in guion:
            plt.text(0.08, y, item, fontsize=12, ha="left")
            y -= 0.045

        pdf.savefig(fig4)
        plt.close(fig4)

    buffer.seek(0)
    return buffer.read()


# ---------------- Estado inicial y preset ----------------

if "preset_cargado" not in st.session_state:
    st.session_state.preset_cargado = False

if "resumen" not in st.session_state:
    st.session_state.resumen = None

if "tabla" not in st.session_state:
    st.session_state.tabla = None


def cargar_preset():
    st.session_state.grupo = ""
    st.session_state.miembros = ""
    st.session_state.pais = "Uruguay"
    st.session_state.vehiculo = "Pesado"
    st.session_state.euro = "V"
    st.session_state.combustible = "diesel"
    st.session_state.distancia_ida = 390.0
    st.session_state.retorna_vacio = True
    st.session_state.consumo_cargado = 0.38
    st.session_state.consumo_vacio = 0.30
    st.session_state.carga_t = 30.0
    st.session_state.llenado_pct = 100
    st.session_state.urbano_pct = 20
    st.session_state.idle_min_h = 8
    st.session_state.velocidad_kmh = 75.0
    st.session_state.reflexion = (
        "Indique tres medidas operativas para reducir la emisión específica "
        "sin afectar el nivel de servicio."
    )
    st.session_state.preset_cargado = True


if not st.session_state.preset_cargado:
    cargar_preset()


# ---------------- Encabezado ----------------

st.title("🚛 Simulador interactivo de emisiones para transporte carretero")
st.caption("Metodología IPCC por base combustible · IPCC 2006 / 2019 Refinement · GWP AR5")


# ---------------- Sidebar ----------------

with st.sidebar:
    st.header("Acciones")

    if st.button("Cargar caso Tacuarembó → Montevideo", use_container_width=True):
        cargar_preset()
        st.success("Caso preset cargado.")

    st.divider()

    st.subheader("Guía rápida")
    st.markdown(
        """
        **Metodología IPCC**  
        Emisiones = Actividad × Factor de emisión.

        **Actividad**  
        Consumo energético del combustible.

        **Diésel**  
        43 TJ por 10⁶ L.

        **Factores IPCC 2019 diésel**  
        CO₂: 74 100 kg/TJ  
        CH₄: 3,9 kg/TJ  
        N₂O: 3,9 kg/TJ

        **GWP AR5**  
        CH₄: 28  
        N₂O: 265
        """
    )


# ---------------- Formularios ----------------

with st.form("formulario_emisiones"):
    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("Identificación del grupo")

        grupo = st.text_input(
            "Nombre del grupo",
            key="grupo"
        )

        miembros_texto = st.text_area(
            "Integrantes, uno por línea, máximo 6",
            key="miembros",
            height=130
        )

        st.subheader("Entradas técnicas generales")

        pais = st.selectbox(
            "País",
            ["Uruguay", "Argentina", "Brasil", "Paraguay", "Bolivia"],
            key="pais"
        )

        vehiculo = st.radio(
            "Vehículo",
            ["Liviano", "Mediano", "Pesado"],
            horizontal=True,
            key="vehiculo"
        )

        euro = st.radio(
            "Clase Euro",
            ["III", "IV", "V", "VI"],
            horizontal=True,
            key="euro"
        )

        combustible = st.radio(
            "Combustible",
            ["diesel", "biodiesel", "gnl", "eléctrico"],
            horizontal=True,
            key="combustible"
        )

    with col2:
        st.subheader("Parámetros operativos")

        distancia_ida = st.number_input(
            "Distancia de ida (km)",
            min_value=0.0,
            value=st.session_state.distancia_ida,
            step=10.0,
            key="distancia_ida"
        )

        retorna_vacio = st.checkbox(
            "¿Retorna vacío?",
            key="retorna_vacio"
        )

        consumo_cargado = st.number_input(
            "Consumo cargado (L/km)",
            min_value=0.0,
            value=st.session_state.consumo_cargado,
            step=0.01,
            format="%.3f",
            key="consumo_cargado"
        )

        consumo_vacio = st.number_input(
            "Consumo vacío (L/km)",
            min_value=0.0,
            value=st.session_state.consumo_vacio,
            step=0.01,
            format="%.3f",
            key="consumo_vacio"
        )

        carga_t = st.number_input(
            "Carga útil transportada (t)",
            min_value=0.0,
            value=st.session_state.carga_t,
            step=1.0,
            key="carga_t"
        )

        llenado_pct = st.slider(
            "Factor de llenado (%)",
            min_value=10,
            max_value=100,
            step=5,
            key="llenado_pct"
        )

        urbano_pct = st.slider(
            "Recorrido urbano (%)",
            min_value=0,
            max_value=100,
            step=5,
            key="urbano_pct"
        )

        idle_min_h = st.slider(
            "Marcha lenta (min por hora)",
            min_value=0,
            max_value=60,
            step=1,
            key="idle_min_h"
        )

        velocidad_kmh = st.number_input(
            "Velocidad promedio (km/h)",
            min_value=0.0,
            value=st.session_state.velocidad_kmh,
            step=5.0,
            key="velocidad_kmh"
        )

    st.subheader("Reflexión del estudiante")

    reflexion = st.text_area(
        "Indique medidas operativas para reducir la emisión específica sin afectar el nivel de servicio",
        key="reflexion",
        height=130
    )

    calcular = st.form_submit_button("Calcular emisiones", use_container_width=True)


# ---------------- Cálculo ----------------

if calcular:
    integrantes = [l.strip() for l in miembros_texto.splitlines() if l.strip()]
    errores = validar(
        grupo=grupo,
        integrantes=integrantes,
        distancia_ida=distancia_ida,
        cons_cargado=consumo_cargado,
        cons_vacio=consumo_vacio,
        carga=carga_t,
        llenado=llenado_pct
    )

    if errores:
        for error in errores:
            st.error(error)
    else:
        integrantes_str = "; ".join(integrantes)

        dist_total = distancia_ida * (2.0 if retorna_vacio else 1.0)
        cons_total_l = distancia_ida * consumo_cargado

        if retorna_vacio:
            cons_total_l += distancia_ida * consumo_vacio

        co2, ch4, n2o, co2e, energia_tj = calcular_emisiones_ipcc(cons_total_l, combustible)

        denom_t_km = max(carga_t * dist_total * (llenado_pct / 100.0), 1e-9)
        emis_tkm = (co2e / 1000.0) / denom_t_km
        emis_kg_tkm = emis_tkm * 1000.0

        clas, reco = clasificar(emis_tkm)

        resumen = {
            "grupo": grupo.strip(),
            "integrantes": integrantes_str,
            "pais": pais,
            "vehiculo": vehiculo,
            "euro": euro,
            "comb": combustible,
            "dist_total": dist_total,
            "cons_total_L": cons_total_l,
            "energia_TJ": energia_tj,
            "CO2": co2,
            "CH4_kg": ch4,
            "N2O_kg": n2o,
            "CO2e": co2e,
            "emis_kg_tkm": emis_kg_tkm,
            "clas": clas,
            "reco": reco,
            "reflexion": reflexion.strip(),
            "urb_pct": urbano_pct,
            "idle_min_h": idle_min_h,
            "vel_kmh": velocidad_kmh,
            "fill_pct": llenado_pct,
            "carga_t": carga_t,
            "retorno_vacio": retorna_vacio,
            "dist_ida_km": distancia_ida
        }

        st.session_state.resumen = resumen
        st.session_state.tabla = crear_dataframe_resultados(resumen)

        st.success("Cálculo realizado correctamente.")


# ---------------- Resultados ----------------

if st.session_state.resumen is not None:
    r = st.session_state.resumen
    tabla = st.session_state.tabla

    st.divider()
    st.header("Resultados según metodología IPCC")

    m1, m2, m3, m4 = st.columns(4)

    m1.metric("CO₂e total", f"{r['CO2e']:.2f} kg")
    m2.metric("Emisión específica", f"{r['emis_kg_tkm']:.3f} kg CO₂e/t·km")
    m3.metric("Consumo total", f"{r['cons_total_L']:.2f} L")
    m4.metric("Energía consumida", f"{r['energia_TJ']:.6f} TJ")

    col_res1, col_res2 = st.columns([1, 1])

    with col_res1:
        st.subheader("Resumen vertical")

        resumen_df = pd.DataFrame({
            "Campo": [
                "Nombre del grupo",
                "Integrantes",
                "País",
                "Vehículo",
                "Clase Euro",
                "Combustible",
                "Distancia total (km)",
                "Consumo total (L)",
                "Energía consumida (TJ)",
                "CO₂ (kg)",
                "CH₄ (g)",
                "N₂O (g)",
                "CO₂e total (kg)",
                "Emisión específica (kg CO₂e por t·km)",
                "Clasificación",
                "Recomendación",
            ],
            "Valor": [
                r["grupo"],
                r["integrantes"] if r["integrantes"] else "—",
                r["pais"],
                r["vehiculo"],
                r["euro"],
                r["comb"],
                f"{r['dist_total']:.1f}",
                f"{r['cons_total_L']:.2f}",
                f"{r['energia_TJ']:.6f}",
                f"{r['CO2']:.2f}",
                f"{r['CH4_kg'] * 1000.0:.3f}",
                f"{r['N2O_kg'] * 1000.0:.3f}",
                f"{r['CO2e']:.2f}",
                f"{r['emis_kg_tkm']:.3f}",
                r["clas"],
                r["reco"],
            ]
        })

        st.dataframe(resumen_df, hide_index=True, use_container_width=True)

    with col_res2:
        st.subheader("Gráfico interactivo")
        fig = crear_grafico_plotly(r)
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Reflexión del estudiante")
    st.write(r["reflexion"] if r["reflexion"] else "Sin respuesta.")

    st.subheader("Exportaciones")

    csv_bytes = tabla.to_csv(index=False).encode("utf-8")

    st.download_button(
        label="Descargar CSV",
        data=csv_bytes,
        file_name="resultado_simulador_emisiones_IPCC.csv",
        mime="text/csv",
        use_container_width=True
    )

    pdf_bytes = generar_pdf(r)

    nombre_pdf = f"reporte_emisiones_IPCC_{r['grupo'].replace(' ', '_') or 'grupo'}.pdf"

    st.download_button(
        label="Descargar PDF",
        data=pdf_bytes,
        file_name=nombre_pdf,
        mime="application/pdf",
        use_container_width=True
    )

else:
    st.info("Complete los datos y presione **Calcular emisiones** para ver los resultados.")
