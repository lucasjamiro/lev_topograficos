import numpy as np
import pandas as pd

def generate_traverse_coordinates(n_points, survey_type="Closed", start_lat=-23.5505, start_lon=-46.6333, scale=0.001):
    """
    Generates a set of coordinates for a traverse survey.
    scale: rough distance between points in degrees (approx 100m)
    """
    if survey_type == "Closed":
        # Generate points in a circle/polygon with some randomness
        angles = np.linspace(0, 2 * np.pi, n_points, endpoint=False)
        radius = scale * (n_points / (2 * np.pi))

        lats = []
        lons = []
        for angle in angles:
            r = radius * np.random.uniform(0.8, 1.2)
            lats.append(start_lat + np.cos(angle) * r)
            lons.append(start_lon + np.sin(angle) * r)

        # Close the loop
        lats.append(lats[0])
        lons.append(lons[0])
    else: # Linked or just a line
        lats = [start_lat]
        lons = [start_lon]
        current_lat, current_lon = start_lat, start_lon

        # General direction: North-East
        base_angle = np.pi / 4

        for i in range(n_points - 1):
            angle = base_angle + np.random.uniform(-np.pi/4, np.pi/4)
            current_lat += np.cos(angle) * scale
            current_lon += np.sin(angle) * scale
            lats.append(current_lat)
            lons.append(current_lon)

    return np.array(lats), np.array(lons)

def calculate_azimuth(lat1, lon1, lat2, lon2):
    dlon = lon2 - lon1
    y = np.sin(np.radians(dlon)) * np.cos(np.radians(lat2))
    x = np.cos(np.radians(lat1)) * np.sin(np.radians(lat2)) - \
        np.sin(np.radians(lat1)) * np.cos(np.radians(lat2)) * np.cos(np.radians(dlon))
    azimuth = np.degrees(np.arctan2(y, x))
    return (azimuth + 360) % 360

def simulate_traverse_observations(lats, lons, angle_sigma=0.005, dist_sigma=0.01):
    """
    Simulates field observations: Horizontal Angles and Distances.
    angle_sigma: standard deviation for angles in degrees.
    dist_sigma: standard deviation for distance in relative terms (fraction).
    """
    n = len(lats)
    observations = []

    for i in range(1, n):
        # Distance (approximate in degrees, then "scaled" to meters for simulation)
        dist_deg = np.sqrt((lats[i] - lats[i-1])**2 + (lons[i] - lons[i-1])**2)
        dist_m = dist_deg * 111139 # Rough conversion to meters

        # Add noise to distance
        measured_dist = dist_m * (1 + np.random.normal(0, dist_sigma))

        # Azimuth
        az = calculate_azimuth(lats[i-1], lons[i-1], lats[i], lons[i])

        # In a real survey we measure internal angles, but for simulation
        # providing azimuths or relative angles is fine.
        # Let's simulate "Deflection angles" or "Internal angles"
        # For simplicity, we'll return Azimuth and Distance as typical "processed" observations
        # or simulate the angle between segments.

        if i == 1:
            measured_angle = az # First point uses North or arbitrary ref
        else:
            prev_az = calculate_azimuth(lats[i-2], lons[i-2], lats[i-1], lons[i-1])
            measured_angle = (az - prev_az + 360) % 360

        # Add noise to angle
        measured_angle = (measured_angle + np.random.normal(0, angle_sigma)) % 360

        observations.append({
            "From": f"P{i}",
            "To": f"P{i+1}",
            "Distance (m)": round(measured_dist, 3),
            "Angle (deg)": round(measured_angle, 4)
        })

    return pd.DataFrame(observations)

def simulate_leveling(n_points, type="Geometric", start_elev=100.0, dist_scale=100, error_per_km=0.005):
    """
    Simulates leveling observations.
    """
    elevations = [start_elev]
    current_elev = start_elev

    observations = []

    for i in range(1, n_points):
        dist = np.random.uniform(30, 80) # Distance between stations
        delta_h = np.random.uniform(-2, 2) # Random terrain variation

        # Add noise proportional to sqrt(distance)
        noise = np.random.normal(0, error_per_km * np.sqrt(dist/1000))

        measured_delta_h = delta_h + noise
        current_elev += delta_h
        elevations.append(current_elev)

        if type == "Geometric":
            # Backsight (BS) and Foresight (FS)
            # Typically BS - FS = delta_h
            bs = np.random.uniform(1.0, 2.0)
            fs = bs - measured_delta_h
            observations.append({
                "Station": f"S{i}",
                "BS (m)": round(bs, 3),
                "FS (m)": round(fs, 3),
                "Dist (m)": round(dist, 1)
            })
        else: # Trigonometric
            # Vertical angle and Slope distance
            slope_dist = np.sqrt(dist**2 + measured_delta_h**2)
            vert_angle = np.degrees(np.arctan2(measured_delta_h, dist))
            observations.append({
                "From": f"P{i}",
                "To": f"P{i+1}",
                "Slope Dist (m)": round(slope_dist, 3),
                "Vert Angle (deg)": round(vert_angle, 4),
                "Inst Height (m)": 1.500,
                "Target Height (m)": 1.500
            })

    return pd.DataFrame(observations), elevations
