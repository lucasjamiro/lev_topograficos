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
if 'radiation_points' not in st.session_state:
    st.session_state.radiation_points = []  # List of dicts
if 'map_locked' not in st.session_state:
    st.session_state.map_locked = False
if 'survey_data' not in st.session_state:
    st.session_state.survey_data = None
if 'map_zoom' not in st.session_state:
    st.session_state.map_zoom = 16
if 'map_center_coord' not in st.session_state:
    st.session_state.map_center_coord = [-25.4484, -49.2310]

def reset_survey():
    st.session_state.survey_points = []
    st.session_state.radiation_points = []
    st.session_state.survey_data = None
    st.session_state.map_locked = False

st.title("🏗️ Simulador de Levantamentos Topográficos")

# --- Sidebar ---
st.sidebar.header("Configurações do Levantamento")

survey_category = st.sidebar.selectbox(
    "1. Tipo de Levantamento",
    ["Poligonação", "Nivelamento"],
    on_change=reset_survey
)

challenge_mode = st.sidebar.toggle("🎯 Modo Desafio", help="Esconde os resultados finais para que o aluno insira seus próprios cálculos.")

if survey_category == "Poligonação":
    survey_type = st.sidebar.radio("1.1 Tipo de Poligonal", ["Fechada", "Enquadrada"], on_change=reset_survey)

    if survey_type == "Fechada":
        # Closed: HV1, HV2 + P1...Pn (Total = n + 2)
        n_inter = st.sidebar.number_input("1.1.1 Nº de Vértices de Passagem (P1...Pn)", min_value=1, max_value=48, value=3)
        max_pts = n_inter + 2
    else:
        # Linked: HV1, HV2 + P1...Pn + HV4, HV5 (Total = n + 4)
        n_inter = st.sidebar.number_input("1.1.1 Nº de Vértices de Passagem (P1...Pn)", min_value=1, max_value=46, value=3)
        max_pts = n_inter + 4

    st.sidebar.subheader("1.1.2 Coordenadas Conhecidas (UTM)")
    u_e, u_n, u_zone, u_letter = 677878.52, 7184223.31, 22, 'J'

    # Initialize session state keys for sidebar inputs if not already present
    if "e1_input" not in st.session_state:
        st.session_state.e1_input = u_e
    if "n1_input" not in st.session_state:
        st.session_state.n1_input = u_n
    if "e2_input" not in st.session_state:
        st.session_state.e2_input = u_e + 50.0
    if "n2_input" not in st.session_state:
        st.session_state.n2_input = u_n + 50.0
    if "e_hv4_input" not in st.session_state:
        st.session_state.e_hv4_input = u_e + 200.0
    if "n_hv4_input" not in st.session_state:
        st.session_state.n_hv4_input = u_n + 200.0
    if "e_hv5_input" not in st.session_state:
        st.session_state.e_hv5_input = u_e + 250.0
    if "n_hv5_input" not in st.session_state:
        st.session_state.n_hv5_input = u_n + 250.0

    # Sync inputs from map clicks
    if len(st.session_state.survey_points) >= 1:
        e, n, _, _ = utm.from_latlon(*st.session_state.survey_points[0])
        st.session_state.e1_input = round(float(e), 3)
        st.session_state.n1_input = round(float(n), 3)
    if len(st.session_state.survey_points) >= 2:
        e, n, _, _ = utm.from_latlon(*st.session_state.survey_points[1])
        st.session_state.e2_input = round(float(e), 3)
        st.session_state.n2_input = round(float(n), 3)

    e_hv_end1, n_hv_end1, e_hv_end2, n_hv_end2 = None, None, None, None
    if survey_type == "Enquadrada":
        if len(st.session_state.survey_points) >= max_pts - 1:
            e, n, _, _ = utm.from_latlon(*st.session_state.survey_points[max_pts-2])
            st.session_state.e_hv4_input = round(float(e), 3)
            st.session_state.n_hv4_input = round(float(n), 3)
        if len(st.session_state.survey_points) >= max_pts:
            e, n, _, _ = utm.from_latlon(*st.session_state.survey_points[max_pts-1])
            st.session_state.e_hv5_input = round(float(e), 3)
            st.session_state.n_hv5_input = round(float(n), 3)

    st.sidebar.write("**Partida:**")
    e1 = st.sidebar.number_input("HV1 Este (m)", format="%.3f", key="e1_input")
    n1 = st.sidebar.number_input("HV1 Norte (m)", format="%.3f", key="n1_input")
    e_hv2 = st.sidebar.number_input("HV2 Este (m)", format="%.3f", key="e2_input")
    n_hv2 = st.sidebar.number_input("HV2 Norte (m)", format="%.3f", key="n2_input")

    if survey_type == "Enquadrada":
        st.sidebar.write("**Chegada:**")
        e_hv_end1 = st.sidebar.number_input("HV4 Este (m)", format="%.3f", key="e_hv4_input")
        n_hv_end1 = st.sidebar.number_input("HV4 Norte (m)", format="%.3f", key="n_hv4_input")
        e_hv_end2 = st.sidebar.number_input("HV5 Este (m)", format="%.3f", key="e_hv5_input")
        n_hv_end2 = st.sidebar.number_input("HV5 Norte (m)", format="%.3f", key="n_hv5_input")

    utm_zone = st.sidebar.number_input("Zona UTM", value=u_zone, min_value=1, max_value=60)
    utm_letter = st.sidebar.text_input("Letra UTM", value=u_letter).upper()

    col_b1, col_b2 = st.sidebar.columns(2)
    if col_b1.button("Plotar Bases"):
        l1 = utm.to_latlon(e1, n1, utm_zone, utm_letter)
        l2 = utm.to_latlon(e_hv2, n_hv2, utm_zone, utm_letter)
        points = [(float(l1[0]), float(l1[1])), (float(l2[0]), float(l2[1]))]
        if survey_type == "Enquadrada":
            l4 = utm.to_latlon(e_hv_end1, n_hv_end1, utm_zone, utm_letter)
            l5 = utm.to_latlon(e_hv_end2, n_hv_end2, utm_zone, utm_letter)
            # Add placeholders for intermediate points if not enough
            while len(points) < max_pts - 2:
                points.append((float(l1[0]), float(l1[1])))
            points.append((float(l4[0]), float(l4[1])))
            points.append((float(l5[0]), float(l5[1])))
        st.session_state.survey_points = points
        st.session_state.map_center_coord = [float(l1[0]), float(l1[1])]
        st.rerun()

    if col_b2.button("Aleatório"):
        start_lat, start_lon = st.session_state.map_center_coord
        lats, lons = simulator.generate_traverse_coordinates(
            n_inter,
            survey_type="Closed" if survey_type == "Fechada" else "Linked",
            start_lat=start_lat,
            start_lon=start_lon
        )
        st.session_state.survey_points = list(zip(lats, lons))
        st.rerun()

