import streamlit as st
import folium
from streamlit_folium import st_folium
import simulator
import pandas as pd
import numpy as np

st.set_page_config(page_title="Simulador de Levantamentos Topográficos", layout="wide")

st.title("🏗️ Simulador de Levantamentos Topográficos")

# --- Sidebar ---
st.sidebar.header("Configurações do Levantamento")

survey_category = st.sidebar.selectbox(
    "Tipo de Levantamento",
    ["Poligonação", "Nivelamento"]
)

if survey_category == "Poligonação":
    survey_type = st.sidebar.radio("Subtipo", ["Fechada", "Enquadrada"])
    n_points = st.sidebar.slider("Número de Pontos", 3, 20, 5)
    angle_precision = st.sidebar.number_input("Precisão Angular (graus)", 0.0, 0.1, 0.005, format="%.4f")
    dist_precision = st.sidebar.number_input("Precisão Linear (proporcional)", 0.0, 0.05, 0.001, format="%.4f")
else:
    survey_type = st.sidebar.radio("Subtipo", ["Geométrico", "Trigonométrico"])
    n_points = st.sidebar.slider("Número de Pontos", 2, 50, 10)
    error_km = st.sidebar.number_input("Erro por km (m)", 0.0, 0.05, 0.005, format="%.3f")

# Starting point
st.sidebar.subheader("Localização Inicial")
start_lat = st.sidebar.number_input("Latitude", value=-23.5505, format="%.6f")
start_lon = st.sidebar.number_input("Longitude", value=-46.6333, format="%.6f")

# --- Data Generation ---
if survey_category == "Poligonação":
    sim_type = "Closed" if survey_type == "Fechada" else "Linked"
    lats, lons = simulator.generate_traverse_coordinates(n_points, survey_type=sim_type, start_lat=start_lat, start_lon=start_lon)
    observations = simulator.simulate_traverse_observations(lats, lons, angle_sigma=angle_precision, dist_sigma=dist_precision)

    # Prepare data for map
    points_df = pd.DataFrame({"lat": lats, "lon": lons})
    points_df["label"] = [f"P{i+1}" for i in range(len(lats))]
else:
    # For leveling, we'll generate a linear traverse to show on map too
    lats, lons = simulator.generate_traverse_coordinates(n_points, survey_type="Linked", start_lat=start_lat, start_lon=start_lon)
    sim_type = "Geometric" if survey_type == "Geométrico" else "Trigonometric"
    observations, elevations = simulator.simulate_leveling(n_points, type=sim_type, error_per_km=error_km)

    points_df = pd.DataFrame({"lat": lats, "lon": lons, "elevation": elevations})
    points_df["label"] = [f"P{i+1}" for i in range(len(lats))]

# --- Layout ---
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("Visualização Espacial")
    m = folium.Map(location=[start_lat, start_lon], zoom_start=16)

    # Add Path
    path = list(zip(lats, lons))
    folium.PolyLine(path, color="blue", weight=2.5, opacity=1).add_to(m)

    # Add Markers
    for idx, row in points_df.iterrows():
        popup_text = f"Ponto: {row['label']}"
        if 'elevation' in row:
            popup_text += f"<br>Elev: {row['elevation']:.3f}m"

        folium.CircleMarker(
            location=[row['lat'], row['lon']],
            radius=5,
            color="red",
            fill=True,
            fill_color="red",
            popup=popup_text
        ).add_to(m)

        folium.Marker(
            location=[row['lat'], row['lon']],
            icon=folium.DivIcon(
                html=f'<div style="font-size: 10pt; color: black; font-weight: bold;">{row["label"]}</div>',
                icon_anchor=(0, 0)
            )
        ).add_to(m)

    st_folium(m, width=700, height=500)

with col2:
    st.subheader("Caderneta de Campo (Simulada)")
    st.dataframe(observations, use_container_width=True)

    if survey_category == "Nivelamento":
        st.subheader("Cotas Calculadas")
        st.dataframe(points_df[["label", "elevation"]].style.format({"elevation": "{:.3f}"}), use_container_width=True)
    else:
        st.subheader("Coordenadas Geográficas")
        st.dataframe(points_df[["label", "lat", "lon"]].style.format({"lat": "{:.6f}", "lon": "{:.6f}"}), use_container_width=True)

st.info("Nota: Os dados são gerados aleatoriamente com base nos parâmetros de precisão selecionados.")
