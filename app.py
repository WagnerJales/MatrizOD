# Carregar bibliotecas
import streamlit as st
import pandas as pd
import pydeck as pdk
import json
from shapely.geometry import shape
import plotly.express as px

# Configurar layout da página
st.set_page_config(layout="wide")

# Carregar dados geojson e csv
@st.cache_data
def load_data():
    with open("zonas_OD.geojson", "r", encoding="utf-8") as f:
        geojson_data = json.load(f)
    df_coletivo = pd.read_csv("matriz_od_coletivo.csv")
    df_individual = pd.read_csv("matriz_od_individual.csv")
    return geojson_data, df_coletivo, df_individual

# Funções para processar os modos
@st.cache_data
def process_modo(df_od, zone_centroids):
    total_geracao = df_od.groupby("origem")["volume"].sum().to_dict()
    total_atracao = df_od.groupby("destino")["volume"].sum().to_dict()
    for feature in geojson_data["features"]:
        zone_id = int(feature["properties"]["id"])
        geom = shape(feature["geometry"])
        centroid = geom.centroid
        zone_centroids[zone_id] = (centroid.y, centroid.x)
        geracao = total_geracao.get(zone_id, 0)
        atracao = total_atracao.get(zone_id, 0)
        feature["properties"]["geracao"] = geracao
        feature["properties"]["atracao"] = atracao
        feature["properties"]["total"] = geracao + atracao
    return zone_centroids, geojson_data

@st.cache_data
def compute_coordinates(df, zone_centroids):
    df = df.copy()
    df["orig_lat"], df["orig_lon"] = zip(*df["origem"].map(lambda x: zone_centroids.get(x, (None, None))))
    df["dest_lat"], df["dest_lon"] = zip(*df["destino"].map(lambda x: zone_centroids.get(x, (None, None))))
    return df

# Inicializar dados
geojson_data, df_coletivo, df_individual = load_data()
modo = st.sidebar.radio("Modo de transporte", ["Transporte Coletivo", "Transporte Individual", "Total dos Dois"])

# Seleção de dados
if modo == "Transporte Coletivo":
    df_od = df_coletivo.copy()
elif modo == "Transporte Individual":
    df_od = df_individual.copy()
else:
    df_coletivo["modo"] = "Coletivo"
    df_individual["modo"] = "Individual"
    df_od = pd.concat([df_coletivo, df_individual])
    df_od = df_od.groupby(["origem", "destino", "modo"]).sum().reset_index()

# Processar centroides e propriedades
zone_centroids = {}
zone_centroids, geojson_data = process_modo(df_od, zone_centroids)
df_od = compute_coordinates(df_od, zone_centroids)

# Filtros interativos
with st.sidebar:
    st.markdown("## Filtros")
    todas_origens = sorted(df_od["origem"].unique().tolist())
    todas_destinos = sorted(df_od["destino"].unique().tolist())
    origem_sel = st.multiselect("Origem", ["Todos"] + todas_origens, default=["Todos"])
    destino_sel = st.multiselect("Destino", ["Todos"] + todas_destinos, default=["Todos"])
    vol_range = st.slider("Volume", 0, int(df_od["volume"].max()), (0, int(df_od["volume"].max())))
    st.markdown("### Tipo de Visualização")
    tipo_dado = st.radio("Exibir no 2º mapa:", ["total", "geracao", "atracao"], index=0)

if "Todos" in origem_sel:
    origem_sel = todas_origens
if "Todos" in destino_sel:
    destino_sel = todas_destinos

max_valor = max([f["properties"][tipo_dado] for f in geojson_data["features"]]) or 1

# Aplicar filtros
df_filtrado = df_od.copy()
df_filtrado = df_filtrado[df_filtrado["origem"].isin(origem_sel)]
df_filtrado = df_filtrado[df_filtrado["destino"].isin(destino_sel)]
df_filtrado = df_filtrado[(df_filtrado["volume"] >= vol_range[0]) & (df_filtrado["volume"] <= vol_range[1])]
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
    get_color="[255, 0, 0, 128]",  # 50% de transparência
    pickable=True
)

