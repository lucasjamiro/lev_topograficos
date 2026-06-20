import streamlit as st
import folium
from streamlit_folium import st_folium
import simulator
import pandas as pd
import numpy as np
import utm

st.set_page_config(page_title="Simulador Topográfico Interativo", layout="wide")

# --- Session State Initialization ---
if 'survey_points' not in st.session_state:
    st.session_state.survey_points = []  # List of (lat, lon)
if 'survey_data' not in st.session_state:
    st.session_state.survey_data = None

def reset_survey():
    st.session_state.survey_points = []
    st.session_state.survey_data = None

st.title("🏗️ Simulador de Levantamentos Topográficos")

# --- Sidebar ---
st.sidebar.header("Configurações do Levantamento")

survey_category = st.sidebar.selectbox(
    "1. Tipo de Levantamento",
    ["Poligonação", "Nivelamento"],
    on_change=reset_survey
)

if survey_category == "Poligonação":
    survey_type = st.sidebar.radio("1.1 Tipo de Poligonal", ["Fechada", "Enquadrada"], on_change=reset_survey)
    n_points = st.sidebar.number_input("1.1.1 Número de vértices", min_value=3, max_value=50, value=5)

    st.sidebar.subheader("1.1.2 Coordenadas Conhecidas (UTM)")
    # Default location (São Paulo)
    default_lat, default_lon = -23.5505, -46.6333
    u_e, u_n, u_zone, u_letter = utm.from_latlon(default_lat, default_lon)

    e1 = st.sidebar.number_input("P1 Este (m)", value=float(round(u_e, 2)))
    n1 = st.sidebar.number_input("P1 Norte (m)", value=float(round(u_n, 2)))

    e2, n2 = None, None
    if survey_type == "Enquadrada":
        st.sidebar.write(f"Vértice Final (P{n_points}) Conhecido:")
        # Offset for default end point
        e2 = st.sidebar.number_input(f"P{n_points} Este (m)", value=float(round(u_e + 200, 2)))
        n2 = st.sidebar.number_input(f"P{n_points} Norte (m)", value=float(round(u_n + 200, 2)))

    utm_zone = st.sidebar.number_input("Zona UTM", value=u_zone, min_value=1, max_value=60)
    utm_letter = st.sidebar.text_input("Letra UTM", value=u_letter).upper()

    if st.sidebar.button("Gerar Coordenadas Aleatórias"):
        # Use current map center if available
        start_lat, start_lon = default_lat, default_lon
        if 'map_center' in st.session_state:
            start_lat = st.session_state.map_center['lat']
            start_lon = st.session_state.map_center['lng']

        gen_end_coords = None
        if survey_type == "Enquadrada" and e2 is not None and n2 is not None:
            # Convert UTM back to Lat/Lon for the generator
            gen_end_coords = utm.to_latlon(e2, n2, utm_zone, utm_letter)

        lats, lons = simulator.generate_traverse_coordinates(
            n_points,
            survey_type="Closed" if survey_type == "Fechada" else "Linked",
            start_lat=start_lat,
            start_lon=start_lon,
            end_coords=gen_end_coords
        )
        st.session_state.survey_points = list(zip(lats, lons))

else: # Nivelamento
    survey_type = st.sidebar.radio("1.2 Tipo de Nivelamento", ["Geométrico", "Trigonométrico"], on_change=reset_survey)
    method = st.sidebar.selectbox("1.2.1 Técnica", ["visadas iguais", "visadas equivalentes", "visadas recíprocas", "visadas extremas"]) if survey_type == "Geométrico" else "trigonométrico"
    n_points = st.sidebar.number_input("Número de Pontos", min_value=2, max_value=50, value=5)

    if st.sidebar.button("Gerar Trajeto de Nivelamento"):
        lats, lons = simulator.generate_traverse_coordinates(n_points, survey_type="Linked", start_lat=-23.5505, start_lon=-46.6333)
        st.session_state.survey_points = list(zip(lats, lons))

# --- Main Layout ---
col_map, col_data = st.columns([1.2, 0.8])

