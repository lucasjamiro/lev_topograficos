import numpy as np
import pandas as pd

COLUMN_PRECISION_MAP = {
    # Angles (7 decimals)
    "Dir. Ré (°)": 7,
    "Dir. Vante (°)": 7,
    "Ângulo Zenital (°)": 7,
    "Ângulo Horiz. (°)": 7,
    "Azimute Transportado (°)": 7,
    "Correção (°)": 7,
    "Azimute Corrigido (°)": 7,
    "Ângulo Vertical (deg)": 7,
    "Erro Angular (°)": 7,

    # Distances (4 decimals)
    "Dist. Inclinada (m)": 4,
    "Dist. Horizontal (m)": 4,
    "Dist (m)": 4,
    "V. Ré (m)": 4,
    "V. Vante (m)": 4,
    "Erro Planimétrico (m)": 4,

    # Partial Coordinates / Increments (5 decimals)
    "ΔH (m)": 5,
    "Correção E": 5,
    "Correção N": 5,
    "Correção Z": 5,

    # Final Coordinates & Elevations / Z (3 decimals)
    "E": 3,
    "N": 3,
    "Z": 3,
    "Este (m)": 3,
    "Norte (m)": 3,
    "AI (m)": 3,
    "Alt. Instrumento (m)": 3,
    "Alt. Sinal (m)": 3,
    "Erro Altimétrico (m)": 3,
}

def format_num(val, decimals=3):
    """
    Formats a numeric value using Portuguese locale conventions:
    dot (.) as thousands separator and comma (,) as decimal separator.
    """
    if val is None or pd.isna(val):
        return ""
    try:
        s = f"{float(val):,.{decimals}f}"
        return s.replace(",", "X").replace(".", ",").replace("X", ".")
    except (ValueError, TypeError):
        return str(val)

def format_df_for_display(df):
    """
    Returns a copy of the DataFrame with numeric columns formatted to strings
    matching the required decimal precision and locale separators.
    """
    if df is None or df.empty:
        return df

    formatted_df = df.copy()
    for col in formatted_df.columns:
        if col in COLUMN_PRECISION_MAP:
            prec = COLUMN_PRECISION_MAP[col]
            formatted_df[col] = formatted_df[col].apply(lambda x: format_num(x, prec))

    return formatted_df

def calculate_azimuth_flat(e1, n1, e2, n2):
    """Calculates azimuth between two points in a flat coordinate system (UTM)."""
    de = e2 - e1
    dn = n2 - n1
    azimuth = np.degrees(np.arctan2(de, dn))
    return (azimuth + 360) % 360

def generate_traverse_coordinates(n_intermediate, survey_type="Closed", start_lat=-23.5505, start_lon=-46.6333, scale=0.001):
    """
    Generates coordinates for traverse.
    - Closed: HV1, HV2, P1...Pn-2 (Total points = n_intermediate + 2)
    - Linked: HV1, HV2, P1...Pn, HV4, HV5 (Total points = n_intermediate + 4)
    """
    if survey_type == "Closed":
        n_total = n_intermediate + 2
        angles = np.linspace(0, 2 * np.pi, n_total, endpoint=False)
        radius = scale * (n_total / (2 * np.pi))
        lats = []
        lons = []
        for angle in angles:
            r = radius * np.random.uniform(0.8, 1.2)
            lats.append(start_lat + np.cos(angle) * r)
            lons.append(start_lon + np.sin(angle) * r)

        # Align HV2 to start_lat/lon
        offset_lat = start_lat - lats[1]
        offset_lon = start_lon - lons[1]
        lats = [lat + offset_lat for lat in lats]
        lons = [lon + offset_lon for lon in lons]
        return np.array(lats), np.array(lons)

    else: # Linked
        n_total = n_intermediate + 4
        # HV1, HV2
        lats = [start_lat - scale, start_lat]
        lons = [start_lon, start_lon]

        current_lat, current_lon = start_lat, start_lon
        base_angle = 0

        # P1...Pn
        for i in range(n_intermediate):
            angle = base_angle + np.random.uniform(-np.pi/4, np.pi/4)
            current_lat += np.cos(angle) * scale
            current_lon += np.sin(angle) * scale
            lats.append(current_lat)
            lons.append(current_lon)

        # HV4, HV5
        # HV4 continues the path
        angle = base_angle + np.random.uniform(-np.pi/4, np.pi/4)
        current_lat += np.cos(angle) * scale
        current_lon += np.sin(angle) * scale
        lats.append(current_lat)
        lons.append(current_lon)
        # HV5 adds one more for orientation
        angle = base_angle + np.random.uniform(-np.pi/4, np.pi/4)
        current_lat += np.cos(angle) * scale
        current_lon += np.sin(angle) * scale
        lats.append(current_lat)
        lons.append(current_lon)

        return np.array(lats), np.array(lons)