else: # Nivelamento
    survey_type = st.sidebar.radio("1.2 Tipo de Nivelamento", ["Geométrico", "Trigonométrico"], on_change=reset_survey)
    method = st.sidebar.selectbox("1.2.1 Técnica", ["visadas iguais", "visadas equivalentes", "visadas recíprocas", "visadas extremas"]) if survey_type == "Geométrico" else "trigonométrico"
    n_pts_level = st.sidebar.number_input("Número de Pontos", min_value=2, max_value=50, value=5)
    max_pts = n_pts_level
    utm_zone, utm_letter = 22, 'J'

    if st.sidebar.button("Gerar Trajeto"):
        start_lat, start_lon = st.session_state.map_center_coord
        lats, lons = simulator.generate_traverse_coordinates(n_pts_level-2, survey_type="Closed", start_lat=start_lat, start_lon=start_lon)
        st.session_state.survey_points = [(float(la), float(lo)) for la, lo in zip(lats, lons)]
        st.rerun()

# --- Labels Generation ---
labels = []
colors = []
if survey_category == "Poligonação":
    if survey_type == "Fechada":
        for i in range(max_pts):
            if i == 0: labels.append("HV1"); colors.append("red")
            elif i == 1: labels.append("HV2"); colors.append("red")
            else: labels.append(f"P{i-1}"); colors.append("blue")
    else: # Linked
        for i in range(max_pts):
            if i == 0: labels.append("HV1"); colors.append("red")
            elif i == 1: labels.append("HV2"); colors.append("red")
            elif i == max_pts - 2: labels.append("HV4"); colors.append("red")
            elif i == max_pts - 1: labels.append("HV5"); colors.append("red")
            else: labels.append(f"P{i-1}"); colors.append("blue")
