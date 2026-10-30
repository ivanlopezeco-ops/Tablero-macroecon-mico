"""Conciliación de escenarios, ventanas tributarias e integración de reservas."""
import copy
import pathlib
import sys
import unittest

import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "pipeline"))
import bopreal_reservas as B


class BoprealReservas(unittest.TestCase):
    def setUp(self):
        self.reglas, self.bonos = B.cargar()

    def test_conciliacion_octubre(self):
        r = B.calcular("2026-10-30", self.reglas, self.bonos)
        self.assertAlmostEqual(r["capital"], 2022.254429)
        self.assertAlmostEqual(r["intereses"], 227.5807694)
        esperado = [2108.6782975, 2014.5736969, 1920.4690963]
        for e, v in zip(r["escenarios"], esperado):
            self.assertAlmostEqual(e["bopreal"], v)
        self.assertEqual({x["titulo"] for x in r["detalle"] if x["capital_elegible"]}, {"BPOB7"})

    def test_cupon_sale_al_pagarse_y_final_entra_al_horizonte(self):
        r = B.calcular("2026-11-01", self.reglas, self.bonos)
        self.assertIn("2027-11-01", {x["pago"] for x in r["detalle"]})
        r = B.calcular("2026-11-02", self.reglas, self.bonos)
        self.assertNotIn("2026-11-02", {x["pago"] for x in r["detalle"]})
        c = [x for x in r["detalle"] if x["titulo"] == "BPOC7" and x["capital"]]
        self.assertEqual(c[0]["capital_elegible"], 0)
        self.assertGreater(c[1]["capital_elegible"], 0)

    def test_serie4_ventana_y_vencimiento(self):
        r = B.calcular("2027-11-02", self.reglas, self.bonos)
        self.assertEqual({x["titulo"] for x in r["detalle"] if x["capital_elegible"]}, {"BPOA8"})
        self.assertEqual(B.calcular("2028-10-31", self.reglas, self.bonos)["capital"], 0)

    def test_nuevo_stock_no_reescribe_historia_ni_duplica_cancelacion(self):
        nuevo = copy.deepcopy(self.reglas)
        foto = copy.deepcopy(nuevo["stocks"][0])
        foto["fecha"] = "2027-04-30"
        foto["montos"]["BPOB7"] *= 0.5
        nuevo["stocks"].append(foto)
        self.assertEqual(B.calcular("2026-10-30", nuevo, self.bonos), B.calcular("2026-10-30", self.reglas, self.bonos))
        r = B.calcular("2027-04-30", nuevo, self.bonos)
        self.assertFalse(any(x["capital_elegible"] for x in r["detalle"] if x["titulo"] == "BPOB7"))
        with self.assertRaises(ValueError):
            B.calcular("2026-10-19", self.reglas, self.bonos)

    def test_integracion_idempotente_historia_e_identidad(self):
        filas = []
        for f in ["2026-10-19", "2026-10-28"]:
            for v, n in [("res_bopreal_1a", 1444), ("reservas_netas", 12000), ("res_dep_tesoro", 1000), ("reservas_super_netas", 9556)]:
                filas.append({"fecha": f, "variable": v, "valor": float(n), "unidad": "USD M", "fuente": "previa"})
        original = pd.DataFrame(filas)
        r = B.aplicar(original, self.reglas, self.bonos)
        pd.testing.assert_frame_equal(r, B.aplicar(r, self.reglas, self.bonos))
        pd.testing.assert_frame_equal(original.iloc[:4], r.iloc[:4])
        actual = r[r.fecha.eq("2026-10-28")].set_index("variable").valor
        self.assertAlmostEqual(actual.reservas_super_netas, actual.reservas_netas - actual.res_dep_tesoro - actual.res_bopreal_1a)
        self.assertAlmostEqual(actual.res_bopreal_1a, actual.res_bopreal_esc_50)


if __name__ == "__main__":
    unittest.main()