def simulate_traverse_observations(e_coords, n_coords, survey_type="Closed", angle_sigma=0.005, dist_sigma=0.005, radiation_data=None):
    """
    Simulates raw field observations for main traverse and optional radiation points.
    """
    n = len(e_coords)
    observations = []

    # Elevations (Z)
    elevations = np.zeros(n)
    elevations[0] = 100.0 # HV1
    for i in range(1, n):
        elevations[i] = elevations[i-1] + np.random.normal(0, 0.5)

    def get_label(idx):
        if survey_type == "Closed":
            if idx == 0: return "HV1"
            if idx == 1: return "HV2"
            return f"P{idx-1}"
        else: # Linked
            if idx == 0: return "HV1"
            if idx == 1: return "HV2"
            if idx == n-2: return "HV4"
            if idx == n-1: return "HV5"
            return f"P{idx-1}"

    label_to_coords = {}
    for i in range(n):
        label_to_coords[get_label(i)] = (e_coords[i], n_coords[i], elevations[i])

    stations = []
    if survey_type == "Closed":
        # Stations: HV2, P1...Pn-2, then back to HV2
        # Sequence indices: 0(HV1), 1(HV2), 2(P1), ..., n-1(P_n-2)
        # 1: R=0, V=2
        stations.append((1, 0, 2))
        # i: R=i-1, V=i+1
        for i in range(2, n - 1):
            stations.append((i, i-1, i+1))
        # Last station: n-1, R=n-2, V=1
        stations.append((n-1, n-2, 1))
        # Closure station at HV2: R=n-1, V=2
        stations.append((1, n-1, 2))

    else: # Linked
        # Sequence indices: 0(HV1), 1(HV2), 2(P1), ..., n-3(Pn), n-2(HV4), n-1(HV5)
        # Stations: 1(HV2), 2(P1)...n-2(HV4)
        for i in range(1, n - 1):
            stations.append((i, i-1, i+1))

    station_zero_dir = {} # Store circle zero direction per station

    for s_idx, re_idx, v_idx in stations:
        s_label = get_label(s_idx)
        re_label = get_label(re_idx)
        v_label = get_label(v_idx)

        d_horiz_true = np.sqrt((e_coords[v_idx]-e_coords[s_idx])**2 + (n_coords[v_idx]-n_coords[s_idx])**2)
        d_inc_true = np.sqrt(d_horiz_true**2 + (elevations[v_idx]-elevations[s_idx])**2)
        d_inc_measured = d_inc_true + np.random.normal(0, dist_sigma)

        dir_re = np.random.uniform(0, 360)
        az_fs = calculate_azimuth_flat(e_coords[s_idx], n_coords[s_idx], e_coords[v_idx], n_coords[v_idx])
        az_re = calculate_azimuth_flat(e_coords[s_idx], n_coords[s_idx], e_coords[re_idx], n_coords[re_idx])

        # Station circle zero direction
        station_zero_dir[s_label] = (dir_re - az_re + 360) % 360

        true_angle = (az_fs - az_re + 360) % 360
        dir_vante = (dir_re + true_angle + np.random.normal(0, angle_sigma)) % 360

        slope_angle = np.degrees(np.arctan2(elevations[v_idx] - elevations[s_idx], d_horiz_true))
        zenith_measured = 90 - slope_angle + np.random.normal(0, angle_sigma)

        observations.append({
            "Estação": s_label,
            "Ré": re_label,
            "Vante": v_label,
            "Dir. Ré (°)": round(dir_re, 7),
            "Dir. Vante (°)": round(dir_vante, 7),
            "Ângulo Zenital (°)": round(zenith_measured, 7),
            "Dist. Inclinada (m)": round(d_inc_measured, 4)
        })

    # Process Radiation Points if provided
    if radiation_data is not None:
        if isinstance(radiation_data, pd.DataFrame):
            rad_list = radiation_data.to_dict("records")
        else:
            rad_list = radiation_data

        for rad in rad_list:
            v_label = rad.get("Ponto") or rad.get("name")
            s_label = rad.get("Estação") or rad.get("station")
            re_label = rad.get("Ré") or rad.get("re")
            e_v = float(rad.get("E") if rad.get("E") is not None else rad.get("e", 0.0))
            n_v = float(rad.get("N") if rad.get("N") is not None else rad.get("n", 0.0))

            if not s_label or not re_label or s_label not in label_to_coords or re_label not in label_to_coords:
                continue

            e_s, n_s, z_s = label_to_coords[s_label]
            e_r, n_r, z_r = label_to_coords[re_label]
            z_v = float(rad.get("Z", z_s + np.random.normal(0, 0.5)))

            d_horiz_true = np.sqrt((e_v - e_s)**2 + (n_v - n_s)**2)
            d_inc_true = np.sqrt(d_horiz_true**2 + (z_v - z_s)**2)
            d_inc_measured = d_inc_true + np.random.normal(0, dist_sigma)

            dir_0 = station_zero_dir.get(s_label, np.random.uniform(0, 360))

            az_re = calculate_azimuth_flat(e_s, n_s, e_r, n_r)
            az_fs = calculate_azimuth_flat(e_s, n_s, e_v, n_v)

            dir_re = (dir_0 + az_re) % 360
            true_angle = (az_fs - az_re + 360) % 360
            dir_vante = (dir_re + true_angle + np.random.normal(0, angle_sigma)) % 360

            slope_angle = np.degrees(np.arctan2(z_v - z_s, d_horiz_true)) if d_horiz_true > 1e-6 else 0.0
            zenith_measured = 90 - slope_angle + np.random.normal(0, angle_sigma)

            observations.append({
                "Estação": s_label,
                "Ré": re_label,
                "Vante": v_label,
                "Dir. Ré (°)": round(dir_re, 7),
                "Dir. Vante (°)": round(dir_vante, 7),
                "Ângulo Zenital (°)": round(zenith_measured, 7),
                "Dist. Inclinada (m)": round(d_inc_measured, 4)
            })

    return pd.DataFrame(observations)

