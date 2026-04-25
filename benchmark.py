"""
main_v4 ve main_v5_paralel karsilastirmali zamanlama.
Her versiyon ayri subprocess'te calistirilir; birbirini etkilemez.

Kullanim:
    python benchmark.py
"""

import subprocess
import sys
import time

PYTHON = sys.executable


def run_and_time(script: str) -> float:
    """Verilen scripti calistirir ve gecen sureyi saniye cinsinden dondurur."""
    wrapper = f"""
import time, io, matplotlib
matplotlib.use('Agg')   # headless: TkAgg yerine goruntu olmayan backend
from contextlib import redirect_stdout
import {script} as mod

# Excel kaydetmeyi atla (benchmark icin dosya yazma gerekmez)
mod.kaydet_excel = lambda *a, **kw: None

# Rastgele 10 VR islenmesi icin load_virtual_requests monkey-patch
import random as _rnd
_orig = mod.load_virtual_requests
def _load_on():
    reqs, fnames = _orig()
    combined = list(zip(reqs, fnames))
    secilen = _rnd.sample(combined, min(10, len(combined)))
    r, f = zip(*secilen)
    return list(r), list(f)
mod.load_virtual_requests = _load_on

buf = io.StringIO()
t0 = time.perf_counter()
with redirect_stdout(buf):
    mod.main()
elapsed = time.perf_counter() - t0
print(f"SURE={{elapsed:.2f}}")
"""
    import os
    env = os.environ.copy()
    env["MPLBACKEND"] = "Agg"  # TkAgg gerektirmeyen headless backend

    t_wall = time.perf_counter()
    result = subprocess.run(
        [PYTHON, "-c", wrapper],
        capture_output=True,
        text=True,
        cwd=".",
        env=env,
    )
    elapsed_wall = time.perf_counter() - t_wall

    # Script icinden gelen sure satirini yakala
    for line in result.stdout.splitlines():
        if line.startswith("SURE="):
            return float(line.split("=")[1])

    # Hata varsa stderr'i goster
    if result.returncode != 0:
        print(f"\n[{script}] HATA:\n{result.stderr[-2000:]}")

    return elapsed_wall


print("=" * 60)
print("  ZAMANLAMA KARSILASTIRMASI")
print("=" * 60)

print("\n[1/2] main_v4 calistiriliyor...")
t_v4 = run_and_time("main_v4")
print(f"  main_v4        : {t_v4:.2f} s")

print("\n[2/2] main_v5_paralel calistiriliyor...")
t_v5 = run_and_time("main_v5_paralel")
print(f"  main_v5_paralel: {t_v5:.2f} s")

print("\n" + "=" * 60)
if t_v4 > 0 and t_v5 > 0:
    hizlanma = t_v4 / t_v5
    fark     = t_v4 - t_v5
    print(f"  v4 suresi      : {t_v4:.2f} s")
    print(f"  v5 suresi      : {t_v5:.2f} s")
    print(f"  Kazanim        : {fark:.2f} s daha hizli  ({hizlanma:.2f}x)")
print("=" * 60)
