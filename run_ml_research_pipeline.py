from pathlib import Path
import importlib.util
ROOT=Path(__file__).resolve().parent
def run(rel,func):
 spec=importlib.util.spec_from_file_location(rel.replace("/","_"),ROOT/rel); mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return getattr(mod,func)(ROOT)
print(run("06_ml/calibration.py","run_calibration"))
print(run("06_ml/ensemble.py","run_ensemble"))