def process_traverse_data(df, start_coords, hv2_coords, survey_type="Closed", end_coords_start=None, end_coords_end=None):
    """
    Strict calculation workflow for Linked and Closed traverses, including radiation points.
    """
    pre = df.copy()
    pre["Ângulo Horiz. (°)"] = ((pre["Dir. Vante (°)"] - pre["Dir. Ré (°)"] + 360) % 360).round(7)
    pre["Dist. Horizontal (m)"] = (pre["Dist. Inclinada (m)"] * np.sin(np.radians(pre["Ângulo Zenital (°)"]))).round(4)
    pre["ΔH (m)"] = (pre["Dist. Inclinada (m)"] * np.cos(np.radians(pre["Ângulo Zenital (°)"]))).round(5)

    # Separate main traverse setups from radiation setups
    # Main traverse stations start with HV labels or P labels.
    # We can detect main setups vs radiation setups based on Vante label.
    main_labels = {"HV1", "HV2", "HV4", "HV5"}
    # Gather all P_i labels that form main sequence if needed, or identify radiation rows
    # In simulated observations, main traverse rows come first in sequence.
    # For Closed: main setups end with the setup at HV2 aiming back to P1.
    # For Linked: main setups end with HV4 aiming HV5.
    main_setup_indices = []
    rad_setup_indices = []

    for idx, row in pre.iterrows():
        v_label = row["Vante"]
        # Check if v_label is part of main traverse or radiation
        # Main traverse points are HV1, HV2, HV4, HV5, or P1..P48 (when in sequence)
        # However, radiation points are typically IRR1, IRR2, or points not in main setup loop
        if v_label.startswith("IRR") or (idx > 0 and v_label == "P1" and survey_type == "Closed" and idx < len(pre) - 1 and pre.iloc[idx-1]["Estação"] == "HV2"):
            # Check carefully: in Closed traverse, setup 0 is HV2->P1, and setup n-1 is HV2->P1 (closure).
            # If v_label is IRR... or clearly radiation, add to rad.
            rad_setup_indices.append(idx)
        else:
            # Check if we already reached closure for Closed traverse
            if survey_type == "Closed" and len(main_setup_indices) > 0 and pre.iloc[main_setup_indices[-1]]["Estação"] == "HV2" and pre.iloc[main_setup_indices[-1]]["Vante"] == "P1" and len(main_setup_indices) > 2:
                # After closure setup at HV2, any subsequent setup is radiation
                rad_setup_indices.append(idx)
            elif survey_type == "Linked" and len(main_setup_indices) > 0 and pre.iloc[main_setup_indices[-1]]["Estação"] == "HV4" and pre.iloc[main_setup_indices[-1]]["Vante"] == "HV5":
                # After HV4->HV5 setup, any subsequent setup is radiation
                rad_setup_indices.append(idx)
            else:
                if v_label.startswith("IRR"):
                    rad_setup_indices.append(idx)
                else:
                    main_setup_indices.append(idx)

    pre_main = pre.loc[main_setup_indices].reset_index(drop=True)
    pre_rad = pre.loc[rad_setup_indices].reset_index(drop=True)

    # 1. Initial Azimuth (HV1 -> HV2)
    az_hv1_hv2 = calculate_azimuth_flat(start_coords[0], start_coords[1], hv2_coords[0], hv2_coords[1])

    # 2. Azimuth Propagation and Angular Closure
    n_setups = len(pre_main)
    az_back = (az_hv1_hv2 + 180) % 360

    propagated_azimuths = []
    curr_az = (az_back + pre_main.iloc[0]["Ângulo Horiz. (°)"]) % 360
    propagated_azimuths.append(curr_az)

    for i in range(1, n_setups):
        # Az(i -> i-1) = Az(i-1 -> i) + 180
        curr_az = (curr_az + 180 + pre_main.iloc[i]["Ângulo Horiz. (°)"]) % 360
        propagated_azimuths.append(curr_az)

    if survey_type == "Closed":
        # Expected last azimuth: Az(HV2 -> P1)
        az_target = propagated_azimuths[0]
        err_ang = (propagated_azimuths[-1] - az_target)
        if err_ang > 180: err_ang -= 360
        if err_ang < -180: err_ang += 360
        # Correction per station (applied to each measured angle except first? No, distribute among all setups)
        corr_ang_per_station = -err_ang / (n_setups - 1)

    else: # Linked
        # Expected last azimuth: Az(HV4 -> HV5)
        az_target = calculate_azimuth_flat(end_coords_start[0], end_coords_start[1], end_coords_end[0], end_coords_end[1])
        err_ang = (propagated_azimuths[-1] - az_target)
        if err_ang > 180: err_ang -= 360
        if err_ang < -180: err_ang += 360
        corr_ang_per_station = -err_ang / n_setups

    # 3. Corrected Azimuths
    adj_azimuths = []
    # Re-propagate with corrections
    curr_az = (az_back + pre_main.iloc[0]["Ângulo Horiz. (°)"] + corr_ang_per_station) % 360
    adj_azimuths.append(curr_az)
    for i in range(1, n_setups):
        curr_az = (curr_az + 180 + pre_main.iloc[i]["Ângulo Horiz. (°)"] + corr_ang_per_station) % 360
        adj_azimuths.append(curr_az)

    # 3b. Transported Azimuths DataFrame
    az_data = []
    for i in range(n_setups):
        az_data.append({
            "Estação": pre_main.iloc[i]["Estação"],
            "Ré": pre_main.iloc[i]["Ré"],
            "Vante": pre_main.iloc[i]["Vante"],
            "Azimute Transportado (°)": round(float(propagated_azimuths[i]), 7),
            "Correção (°)": round(float((i + 1) * corr_ang_per_station), 7),
            "Azimute Corrigido (°)": round(float(adj_azimuths[i]), 7)
        })
    az_df = pd.DataFrame(az_data)

    # 4. Provisional Coordinates
    # Sequence starts at HV2
    raw_coords = [
        {"Ponto": "HV1", "E": start_coords[0], "N": start_coords[1], "Z": start_coords[2]},
        {"Ponto": "HV2", "E": hv2_coords[0], "N": hv2_coords[1], "Z": hv2_coords[2]}
    ]

    # Coordinates calculation loop
    for i in range(n_setups - 1): # Exclude last setup (HV4-HV5) for coordinate propagation to HV4
        dist = pre_main.iloc[i]["Dist. Horizontal (m)"]
        az = adj_azimuths[i]
        de = dist * np.sin(np.radians(az))
        dn = dist * np.cos(np.radians(az))
        dz = pre_main.iloc[i]["ΔH (m)"]

        last = raw_coords[-1]
        raw_coords.append({
            "Ponto": pre_main.iloc[i]["Vante"],
            "E": last["E"] + de,
            "N": last["N"] + dn,
            "Z": last["Z"] + dz
        })

    # 5. Linear Closure (Bowditch)
    total_dist = pre_main.iloc[:n_setups-1]["Dist. Horizontal (m)"].sum()
    if survey_type == "Closed":
        err_e = raw_coords[-1]["E"] - hv2_coords[0]
        err_n = raw_coords[-1]["N"] - hv2_coords[1]
        err_z = raw_coords[-1]["Z"] - hv2_coords[2]
    else:
        err_e = raw_coords[-1]["E"] - end_coords_start[0]
        err_n = raw_coords[-1]["N"] - end_coords_start[1]
        err_z = raw_coords[-1]["Z"] - end_coords_start[2]

    err_plan = np.sqrt(err_e**2 + err_n**2)

    prec_denom = int(total_dist/err_plan) if err_plan > 0.001 else None
    prec_str = f"1/{format_num(prec_denom, 0)}" if prec_denom is not None else "1/inf"

    errors = {
        "Erro Angular (°)": round(float(err_ang), 7),
        "Erro Planimétrico (m)": round(float(err_plan), 4),
        "Erro Altimétrico (m)": round(float(err_z), 3),
        "Precisão Relativa": prec_str
    }

    # 6. Final Adjusted Coordinates
    hv1_adj = raw_coords[0].copy()
    hv1_adj["Correção E"], hv1_adj["Correção N"], hv1_adj["Correção Z"] = 0.0, 0.0, 0.0
    hv2_adj = raw_coords[1].copy()
    hv2_adj["Correção E"], hv2_adj["Correção N"], hv2_adj["Correção Z"] = 0.0, 0.0, 0.0
    adj_coords = [hv1_adj, hv2_adj]
    # Apply Bowditch to P1...HV4
    cum_dist = 0
    for i in range(n_setups - 1):
        cum_dist += pre_main.iloc[i]["Dist. Horizontal (m)"]
        corr_e = -err_e * (cum_dist / total_dist)
        corr_n = -err_n * (cum_dist / total_dist)
        corr_z = -err_z * (cum_dist / total_dist)

        pt = raw_coords[i+2].copy()
        pt["Correção E"] = round(corr_e, 5)
        pt["Correção N"] = round(corr_n, 5)
        pt["Correção Z"] = round(corr_z, 5)
        pt["E"] = round(pt["E"] + corr_e, 3)
        pt["N"] = round(pt["N"] + corr_n, 3)
        pt["Z"] = round(pt["Z"] + corr_z, 3)
        adj_coords.append(pt)

    # For linked, add HV5 at the end
    if survey_type == "Linked":
        # HV5 position can be calculated from adjusted HV4 + corrected Az(HV4-HV5)
        last_adj = adj_coords[-1] # HV4
        dist_final = pre_main.iloc[-1]["Dist. Horizontal (m)"]
        az_final = adj_azimuths[-1]
        hv5_e = last_adj["E"] + dist_final * np.sin(np.radians(az_final))
        hv5_n = last_adj["N"] + dist_final * np.cos(np.radians(az_final))
        hv5_z = last_adj["Z"] + pre_main.iloc[-1]["ΔH (m)"]

        adj_coords.append({
            "Ponto": "HV5", "E": round(hv5_e, 3), "N": round(hv5_n, 3), "Z": round(hv5_z, 3),
            "Correção E": 0.0, "Correção N": 0.0, "Correção Z": 0.0
        })
        raw_coords.append({"Ponto": "HV5", "E": round(hv5_e, 3), "N": round(hv5_n, 3), "Z": round(hv5_z, 3)})

    # Append radiation points to adj_coords and raw_coords
    adj_map = {pt["Ponto"]: pt for pt in adj_coords}
    raw_map = {pt["Ponto"]: pt for pt in raw_coords}

    for _, rad_row in pre_rad.iterrows():
        s_lbl = rad_row["Estação"]
        re_lbl = rad_row["Ré"]
        v_lbl = rad_row["Vante"]
        ang_h = rad_row["Ângulo Horiz. (°)"]
        dist_h = rad_row["Dist. Horizontal (m)"]
        dh = rad_row["ΔH (m)"]

        if s_lbl in adj_map and re_lbl in adj_map:
            st_pt = adj_map[s_lbl]
            re_pt = adj_map[re_lbl]

            az_sr = calculate_azimuth_flat(st_pt["E"], st_pt["N"], re_pt["E"], re_pt["N"])
            az_sv = (az_sr + ang_h) % 360

            e_v = st_pt["E"] + dist_h * np.sin(np.radians(az_sv))
            n_v = st_pt["N"] + dist_h * np.cos(np.radians(az_sv))
            z_v = st_pt["Z"] + dh

            adj_pt = {
                "Ponto": v_lbl,
                "Correção E": 0.0,
                "Correção N": 0.0,
                "Correção Z": 0.0,
                "E": round(float(e_v), 3),
                "N": round(float(n_v), 3),
                "Z": round(float(z_v), 3)
            }
            adj_coords.append(adj_pt)
            adj_map[v_lbl] = adj_pt

        if s_lbl in raw_map and re_lbl in raw_map:
            st_pt = raw_map[s_lbl]
            re_pt = raw_map[re_lbl]

            az_sr = calculate_azimuth_flat(st_pt["E"], st_pt["N"], re_pt["E"], re_pt["N"])
            az_sv = (az_sr + ang_h) % 360

            e_v = st_pt["E"] + dist_h * np.sin(np.radians(az_sv))
            n_v = st_pt["N"] + dist_h * np.cos(np.radians(az_sv))
            z_v = st_pt["Z"] + dh

            raw_pt = {
                "Ponto": v_lbl,
                "E": round(float(e_v), 3),
                "N": round(float(n_v), 3),
                "Z": round(float(z_v), 3)
            }
            raw_coords.append(raw_pt)
            raw_map[v_lbl] = raw_pt

    raw_df = pd.DataFrame(raw_coords)
    for col in ["E", "N", "Z"]: raw_df[col] = raw_df[col].round(3)

    return pre, az_df, raw_df, errors, pd.DataFrame(adj_coords)

