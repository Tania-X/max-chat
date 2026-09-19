"""校验 requirements.lock.txt 与 requirements.txt 是否一致。

直接依赖（requirements.txt）被改动后若忘记重新生成锁文件，CI 会在此失败，
避免"声明一套、实际装另一套"的漂移。

用法：
    python backend/scripts/check_requirements_lock.py
"""

import re
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
REQUIREMENTS = BACKEND_DIR / "requirements.txt"
LOCK = BACKEND_DIR / "requirements.lock.txt"

# 形如 name、name[extra1,extra2]，后接 == 版本
_PIN_RE = re.compile(r"^(?P<name>[A-Za-z0-9._-]+)(?:\[[^\]]*\])?==(?P<version>[^\s;]+)")


def _parse_pins(path: Path) -> dict[str, str]:
    pins: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        match = _PIN_RE.match(line)
        if match:
            pins[match.group("name").lower().replace("_", "-")] = match.group("version")
    return pins


def main() -> int:
    if not REQUIREMENTS.exists() or not LOCK.exists():
        print("ERROR: requirements.txt 或 requirements.lock.txt 缺失")
        return 1

    direct = _parse_pins(REQUIREMENTS)
    locked = _parse_pins(LOCK)

    problems: list[str] = []
    for name, version in sorted(direct.items()):
        if name not in locked:
            problems.append(f"{name}=={version} 未出现在锁文件中")
        elif locked[name] != version:
            problems.append(f"{name} 版本不一致：requirements.txt={version}，锁文件={locked[name]}")

    if problems:
        print("ERROR: requirements.lock.txt 与 requirements.txt 不一致：")
        for item in problems:
            print(f"  - {item}")
        print("重新生成：pip freeze --exclude-editable > backend/requirements.lock.txt")
        return 1

    print(f"依赖锁文件一致（{len(direct)} 个直接依赖，锁文件共 {len(locked)} 个包）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
