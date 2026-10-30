import streamlit as st
import pandas as pd

st.title("Demo Streamlit App")

df = pd.read_csv("/home/debian12/DS2026/4.GUI/Streamlit/state_data.csv")

# Exercise: Change this code to:
# 1. Ask the user to select a state
# 2. Have it populate with all the list of unique states
option = st.selectbox("Select a state:", df["State"].unique())

st.write("You selected:", option)

# Filter df to just the values the user selected
df["State"] = option

st.dataframe(df)