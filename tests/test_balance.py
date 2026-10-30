import datetime as dt
import pathlib
import sys
import unittest
from unittest.mock import patch
import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'pipeline'))
import balance_control as C
import balance_pdf as P

TEXTO = '''Septiembre de 2026
Las Personas Humanas realizaron compras netas de moneda extranjera por USD 3.410 millones.
El balance mostró un superávit de cuenta corriente de USD 1.521 millones.
La cuenta financiera cambiaria resultó deficitaria por USD 3.185 millones.
Los sectores más superavitarios fueron Energía, Alimentos, Bebidas y Tabaco y Minería con USD 1.665 millones, USD 832 millones y USD 715 millones, respectivamente.
Los más deficitarios fueron Industria Automotriz, Comercio e Industria Química, Caucho y Plástico con compras netas por USD 628 millones, USD 534 millones y USD 500 millones, en ese orden.
Oleaginosas y Cereales fue el principal oferente con ventas netas por USD 3.313 millones.
'''


class PDF(unittest.TestCase):
    def test_periodo_signos_y_cifras_del_informe(self):
        r = P.parsear(TEXTO, dt.date(2026, 9, 1))
        self.assertEqual(r['personas'], -3410)
        self.assertEqual(r['comercio'], -534)
        self.assertEqual(r['energia'], 1665)
        self.assertEqual(r['cuenta_financiera'], -3185)

    def test_no_asume_siempre_compras_o_deficit_financiero(self):
        t = TEXTO.replace('compras netas de moneda extranjera', 'ventas netas de moneda extranjera')
        t = t.replace('superávit de cuenta corriente', 'déficit de cuenta corriente').replace('resultó deficitaria', 'resultó superavitaria')
        r = P.parsear(t, dt.date(2026, 9, 1))
        self.assertEqual((r['personas'], r['cuenta_corriente'], r['cuenta_financiera']), (3410, -1521, 3185))

    def test_sectores_pueden_cambiar_de_orden(self):
        t = TEXTO.replace('Energía, Alimentos, Bebidas y Tabaco y Minería', 'Minería, Energía y Alimentos, Bebidas y Tabaco')
        r = P.parsear(t, dt.date(2026, 9, 1))
        self.assertEqual((r['mineria'], r['energia'], r['alimentos']), (1665, 832, 715))

    def test_rechaza_periodo_incorrecto_y_cifras_contradictorias(self):
        with self.assertRaises(ValueError): P.parsear(TEXTO, dt.date(2026, 8, 1))
        t = TEXTO + ' Las Personas Humanas realizaron compras netas de moneda extranjera por USD 9.999 millones.'
        with self.assertRaises(ValueError): P.parsear(t, dt.date(2026, 9, 1))

    def test_no_acepta_una_lista_sectorial_desalineada(self):
        with self.assertRaises(ValueError):
            P.parsear(TEXTO.replace(' y USD 715 millones', ''), dt.date(2026, 9, 1))


class Conciliacion(unittest.TestCase):
    def test_no_acepta_un_total_incorrecto(self):
        d = pd.DataFrame([('2026-09-01', 'total', 12), ('2026-09-01', 'a', 5), ('2026-09-01', 'b', 6)], columns=['fecha', 'variable', 'valor'])
        with patch.dict(C.IDENTIDADES, {'total': ['a', 'b']}, clear=True):
            with self.assertRaises(ValueError): C.conciliar(d)
            d.loc[d.variable.eq('total'), 'valor'] = 11
            self.assertEqual(C.conciliar(d)[0]['diferencia_maxima'], 0)

    def test_no_suma_huecos_como_ceros(self):
        d = pd.DataFrame([('2026-08-01', 'b', 6), ('2026-09-01', 'total', 5), ('2026-09-01', 'a', 5)], columns=['fecha', 'variable', 'valor'])
        with patch.dict(C.IDENTIDADES, {'total': ['a', 'b']}, clear=True):
            with self.assertRaises(ValueError): C.conciliar(d)

    def test_redondeo_no_oculta_diferencias_economicas(self):
        d = pd.DataFrame([('2026-09-01', 'total', 10.01), ('2026-09-01', 'a', 5), ('2026-09-01', 'b', 5)], columns=['fecha', 'variable', 'valor'])
        with patch.dict(C.IDENTIDADES, {'total': ['a', 'b']}, clear=True):
            C.conciliar(d, tolerancia=None)
            d.loc[d.variable.eq('total'), 'valor'] = 10.1
            with self.assertRaises(ValueError): C.conciliar(d, tolerancia=None)

    def test_migracion_fuerza_una_consulta_y_luego_respeta_12_horas(self):
        import run
        ahora = dt.datetime.now(dt.timezone.utc).replace(tzinfo=None).isoformat()
        previo = {'balance_cambiario': {'estado': 'ok', 'ok_utc': ahora}}
        with patch.object(run.F, 'COMPLETO', False):
            self.assertTrue(run.toca('balance_cambiario', previo))
            previo['balance_cambiario']['version_fuente'] = C.VERSION
            self.assertFalse(run.toca('balance_cambiario', previo))
        self.assertEqual(run.FRECUENCIA_H['balance_cambiario'], 12)


if __name__ == '__main__': unittest.main()
