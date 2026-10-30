"""Contratos de actualización: revisiones, caché, fallas y fechas exactas."""
import datetime as dt
import json
import pathlib
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'pipeline'))
import ipom as I
import ipom_io as IO


def serie():
    return {'ipom_prueba': I.serie('Prueba', '%', 'Oficial', 'https://example.org',
        [[f'2025-{m:02d}-01', float(m)] for m in range(1, 13)], 'Método')}


class Contratos(unittest.TestCase):
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

    def test_fed_conserva_ceros_y_rechaza_limites_cruzados(self):
        with patch.object(I, 'fred', return_value={'DFEDTARL': [['2020-04-01', 0]], 'DFEDTARU': [['2020-04-01', .25]]}):
            self.assertEqual(I.fed()['ipom_fed_piso']['d'][0][1], 0)
        with patch.object(I, 'fred', return_value={'DFEDTARL': [['2020-04-01', .5]], 'DFEDTARU': [['2020-04-01', .25]]}):
            with self.assertRaises(ValueError): I.fed()

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
