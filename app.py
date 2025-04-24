import streamlit as st
import pandas as pd
import pydeck as pdk
import json
from shapely.geometry import shape

# Configuração da página deve ser a primeira chamada Streamlit
st.set_page_config(layout="wide")

@st.cache_data
def load_data():
    with open("zonas_OD.geojson", "r", encoding="utf-8") as f:
        geojson_data = json.load(f)
    df_od = pd.read_csv("matriz_od.csv")
    return geojson_data, df_od

geojson_data, df_od = load_data()

zone_centroids = {}
zone_trip_counts = {}
for feature in geojson_data["features"]:
    zone_id = int(feature["properties"]["id"])
    geom = shape(feature["geometry"])
    centroid = geom.centroid
    zone_centroids[zone_id] = (centroid.y, centroid.x)
    zone_trip_counts[zone_id] = 0

total_by_zone = df_od.groupby("origem")["volume"].sum().to_dict()
max_volume = max(total_by_zone.values()) if total_by_zone else 1
for zone_id in zone_trip_counts:
    zone_trip_counts[zone_id] = total_by_zone.get(zone_id, 0)

for feature in geojson_data["features"]:
    zone_id = int(feature["properties"]["id"])
    feature["properties"]["volume"] = zone_trip_counts.get(zone_id, 0)

@st.cache_data
def compute_coordinates(df):
    df = df.copy()
    df["orig_lat"], df["orig_lon"] = zip(*df["origem"].map(lambda x: zone_centroids.get(x, (None, None))))
    df["dest_lat"], df["dest_lon"] = zip(*df["destino"].map(lambda x: zone_centroids.get(x, (None, None))))
    return df

df_od = compute_coordinates(df_od)

with st.sidebar:
    st.markdown("## Filtros")
    origem_sel = st.selectbox("Origem", ["Todas"] + sorted(df_od["origem"].unique().tolist()))
    destino_sel = st.selectbox("Destino", ["Todas"] + sorted(df_od["destino"].unique().tolist()))
    vol_range = st.slider("Volume", 0, int(df_od["volume"].max()), (0, int(df_od["volume"].max())))

df_filtrado = df_od.copy()
if origem_sel != "Todas":
    df_filtrado = df_filtrado[df_filtrado["origem"] == origem_sel]
if destino_sel != "Todas":
    df_filtrado = df_filtrado[df_filtrado["destino"] == destino_sel]
df_filtrado = df_filtrado[(df_filtrado["volume"] >= vol_range[0]) & (df_filtrado["volume"] <= vol_range[1])]

# Limita visualmente para performance
df_limitado = df_filtrado.head(500)

od_lines = [
    {
        "from_lat": row.orig_lat, "from_lon": row.orig_lon,
        "to_lat": row.dest_lat, "to_lon": row.dest_lon,
        "volume": row.volume
    }
    for _, row in df_limitado.iterrows()
    if pd.notnull(row.orig_lat) and pd.notnull(row.dest_lat)
]

geo_layer = pdk.Layer(
    "GeoJsonLayer",
    geojson_data,
    stroked=True,
    filled=True,
    get_fill_color=[200, 200, 200, 50],
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

choropleth_layer = pdk.Layer(
    "GeoJsonLayer",
    geojson_data,
    get_fill_color=f"[255 * properties.volume / {max_volume}, 100, 100, 200]",
    get_line_color=[80, 80, 80, 100],
    pickable=True,
    filled=True,
    stroked=True,
    auto_highlight=True
)

text_layer = pdk.Layer(
    "TextLayer",
    [{
        "position": [centroid[1], centroid[0]],
        "text": str(zone_id),
        "size": 16,
        "color": [0, 0, 0],
        "alignment_baseline": "center"
    } for zone_id, centroid in zone_centroids.items()],
    get_position="position",
    get_text="text",
    get_size=16,
    get_color="color",
    billboard=True
)

view_state = pdk.ViewState(
    latitude=sum(c[0] for c in zone_centroids.values()) / len(zone_centroids),
    longitude=sum(c[1] for c in zone_centroids.values()) / len(zone_centroids),
    zoom=11
)

st.markdown("""
    <div style='text-align:center'>
        <h1 style='margin-bottom: 10px;'>Matriz OD</h1>
    </div>
""", unsafe_allow_html=True)

col1, col2 = st.columns([1, 1])

with col1:
    st.pydeck_chart(pdk.Deck(layers=[geo_layer, line_layer], initial_view_state=view_state, map_style="mapbox://styles/mapbox/dark-v10"))

with col2:
    st.markdown("<h3 style='text-align:center;'>Geração/Atração de viagens</h3>", unsafe_allow_html=True)
    st.pydeck_chart(pdk.Deck(layers=[choropleth_layer, text_layer], initial_view_state=view_state, map_style="mapbox://styles/mapbox/light-v9"))
    st.markdown("""
        <div style='text-align:center; font-size: 14px; margin-top: -10px;'>
            <b>Legenda:</b> tons de vermelho indicam maior geração de viagens. Tons claros indicam baixa geração.
        </div>
    """, unsafe_allow_html=True)

st.subheader("Tabela de pares OD filtrados")
st.dataframe(df_filtrado.sort_values("volume", ascending=False))
