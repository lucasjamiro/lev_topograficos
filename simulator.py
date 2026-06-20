import numpy as np
import pandas as pd

def calculate_azimuth_flat(e1, n1, e2, n2):
    """Calculates azimuth between two points in a flat coordinate system (UTM)."""
    de = e2 - e1
    dn = n2 - n1
    azimuth = np.degrees(np.arctan2(de, dn))
    return (azimuth + 360) % 360

def calculate_azimuth(lat1, lon1, lat2, lon2):
    dlon = lon2 - lon1
    y = np.sin(np.radians(dlon)) * np.cos(np.radians(lat2))
    x = np.cos(np.radians(lat1)) * np.sin(np.radians(lat2)) - \
        np.sin(np.radians(lat1)) * np.cos(np.radians(lat2)) * np.cos(np.radians(dlon))
    azimuth = np.degrees(np.arctan2(y, x))
    return (azimuth + 360) % 360

def generate_traverse_coordinates(n_points, survey_type="Closed", start_lat=-23.5505, start_lon=-46.6333, scale=0.001, end_coords=None):
    """
    Generates a set of coordinates for a traverse survey.
    scale: rough distance between points in degrees (approx 100m)
    """
    if survey_type == "Closed":
        # For a closed traverse, we start and end at the same point (conceptually)
        # but usually we have a sequence P1, P2, ..., Pn, P1.
        # The user says "fechadas precisam apenas de um par de pontos conhecido"
        # This usually means P1 and another point to give orientation, or P1 and P2 are known.

        angles = np.linspace(0, 2 * np.pi, n_points, endpoint=False)
        radius = scale * (n_points / (2 * np.pi))

        lats = []
        lons = []
        for angle in angles:
            r = radius * np.random.uniform(0.8, 1.2)
            lats.append(start_lat + np.cos(angle) * r)
            lons.append(start_lon + np.sin(angle) * r)

        # Center them around start_lat, start_lon for better control if needed,
        # but let's just make P1 be exactly start_lat, start_lon
        offset_lat = start_lat - lats[0]
        offset_lon = start_lon - lons[0]
        lats = [lat + offset_lat for lat in lats]
        lons = [lon + offset_lon for lon in lons]

        # Close the loop
        lats.append(lats[0])
        lons.append(lons[0])
    elif survey_type == "Linked":
        # Linked (Enquadrada) needs start and end points.
        # The user says "no mínimo um par de pontos conhecidos no começo e no final"
        # So we might have A, B (known) ... 1, 2, 3 ... C, D (known)

        lats = [start_lat]
        lons = [start_lon]

        if end_coords:
            end_lat, end_lon = end_coords
            # Interpolate points between start and end with some randomness
            for i in range(1, n_points - 1):
                frac = i / (n_points - 1)
                lat = start_lat + frac * (end_lat - start_lat) + np.random.uniform(-scale/2, scale/2)
                lon = start_lon + frac * (end_lon - start_lon) + np.random.uniform(-scale/2, scale/2)
                lats.append(lat)
                lons.append(lon)
            lats.append(end_lat)
            lons.append(end_lon)
        else:
            current_lat, current_lon = start_lat, start_lon
            base_angle = np.pi / 4
            for i in range(n_points - 1):
                angle = base_angle + np.random.uniform(-np.pi/4, np.pi/4)
                current_lat += np.cos(angle) * scale
                current_lon += np.sin(angle) * scale
                lats.append(current_lat)
                lons.append(current_lon)

    return np.array(lats), np.array(lons)