else: # Nivelamento
    for i in range(max_pts):
        labels.append(f"P{i+1}")
        colors.append("red" if i == 0 else "blue")

# --- Main Layout ---
col_map, col_data = st.columns([1.2, 0.8])

with col_map:
    st.subheader("Mapa Interativo")
    m = folium.Map(location=st.session_state.map_center_coord, zoom_start=st.session_state.map_zoom)

    if st.session_state.survey_points:
        points = st.session_state.survey_points
        line_points = list(points)
        if survey_category == "Poligonação" and survey_type == "Fechada" and len(points) >= max_pts:
            line_points.append(points[1]) # Close on HV2

        folium.PolyLine(line_points, color="blue", weight=2.5, dash_array='5, 5' if survey_category=="Poligonação" else None).add_to(m)
        for i, (lat, lon) in enumerate(points):
            if i < len(labels):
                folium.CircleMarker([lat, lon], radius=6, color=colors[i], fill=True, popup=labels[i]).add_to(m)

    # Render Radiation Points on Map
    if survey_category == "Poligonação" and st.session_state.radiation_points:
        for rad in st.session_state.radiation_points:
            rad_lat, rad_lon = rad['lat'], rad['lon']
            popup_text = f"{rad['name']} (Est: {rad['station']}, Ré: {rad['re']})"
            folium.CircleMarker([rad_lat, rad_lon], radius=5, color="green", fill=True, fill_color="green", popup=popup_text).add_to(m)

            if rad['station'] in labels:
                st_idx = labels.index(rad['station'])
                if st_idx < len(st.session_state.survey_points):
                    st_lat, st_lon = st.session_state.survey_points[st_idx]
                    folium.PolyLine([(st_lat, st_lon), (rad_lat, rad_lon)], color="green", weight=1.5, dash_array='3, 3').add_to(m)

    map_data = st_folium(
        m,
        center=st.session_state.map_center_coord,
        zoom=st.session_state.map_zoom,
        width=None,
        height=500,
        returned_objects=["last_clicked", "center", "zoom"],
        use_container_width=True
    )

    if map_data:
        new_center = map_data.get("center")
        if new_center:
            if isinstance(new_center, dict) and "lat" in new_center and "lng" in new_center:
                st.session_state.map_center_coord = [float(new_center["lat"]), float(new_center["lng"])]
            elif isinstance(new_center, (list, tuple)) and len(new_center) >= 2:
                st.session_state.map_center_coord = [float(new_center[0]), float(new_center[1])]

        new_zoom = map_data.get("zoom")
        if new_zoom:
            st.session_state.map_zoom = int(new_zoom)

        if not st.session_state.map_locked and map_data.get("last_clicked"):
            clicked = (float(map_data["last_clicked"]["lat"]), float(map_data["last_clicked"]["lng"]))
            if len(st.session_state.survey_points) < max_pts:
                if clicked not in st.session_state.survey_points:
                    st.session_state.survey_points.append(clicked)
                    st.rerun()
            elif survey_category == "Poligonação":
                existing_rad_coords = [(r['lat'], r['lon']) for r in st.session_state.radiation_points]
                if clicked not in existing_rad_coords and clicked not in st.session_state.survey_points:
                    idx = len(st.session_state.radiation_points) + 1
                    e_pt, n_pt, _, _ = utm.from_latlon(clicked[0], clicked[1])
                    def_station = labels[1] if len(labels) > 1 else labels[0]
                    st.session_state.radiation_points.append({
                        'name': f"IRR{idx}",
                        'lat': clicked[0],
                        'lon': clicked[1],
                        'e': round(float(e_pt), 3),
                        'n': round(float(n_pt), 3),
                        'station': def_station,
                        're': "-- Selecione --"
                    })
                    st.rerun()

    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("Limpar Pontos"): reset_survey(); st.rerun()
    with col_btn2:
        if st.session_state.map_locked:
            if st.button("🔓 Desbloquear Traçado"):
                st.session_state.map_locked = False
                st.session_state.survey_data = None
                st.rerun()