choropleth_layer = pdk.Layer(
    "GeoJsonLayer",
    geojson_data,
    get_fill_color=f"[255, 255 * (1 - properties.{tipo_dado} / {max_valor}), 255 * (1 - properties.{tipo_dado} / {max_valor}), 180]",
    get_line_color=[90, 90, 90, 120],
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
        "size": 14,
        "color": [0, 0, 0],
        "alignment_baseline": "center"
    } for zone_id, centroid in zone_centroids.items()],
    get_position="position",
    get_text="text",
    get_size=14,
    get_color="color",
    billboard=True
)

view_state = pdk.ViewState(
    latitude=sum(c[0] for c in zone_centroids.values()) / len(zone_centroids),
    longitude=sum(c[1] for c in zone_centroids.values()) / len(zone_centroids),
    zoom=11
)

# Título principal
st.markdown("""
    <div style='text-align:center'>
        <h1 style='margin-bottom: 10px;'>Matriz Origem/Destino da Ilha de São Luís</h1>
    </div>
""", unsafe_allow_html=True)

# Dispor os dois mapas lado a lado
col1, col2 = st.columns([1, 1], gap="small")

with col1:
    st.markdown("<h4 style='text-align:center;'>Matriz OD</h4>", unsafe_allow_html=True)
    st.pydeck_chart(pdk.Deck(layers=[geo_layer, line_layer], initial_view_state=view_state, map_style="mapbox://styles/mapbox/dark-v10"))

with col2:
    st.markdown("<h4 style='text-align:center;'>Geração e Atração de Viagens</h4>", unsafe_allow_html=True)
    st.pydeck_chart(pdk.Deck(layers=[choropleth_layer, text_layer], initial_view_state=view_state, map_style="mapbox://styles/mapbox/light-v9"))
    st.markdown(f"""
        <div style='text-align:center; margin-top: -10px;'>
            <div style='background: linear-gradient(to right, #f5e0e0, #ff0000); height: 20px; width: 80%; margin: 0 auto; border: 1px solid #aaa;'></div>
            <div style='display: flex; justify-content: space-between; font-size: 12px; color: #333; width: 80%; margin: 2px auto;'>
                <span>0</span>
                <span>{int(max_valor)}</span>
            </div>
        </div>
    """, unsafe_allow_html=True)

# Total de viagens - destaque com fonte maior
total_viagens = round(df_filtrado['volume'].sum())
st.markdown(f"""
<div style='font-size:22px; font-weight:bold; text-align:center; padding: 10px;'>
    Total de viagens filtradas: {total_viagens:,d}
</div>
""".replace(",", "X").replace(".", ",").replace("X", "."), unsafe_allow_html=True)

# Gráfico por tipo
if modo != "Total dos Dois":
    modo_label = "Coletivo" if modo == "Transporte Coletivo" else "Individual"
    df_chart = df_filtrado.copy()
    df_chart["modo"] = modo_label
else:
    df_chart = df_od[df_od["origem"].isin(origem_sel) & df_od["destino"].isin(destino_sel)]
    df_chart = df_chart[(df_chart["volume"] >= vol_range[0]) & (df_chart["volume"] <= vol_range[1])]

st.subheader("Gráfico de Viagens por Par OD e Tipo de Transporte")
df_chart["par"] = df_chart["origem"].astype(str) + " - " + df_chart["destino"].astype(str)
fig = px.bar(df_chart, x="par", y="volume", color="modo", barmode="group",
             labels={"par": "Par OD", "volume": "Volume de Viagens", "modo": "Modo"})
st.plotly_chart(fig, use_container_width=True)

# Fonte dos dados
st.markdown("""
<div style='text-align:center; font-size: 1.3em; padding-top: 1em;'>
    <strong>Fonte:</strong> Os dados foram retirados da Tabela 2-8, do documento P8-Avaliação da Infraestrutura urbana, viária e de mobilidade,<br>
    disponível em <a href='https://www.saoluis.ma.gov.br/arquivos/etapa_8_plano_de_mobilidade_08125036.pdf' target='_blank'>saoluis.ma.gov.br</a>.<br>
    Desenvolvido por <a href='https://www.linkedin.com/in/wagner-jales-663b4831/' target='_blank'>Wagner Jales</a>
</div>
""", unsafe_allow_html=True)

