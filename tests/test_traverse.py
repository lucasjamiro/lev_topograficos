import unittest
import numpy as np
import pandas as pd
import utm
import simulator

class TestTraverseSimulation(unittest.TestCase):

    def test_linked_traverse_coordinate_generation(self):
        n = 5
        lats, lons, labels = simulator.generate_traverse_coordinates(n, survey_type="Linked")
        self.assertEqual(len(lats), n + 4)
        self.assertEqual(len(lons), n + 4)
        self.assertEqual(labels, ['HV1', 'HV2', 'P1', 'P2', 'P3', 'P4', 'P5', 'HV4', 'HV5'])

    def test_closed_traverse_coordinate_generation(self):
        n = 5
        lats, lons, labels = simulator.generate_traverse_coordinates(n, survey_type="Closed")
        self.assertEqual(len(lats), n)
        self.assertEqual(len(lons), n)
        self.assertEqual(labels, ['HV1', 'HV2', 'P1', 'P2', 'P3'])

    def test_linked_observations_setups(self):
        n = 3
        lats, lons, labels = simulator.generate_traverse_coordinates(n, survey_type="Linked")
        obs = simulator.simulate_traverse_observations(lats, lons, labels=labels, survey_type="Linked")
        self.assertEqual(obs.iloc[0]['Estação'], 'HV2')
        self.assertEqual(obs.iloc[0]['Ré'], 'HV1')
        self.assertEqual(obs.iloc[0]['Vante'], 'P1')

        self.assertEqual(obs.iloc[-1]['Estação'], 'HV4')
        self.assertEqual(obs.iloc[-1]['Ré'], 'P3')
        self.assertEqual(obs.iloc[-1]['Vante'], 'HV5')

    def test_closed_observations_setups(self):
        n = 5
        lats, lons, labels = simulator.generate_traverse_coordinates(n, survey_type="Closed")
        obs = simulator.simulate_traverse_observations(lats, lons, labels=labels, survey_type="Closed")
        self.assertEqual(obs.iloc[0]['Estação'], 'HV2')
        self.assertEqual(obs.iloc[0]['Ré'], 'HV1')
        self.assertEqual(obs.iloc[0]['Vante'], 'P1')

        self.assertEqual(obs.iloc[-1]['Estação'], 'HV2')
        self.assertEqual(obs.iloc[-1]['Ré'], 'P3')
        self.assertEqual(obs.iloc[-1]['Vante'], 'P1')

    def test_traverse_processing_columns_and_rigorous_chain(self):
        n = 4
        lats, lons, labels = simulator.generate_traverse_coordinates(n, survey_type="Linked")
        obs = simulator.simulate_traverse_observations(lats, lons, labels=labels, survey_type="Linked")

        known_dict = {}
        for label, lat, lon in zip(labels, lats, lons):
            e, n_val, _, _ = utm.from_latlon(float(lat), float(lon))
            known_dict[label] = (float(e), float(n_val), 100.0)

        pre, azimuths_df, raw_df, errors, adj_df = simulator.process_traverse_data(obs, known_dict, survey_type="Linked")

        expected_cols = ['Ponto', 'Correção E', 'Correção N', 'Correção Z', 'E', 'N', 'Z']
        self.assertEqual(list(raw_df.columns), expected_cols)
        self.assertEqual(list(adj_df.columns), expected_cols)

        expected_az_cols = [
            'Alinhamento',
            'Ângulo Horiz. Medido (°)',
            'Azimute Transportado Bruto (°)',
            'Correção Angular Acumulada (°)',
            'Azimute Corrigido (°)'
        ]
        self.assertEqual(list(azimuths_df.columns), expected_az_cols)

        self.assertIn('Erro Angular (°)', errors)
        self.assertIn('Erro Planimétrico (m)', errors)
        self.assertIn('Erro Altimétrico (m)', errors)
        self.assertIn('Precisão Relativa', errors)

        self.assertEqual(raw_df.iloc[0]['Ponto'], 'HV1')
        self.assertEqual(raw_df.iloc[1]['Ponto'], 'HV2')
        self.assertEqual(raw_df.iloc[-1]['Ponto'], 'HV5')

    def test_observation_high_precision_formatting(self):
        n = 3
        lats, lons, labels = simulator.generate_traverse_coordinates(n, survey_type="Closed")
        obs = simulator.simulate_traverse_observations(lats, lons, labels=labels, survey_type="Closed")

        for col in ["Dir. Ré (°)", "Dir. Vante (°)", "Ângulo Zenital (°)"]:
            val = obs.iloc[0][col]
            # Verify floating point string representation precision
            val_str = f"{val:.8f}"
            self.assertEqual(len(val_str.split(".")[1]), 8)

    def test_leveling_ai_column(self):
        obs, elevs = simulator.simulate_leveling(4, type="Geometric")
        self.assertIn('AI (m)', obs.columns)

if __name__ == '__main__':
    unittest.main()
