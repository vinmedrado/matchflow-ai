from __future__ import annotations

import importlib


def main() -> int:
    module = importlib.import_module("07_data_ops.run_data_ops")
    return module.main()


if __name__ == "__main__":
    raise SystemExit(main())