with col_map:
    st.subheader("Mapa Interativo")
    center_lat, center_lon = (-23.5505, -46.6333) if not st.session_state.survey_points else st.session_state.survey_points[0]

    m = folium.Map(location=[center_lat, center_lon], zoom_start=16)

    if st.session_state.survey_points:
        points = st.session_state.survey_points
        folium.PolyLine(points, color="blue", weight=2.5).add_to(m)
        for i, (lat, lon) in enumerate(points):
            color = "red" if (i == 0 or (survey_category == "Poligonação" and survey_type == "Enquadrada" and i == len(points)-1)) else "blue"
            folium.CircleMarker([lat, lon], radius=6, color=color, fill=True, popup=f"Ponto {i+1}").add_to(m)

    # Optimized st_folium call for Stlite (Pyodide)
    # Using returned_objects to minimize serialization overhead and avoid MarshallComponentException
    map_data = st_folium(
        m,
        width=None,
        height=500,
        returned_objects=["last_clicked", "center"],
        use_container_width=True
    )

    if map_data:
        if map_data.get("center"):
            st.session_state.map_center = map_data["center"]

        if map_data.get("last_clicked"):
            clicked_coords = (float(map_data["last_clicked"]["lat"]), float(map_data["last_clicked"]["lng"]))
            if clicked_coords not in st.session_state.survey_points:
                st.session_state.survey_points.append(clicked_coords)
                st.rerun()

    if st.button("Limpar Pontos"):
        reset_survey()
        st.rerun()

with col_data:
    st.subheader("Dados dos Vértices")
    if st.session_state.survey_points:
        # Convert Lat/Lon to UTM for display
        utm_data = []
        for i, (lat, lon) in enumerate(st.session_state.survey_points):
            e, n, zone, letter = utm.from_latlon(lat, lon)
            utm_data.append({"Ponto": f"P{i+1}", "Este (m)": round(e, 2), "Norte (m)": round(n, 2), "Lat": round(lat, 6), "Lon": round(lon, 6)})

        df_points = pd.DataFrame(utm_data)
        st.dataframe(df_points[["Ponto", "Este (m)", "Norte (m)"]], use_container_width=True)

        if st.button("Simular Observações de Campo"):
            e_coords = df_points["Este (m)"].values
            n_coords = df_points["Norte (m)"].values
            if survey_category == "Poligonação":
                st.session_state.survey_data = simulator.simulate_traverse_observations(e_coords, n_coords)
            else:
                obs, elevs = simulator.simulate_leveling(len(e_coords), type=survey_type, method=method)
                st.session_state.survey_data = obs
                st.session_state.true_elevations = elevs
            st.rerun()

# --- Modules Output ---
if st.session_state.survey_data is not None:
    st.write("---")
    if survey_category == "Poligonação":
        st.subheader("🌐 Resultados da Poligonação (UTM)")

        end_coords = (e2, n2, 100.0) if (e2 is not None and n2 is not None) else None

        pre, raw_coords, errors, adj_coords = simulator.process_traverse_data(
            st.session_state.survey_data,
            (e1, n1, 100.0),
            survey_type="Closed" if survey_type == "Fechada" else "Linked",
            end_coords=end_coords
        )

        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "📋 Dados de Campo", "⚙️ Dados Pré-calculados", "📍 Coordenadas Iniciais", "📊 Análise de Erros", "✅ Coordenadas Finais (Bowditch)"
        ])

        with tab1: st.dataframe(st.session_state.survey_data, use_container_width=True)
        with tab2: st.dataframe(pre, use_container_width=True)
        with tab3: st.dataframe(raw_coords, use_container_width=True)
        with tab4:
            c1, c2, c3 = st.columns(3)
            c1.metric("Erro Angular", f"{errors['Erro Angular (°)']:.5f}°")
            c2.metric("Erro Planimétrico", f"{errors['Erro Planimétrico (m)']:.3f} m")
            c3.metric("Precisão Relativa", errors['Precisão Relativa'])
            st.metric("Erro Altimétrico", f"{errors['Erro Altimétrico (m)']:.3f} m")
        with tab5: st.dataframe(adj_coords, use_container_width=True)

    else: # Nivelamento
        st.subheader("📐 Resultados do Nivelamento")
        if survey_type == "Geométrico":
            st.header("🔍 Módulo de Leitura de Réguas")
            selected_row = st.selectbox("Selecione a Estação para leitura", range(len(st.session_state.survey_data)))
            row = st.session_state.survey_data.iloc[selected_row]
            c1, c2 = st.columns(2)
            with c1: st.code(simulator.get_rod_reading_visual(row['V. Ré (m)']))
            with c2: st.code(simulator.get_rod_reading_visual(row['V. Vante (m)']))

        st.header("🧮 Módulo de Validação")
        user_elevs = []
        cols = st.columns(3)
        for i in range(len(st.session_state.survey_points)):
            with cols[i % 3]:
                val = st.number_input(f"Cota P{i+1}", value=0.0, format="%.3f", key=f"user_elev_{i}")
                user_elevs.append(val)

        if st.button("Validar Cotas", use_container_width=True):
            closure_error = user_elevs[-1] - st.session_state.true_elevations[-1]
            st.metric("Erro de Cálculo (m)", f"{closure_error:.3f} m")
