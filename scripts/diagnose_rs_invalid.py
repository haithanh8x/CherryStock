"""Invalid ticker + empty-state behavior check (section 13)."""
from src.calcEngine.levelLadder import build_level_ladder

print("== invalid ticker ==")
try:
    r = build_level_ladder("ZZZZZ")
    print("no error; result:", r)
except Exception as exc:
    print(type(exc).__name__, "-", exc)
