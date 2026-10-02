import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path
import pandas as pd

st.title("US State Demographics")

DATA_PATH = Path(__file__).parent.parent / "state_data.csv"
df = pd.read_csv(DATA_PATH)

col1, col2, col3 = st.columns(3)
with col1:
    state = st.selectbox("State:", df["State"].unique())
with col2:
    demographic = st.selectbox(
        "Demographic:", ["Total Population", "Median Household Income"]
    )
with col3:
    year = st.selectbox("Year:", df["Year"].unique())

graph_tab, map_tab, table_tab = st.tabs(["📈 Graph", "🗺️ Map", "📊 Table"])
with graph_tab:
    mask = df["State"] == state
    df_state = df[mask]
    fig = px.line(df_state, x="Year", y=demographic, title=f"{demographic} for {state}")
    st.plotly_chart(fig)
with map_tab:
    mask = df["Year"] == year
    df_year = df[mask]

    fig = px.choropleth(
        df_year,
        locations="State Abbrev",  # Column for region
        locationmode="USA-states",
        color=demographic,  # Column for color
        scope="usa",
        title=f"{demographic} for {year}",
        color_continuous_scale="viridis",
    )
    st.plotly_chart(fig)
with table_tab:
    st.dataframe(df_state)
