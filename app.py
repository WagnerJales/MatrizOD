import streamlit as st
import geopandas as gpd
import pandas as pd
import pydeck as pdk
import os

# Carregamento de dados com engine=fiona para evitar erros com pyogrio
gdf = gpd.read_file("zonas_OD/zonas_OD.shp", engine="fiona")
od_df = pd.read_csv("matriz_od.csv")

# Centroides das zonas para ligação OD
gdf_centroids = gdf.copy()
gdf_centroids["geometry"] = gdf_centroids.centroid
coords = gdf_centroids.set_index("id").geometry

def get_coords(zone_id):
    geom = coords.get(zone_id)
    if geom:
        return geom.y, geom.x
    return None, None

# Adicionar colunas de coordenadas
od_df["orig_lat"], od_df["orig_lon"] = zip(*od_df["origem"].map(get_coords))
od_df["dest_lat"], od_df["dest_lon"] = zip(*od_df["destino"].map(get_coords))

# Filtros
st.sidebar.title("Filtros")
origem_sel = st.sidebar.selectbox("Origem", ["Todas"] + sorted(od_df["origem"].unique().tolist()))
destino_sel = st.sidebar.selectbox("Destino", ["Todas"] + sorted(od_df["destino"].unique().tolist()))
vol_range = st.sidebar.slider("Volume", 0, int(od_df["volume"].max()), (0, int(od_df["volume"].max())))

df_filtrado = od_df.copy()
if origem_sel != "Todas":
    df_filtrado = df_filtrado[df_filtrado["origem"] == origem_sel]
if destino_sel != "Todas":
    df_filtrado = df_filtrado[df_filtrado["destino"] == destino_sel]
df_filtrado = df_filtrado[(df_filtrado["volume"] >= vol_range[0]) & (df_filtrado["volume"] <= vol_range[1])]

# Criar linhas OD
od_lines = [
    {
        "from_lat": row.orig_lat, "from_lon": row.orig_lon,
        "to_lat": row.dest_lat, "to_lon": row.dest_lon,
        "volume": row.volume
    }
    for _, row in df_filtrado.iterrows()
    if pd.notnull(row.orig_lat) and pd.notnull(row.dest_lat)
]

layer = pdk.Layer(
    "LineLayer",
    od_lines,
    get_source_position=["from_lon", "from_lat"],
    get_target_position=["to_lon", "to_lat"],
    get_width="volume",
    get_color=[255, 0, 0],
    pickable=True,
    auto_highlight=True
)

view_state = pdk.ViewState(
    latitude=gdf_centroids.geometry.y.mean(),
    longitude=gdf_centroids.geometry.x.mean(),
    zoom=11
)

st.title("Visualizador de Matriz OD")
st.pydeck_chart(pdk.Deck(layers=[layer], initial_view_state=view_state))

st.subheader("Tabela de pares OD filtrados")
st.dataframe(df_filtrado.sort_values("volume", ascending=False))