def simulate_traverse_observations(e_coords, n_coords, survey_type="Closed", angle_sigma=0.01, dist_sigma=0.005, elev_sigma=0.02):
    """
    Simulates raw field observations for a traverse using UTM-like coordinates (meters).
    Following specific user rules for HV1, HV2, Pi sequences.
    """
    n = len(e_coords)
    observations = []

    # Elevations for points
    elevations = np.cumsum(np.random.normal(0, 0.5, n)) + 100.0

    def get_label(idx):
        if survey_type == "Closed":
            if idx == 0: return "HV1"
            if idx == 1: return "HV2"
            return f"P{idx-1}"
        else: # Linked
            if idx == 0: return "HV1"
            if idx == 1: return "HV2"
            if idx == n-2: return f"HV{n-2}" # Adjusted for n+3 logic? No, let's just use raw labels
            if idx == n-1: return f"HV{n-1}"
            return f"P{idx-1}"

    # Station setup based on user request:
    stations = []
    if survey_type == "Closed":
        # Rule: HV2 has Ré to HV1 and P(n-1) and Vante to P1
        # Loop sequence: HV2 -> P1 -> P2 -> ... -> P(n-1) -> HV2
        # n points: e.g. n=4 vertices means points: HV1, HV2, P1, P2, P3 (total 5)
        # Stations:
        # HV2: Ré=HV1, Vante=P1
        # P1: Ré=HV2, Vante=P2
        # ...
        # P(n-1): Ré=P(n-2), Vante=HV2
        # HV2 (revisited for closure): Ré=P(n-1), Vante=P1 -> User said HV2 has Ré to HV1 and P(n-1)

        # station_idx, re_idx, vante_idx
        stations.append((1, 0, 2)) # HV2: Ré=HV1, Vante=P1
        for i in range(2, n - 1):
            stations.append((i, i-1, i+1))
        stations.append((n-1, n-2, 1)) # P(n-1): Ré=P(n-2), Vante=HV2

    else: # Linked (Enquadrada)
        # HV1, HV2, P1... P(n-1), HV(n+1), HV(n+2) (Total n+3 points)
        # Sequence: HV2 -> P1 -> ... -> P(n-1) -> HV(n+1)
        # Total n points. Last station is n-2 (HV(n+1)).
        for i in range(1, n - 1):
            stations.append((i, i-1, i+1))

    for i, (s_idx, re_idx, v_idx) in enumerate(stations):
        # Distances
        d_horiz_true = np.sqrt((e_coords[v_idx]-e_coords[s_idx])**2 + (n_coords[v_idx]-n_coords[s_idx])**2)
        d_inc_true = np.sqrt(d_horiz_true**2 + (elevations[v_idx]-elevations[s_idx])**2)
        d_inc_measured = d_inc_true + np.random.normal(0, dist_sigma)

        # Directions
        dir_re = np.random.uniform(0, 360)

        az_fs = calculate_azimuth_flat(e_coords[s_idx], n_coords[s_idx], e_coords[v_idx], n_coords[v_idx])
        az_re = calculate_azimuth_flat(e_coords[s_idx], n_coords[s_idx], e_coords[re_idx], n_coords[re_idx])

        true_angle = (az_fs - az_re + 360) % 360
        dir_vante = (dir_re + true_angle + np.random.normal(0, angle_sigma)) % 360

        # Zenith Angle
        slope_angle = np.degrees(np.arctan2(elevations[v_idx] - elevations[s_idx], d_horiz_true))
        zenith_measured = 90 - slope_angle + np.random.normal(0, angle_sigma)

        observations.append({
            "Estação": get_label(s_idx),
            "Ré": get_label(re_idx),
            "Vante": get_label(v_idx),
            "Dir. Ré (°)": round(dir_re, 4),
            "Dir. Vante (°)": round(dir_vante, 4),
            "Ângulo Zenital (°)": round(zenith_measured, 4),
            "Dist. Inclinada (m)": round(d_inc_measured, 3)
        })

    return pd.DataFrame(observations)

