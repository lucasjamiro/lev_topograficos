import unittest
import pandas as pd
import numpy as np
import simulator

class TestFormatting(unittest.TestCase):

    def test_format_num_locale_and_precision(self):
        # Thousands and decimal separators
        val1 = 1234567.8901234
        self.assertEqual(simulator.format_num(val1, 7), "1.234.567,8901234")

        # Angle (7 decimals)
        val_angle = 123.456789012
        self.assertEqual(simulator.format_num(val_angle, 7), "123,4567890")

        # Distance (4 decimals)
        val_dist = 1234.56789
        self.assertEqual(simulator.format_num(val_dist, 4), "1.234,5679")

        # Increment (5 decimals)
        val_inc = 0.00123456
        self.assertEqual(simulator.format_num(val_inc, 5), "0,00123")

        # Coordinate (3 decimals)
        val_coord = 677878.5164
        self.assertEqual(simulator.format_num(val_coord, 3), "677.878,516")

        # Negative values
        self.assertEqual(simulator.format_num(-1234.56, 3), "-1.234,560")

        # Zero
        self.assertEqual(simulator.format_num(0.0, 3), "0,000")

        # NaNs and None
        self.assertEqual(simulator.format_num(None, 3), "")
        self.assertEqual(simulator.format_num(np.nan, 3), "")

        # Non-numeric string
        self.assertEqual(simulator.format_num("HV1", 3), "HV1")

    def test_format_df_for_display(self):
        df = pd.DataFrame({
            "Ponto": ["P1"],
            "Dir. Ré (°)": [12.34567891],       # Angle -> 7 decimals
            "Dist. Inclinada (m)": [123.456789], # Distance -> 4 decimals
            "ΔH (m)": [0.0012345],              # Increment -> 5 decimals
            "E": [677878.516],                  # Coordinate -> 3 decimals
            "N": [7184223.309]                  # Coordinate -> 3 decimals
        })

        formatted = simulator.format_df_for_display(df)

        self.assertEqual(formatted.iloc[0]["Ponto"], "P1")
        self.assertEqual(formatted.iloc[0]["Dir. Ré (°)"], "12,3456789")
        self.assertEqual(formatted.iloc[0]["Dist. Inclinada (m)"], "123,4568")
        self.assertEqual(formatted.iloc[0]["ΔH (m)"], "0,00123")
        self.assertEqual(formatted.iloc[0]["E"], "677.878,516")
        self.assertEqual(formatted.iloc[0]["N"], "7.184.223,309")

    def test_process_traverse_data_formatting_and_precision(self):
        e_coords = np.array([0, 100, 200, 300, 400, 500, 600], dtype=float)
        n_coords = np.array([0, 0, 100, 0, 100, 0, 0], dtype=float)
        obs = simulator.simulate_traverse_observations(e_coords, n_coords, survey_type="Linked")

        start_coords = (0, 0, 100.0)
        hv2_coords = (100, 0, 100.0)
        end_coords_start = (500, 0, 100.0)
        end_coords_end = (600, 0, 100.0)

        pre, az_df, raw_df, errors, adj_df = simulator.process_traverse_data(
            obs, start_coords, hv2_coords, survey_type="Linked",
            end_coords_start=end_coords_start, end_coords_end=end_coords_end
        )

        formatted_pre = simulator.format_df_for_display(pre)
        formatted_az = simulator.format_df_for_display(az_df)
        formatted_adj = simulator.format_df_for_display(adj_df)

        # Check precision format in columns
        # Angle column in pre has 7 decimals and comma
        sample_angle_str = formatted_pre.iloc[0]["Ângulo Horiz. (°)"]
        self.assertIn(",", sample_angle_str)
        self.assertEqual(len(sample_angle_str.split(",")[1]), 7)

        # Distance column in pre has 4 decimals and comma
        sample_dist_str = formatted_pre.iloc[0]["Dist. Horizontal (m)"]
        self.assertIn(",", sample_dist_str)
        self.assertEqual(len(sample_dist_str.split(",")[1]), 4)

        # ΔH column in pre has 5 decimals and comma
        sample_dh_str = formatted_pre.iloc[0]["ΔH (m)"]
        self.assertIn(",", sample_dh_str)
        self.assertEqual(len(sample_dh_str.split(",")[1]), 5)

        # Correção E in adj has 5 decimals
        sample_corre_str = formatted_adj.iloc[0]["Correção E"]
        self.assertIn(",", sample_corre_str)
        self.assertEqual(len(sample_corre_str.split(",")[1]), 5)

        # E in adj has 3 decimals and dot thousands
        sample_e_str = formatted_adj.iloc[0]["E"]
        self.assertIn(",", sample_e_str)
        self.assertEqual(len(sample_e_str.split(",")[1]), 3)

if __name__ == "__main__":
    unittest.main()
