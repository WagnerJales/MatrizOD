import streamlit as st
import pandas as pd
import pydeck as pdk
import json

# Carrega GeoJSON e CSV
with open("zonas_OD.geojson", "r", encoding="utf-8") as f:
    geojson_data = json.load(f)

df_od = pd.read_csv("matriz_od.csv")

# Obter centroides a partir do GeoJSON
from shapely.geometry import shape
zone_centroids = {}
for feature in geojson_data["features"]:
    zone_id = int(feature["properties"]["id"])
    geom = shape(feature["geometry"])
    centroid = geom.centroid
    zone_centroids[zone_id] = (centroid.y, centroid.x)

# Adiciona coordenadas no DataFrame
df_od["orig_lat"], df_od["orig_lon"] = zip(*df_od["origem"].map(lambda x: zone_centroids.get(x, (None, None))))
df_od["dest_lat"], df_od["dest_lon"] = zip(*df_od["destino"].map(lambda x: zone_centroids.get(x, (None, None))))

# Filtros
st.sidebar.title("Filtros")
origem_sel = st.sidebar.selectbox("Origem", ["Todas"] + sorted(df_od["origem"].unique().tolist()))
destino_sel = st.sidebar.selectbox("Destino", ["Todas"] + sorted(df_od["destino"].unique().tolist()))
vol_range = st.sidebar.slider("Volume", 0, int(df_od["volume"].max()), (0, int(df_od["volume"].max())))

df_filtrado = df_od.copy()
if origem_sel != "Todas":
    df_filtrado = df_filtrado[df_filtrado["origem"] == origem_sel]
if destino_sel != "Todas":
    df_filtrado = df_filtrado[df_filtrado["destino"] == destino_sel]
df_filtrado = df_filtrado[(df_filtrado["volume"] >= vol_range[0]) & (df_filtrado["volume"] <= vol_range[1])]

# Criar linhas
od_lines = [
    {
        "from_lat": row.orig_lat, "from_lon": row.orig_lon,
        "to_lat": row.dest_lat, "to_lon": row.dest_lon,
        "volume": row.volume
    }
    for _, row in df_filtrado.iterrows()
    if pd.notnull(row.orig_lat) and pd.notnull(row.dest_lat)
]

# Layers
geo_layer = pdk.Layer(
    "GeoJsonLayer",
    geojson_data,
    stroked=True,
    filled=True,
    get_fill_color=[200, 200, 200, 100],
    get_line_color=[0, 0, 0, 255],
    line_width_min_pixels=1,
    pickable=True
)

line_layer = pdk.Layer(
    "LineLayer",
    od_lines,
    get_source_position=["from_lon", "from_lat"],
    get_target_position=["to_lon", "to_lat"],
    get_width="volume",
    get_color=[255, 0, 0],
    pickable=True
)

view_state = pdk.ViewState(
    latitude=sum(c[0] for c in zone_centroids.values()) / len(zone_centroids),
    longitude=sum(c[1] for c in zone_centroids.values()) / len(zone_centroids),
    zoom=11
)

st.title("Visualizador de Matriz OD")
st.pydeck_chart(pdk.Deck(layers=[geo_layer, line_layer], initial_view_state=view_state))

st.subheader("Tabela de pares OD filtrados")
st.dataframe(df_filtrado.sort_values("volume", ascending=False))