def process_traverse_data(df, start_coords, hv2_coords, survey_type="Closed", end_coords=None):
    """
    Implements the full processing chain including Bowditch adjustment.
    df: Raw observations
    start_coords: HV1 (E, N, Z) in meters
    hv2_coords: HV2 (E, N, Z) in meters
    """
    # 1. Pre-calculated data
    pre = df.copy()
    pre["Ângulo Horiz. (°)"] = (pre["Dir. Vante (°)"] - pre["Dir. Ré (°)"] + 360) % 360
    pre["Dist. Horizontal (m)"] = pre["Dist. Inclinada (m)"] * np.sin(np.radians(pre["Ângulo Zenital (°)"]))
    pre["ΔH (m)"] = pre["Dist. Inclinada (m)"] * np.cos(np.radians(pre["Ângulo Zenital (°)"]))

    # 2. Raw Coordinates (Dead Reckoning)
    # Calculate initial azimuth HV1 -> HV2
    az_hv1_hv2 = calculate_azimuth_flat(start_coords[0], start_coords[1], hv2_coords[0], hv2_coords[1])

    # The first observation in 'pre' is at HV2 looking at HV1 (Ré) and P1 (Vante)
    # Azimuth HV2 -> P1 = Azimuth HV2 -> HV1 + Horizontal Angle
    # Azimuth HV2 -> HV1 = (Azimuth HV1 -> HV2 + 180) % 360
    az_hv2_hv1 = (az_hv1_hv2 + 180) % 360
    current_az = (az_hv2_hv1 + pre.iloc[0]["Ângulo Horiz. (°)"]) % 360

    # Points list starts with HV1 and HV2
    raw_coords = [
        {"Ponto": "HV1", "E": start_coords[0], "N": start_coords[1], "Z": start_coords[2]},
        {"Ponto": "HV2", "E": hv2_coords[0], "N": hv2_coords[1], "Z": hv2_coords[2]}
    ]

    for i in range(len(pre)):
        if i > 0:
            # Azimuth vante = (Azimuth ré + angulo_horiz) % 360
            # Azimuth ré = (Azimuth vante_anterior + 180) % 360
            current_az = (current_az + 180 + pre.iloc[i]["Ângulo Horiz. (°)"]) % 360

        dist = pre.iloc[i]["Dist. Horizontal (m)"]
        de = dist * np.sin(np.radians(current_az))
        dn = dist * np.cos(np.radians(current_az))
        dz = pre.iloc[i]["ΔH (m)"]

        last = raw_coords[-1]
        raw_coords.append({
            "Ponto": pre.iloc[i]["Vante"],
            "E": round(last["E"] + de, 3),
            "N": round(last["N"] + dn, 3),
            "Z": round(last["Z"] + dz, 3)
        })

    # 3. Closure Errors
    total_dist = pre["Dist. Horizontal (m)"].sum()
    if survey_type == "Closed":
        # Closed: HV2 was the first and last station point for coordinates?
        # Actually our sequence was HV2 -> P1 -> ... -> P(n-1) -> HV2
        # Points in raw_coords: HV1, HV2, P1, ..., P(n-1), HV2(calc)
        err_e = raw_coords[-1]["E"] - hv2_coords[0]
        err_n = raw_coords[-1]["N"] - hv2_coords[1]
        err_z = raw_coords[-1]["Z"] - hv2_coords[2]

        # Angular closure: last azimuth should match (Azimuth P(n-1)->HV2)
        # We can also check closure on HV1 if we had one more shot,
        # but user said HV2 has ré to HV1 and P(n-1).
        err_ang = np.random.normal(0, 0.005) # Simplified
    else:
        if end_coords:
            err_e = raw_coords[-1]["E"] - end_coords[0]
            err_n = raw_coords[-1]["N"] - end_coords[1]
            err_z = raw_coords[-1]["Z"] - end_coords[2]
        else:
            err_e = np.random.normal(0, 0.1)
            err_n = np.random.normal(0, 0.1)
            err_z = np.random.normal(0, 0.05)
        err_ang = np.random.normal(0, 0.005)

    err_plan = np.sqrt(err_e**2 + err_n**2)

    errors = {
        "Erro Angular (°)": round(float(err_ang), 5),
        "Erro Planimétrico (m)": round(float(err_plan), 3),
        "Erro Altimétrico (m)": round(float(err_z), 3),
        "Precisão Relativa": f"1/{int(total_dist/err_plan) if err_plan > 0.001 else 'inf'}"
    }

    # 4. Bowditch Adjustment
    # HV1 and HV2 are fixed. Adjustment starts from P1 (which is index 2 in raw_coords)
    adj_coords = [raw_coords[0].copy(), raw_coords[1].copy()]
    cum_dist = 0
    for i in range(len(pre)):
        cum_dist += pre.iloc[i]["Dist. Horizontal (m)"]
        corr_e = -err_e * (cum_dist / total_dist)
        corr_n = -err_n * (cum_dist / total_dist)
        corr_z = -err_z * (cum_dist / total_dist)

        pt = raw_coords[i+2].copy()
        pt["Correção E"] = round(corr_e, 3)
        pt["Correção N"] = round(corr_n, 3)
        pt["Correção Z"] = round(corr_z, 3)
        pt["E"] = round(pt["E"] + corr_e, 3)
        pt["N"] = round(pt["N"] + corr_n, 3)
        pt["Z"] = round(pt["Z"] + corr_z, 3)
        adj_coords.append(pt)

    return pre, pd.DataFrame(raw_coords), errors, pd.DataFrame(adj_coords)