with col_data:
    st.subheader("Dados dos Vértices")
    if st.session_state.survey_points:
        utm_data = []
        for i, (lat, lon) in enumerate(st.session_state.survey_points):
            e, n, zone, letter = utm.from_latlon(lat, lon)
            pt_label = labels[i] if i < len(labels) else f"P{i+1}"
            utm_data.append({"Ponto": pt_label, "Este (m)": round(e, 3), "Norte (m)": round(n, 3)})

        df_pts = pd.DataFrame(utm_data)
        edited_df = st.data_editor(
            df_pts,
            column_config={
                "Ponto": st.column_config.TextColumn("Ponto", disabled=True),
                "Este (m)": st.column_config.NumberColumn("Este (m)", format="%.3f"),
                "Norte (m)": st.column_config.NumberColumn("Norte (m)", format="%.3f"),
            },
            use_container_width=True,
            num_rows="fixed",
            disabled=["Ponto"],
            key="vertex_editor"
        )

        if not edited_df.equals(df_pts):
            new_pts = []
            for idx, row in edited_df.iterrows():
                try:
                    nl, nln = utm.to_latlon(row["Este (m)"], row["Norte (m)"], utm_zone, utm_letter)
                    new_pts.append((nl, nln))
                except: new_pts.append(st.session_state.survey_points[idx])
            st.session_state.survey_points = new_pts
            st.rerun()

        # Section for Radiation Points
        if survey_category == "Poligonação":
            st.write("---")
            st.subheader("📍 Pontos de Irradiação")
            if len(st.session_state.survey_points) < max_pts:
                st.info("Complete a poligonal principal para habilitar a adição de pontos de irradiação.")
            else:
                if not st.session_state.map_locked:
                    col_rad_a, col_rad_b = st.columns(2)
                    if col_rad_a.button("+ Adicionar Irradiação"):
                        idx = len(st.session_state.radiation_points) + 1
                        def_lat, def_lon = st.session_state.map_center_coord
                        def_lat += 0.0001 * idx
                        def_lon += 0.0001 * idx
                        e_pt, n_pt, _, _ = utm.from_latlon(def_lat, def_lon)
                        def_station = labels[1] if len(labels) > 1 else labels[0]
                        st.session_state.radiation_points.append({
                            'name': f"IRR{idx}",
                            'lat': def_lat,
                            'lon': def_lon,
                            'e': round(float(e_pt), 3),
                            'n': round(float(n_pt), 3),
                            'station': def_station,
                            're': "-- Selecione --"
                        })
                        st.rerun()
                    if col_rad_b.button("Limpar Irradiações"):
                        st.session_state.radiation_points = []
                        st.rerun()

                if st.session_state.radiation_points:
                    rad_rows = []
                    for r in st.session_state.radiation_points:
                        rad_rows.append({
                            "Ponto": r['name'],
                            "Este (m)": r['e'],
                            "Norte (m)": r['n'],
                            "Estação": r['station'] if r['station'] in labels else labels[0],
                            "Ré": r['re'] if r['re'] in labels or r['re'] == "-- Selecione --" else "-- Selecione --"
                        })
                    df_rad = pd.DataFrame(rad_rows)
                    edited_rad_df = st.data_editor(
                        df_rad,
                        column_config={
                            "Ponto": st.column_config.TextColumn("Ponto", disabled=True),
                            "Este (m)": st.column_config.NumberColumn("Este (m)", format="%.3f"),
                            "Norte (m)": st.column_config.NumberColumn("Norte (m)", format="%.3f"),
                            "Estação": st.column_config.SelectboxColumn("Estação", options=labels, required=True),
                            "Ré": st.column_config.SelectboxColumn("Ré", options=["-- Selecione --"] + labels, required=True)
                        },
                        disabled=st.session_state.map_locked,
                        num_rows="fixed",
                        use_container_width=True,
                        key="rad_editor"
                    )

                    if not edited_rad_df.equals(df_rad):
                        updated_rads = []
                        for idx_r, row_r in edited_rad_df.iterrows():
                            try:
                                nl_r, nln_r = utm.to_latlon(row_r["Este (m)"], row_r["Norte (m)"], utm_zone, utm_letter)
                            except:
                                nl_r, nln_r = st.session_state.radiation_points[idx_r]['lat'], st.session_state.radiation_points[idx_r]['lon']
                            updated_rads.append({
                                'name': row_r["Ponto"],
                                'lat': nl_r,
                                'lon': nln_r,
                                'e': float(row_r["Este (m)"]),
                                'n': float(row_r["Norte (m)"]),
                                'station': row_r["Estação"],
                                're': row_r["Ré"]
                            })
                        st.session_state.radiation_points = updated_rads
                        st.rerun()

        if st.session_state.map_locked:
            st.info("🔒 Traçado e irradiações bloqueados.")

        if st.button("Simular Observações de Campo"):
            if len(st.session_state.survey_points) < max_pts:
                st.error(f"Selecione todos os {max_pts} pontos!")
            else:
                # Validation check for radiation points
                invalid_rad = False
                if survey_category == "Poligonação" and st.session_state.radiation_points:
                    for rad in st.session_state.radiation_points:
                        re_val = rad.get("re")
                        st_val = rad.get("station")
                        if not re_val or re_val in ["-- Selecione --", ""] or re_val not in labels:
                            invalid_rad = True
                            break
                        if re_val == st_val:
                            invalid_rad = True
                            break

                if invalid_rad:
                    st.error("Erro: Selecione uma estação de Ré válida (diferente da Estação) para todos os pontos de irradiação!")
                else:
                    st.session_state.map_locked = True
                    e_coords = df_pts["Este (m)"].values
                    n_coords = df_pts["Norte (m)"].values
                    if survey_category == "Poligonação":
                        st.session_state.survey_data = simulator.simulate_traverse_observations(
                            e_coords, n_coords,
                            survey_type="Closed" if survey_type == "Fechada" else "Linked",
                            radiation_data=st.session_state.radiation_points
                        )
                    else:
                        obs, elevs = simulator.simulate_leveling(len(e_coords), type=survey_type, method=method)
                        st.session_state.survey_data = obs
                        st.session_state.true_elevations = elevs
                    st.rerun()

