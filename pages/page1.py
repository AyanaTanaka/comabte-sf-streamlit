import dask.dataframe as dd
import geopandas as gpd
import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import matplotlib.pyplot as plt
import contextily as ctx
from matplotlib.colors import ListedColormap
from matplotlib_scalebar.scalebar import ScaleBar
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import duckdb

st.set_page_config(page_title="Mapa da fazenda", layout="wide")


#Barra superior com logos
col1, col2, col3, col4 = st.columns([3, 2, 1, 3])
with col2:
    st.image("logos/logotipo_combate.png")
with col3:
    st.image("logos/logotipo_Maxsatt.png")


st.title("Mapa da fazenda")

# Query para carregar os dados de forma mais rápida
conn = duckdb.connect('my_database.db')
conn.execute("CREATE TABLE IF NOT EXISTS pred_attack AS SELECT * FROM 'prediction/pred_attack_2024.parquet'")
query = """
SELECT * FROM pred_attack
WHERE UPPER(FARM) = ?
"""

query_farm = """
SELECT DISTINCT UPPER(FARM) AS FARM 
FROM pred_attack
"""
unique_farm = conn.execute(query_farm).fetchdf()
unique_farms_list = unique_farm['FARM'].tolist()

if 'selectedvariable1' not in st.session_state:
    st.session_state.selectedvariable1 = 'EMBAY'

st.sidebar.title("Filtros")
selectedvariable1 = st.sidebar.selectbox(
    'Selecione a Fazenda',
    unique_farms_list
)

if st.sidebar.button('Confirmar Fazenda'):
    st.session_state.selectedvariable1 = selectedvariable1
    st.success(f"Fazenda selecionada: {st.session_state.selectedvariable1}")

if st.session_state.selectedvariable1:
    pred_attack = conn.execute(query, [st.session_state.selectedvariable1]).fetchdf()
    pred_attack['COMPANY'] = pred_attack['COMPANY'].str.upper()
    pred_attack['FARM'] = pred_attack['FARM'].str.upper()
    pred_attack['STAND'] = pred_attack['STAND'].str.upper()

    stands_all = gpd.read_file("prediction/Talhoes_Manulife_2.shp")
    stands_all = stands_all.to_crs(epsg=4326)
    stands_all['COMPANY'] = stands_all['Companhia'].str.upper()
    stands_all['FARM'] = stands_all['Fazenda'].str.replace(" ", "_")
    stands_all['STAND'] = stands_all.apply(lambda row: f"{row['Fazenda']}_{row['CD_TALHAO']}", axis=1)

    if 'selectedvariable2' not in st.session_state:
        st.session_state.selectedvariable2 = 'EMBAY_001'

    if 'selectedvariable3' not in st.session_state:
        st.session_state.selectedvariable3 = pd.to_datetime('2024-01-05')

    unique_company = pred_attack['COMPANY'].unique()
    unique_farms = pred_attack['FARM'].unique()
    unique_stands_filtered = pred_attack['STAND'].unique()
    unique_stands = {
        farm: stands_all[stands_all['FARM'] == farm][stands_all['STAND'].isin(unique_stands_filtered)]['STAND'].unique().tolist() 
        for farm in unique_farms
    }
    
    selectedvariable3 = st.sidebar.date_input(
        'Selecione a Data:',
        min_value=pd.to_datetime('2018-01-01'),
        max_value=pd.to_datetime('2024-12-31'),
        value=pd.to_datetime('2024-01-05')  # Defina uma data padrão, se necessário
    )

    # Definir variáveis e tabelas que serão usadas pelos gráficos
    # Definir QT usando query para não sobrecarregar a memória
    quantile_query = """
    SELECT QUANTILE(canopycov, 0.10) AS QT
    FROM pred_attack
    """

    QT = conn.execute(quantile_query).fetchdf().iloc[0]['QT']

    # Mapa da fazenda

    # 2. Filtragem de dados
    pred_attack_BQ = pred_attack[pred_attack['FARM'] == selectedvariable1]
    pred_attack_BQ_FARM = pred_attack_BQ.groupby(['FARM', 'STAND', 'DATE']).agg(
        {'X': 'mean', 'Y': 'mean', 'canopycov': 'mean', 'cover_min': 'mean'}
    ).reset_index()

    stands_sel_farm = stands_all[stands_all['FARM'] == selectedvariable1]

    # 3. Filtrando por cobertura do dossel
    list_stands_healthy = pred_attack_BQ_FARM[pred_attack_BQ_FARM['canopycov'] > QT]
    list_stands_attack = pred_attack_BQ_FARM[pred_attack_BQ_FARM['canopycov'] < QT]

    stands_sel_farm_health = stands_sel_farm[stands_sel_farm['STAND'].isin(list_stands_healthy['STAND'])]
    stands_sel_farm_attack = stands_sel_farm[stands_sel_farm['STAND'].isin(list_stands_attack['STAND'])]

    mean_lat = pred_attack_BQ['Y'].mean()
    mean_lon = pred_attack_BQ['X'].mean()

    # 4. Mapa Interativo com Folium
# 4. Mapa Interativo com Folium
if 'm' not in locals():  # Garante que 'm' será definido mesmo em cenários sem dados
    m = folium.Map(location=[0, 0], zoom_start=2)

if st.session_state.selectedvariable1:
    if np.isnan(mean_lat) or np.isnan(mean_lon):
        # Caso contenham NaNs, cria um mapa genérico
        m = folium.Map(location=[0, 0], zoom_start=10)
        folium.Marker(
            location=[0, 0],
            popup="Nenhum dado válido para exibir.",
        ).add_to(m)
    else:
        # Caso válido, cria o mapa normalmente
        m = folium.Map(location=[mean_lat, mean_lon], zoom_start=12)

        # Adicionando camada de satélite
        folium.TileLayer('Esri.WorldImagery').add_to(m)

        # Adicionando polígonos com contornos
        for _, row in stands_sel_farm_health.iterrows():
            folium.GeoJson(
                row['geometry'], 
                style_function=lambda x: {'color': 'yellow', 'fillOpacity': 0}
            ).add_to(m)

        for _, row in stands_sel_farm_attack.iterrows():
            folium.GeoJson(
                row['geometry'], 
                style_function=lambda x: {'color': 'red', 'fillOpacity': 0}
            ).add_to(m)

# Exibir o mapa no Streamlit
st_folium(m, width=700, height=500)
