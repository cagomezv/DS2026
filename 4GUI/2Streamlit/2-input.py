import streamlit as st
import pandas as pd

st.title("Demo Streamlit App")

df = pd.read_csv("state_data.csv")

# Exercise: Change this code to:
# 1. Ask the user to select a state
# 2. Have it populate with all the list of unique states
option = st.selectbox("Select your favorite fruit:", ["Apple", "Banana", "Cherry"])

st.write("You selected:", option)

# Filter df to just the values the user selected
# df = ...

st.dataframe(df)
