"""Contratos de actualización: revisiones, caché, fallas y fechas exactas."""
import datetime as dt
import json
import pathlib
import sys
import tempfile
import unittest
import pandas as pd
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'pipeline'))
import ipom as I
import ipom_io as IO


def serie():
    return {'ipom_prueba': I.serie('Prueba', '%', 'Oficial', 'https://example.org',
        [[f'2025-{m:02d}-01', float(m)] for m in range(1, 13)], 'Método')}


class Contratos(unittest.TestCase):
    def test_pce_lee_codigos_general_y_nucleo_no_otro_agregado(self):
        d = pd.DataFrame([[None] * 16 for _ in range(13)], dtype=object)
        d.iloc[0, 0] = 'Table 2.3.4U'; d.iloc[1, 0] = '2017=100; seasonally adjusted'
        for c, mes in enumerate(pd.date_range('2015-01-01', periods=13, freq='MS'), 3):
            d.iloc[7, c] = mes.strftime('%YM%m')
            d.iloc[9, c] = d.iloc[12, c] = 100 + c
            d.iloc[10, c] = 90 + c
            d.iloc[11, c] = 999
        d.iloc[9, 2] = d.iloc[12, 2] = 'DPCERG'
        d.iloc[10, 2] = 'DPCCRG'; d.iloc[11, 2] = 'DPCXRG'
        out = I.parsear_pce(d)
        self.assertEqual(out['ipom_pce_nucleo']['d'][0][1], 93)
        self.assertEqual(len(out['ipom_pce_general_ia']['d']), 1)
        d.iloc[12, 3] = 444
        with self.assertRaises(ValueError): I.parsear_pce(d)

    def test_variacion_requiere_mes_exacto(self):
        filas = [['2024-01-01', 100], ['2024-03-01', 150], ['2025-01-01', 110]]
        self.assertEqual(I.variacion(filas, 1), [])
        self.assertAlmostEqual(I.variacion(filas, 12)[0][1], 10)

    def test_revisiones_validas_y_extension_de_serie(self):
        viejo = serie(); nuevo = serie()
        nuevo['ipom_prueba']['d'][0][1] = 1.5
        nuevo['ipom_prueba']['d'].append(['2026-01-01', 13])
        I.validar(nuevo, viejo, 1)

    def test_truncamiento_duplicados_y_nan_se_rechazan(self):
        for modo in ['truncado', 'duplicado', 'nan', 'futuro', 'hueco']:
            with self.subTest(modo=modo):
                old = serie(); new = serie(); rows = new['ipom_prueba']['d']
                if modo == 'truncado': rows.pop(0)
                if modo == 'duplicado': rows.append(rows[-1])
                if modo == 'nan': rows[-1][1] = float('nan')
                if modo == 'futuro': rows.append(['2099-01-01', 1])
                if modo == 'hueco': rows[3][0] = '2025-04-02'
                with self.assertRaises(ValueError): I.validar(new, old, 1)

    def test_falla_conserva_datos_y_fecha_exito_y_recupera(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(I, 'DATA', pathlib.Path(tmp)):
            with patch.dict(I.FUENTES, {'prueba': (serie, 12, 1)}, clear=True):
                self.assertEqual(I.actualizar()['ipom_prueba']['estado'], 'ok')
                path = pathlib.Path(tmp) / 'ipom.json'
                anterior = json.loads(path.read_text('utf8'))
                def fallar(): raise ValueError('Respuesta inválida')
                with patch.dict(I.FUENTES, {'prueba': (fallar, 12, 1)}, clear=True):
                    estado = I.actualizar(force=True)['ipom_prueba']
                ahora = json.loads(path.read_text('utf8'))
                self.assertEqual(estado['estado'], 'PARCIAL')
                self.assertEqual(ahora['series'], anterior['series'])
                self.assertEqual(estado['ok_utc'], anterior['fuentes']['prueba']['ok_utc'])
                # Una falla se reintenta aun antes de vencer las 12 horas.
                self.assertEqual(I.actualizar()['ipom_prueba']['estado'], 'ok')

    def test_cache_no_consulta_antes_de_vencer(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(I, 'DATA', pathlib.Path(tmp)):
            with patch.dict(I.FUENTES, {'prueba': (serie, 12, 1)}, clear=True): I.actualizar()
            def no_llamar(): self.fail('Se consultó una fuente con caché vigente')
            with patch.dict(I.FUENTES, {'prueba': (no_llamar, 12, 1)}, clear=True):
                estado = I.actualizar()['ipom_prueba']
            self.assertTrue(estado['cache'])
            self.assertEqual(estado['estado'], 'ok')

    def test_inicio_sin_fuente_no_publica_base_incompleta(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(I, 'DATA', pathlib.Path(tmp)):
            def fallar(): raise ValueError('Sin red')
            with patch.dict(I.FUENTES, {'prueba': (fallar, 12, 1)}, clear=True):
                self.assertEqual(I.actualizar()['ipom_prueba']['estado'], 'ERROR')
                with self.assertRaises(ValueError): I.verificar_archivo(pathlib.Path(tmp) / 'ipom.json')

    def test_fed_usa_rango_no_tasa_efectiva_y_no_completa_dias(self):
        raw = {'refRates': [{'type':'EFFR','effectiveDate':'2020-04-03','percentRate':0.05,'targetRateFrom':0,'targetRateTo':.25},
                            {'type':'EFFR','effectiveDate':'2020-04-06','percentRate':0.06,'targetRateFrom':0,'targetRateTo':.25}]}
        out = I.parsear_fed(raw)
        self.assertEqual(out['ipom_fed_piso']['d'], [['2020-04-03', 0], ['2020-04-06', 0]])
        raw['refRates'][0]['targetRateFrom'] = .5
        with self.assertRaises(ValueError): I.parsear_fed(raw)

    def test_migracion_aprobada_reconsulta_y_respalda_historia_previa(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(I, 'DATA', pathlib.Path(tmp)):
            with patch.dict(I.FUENTES, {'fed': (serie, 12, 1)}, clear=True): I.actualizar()
            path = pathlib.Path(tmp) / 'ipom.json'; anterior = json.loads(path.read_text('utf8'))
            anterior['fuentes']['fed']['version_fuente'] = 1
            path.write_text(json.dumps(anterior), encoding='utf8')
            def nueva():
                s = serie(); s['ipom_prueba']['frecuencia'] = 'diaria'
                s['ipom_prueba']['d'] = [[f[:8] + '02', v] for f, v in s['ipom_prueba']['d']]
                return s
            with patch.dict(I.FUENTES, {'fed': (nueva, 12, 1)}, clear=True): estado = I.actualizar()['ipom_fed']
            self.assertEqual(estado['estado'], 'ok')
            self.assertEqual(estado['version_fuente'], 2)
            self.assertTrue((pathlib.Path(tmp) / 'raw/ipom/migracion-fed-v1.json').exists())

    def test_bcra_pagina_todas_las_observaciones(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = []
            for n, filas in enumerate([[{'fecha':'2025-01-02','valor':10}], [{'fecha':'2025-01-03','valor':11}]]):
                p = pathlib.Path(tmp) / f'{n}.json'
                p.write_text(json.dumps({'metadata':{'resultset':{'count':2}},'results':[{'detalle':filas}]}))
                paths.append(p)
            with patch.object(IO, 'descargar', side_effect=paths * 2) as download:
                out = I.tasas_diarias()
            self.assertEqual(len(out['ipom_tasa_adelantos_diaria']['d']), 2)
            self.assertIn('offset=1', download.call_args_list[1].args[0])

    def test_download_fallido_no_reemplaza_crudo_ni_marca_exito(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(IO, 'RAW', pathlib.Path(tmp)):
            p = pathlib.Path(tmp) / 'a.xls'; p.write_bytes(b'valido')
            with patch.object(IO.F, '_get', side_effect=TimeoutError('Red')):
                with self.assertRaises(TimeoutError): IO.descargar('https://example.org', 'a.xls')
            self.assertEqual(p.read_bytes(), b'valido')
            self.assertFalse((pathlib.Path(tmp) / 'a.xls.meta.json').exists())


if __name__ == '__main__': unittest.main()
