# Local Cross-Check Test Guide — Centralized Theme System

## Purpose

Tài liệu này dành cho local coding agent / developer để cross-check Theme System sau khi pull main.

Phạm vi:
- Theme registry và semantic tokens
- NiceGUI / Quasar
- AG Grid
- Apache ECharts
- lightweight_charts
- R/S Ladder
- standalone web chart
- backward compatibility qua Ults.lstPara.THEME
- startup selection qua CHERRYSTOCK_THEME

Thiết kế tham chiếu:
- docs/architecture/theme.md
- docs/adr/ADR-003-centralized-theme-system.md

## 1. Sync main

~~~powershell
cd C:\Github\CherryStock
git status
git fetch origin
git checkout main
git pull --ff-only origin main
git log -5 --oneline
~~~

Expected:
- working tree sạch trước khi test
- commit merge Theme System xuất hiện trong log

Nếu project dùng virtualenv:

~~~powershell
.\.venv\Scripts\Activate.ps1
python --version
~~~

## 2. Focused automated tests

~~~powershell
python -m pytest tests/test_theme.py -v
~~~

Expected: tất cả PASS.

Contract phải được cover:
1. cherry_dark tồn tại
2. cherry_light tồn tại
3. THEME proxy đổi theo set_theme()
4. invalid theme raise ValueError
5. NiceGUI CSS chứa active tokens
6. cherry_light có is_dark=False
7. AG Grid adapter trả base theme hợp lệ
8. with_alpha() tạo đúng rgba

## 3. R/S regression

~~~powershell
python -m pytest tests/test_rs_ladder.py -v
python -m pytest tests -k "theme or rs or ladder or chart" -v
~~~

Expected:
- R/S tests PASS
- refactor theme không thay đổi ranking, clustering, Reward/Risk business logic

## 4. Import and compatibility checks

~~~powershell
python -c "from src.Presentation.theme import THEME,get_theme_name,get_ag_grid_theme; print(get_theme_name()); print(THEME['background']); print(get_ag_grid_theme())"
~~~

Expected mặc định:
- cherry_dark
- #07111f
- quartz

Compatibility alias:

~~~powershell
python -c "from src.Ults.lstPara import THEME; print(THEME['name'], THEME['primary'])"
~~~

R/S presentation:

~~~powershell
python -c "from src.Chart.levelLadderChart import empty_level_ladder_chart_options; print(empty_level_ladder_chart_options()['title']['textStyle'])"
~~~

Expected: import thành công và presentation color lấy từ active theme.

## 5. Static hard-code scan

~~~powershell
Select-String -Path src\webapp\NiceGUI_chart.py,src\webapp\NiceGUI_grid.py,src\webapp\app.py,src\Chart\levelLadderChart.py,src\Chart\plot.py -Pattern '#[0-9A-Fa-f]{6}'
~~~

Expected:
- không có application theme HEX hard-code trong consumer files

Nếu tìm thấy literal:
- theme semantic => chuyển về Presentation.theme
- data identity thực sự => phải giải thích rõ
- test fixture => có thể chấp nhận nếu cố ý

## 6. Manual UI — cherry_dark

~~~powershell
$env:CHERRYSTOCK_THEME = "cherry_dark"
python src\webapp\NiceGUI_chart.py
~~~

Mở http://localhost:8081

Cross-check:
- body dark
- header/drawer cùng hệ màu
- main text sáng, muted text readable
- card/grid border đồng nhất
- active tab khác inactive tab
- input outlined border đúng theme
- hover không còn legacy color
- metric cards đúng theme
- Intermarket render
- Market Breadth render
- Sector ECharts render
- Cashflow render
- tooltip cashflow readable
- positive/negative/warning đúng semantic token
- AG Grid background/header/odd row/hover/border/text đúng theme

Không được xuất hiện vùng trắng ngoài chủ ý.

## 7. Manual UI — cherry_light

Stop app rồi chạy:

~~~powershell
$env:CHERRYSTOCK_THEME = "cherry_light"
python src\webapp\NiceGUI_chart.py
~~~

Hard refresh bằng Ctrl+F5.

Expected:
- background chuyển light
- surface/card chuyển light
- text chuyển dark
- Quasar không còn ép dark mode
- input/select readable
- header/drawer không giữ hard-coded dark
- AG Grid chuyển đúng
- ECharts axis label readable
- tooltip không dùng nền dark cố định
- lightweight charts đổi background/text
- R/S current-price label readable
- avatar có contrast tốt

Fail nếu bất kỳ vùng lớn nào vẫn giữ cherry_dark do hard-code.

