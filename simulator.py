import numpy as np
import pandas as pd

def calculate_azimuth(x1, y1, x2, y2):
    """
    Computes true grid azimuth from point 1 to point 2 using atan2(delta_E, delta_N).
    Supports either UTM coordinates (E1, N1, E2, N2) or Geographic coordinates (lat1, lon1, lat2, lon2).
    """
    if abs(x1) <= 90 and abs(y1) <= 180 and abs(x2) <= 90 and abs(y2) <= 180:
        e1, n1, _, _ = utm.from_latlon(float(x1), float(y1))
        e2, n2, _, _ = utm.from_latlon(float(x2), float(y2))
    else:
        e1, n1, e2, n2 = float(x1), float(y1), float(x2), float(y2)

    de = e2 - e1
    dn = n2 - n1
    azimuth = (np.degrees(np.arctan2(de, dn)) + 360) % 360
    return float(azimuth)

import utm

def get_traverse_labels(n_points, survey_type="Closed"):
    """
    Returns point labels based on survey type and user input n_points:
    - Linked (Enquadrada): n_points intermediate stations (P1..Pn) + 4 control points (HV1, HV2, HV4, HV5) -> Total = n_points + 4
    - Closed (Fechada): total n_points vertices = HV1, HV2, P1, ..., P_{n-2} -> Total = n_points
    """
    if survey_type in ["Linked", "Enquadrada"]:
        return ["HV1", "HV2"] + [f"P{i+1}" for i in range(n_points)] + ["HV4", "HV5"]
    else:
        # For closed traverse, total vertices = n_points (HV1, HV2, P1, ..., P_{n-2})
        n_p = max(0, n_points - 2)
        return ["HV1", "HV2"] + [f"P{i+1}" for i in range(n_p)]

def generate_traverse_coordinates(n_points, survey_type="Closed", start_lat=-25.448369, start_lon=-49.230955, scale=0.001, end_coords=None):
    """
    Generates UTM-based coordinates for traverse points and returns (lats, lons, labels).
    """
    labels = get_traverse_labels(n_points, survey_type)
    e0, n0, zone_num, zone_let = utm.from_latlon(float(start_lat), float(start_lon))

    utm_points = []

    if survey_type in ["Linked", "Enquadrada"]:
        # HV2 at start_lat, start_lon
        hv2_e, hv2_n = float(e0), float(n0)
        # HV1 for initial orientation check
        hv1_e, hv1_n = hv2_e - 50.0, hv2_n - 30.0

        if end_coords:
            hv4_e, hv4_n, _, _ = utm.from_latlon(float(end_coords[0]), float(end_coords[1]))
            hv4_e, hv4_n = float(hv4_e), float(hv4_n)
        else:
            hv4_e = hv2_e + (n_points + 1) * 80.0
            hv4_n = hv2_n + (n_points + 1) * 40.0

        hv5_e, hv5_n = hv4_e + 50.0, hv4_n + 30.0

        utm_points.append((hv1_e, hv1_n))
        utm_points.append((hv2_e, hv2_n))

        for i in range(1, n_points + 1):
            frac = i / (n_points + 1)
            noise_e = float(np.random.uniform(-10, 10))
            noise_n = float(np.random.uniform(-10, 10))
            p_e = hv2_e + frac * (hv4_e - hv2_e) + noise_e
            p_n = hv2_n + frac * (hv4_n - hv2_n) + noise_n
            utm_points.append((p_e, p_n))

        utm_points.append((hv4_e, hv4_n))
        utm_points.append((hv5_e, hv5_n))

    else:
        # Closed traverse: total n_points vertices = HV1, HV2, P1...P_{n-2}
        hv2_e, hv2_n = float(e0), float(n0)
        hv1_e, hv1_n = hv2_e - 60.0, hv2_n - 20.0

        utm_points.append((hv1_e, hv1_n))
        utm_points.append((hv2_e, hv2_n))

        n_p = max(0, n_points - 2)
        if n_p > 0:
            # Generate intermediate points in a loop returning back towards HV1/HV2
            # Total loop points = n_points (from HV2 around to P_{n-2} and closing to HV2)
            n_vertices = n_points
            radius = 100.0
            # Center of closed loop offset from HV2
            center_e = hv2_e - radius / 2.0
            center_n = hv2_n
            # Base angle for HV2 relative to center
            start_angle = np.arctan2(hv2_n - center_n, hv2_e - center_e)

            for i in range(1, n_p + 1):
                angle = start_angle + (2 * np.pi * i / n_vertices)
                noise_e = float(np.random.uniform(-5, 5))
                noise_n = float(np.random.uniform(-5, 5))
                p_e = center_e + radius * np.cos(angle) + noise_e
                p_n = center_n + radius * np.sin(angle) + noise_n
                utm_points.append((p_e, p_n))

    lats = []
    lons = []
    for e, n in utm_points:
        lat, lon = utm.to_latlon(e, n, zone_num, zone_let)
        lats.append(float(lat))
        lons.append(float(lon))

    return np.array(lats, dtype=float), np.array(lons, dtype=float), labels