def simulate_leveling(n_points, type="Geometric", method="visadas iguais", start_elev=100.0, error_per_km=0.005):
    """
    Simulates leveling observations.
    """
    elevations = [start_elev]
    current_elev = start_elev
    observations = []

    for i in range(1, n_points):
        dist = np.random.uniform(30, 80)
        delta_h = np.random.uniform(-0.5, 0.5)
        measured_delta_h = delta_h + np.random.normal(0, error_per_km * np.sqrt(dist/1000))

        prev_elev = current_elev
        current_elev += delta_h
        elevations.append(current_elev)

        if type in ["Geometric", "Geométrico"]:
            bs = np.random.uniform(1.0, 2.5)
            ai = prev_elev + bs
            fs = ai - (prev_elev + measured_delta_h)

            obs = {
                "Estação": f"E{i}",
                "Ponto": f"P{i+1}",
                "V. Ré (m)": round(bs, 4),
                "AI (m)": round(ai, 3),
                "V. Vante (m)": round(fs, 4),
                "Dist (m)": round(dist, 4),
                "Método": method
            }
            observations.append(obs)
        else: # Trigonométrico
            slope_dist = np.sqrt(dist**2 + measured_delta_h**2)
            vert_angle = np.degrees(np.arctan2(measured_delta_h, dist))
            observations.append({
                "De": f"P{i}",
                "Para": f"P{i+1}",
                "Dist. Inclinada (m)": round(slope_dist, 4),
                "Ângulo Vertical (deg)": round(vert_angle, 7),
                "Alt. Instrumento (m)": 1.500,
                "Alt. Sinal (m)": 1.500
            })

    return pd.DataFrame(observations), elevations

def get_rod_reading_visual(value):
    """
    Returns an ASCII representation of a topographical rod.
    """
    v = round(value, 4)
    v_cm = int(v * 100)
    mm_part = int(round((v * 100 - v_cm) * 10))

    lines = []
    lines.append(f"   MIRA (Leitura: {format_num(v, 4)}m)")
    lines.append("   +----------+")
    for cm in range(v_cm + 5, v_cm - 6, -1):
        m_val = cm / 100.0
        pattern = "#####     " if cm % 2 == 0 else "     #####"
        pointer = ">" if cm == v_cm else " "
        mm_label = f" [+{mm_part}mm]" if cm == v_cm else ""
        lines.append(f"{format_num(m_val, 2):>7} |{pattern}| {pointer}{mm_label}")
    lines.append("   +----------+")
    lines.append("   (Intervalos de 1cm)")
    return "\n".join(lines)