## 8. R/S Ladder visual cross-check

Trong app:
1. Mở tab R/S
2. Ticker = MWG
3. Cluster = 1.0%
4. Click Refresh

Kiểm tra:
- chart render thành công
- Price hiển thị
- Support dùng positive token
- Resistance dùng negative token
- Current Price dùng warning token
- tooltip background theo theme
- grid lines theo border token
- label text theo text/muted token
- Level Details dùng AG Grid theme

Lặp lại cả cherry_dark và cherry_light.

Calculation result không được thay đổi chỉ vì đổi theme.

## 9. lightweight_charts cross-check

Intermarket:
- VNINDEX
- Remaining VNINDEX
- BTC
- SPX
- NDX
- Gold
- Oil
- DXY
- USD/VND

Expected:
- màu lấy từ theme registry
- legend readable
- select/hide legend hoạt động
- hidden state đủ contrast
- selected state rõ ở dark/light

Market Breadth:
- VNINDEX
- MA20
- MA50
- MA100
- MA200

Expected:
- series phân biệt rõ
- light theme không còn text/background dark legacy

## 10. Cashflow chart

Hover cashflow chart.

Expected:
- tooltip background theo theme
- border theo theme
- date/title readable
- institutional/individual/foreign/proprietary colors đúng
- positive number dùng positive
- negative number dùng negative
- zero/empty dùng muted
- crosshair marker nhìn rõ

Test cả dark và light.

## 11. Standalone webapp

~~~powershell
$env:CHERRYSTOCK_THEME = "cherry_dark"
python src\webapp\app.py
~~~

Sau đó test light:

~~~powershell
$env:CHERRYSTOCK_THEME = "cherry_light"
python src\webapp\app.py
~~~

Expected:
- generated page body đổi theme
- chart không giữ background legacy
- error page cũng dùng theme token

## 12. Invalid environment theme

~~~powershell
$env:CHERRYSTOCK_THEME = "invalid_theme"
python -c "import src.Presentation.theme"
~~~

Expected:
- fail rõ ràng
- message có Available themes

Reset:

~~~powershell
Remove-Item Env:CHERRYSTOCK_THEME -ErrorAction SilentlyContinue
~~~

## 13. Cross-session warning

V1 là process-wide startup theme.

Local agent KHÔNG được kết luận V1 hỗ trợ per-user live switching.

set_theme() chỉ ảnh hưởng future renders; DOM/ECharts/iframe đã render cần rebuild hoặc refresh.

Nếu làm live theme selector sau này:
- dùng session-scoped state
- không dùng process-global variable làm user preference
- rerender ECharts
- rebuild iframe/lightweight charts
- tạo ADR mới nếu thay đổi architectural decision

## 14. Full regression suite

~~~powershell
python -m pytest tests -v
~~~

Tối thiểu:

~~~powershell
python -m pytest tests/test_theme.py tests/test_rs_ladder.py -v
~~~

Không được report PASS nếu chỉ review source mà chưa thực thi command.

## 15. Local agent result format

~~~text
Theme Cross-Check Result
========================
Commit tested:
Environment:
Python:
OS:

Automated
---------
tests/test_theme.py: PASS / FAIL
tests/test_rs_ladder.py: PASS / FAIL
related suite: PASS / FAIL / NOT RUN

Static scan
-----------
Hard-coded theme colors found: YES / NO
Files:

Dark UI
-------
App shell: PASS / FAIL
AG Grid: PASS / FAIL
ECharts: PASS / FAIL
lightweight_charts: PASS / FAIL
R/S Ladder: PASS / FAIL
Cashflow tooltip: PASS / FAIL

Light UI
--------
App shell: PASS / FAIL
AG Grid: PASS / FAIL
ECharts: PASS / FAIL
lightweight_charts: PASS / FAIL
R/S Ladder: PASS / FAIL
Cashflow tooltip: PASS / FAIL

Issues found
------------
1.
2.

Final verdict
-------------
PASS / PASS WITH ISSUES / FAIL
~~~

Nếu FAIL phải ghi:
- exact command
- exception / screenshot description
- file/function nghi ngờ
- expected vs actual
- regression do Theme System hay existing issue

## 16. Completion criteria

Chỉ kết luận PASS khi:
- tests/test_theme.py pass
- R/S regression pass
- dark app render đúng
- light app render đúng
- AG Grid đổi theo theme
- ECharts đổi theo theme
- lightweight_charts đổi theo theme
- cashflow tooltip đổi theo theme
- standalone page đổi theo theme
- không còn theme HEX hard-code trong consumer files
- không có business calculation regression