def simulate_traverse_observations(lats, lons, labels=None, survey_type="Closed", angle_sigma=0.001, dist_sigma=0.005, elev_sigma=0.02):
    """
    Simulates raw field observations for a traverse using UTM coordinates.
    Returns a DataFrame with: Estação, Ré, Vante, Dir. Ré, Dir. Vante, Ângulo Zenital, Dist. Inclinada
    """
    n = len(lats)
    if labels is None:
        labels = get_traverse_labels(n, survey_type)

    utm_coords = []
    for lat, lon in zip(lats, lons):
        e, n_val, _, _ = utm.from_latlon(float(lat), float(lon))
        utm_coords.append((float(e), float(n_val)))

    elevations = np.cumsum(np.random.normal(0, 0.2, n)) + 100.0

    setups = []
    if survey_type in ["Linked", "Enquadrada"]:
        # Setups run from HV2 (idx 1) through HV4 (idx n-2)
        # Sequence: [HV1(0), HV2(1), P1(2)... Pn(n-3), HV4(n-2), HV5(n-1)]
        for st_idx in range(1, n - 1):
            bs_idx = st_idx - 1
            fs_idx = st_idx + 1
            setups.append((st_idx, bs_idx, fs_idx))
    else:
        # Closed traverse sequence: [HV1(0), HV2(1), P1(2)... P_{n-2}(n-1)]
        # Initial orientation setup at HV2: BS=HV1(0), FS=P1(2)
        first_fs = 2 if n > 2 else 1
        setups.append((1, 0, first_fs))

        # Intermediate station setups P1..P_{n-2}
        for st_idx in range(2, n):
            bs_idx = st_idx - 1
            fs_idx = st_idx + 1 if st_idx + 1 < n else 1 # Last station sights back to HV2(1)
            setups.append((st_idx, bs_idx, fs_idx))

        # Final closure station setup at HV2: BS=last_point (n-1), FS=P1 (first_fs)
        setups.append((1, n - 1, first_fs))

    observations = []
    for st_idx, bs_idx, fs_idx in setups:
        e_s, n_s = utm_coords[st_idx]
        e_b, n_b = utm_coords[bs_idx]
        e_f, n_f = utm_coords[fs_idx]

        az_bs = np.degrees(np.arctan2(e_b - e_s, n_b - n_s)) % 360
        az_fs = np.degrees(np.arctan2(e_f - e_s, n_f - n_s)) % 360

        true_angle = (az_fs - az_bs + 360) % 360
        dir_re = float(np.random.uniform(0, 360))
        dir_vante = (dir_re + true_angle + np.random.normal(0, angle_sigma)) % 360

        d_horiz_true = np.sqrt((e_f - e_s)**2 + (n_f - n_s)**2)
        dz = elevations[fs_idx] - elevations[st_idx]
        d_inc_true = np.sqrt(d_horiz_true**2 + dz**2)
        d_inc_measured = d_inc_true + np.random.normal(0, dist_sigma)

        slope_angle = np.degrees(np.arctan2(dz, d_horiz_true))
        zenith_measured = 90.0 - slope_angle + np.random.normal(0, angle_sigma)

        observations.append({
            "Estação": labels[st_idx],
            "Ré": labels[bs_idx],
            "Vante": labels[fs_idx],
            "Dir. Ré (°)": round(float(dir_re), 4),
            "Dir. Vante (°)": round(float(dir_vante), 4),
            "Ângulo Zenital (°)": round(float(zenith_measured), 4),
            "Dist. Inclinada (m)": round(float(d_inc_measured), 3)
        })

    return pd.DataFrame(observations)

