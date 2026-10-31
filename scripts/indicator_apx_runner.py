"""Run a mode-specific APX without changing the checked-in AmiBroker project."""
from __future__ import annotations
import re
import tempfile
from pathlib import Path
from xml.etree import ElementTree as ET
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))
from cherrystock.config.settings import settings
from cherrystock.infrastructure.amibroker.windows_adapter import WindowsAmiBrokerAdapter
from scripts.sync_amibroker_indicator_full import DEFAULT_AFL

def export_incremental(csv_path: Path, bars: int) -> None:
    if bars not in (1, 10, 600):
        raise ValueError("Expected 1, 10 or 600 bars")
    source = DEFAULT_AFL.read_text(encoding="utf-8-sig")
    pattern = r'x_exportDays\s*=\s*Param\(\s*"Incremental trading bars"\s*,\s*\d+'
    source, count = re.subn(pattern, f'x_exportDays = Param( "Incremental trading bars", {bars}', source)
    if count != 1 or 'ParamList( "Export mode", "FULL|INCREMENTAL", 1 )' not in source:
        raise RuntimeError("AFL export defaults changed; refusing unverified run")
    original = DEFAULT_AFL.with_suffix(".apx")
    root = ET.parse(original).getroot()
    general = root.find("./General")
    if general is None or general.findtext("ApplyTo") != "2" or general.findtext("RangeType") != "2":
        raise RuntimeError("Unexpected APX ApplyTo/RangeType")
    with tempfile.TemporaryDirectory(prefix="cherrystock_indicator_") as directory:
        afl = Path(directory) / "Export_Indicator.afl"
        apx = afl.with_suffix(".apx")
        afl.write_text(source, encoding="utf-8")
        general.find("FormulaPath").text = str(afl)
        general.find("FormulaContent").text = source
        general.find("RangeAmount").text = str(bars)
        ET.ElementTree(root).write(apx, encoding="utf-8", xml_declaration=True)
        WindowsAmiBrokerAdapter(database_path=settings.amibroker_database_path).run_explore_export(
            formula_path=afl, export_path=csv_path, apply_to=2,
            range_mode=2, range_n=bars, timeout_seconds=3600.0)
