"""Diagnóstico de conectividad con distintas descargas de la misma fuente FRED."""
import concurrent.futures
import urllib.request
import time
urls = [
 'https://apps.bea.gov/national/Release/XLS/Underlying/Section2All_xls.xlsx',
 'https://markets.newyorkfed.org/api/rates/unsecured/effr/search.json?startDate=2015-01-01&endDate=2026-10-30',
]
def probar(url):
    t=time.monotonic()
    try:
        with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'}),timeout=25) as r:
            b=r.read()
        print(url, 'ok',len(b),round(time.monotonic()-t,1),repr(b[:40]),flush=True)
    except Exception as e: print(url,type(e).__name__,str(e),flush=True)
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as p:list(p.map(probar,urls))