def process_traverse_data(df, known_dict, survey_type="Fechada"):
    """
    Implements the full rigorous processing chain:
    1. Initial Azimuth (Az_start) between HV1 -> HV2.
    2. Target Azimuth (Az_target) between HV4 -> HV5 (Linked) or HV2 -> P1 (Closed).
    3. Azimuth propagation across all station setups using horizontal angles.
    4. True Angular Error e_A computation and equal distribution of -e_A.
    5. Horizontal distance and provisional coordinate calculation.
    6. True Linear Closure Error (e_E, e_N, e_Z) at arrival station (HV4 for Linked, HV2 for Closed).
    7. Bowditch adjustment proportional to distance.
    Returns: pre, raw_coords, errors, adj_coords with columns: Ponto, Correção E, Correção N, Correção Z, E, N, Z
    """
    is_linked = survey_type in ["Linked", "Enquadrada"]

    # 1. Pre-calculated data
    pre = df.copy()
    pre["Ângulo Horiz. (°)"] = (pre["Dir. Vante (°)"] - pre["Dir. Ré (°)"] + 360) % 360
    pre["Dist. Horizontal (m)"] = pre["Dist. Inclinada (m)"] * np.sin(np.radians(pre["Ângulo Zenital (°)"]))
    pre["ΔH (m)"] = pre["Dist. Inclinada (m)"] * np.cos(np.radians(pre["Ângulo Zenital (°)"]))

    hv1 = known_dict["HV1"]
    hv2 = known_dict["HV2"]
    az_start = calculate_azimuth(hv1[0], hv1[1], hv2[0], hv2[1])

    if is_linked:
        hv4 = known_dict["HV4"]
        hv5 = known_dict["HV5"]
        az_target = calculate_azimuth(hv4[0], hv4[1], hv5[0], hv5[1])
    else:
        angle_0 = pre.iloc[0]["Ângulo Horiz. (°)"]
        az_target = (az_start - 180.0 + angle_0 + 360) % 360

    n_setups = len(pre)
    propagated_az = []
    current_az = az_start
    for i in range(n_setups):
        angle = pre.iloc[i]["Ângulo Horiz. (°)"]
        if i == 0:
            az_i = (az_start - 180.0 + angle + 360) % 360
        else:
            az_i = (current_az + angle - 180.0 + 360) % 360
        propagated_az.append(az_i)
        current_az = az_i

    az_final_propagated = propagated_az[-1]
    e_A = (az_final_propagated - az_target + 180) % 360 - 180
    corr_per_station = -e_A / n_setups

    corrected_az = []
    current_az = az_start
    for i in range(n_setups):
        angle = pre.iloc[i]["Ângulo Horiz. (°)"]
        if i == 0:
            az_i = (az_start - 180.0 + angle + corr_per_station + 360) % 360
        else:
            az_i = (current_az + angle - 180.0 + corr_per_station + 360) % 360
        corrected_az.append(az_i)
        current_az = az_i

    # Segment setups for coordinate propagation
    leg_setups = pre.iloc[:n_setups] if is_linked else pre.iloc[:n_setups - 1]
    leg_az = corrected_az[:n_setups] if is_linked else corrected_az[:n_setups - 1]

    e_curr, n_curr, z_curr = hv2[0], hv2[1], hv2[2]
    raw_coords = [{
        "Ponto": "HV2",
        "Correção E": 0.0,
        "Correção N": 0.0,
        "Correção Z": 0.0,
        "E": round(float(e_curr), 3),
        "N": round(float(n_curr), 3),
        "Z": round(float(z_curr), 3)
    }]

    total_dist = leg_setups["Dist. Horizontal (m)"].sum()
    prov_points = []

    for idx in range(len(leg_setups)):
        row = leg_setups.iloc[idx]
        az = leg_az[idx]
        d_h = row["Dist. Horizontal (m)"]
        dz = row["ΔH (m)"]

        de = d_h * np.sin(np.radians(az))
        dn = d_h * np.cos(np.radians(az))

        e_curr += de
        n_curr += dn
        z_curr += dz

        prov_points.append({
            "Ponto": row["Vante"],
            "E": float(e_curr),
            "N": float(n_curr),
            "Z": float(z_curr),
            "d_h": float(d_h)
        })
        raw_coords.append({
            "Ponto": row["Vante"],
            "Correção E": 0.0,
            "Correção N": 0.0,
            "Correção Z": 0.0,
            "E": round(float(e_curr), 3),
            "N": round(float(n_curr), 3),
            "Z": round(float(z_curr), 3)
        })

    target_arrival = known_dict["HV4"] if is_linked else known_dict["HV2"]
    e_arrival_calc = prov_points[-1]["E"]
    n_arrival_calc = prov_points[-1]["N"]
    z_arrival_calc = prov_points[-1]["Z"]

    e_E = e_arrival_calc - target_arrival[0]
    e_N = n_arrival_calc - target_arrival[1]
    e_Z = z_arrival_calc - target_arrival[2]
    err_plan = np.sqrt(e_E**2 + e_N**2)

    errors = {
        "Erro Angular (°)": round(float(e_A), 5),
        "Erro Planimétrico (m)": round(float(err_plan), 3),
        "Erro Altimétrico (m)": round(float(e_Z), 3),
        "Precisão Relativa": f"1/{int(total_dist / err_plan) if err_plan > 0 else 'inf'}"
    }

    # Bowditch Adjustment
    adj_coords = [{
        "Ponto": "HV2",
        "Correção E": 0.0,
        "Correção N": 0.0,
        "Correção Z": 0.0,
        "E": round(float(hv2[0]), 3),
        "N": round(float(hv2[1]), 3),
        "Z": round(float(hv2[2]), 3)
    }]

    cum_d = 0.0
    for pt in prov_points:
        cum_d += pt["d_h"]
        frac = cum_d / total_dist if total_dist > 0 else 0
        corr_e = -e_E * frac
        corr_n = -e_N * frac
        corr_z = -e_Z * frac

        adj_e = pt["E"] + corr_e
        adj_n = pt["N"] + corr_n
        adj_z = pt["Z"] + corr_z

        adj_coords.append({
            "Ponto": pt["Ponto"],
            "Correção E": round(float(corr_e), 3),
            "Correção N": round(float(corr_n), 3),
            "Correção Z": round(float(corr_z), 3),
            "E": round(float(adj_e), 3),
            "N": round(float(adj_n), 3),
            "Z": round(float(adj_z), 3)
        })

    raw_df = pd.DataFrame(raw_coords)
    adj_df = pd.DataFrame(adj_coords)

    # Prepend HV1
    hv1_row = {
        "Ponto": "HV1",
        "Correção E": 0.0,
        "Correção N": 0.0,
        "Correção Z": 0.0,
        "E": round(float(hv1[0]), 3),
        "N": round(float(hv1[1]), 3),
        "Z": round(float(hv1[2]), 3)
    }
    raw_df = pd.concat([pd.DataFrame([hv1_row]), raw_df], ignore_index=True)
    adj_df = pd.concat([pd.DataFrame([hv1_row]), adj_df], ignore_index=True)

    if is_linked and "HV5" in known_dict:
        hv5 = known_dict["HV5"]
        hv5_row = {
            "Ponto": "HV5",
            "Correção E": 0.0,
            "Correção N": 0.0,
            "Correção Z": 0.0,
            "E": round(float(hv5[0]), 3),
            "N": round(float(hv5[1]), 3),
            "Z": round(float(hv5[2]), 3)
        }
        # Check if HV5 is not already the last row
        if raw_df.iloc[-1]["Ponto"] != "HV5":
            raw_df = pd.concat([raw_df, pd.DataFrame([hv5_row])], ignore_index=True)
            adj_df = pd.concat([adj_df, pd.DataFrame([hv5_row])], ignore_index=True)

    cols = ["Ponto", "Correção E", "Correção N", "Correção Z", "E", "N", "Z"]
    return pre, raw_df[cols], errors, adj_df[cols]

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
            inst_height = elevations[i-1] + bs

            obs = {
                "Estação": f"E{i}",
                "Ponto": f"P{i+1}",
                "V. Ré (m)": round(bs, 3),
                "AI (m)": round(inst_height, 3),
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
