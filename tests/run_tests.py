"""Minimal runner for environments without pytest: python tests/run_tests.py"""
import importlib.util
import os
import sys
import time
import traceback
import warnings

here = os.path.dirname(os.path.abspath(__file__))
failed = 0
warnings.simplefilter("ignore")
for fn in sorted(os.listdir(here)):
    if not (fn.startswith("test_") and fn.endswith(".py")):
        continue
    spec = importlib.util.spec_from_file_location(fn[:-3], os.path.join(here, fn))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    for name in [n for n in dir(mod) if n.startswith("test_")]:
        t = time.time()
        try:
            getattr(mod, name)()
            print(f"PASS {name} ({time.time() - t:.1f}s)")
        except Exception:
            failed += 1
            print(f"FAIL {name}")
            traceback.print_exc()
print(f"\n{failed} failed")
sys.exit(1 if failed else 0)