# --- Results Modules ---
if st.session_state.survey_data is not None:
    st.write("---")
    if survey_category == "Poligonação":
        st.subheader("🌐 Resultados da Poligonação (UTM)")
        end_cs = (e_hv_end1, n_hv_end1, 100.0) if e_hv_end1 else None
        end_ce = (e_hv_end2, n_hv_end2, 100.0) if e_hv_end2 else None

        pre, az_df, raw, errs, adj = simulator.process_traverse_data(
            st.session_state.survey_data, (e1, n1, 100.0), (e_hv2, n_hv2, 100.0),
            survey_type="Closed" if survey_type == "Fechada" else "Linked",
            end_coords_start=end_cs, end_coords_end=end_ce
        )

        t1, t2, t3, t4, t5, t6 = st.tabs(["📋 Campo", "⚙️ Pré-calculos", "🧭 Azimutes Transportados", "📍 Provisórias", "📊 Erros", "✅ Finais (Bowditch)"])
        with t1: st.dataframe(simulator.format_df_for_display(st.session_state.survey_data), use_container_width=True)
        with t2:
            if challenge_mode: st.info("Modo Desafio Ativo.")
            else: st.dataframe(simulator.format_df_for_display(pre), use_container_width=True)
        with t3:
            if challenge_mode: st.info("Modo Desafio Ativo.")
            else: st.dataframe(simulator.format_df_for_display(az_df), use_container_width=True)
        with t4:
            if challenge_mode: st.info("Modo Desafio Ativo.")
            else: st.dataframe(simulator.format_df_for_display(raw), use_container_width=True)
        with t5:
            if challenge_mode:
                uea = st.number_input("Erro Angular (°)", format="%.7f")
                uep = st.number_input("Erro Planimétrico (m)", format="%.4f")
                if st.button("Verificar Erros"):
                    if abs(uea - errs['Erro Angular (°)']) < 0.0001 and abs(uep - errs['Erro Planimétrico (m)']) < 0.01:
                        st.success("Correto!")
                    else: st.error("Divergência nos cálculos.")
            else:
                c1, c2, c3 = st.columns(3)
                c1.metric("Erro Angular", f"{simulator.format_num(errs['Erro Angular (°)'], 7)}°")
                c2.metric("Erro Planimétrico", f"{simulator.format_num(errs['Erro Planimétrico (m)'], 4)} m")
                c3.metric("Precisão", errs['Precisão Relativa'])
        with t6:
            if challenge_mode:
                last_label = adj.iloc[-1]['Ponto']
                uef = st.number_input(f"Este Final ({last_label})", format="%.3f")
                unf = st.number_input(f"Norte Final ({last_label})", format="%.3f")
                if st.button("Verificar Finais"):
                    if abs(uef-adj.iloc[-1]['E']) < 0.01 and abs(unf-adj.iloc[-1]['N']) < 0.01:
                        st.success("Correto!")
                    else: st.error("Divergência.")
            else:
                final_cols = ["Ponto", "Correção E", "Correção N", "Correção Z", "E", "N", "Z"]
                st.dataframe(simulator.format_df_for_display(adj[final_cols]), use_container_width=True)
    else: # Nivelamento
        st.subheader("📐 Resultados do Nivelamento")
        if not challenge_mode: st.dataframe(simulator.format_df_for_display(st.session_state.survey_data), use_container_width=True)
        if survey_type == "Geométrico":
            st.header("🔍 Leitura de Réguas")
            sel = st.selectbox("Estação", range(len(st.session_state.survey_data)))
            r = st.session_state.survey_data.iloc[sel]
            c1, c2 = st.columns(2)
            with c1: st.write("Ré"); st.code(simulator.get_rod_reading_visual(r['V. Ré (m)']))
            with c2: st.write("Vante"); st.code(simulator.get_rod_reading_visual(r['V. Vante (m)']))
        st.header("🧮 Validação")
        uevs = [st.number_input(f"Cota P{i+1}", format="%.3f", key=f"lev_{i}") for i in range(len(st.session_state.survey_points))]
        if st.button("Verificar Cotas"):
            err = np.mean([abs(u - c) for u, c in zip(uevs, st.session_state.true_elevations)])
            if err < 0.005: st.success(f"Correto! Erro: {simulator.format_num(err, 4)}m")
            else: st.error(f"Divergência. Erro: {simulator.format_num(err, 4)}m")
