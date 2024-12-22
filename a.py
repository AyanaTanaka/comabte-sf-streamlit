import streamlit as st
import duckdb
import pandas as pd
import geopandas as gpd

st.set_page_config(page_title="MAXSATT - Plataforma de Monitoramento", layout="wide")

col1, col2, col3, col4 = st.columns([2, 2, 1, 2])
with col2:
    st.image("logos/logotipo_combate.png")
with col3:
    st.image("logos/logotipo_Maxsatt.png")

st.markdown("<h1 style='text-align:center;'font-size:40px;'>Plataforma de Monitoramento de Formigas por Sensoriamento Remoto</h1>", unsafe_allow_html=True)

st.write("**Baixar planilhas:**")


col1, col2 = st.columns([1,1])
with col1:
    st.download_button(
        label="Porcentagem desfolha por talhão",
        data=csv_stand,
        file_name='desfolha_talhao.csv',
        mime='text/csv'
    )
with col2:
    st.download_button(
        label="Porcentagem desfolha por fazenda",
        data=csv_farm,
        file_name='desfolha_fazenda.csv',
        mime='text/csv'
    )
