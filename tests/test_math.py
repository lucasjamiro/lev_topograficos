
import numpy as np
import pandas as pd
import simulator

def test_linked_traverse_math():
    print("Testing Linked Traverse Math...")
    # 5 stations -> 7 points
    # HV1, HV2, P1, P2, P3, HV4, HV5
    # Let's define some true coordinates in UTM
    # HV1 (0,0), HV2 (100,0) -> Azimuth 90
    # P1 (200, 100)
    # P2 (300, 0)
    # P3 (400, 100)
    # HV4 (500, 0), HV5 (600, 0) -> Azimuth 90

    e_coords = np.array([0, 100, 200, 300, 400, 500, 600], dtype=float)
    n_coords = np.array([0, 0, 100, 0, 100, 0, 0], dtype=float)

    # Simulate observations
    obs = simulator.simulate_traverse_observations(e_coords, n_coords, survey_type="Linked", angle_sigma=0.0001, dist_sigma=0.001)
    print("\nSimulated Observations:")
    print(obs)

    # Process
    start_coords = (0, 0, 100.0)
    hv2_coords = (100, 0, 100.0)
    end_coords_start = (500, 0, 100.0)
    end_coords_end = (600, 0, 100.0)

    pre, raw, errors, adj = simulator.process_traverse_data(
        obs, start_coords, hv2_coords, survey_type="Linked",
        end_coords_start=end_coords_start, end_coords_end=end_coords_end
    )

    print("\nErrors:")
    print(errors)

    print("\nAdjusted Coordenates:")
    print(adj[['Ponto', 'E', 'N']])

    # Check if HV4 and HV5 are correct in adjusted list
    # adj columns: Ponto, E, N, H
    hv4_row = adj[adj['Ponto'] == 'HV4'].iloc[0]
    hv5_row = adj[adj['Ponto'] == 'HV5'].iloc[0]

    assert abs(hv4_row['E'] - 500) < 0.1, f"Expected HV4 E=500, got {hv4_row['E']}"
    assert abs(hv4_row['N'] - 0) < 0.1, f"Expected HV4 N=0, got {hv4_row['N']}"
    assert abs(hv5_row['E'] - 600) < 0.1, f"Expected HV5 E=600, got {hv5_row['E']}"
    assert abs(hv5_row['N'] - 0) < 0.1, f"Expected HV5 N=0, got {hv5_row['N']}"

    print("\nLinked Traverse Math Test Passed!")

def test_closed_traverse_math():
    print("\nTesting Closed Traverse Math...")
    # 5 stations -> 5 points
    # HV1, HV2, P1, P2, P3
    # Traverse: HV2 -> P1 -> P2 -> P3 -> HV2
    e_coords = np.array([0, 100, 200, 100, 0], dtype=float)
    n_coords = np.array([0, 0, 100, 200, 100], dtype=float)

    obs = simulator.simulate_traverse_observations(e_coords, n_coords, survey_type="Closed", angle_sigma=0.0001, dist_sigma=0.001)

    start_coords = (0, 0, 100.0)
    hv2_coords = (100, 0, 100.0)

    pre, raw, errors, adj = simulator.process_traverse_data(
        obs, start_coords, hv2_coords, survey_type="Closed"
    )

    print("Errors:")
    print(errors)

    # For closed traverse, the last point in adj should be HV2 again
    last_row = adj.iloc[-1]
    assert last_row['Ponto'] == 'HV2', f"Expected last point HV2, got {last_row['Ponto']}"

    assert abs(last_row['E'] - 100) < 0.1, f"Expected E=100, got {last_row['E']}"
    assert abs(last_row['N'] - 0) < 0.1, f"Expected N=0, got {last_row['N']}"
    print("Closed Traverse Math Test Passed!")

if __name__ == "__main__":
    test_linked_traverse_math()
    test_closed_traverse_math()
