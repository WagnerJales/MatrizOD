import streamlit as st
import pandas as pd
import folium
from folium import PolyLine, Marker
from streamlit_folium import st_folium
import plotly.express as px
import io

st.set_page_config(layout="wide")

st.markdown("""
    <style>
        .block-container {
            padding-top: 1rem;
        }
    </style>
""", unsafe_allow_html=True)

st.title("Mapa Origem-Destino - RMGSL PDDI (2025)")

@st.cache_data
def carregar_dados():
    return pd.read_csv("dados_filtrados_com_modal.csv")  # Arquivo atualizado com 'Modal Agrupado'

try:
    df = carregar_dados()
except Exception as e:
    st.error(f"Erro ao carregar o CSV: {e}")
    st.stop()

municipios_coords = {
    "São Luís": [-2.53, -44.3],
    "São José de Ribamar": [-2.56, -44.05],
    "Paço do Lumiar": [-2.52, -44.1],
    "Raposa": [-2.43, -44.1],
    "Cachoeira Grande": [-2.93, -44.05],
    "Presidente Juscelino": [-2.925, -44.06],
    "Rosário": [-2.9344, -44.2511],
    "Alcântara": [-2.41, -44.41],
    "Icatu": [-2.77, -44.05],
    "Morros": [-2.86, -44.04],
    "Bacabeira": [-2.96, -44.31],
    "Axixá": [-2.83, -44.05],
    "Santa Rita": [-3.139, -44.325],
    "FORA DA RMGSL": [-2.88, -44.53]
}

st.sidebar.header("Filtros")
origens = st.sidebar.multiselect("Origem:", sorted(df["ORIGEM 2"].dropna().unique()), default=[])
destinos = st.sidebar.multiselect("Destino:", sorted(df["DESTINO 2"].dropna().unique()), default=[])
motivo = st.sidebar.multiselect("Motivo da Viagem:", sorted(df["motivo_ajustado"].dropna().unique()), default=[])
frequencia = st.sidebar.multiselect("Frequência:", sorted(df["Com que frequência você faz essa viagem?"].dropna().unique()), default=[])
periodo = st.sidebar.multiselect("Período do dia:", sorted(df["A viagem foi realizada em qual período do dia?"].dropna().unique()), default=[])
modal = st.sidebar.multiselect("Modal Agrupado:", sorted(df["Modal Agrupado"].dropna().unique()), default=[])

# Aplicar filtros
df_filtrado = df.copy()
if origens:
    df_filtrado = df_filtrado[df_filtrado["ORIGEM 2"].isin(origens)]
if destinos:
    df_filtrado = df_filtrado[df_filtrado["DESTINO 2"].isin(destinos)]
if motivo:
    df_filtrado = df_filtrado[df_filtrado["motivo_ajustado"].isin(motivo)]
if frequencia:
    df_filtrado = df_filtrado[df_filtrado["Com que frequência você faz essa viagem?"].isin(frequencia)]
if periodo:
    df_filtrado = df_filtrado[df_filtrado["A viagem foi realizada em qual período do dia?"].isin(periodo)]
if modal:
    df_filtrado = df_filtrado[df_filtrado["Modal Agrupado"].isin(modal)]

# Agrupar OD
df_agrupado = df_filtrado.groupby(["ORIGEM 2", "DESTINO 2"]).size().reset_index(name="total")

# Criar mapa
mapa = folium.Map(location=[-2.53, -43.9], zoom_start=10, tiles="CartoDB positron")
for _, row in df_agrupado.sort_values("total", ascending=False).head(100).iterrows():
    origem = row["ORIGEM 2"]
    destino = row["DESTINO 2"]
    if origem in municipios_coords and destino in municipios_coords:
        coords = [municipios_coords[origem], municipios_coords[destino]]
        folium.PolyLine(
            coords,
            color="red",
            weight=1 + (row["total"] / 30) * 5,
            opacity=0.8,
            tooltip=f"{origem} → {destino}: {row['total']} deslocamentos"
        ).add_to(mapa)

for cidade, coord in municipios_coords.items():
    folium.Marker(location=coord, popup=cidade, tooltip=cidade).add_to(mapa)

# Mostrar mapa
st.subheader("229 Registros realizados entre os dias 10/03/25 e 05/05/25")
st_folium(mapa, width=1600, height=700)


# Heatmap principal: Matriz OD
st.subheader("Matriz OD (Gráfico Térmico)")
matriz = df_filtrado.groupby(["ORIGEM", "DESTINO"]).size().unstack(fill_value=0)
st.plotly_chart(
    px.imshow(matriz, text_auto=True, color_continuous_scale="Purples", title="Matriz OD"),
    use_container_width=True
)

# Heatmaps adicionais em pares
col1, col2 = st.columns(2)

with col1:
    st.subheader("Motivo x Frequência")
    heatmap_a = df_filtrado.groupby(["Motivo", "Frequência"]).size().unstack(fill_value=0)
    st.plotly_chart(px.imshow(heatmap_a, text_auto=True, color_continuous_scale="Blues", title="Motivo x Frequência"), use_container_width=True)

with col2:
    st.subheader("Motivo x Período do Dia")
    heatmap_b = df_filtrado.groupby(["Motivo", "Periodo do dia"]).size().unstack(fill_value=0)
    st.plotly_chart(px.imshow(heatmap_b, text_auto=True, color_continuous_scale="Greens", title="Motivo x Período do Dia"), use_container_width=True)

col3, col4 = st.columns(2)

with col3:
    st.subheader("Frequência x Período do Dia")
    heatmap_c = df_filtrado.groupby(["Frequência", "Periodo do dia"]).size().unstack(fill_value=0)
    st.plotly_chart(px.imshow(heatmap_c, text_auto=True, color_continuous_scale="Oranges", title="Frequência x Período do Dia"), use_container_width=True)

with col4:
    st.subheader("Motivo x Modal (Principal Modal)")
    heatmap_e = df_filtrado.groupby(["Motivo", "Principal Modal"]).size().unstack(fill_value=0)
    st.plotly_chart(px.imshow(heatmap_e, text_auto=True, color_continuous_scale="Teal", title="Motivo x Principal Modal"), use_container_width=True)

col5, col6 = st.columns(2)

with col5:
    st.subheader("Modal x Frequência")
    heatmap_f = df_filtrado.groupby(["Principal Modal", "Frequência"]).size().unstack(fill_value=0)
    st.plotly_chart(px.imshow(heatmap_f, text_auto=True, color_continuous_scale="Pinkyl", title="Principal Modal x Frequência"), use_container_width=True)
ww.wagnerjales.com.br)")