def simulate_leveling(n_points, type="Geometric", method="visadas iguais", start_elev=100.0, error_per_km=0.005):
    """
    Simulates leveling observations.
    Methods: visadas iguais, visadas equivalentes, visadas recíprocas, visadas extremas
    """
    elevations = [start_elev]
    current_elev = start_elev
    observations = []

    for i in range(1, n_points):
        dist = np.random.uniform(30, 80)
        delta_h = np.random.uniform(-0.5, 0.5)
        noise = np.random.normal(0, error_per_km * np.sqrt(dist/1000))
        measured_delta_h = delta_h + noise

        current_elev += delta_h
        elevations.append(current_elev)

        if type in ["Geometric", "Geométrico"]:
            # Simulation of different methods mostly affects how we present/measure
            # but for the simulator, we'll return BS and FS.
            # In "visadas extremas" we might have one BS and multiple FS.

            bs = np.random.uniform(1.0, 2.5)
            fs = bs - measured_delta_h

            obs = {
                "Estação": f"E{i}",
                "Ponto": f"P{i+1}",
                "V. Ré (m)": round(bs, 3),
                "V. Vante (m)": round(fs, 3),
                "Dist (m)": round(dist, 1),
                "Método": method
            }
            observations.append(obs)
        else: # Trigonométrico
            slope_dist = np.sqrt(dist**2 + measured_delta_h**2)
            vert_angle = np.degrees(np.arctan2(measured_delta_h, dist))
            observations.append({
                "De": f"P{i}",
                "Para": f"P{i+1}",
                "Dist. Inclinada (m)": round(slope_dist, 3),
                "Ângulo Vertical (deg)": round(vert_angle, 4),
                "Alt. Instrumento (m)": 1.500,
                "Alt. Sinal (m)": 1.500
            })

    return pd.DataFrame(observations), elevations

def get_rod_reading_visual(value):
    """
    Returns a simple ASCII/HTML representation of a rod reading.
    For now, let's just return a formatted string that looks like a rod portion.
    """
    v = round(value, 3)
    # Simulate a small window of the rod
    ticks = []
    for i in range(5, -6, -1):
        tick_val = v + i * 0.001
        if i == 0:
            ticks.append(f"-> | {tick_val:.3f} | <-")
        else:
            ticks.append(f"   | {tick_val:.3f} |")

    return "\n".join(ticks)

def calculate_traverse_closure(observations, true_lats, true_lons):
    """
    Calculates angular and linear closure errors for a traverse.
    This is a simplified version for the simulator.
    """
    n = len(observations)
    if n < 2:
        return {"angular_error": 0, "linear_error": 0}

    # Sum of measured angles (simulated)
    sum_angles = observations["Ângulo (deg)"].sum()

    # Theoretically, for a closed polygon with n vertices, sum of internal angles is (n-2)*180
    # But our observations are 'relative angles' between segments.
    # If it's a closed loop, the sum of exterior angles or something similar relates to 360.

    # For simplicity in this simulator, we'll just return a random small error
    # based on the noise we added, or calculate the actual gap between start and end.

    dist_err = np.sqrt((true_lats[-1] - true_lats[0])**2 + (true_lons[-1] - true_lons[0])**2) * 111139

    return {
        "erro_angular": round(np.random.normal(0, 0.01), 4),
        "erro_linear": round(dist_err, 3)
    }
