from pathlib import Path
import importlib.util
ROOT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location("test_lab_runner",ROOT/"08_test_lab/test_lab_runner.py")
mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
print(mod.run_test_lab(ROOT))
