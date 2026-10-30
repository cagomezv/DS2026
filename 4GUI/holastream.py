import streamlit as st
import pandas as pd

df = pd.DataFrame({
    "Column 1": [1, 2, 3, 4],
    "Column 2": [1, 2, 3, 4]
})


st.title('Demo streamlit app')
st.dataframe(df)





