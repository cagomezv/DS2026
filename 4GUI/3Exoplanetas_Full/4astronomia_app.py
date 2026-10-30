import streamlit as st
import pandas as pd
import numpy as np
import mysql.connector
import plotly.express as px
import plotly.graph_objects as go

# --------------------------------------------------
# 1. CONFIGURACIÓN GLOBAL
# --------------------------------------------------
st.set_page_config(
    page_title="Sistema de Análisis Exoplanetario",
    page_icon="🌌",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --------------------------------------------------
# 2. CONEXIÓN Y EXTRACCIÓN DE DATOS
# --------------------------------------------------
@st.cache_resource
def init_connection():
    return mysql.connector.connect(
        host="localhost", # Mantener localhost para la ejecución local
        port=3306,
        user="root",
        password="root",
        database="astronomia"
    )

@st.cache_data
def load_master_data():
    conn = init_connection()
    query = """
        SELECT 
            p.nombre AS planeta, p.masa AS p_masa, p.radio AS p_radio, 
            p.periodo_orbital, p.semieje_mayor,
            e.nombre AS estrella, e.masa AS e_masa, e.radio AS e_radio, e.temperatura,
            d.año, d.metodo,
            t.nombre AS telescopio, t.instalacion, t.instrumento
        FROM planeta p
        JOIN estrella e ON p.id_estrella = e.id_estrella
        JOIN descubrimiento d ON p.id_planeta = d.id_planeta
        JOIN telescopio t ON d.id_telescopio = t.id_telescopio
    """
    df = pd.read_sql(query, conn)
    return df

df_master = load_master_data()

# --------------------------------------------------
# 3. MENÚ LATERAL Y FILTROS GLOBALES
# --------------------------------------------------
st.sidebar.title("🌌 Navegación Analítica")
st.sidebar.markdown("---")

modulo = st.sidebar.radio(
    "Módulos de Análisis:",
    ["Visión General", "Astrofísica Planetaria", "Análisis Estelar", "Instrumentación y Métodos"]
)

st.sidebar.markdown("---")
st.sidebar.subheader("Filtros Globales")

min_year = int(df_master['año'].min())
max_year = int(df_master['año'].max())
rango_años = st.sidebar.slider("Rango de Descubrimiento", min_year, max_year, (min_year, max_year))

metodos_disponibles = df_master['metodo'].unique().tolist()
metodos_seleccionados = st.sidebar.multiselect("Método de Detección", metodos_disponibles, default=metodos_disponibles)

df_filtrado = df_master[
    (df_master['año'] >= rango_años[0]) & 
    (df_master['año'] <= rango_años[1]) &
    (df_master['metodo'].isin(metodos_seleccionados))
]

st.sidebar.markdown("---")
st.sidebar.info(f"Mostrando {len(df_filtrado):,} planetas filtrados.")

# --------------------------------------------------
# 4. MÓDULOS DE VISUALIZACIÓN
# --------------------------------------------------

if modulo == "Visión General":
    st.title("Visión General del Catálogo Exoplanetario")
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Exoplanetas Confirmados", f"{len(df_filtrado):,}")
    col2.metric("Sistemas Estelares", f"{df_filtrado['estrella'].nunique():,}")
    col3.metric("Telescopios Involucrados", f"{df_filtrado['telescopio'].nunique():,}")
    metodo_top = df_filtrado['metodo'].mode()[0] if not df_filtrado.empty else "N/A"
    col4.metric("Método Dominante", metodo_top)
    
    st.markdown("---")
    
    st.subheader("Fundamento Teórico: La Revolución Observacional")
    st.markdown("""
    Históricamente, la confirmación de exoplanetas representó un cambio de paradigma en la astrofísica moderna. 
    Pasamos de modelos teóricos de formación planetaria basados en una única muestra (nuestro Sistema Solar) a la 
    necesidad de formular teorías generales que explicaran una diversidad orbital y composicional inesperada. 
    Este salto epistemológico fue impulsado enteramente por la evolución de las técnicas de recolección de datos, 
    especialmente la transición de la *Velocidad Radial* (espectroscopía) a los *Tránsitos* (fotometría de alta precisión).
    """)
    
    fig_hist = px.histogram(
        df_filtrado, x="año", color="metodo",
        title="Distribución histórica de detecciones por técnica",
        labels={"año": "Año", "count": "Número de Descubrimientos", "metodo": "Técnica"},
        barmode="stack",
        color_discrete_sequence=px.colors.qualitative.Prism
    )
    fig_hist.update_layout(bargap=0.1)
    st.plotly_chart(fig_hist, use_container_width=True)
    
    st.info("**Insight Analítico:** La gráfica exhibe anomalías estadísticas (picos masivos) en años específicos (ej. 2014, 2016). Estas discontinuidades no reflejan fenómenos físicos, sino *sesgos observacionales* derivados de la liberación de grandes volúmenes de datos minados por misiones espaciales como Kepler. Observamos cómo el método de tránsito desplaza casi por completo a la velocidad radial en la última década.")

elif modulo == "Astrofísica Planetaria":
    st.title("Astrofísica y Dinámica Planetaria")
    
    tab1, tab2 = st.tabs(["Ecuación de Estado (Masa-Radio)", "Mecánica Celeste (Leyes de Kepler)"])
    
    with tab1:
        st.subheader("Fundamento Teórico: Diferenciación Estructural")
        st.markdown("""
        La relación entre la masa ($M$) y el radio ($R$) de un planeta está regida por su ecuación de estado. 
        Para mundos rocosos, el radio crece aproximadamente como $R \propto M^{1/3}$ asumiendo densidad constante o 
        ligeramente compresible. Sin embargo, para los gigantes gaseosos (dominados por H y He), la presión de 
        degeneración electrónica de los núcleos de hidrógeno contrarresta el colapso gravitacional, provocando 
        que el radio se estabilice matemáticamente (alrededor de 10-15 radios terrestres) independientemente de 
        cuánta masa se añada, hasta cruzar el umbral hacia la fusión nuclear (enanas marrones y estrellas).
        """)
        
        df_mr = df_filtrado.dropna(subset=['p_masa', 'p_radio'])
        fig_mr = px.scatter(
            df_mr, x="p_masa", y="p_radio", color="temperatura",
            hover_name="planeta", log_x=True, log_y=True,
            labels={"p_masa": "Masa Terrestre ($M_\oplus$)", "p_radio": "Radio Terrestre ($R_\oplus$)", "temperatura": "Temp. Estelar (K)"},
            color_continuous_scale="Viridis",
            title="Relación de Densidad Poblacional: Supertierras y Gigantes Gaseosos"
        )
        st.plotly_chart(fig_mr, use_container_width=True)
        st.info("**Insight Analítico:** La escala logarítmica evidencia topologías poblacionales claras. Observamos la meseta estructural en la parte superior derecha (el límite de degeneración de Júpiter) y una diagonal pronunciada en la parte inferior izquierda correspondiente a planetas rocosos donde el volumen sí responde linealmente al incremento de masa.")

    with tab2:
        st.subheader("Fundamento Teórico: Dinámica Orbital")
        st.markdown("""
        La mecánica de los sistemas exoplanetarios sigue la generalización newtoniana de la Tercera Ley de Kepler. 
        Igualando la fuerza de gravedad a la fuerza centrípeta, obtenemos la relación entre el periodo orbital ($P$) 
        y el semieje mayor ($a$):
        
        $$ P^2 = \\frac{4\pi^2}{G(M_\\star + m_p)} a^3 $$
        
        Dado que la masa del planeta ($m_p$) es despreciable frente a la masa de la estrella ($M_\\star$), 
        en un espacio logarítmico, la relación debe presentarse como una línea recta perfecta con pendiente 3/2, 
        cuya única fuente de dispersión vertical sistemática será la varianza poblacional de las masas estelares ($M_\\star$).
        """)
        
        df_kep = df_filtrado.dropna(subset=['periodo_orbital', 'semieje_mayor'])
        fig_kep = px.scatter(
            df_kep, x="semieje_mayor", y="periodo_orbital", color="metodo",
            hover_name="planeta", log_x=True, log_y=True,
            labels={"semieje_mayor": "Semieje Mayor (UA)", "periodo_orbital": "Periodo Orbital (Días)"},
            title="Validación de la Generalización de Newton-Kepler"
        )
        st.plotly_chart(fig_kep, use_container_width=True)
        st.info("**Insight Analítico:** Los algoritmos de extracción confirman invariabilidad de la mecánica clásica en sistemas exoplanetarios. Las ligeras franjas paralelas a la diagonal principal corresponden matemáticamente a diferentes tipos espectrales de estrellas (estrellas más masivas empujan la curva hacia abajo por poseer mayor atracción gravitatoria a igual distancia).")

elif modulo == "Análisis Estelar":
    st.title("Termodinámica y Sesgos en Estrellas Hospedadoras")
    
    st.subheader("Fundamento Teórico: Equilibrio Hidrostático")
    st.markdown("""
    La viabilidad de hospedar planetas a largo plazo depende de la estabilidad térmica y gravitacional de la estrella, 
    descrita por el equilibrio hidrostático. En el Diagrama de Hertzsprung-Russell (H-R), las estrellas que fusionan 
    hidrógeno mediante la cadena p-p ocupan la *Secuencia Principal*. Las variaciones en la temperatura efectiva 
    ($T_{eff}$) y el radio ($R_\\star$) influyen críticamente en la zona de habitabilidad. Además, las técnicas de 
    detección de anomalías tienen umbrales de sensibilidad diferentes según la termodinámica de la estrella.
    """)
    
    col1, col2 = st.columns(2)
    
    with col1:
        df_temp = df_filtrado.dropna(subset=['temperatura'])
        fig_box = px.box(
            df_temp, x="metodo", y="temperatura", color="metodo",
            labels={"temperatura": "Temperatura Efectiva (K)"},
            title="Sesgo Instrumental vs Termodinámica Estelar"
        )
        fig_box.update_layout(showlegend=False)
        st.plotly_chart(fig_box, use_container_width=True)
        st.info("**Insight Analítico:** El 'Transit Method' (Tránsito) tiene una mediana de temperatura más baja debido a un sesgo geométrico: es exponencialmente más fácil detectar caídas fotométricas (eclipses) alrededor de estrellas pequeñas y frías (Enanas Rojas/Clase M).")
        
    with col2:
        df_hr = df_filtrado.dropna(subset=['temperatura', 'e_radio'])
        fig_hr = px.scatter(
            df_hr, x="temperatura", y="e_radio", color="e_masa",
            hover_name="estrella", log_y=True,
            labels={"temperatura": "Temperatura Efectiva (K)", "e_radio": "Radio Solar ($R_\odot$)", "e_masa": "Masa Solar ($M_\odot$)"},
            color_continuous_scale="Inferno",
            title="Aproximación Poblacional al Diagrama H-R"
        )
        fig_hr.update_xaxes(autorange="reversed")
        st.plotly_chart(fig_hr, use_container_width=True)
        st.info("**Insight Analítico:** Observamos el contorno inconfundible de la Secuencia Principal. La casi total ausencia de datos en la región de gigantes rojas (alta luminosidad/radio, baja temperatura) se debe a que la expansión de la envoltura estelar en fases tardías envuelve o perturba gravitacionalmente el sistema planetario interior.")

elif modulo == "Instrumentación y Métodos":
    st.title("Eficacia Fotométrica y Espectroscópica")
    
    st.subheader("Fundamento Teórico: Señal/Ruido y Centelleo Atmosférico")
    st.markdown("""
    La recolección de datos astrofísicos se enfrenta a un desafío fundamental: el *seeing* y la absorción atmosférica. 
    Para el método de tránsito, necesitamos medir fluctuaciones del flujo fotométrico del orden del 0.01% 
    (equivalentemente a observar un mosquito pasar por un faro automotriz a kilómetros de distancia). 
    Las turbulencias atmosféricas añaden un ruido estocástico masivo a los tensores de datos terrestres, 
    haciendo imperativa la migración hacia sensores CCD ubicados en satélites de órbita heliocéntrica o LEO, 
    maximizando así el SNR (Relación Señal/Ruido).
    """)
    
    df_inst = df_filtrado.groupby(['instalacion', 'telescopio']).size().reset_index(name='total')
    df_inst = df_inst.sort_values('total', ascending=False).head(15)
    
    fig_tree = px.treemap(
        df_inst, path=['instalacion', 'telescopio'], values='total',
        title="Impacto por Infraestructura (Top 15)",
        color='total', color_continuous_scale='Blues'
    )
    fig_tree.update_traces(root_color="lightgrey")
    fig_tree.update_layout(margin=dict(t=50, l=25, r=25, b=25))
    st.plotly_chart(fig_tree, use_container_width=True)
    
    st.info("**Insight Analítico:** La topología del Treemap demuestra una ley de Pareto extrema. Instalaciones espaciales únicas (como el telescopio Kepler y sus derivados de la matriz CCD) acumulan la abrumadora mayoría de detecciones positivas debido a su capacidad ininterrumpida para procesar series temporales largas y libres de ruido atmosférico.")