# SmartMoney Ticker Detail Popup — triển khai và nghiệm thu

Status: IMPLEMENTED_PENDING_VALIDATION
Implementation commit: fc7f5bb23ea0d8d7302704fd24dc0a18b1eee231
Branch: feature/smartmoney-ticker-detail
Entry: src/webapp/NiceGUI_chart.py → SmartMoney
Next owner: local TestEngineer

## 1. Mục tiêu / phạm vi

Một click ticker mở popup bên trong CherryStock gồm:
- TradingView Advanced Chart cùng ticker/sàn, có link mở website đầy đủ.
- R/S Price Ladder và chi tiết mức giá, dùng engine/renderer hiện hữu.
- Đủ 21 trường SmartMoney, 24 trường Movement Profile, 44 trường Movement Context.
- Tooltip tiếng Việt có ý nghĩa, đơn vị và ví dụ minh họa; hover/focus hỗ trợ bàn phím.
- Ticker hover/active/focus dùng theme; 150ms ease-out; không nhảy layout; reduced motion.

Không chạy migration, initload, run.py, full-universe/backtest hoặc sửa công thức.
Popup chỉ đọc dữ liệu. Không gộp ba view thành tín hiệu mua/bán mới.
Controls bên trong iframe do TradingView quản lý; tooltip mới áp dụng UI CherryStock.

PR #22 chưa merge ở thời điểm bắt đầu thay đổi. Nhánh này xuất phát từ main
fc5f2370f4856e664495ca04602090ceb87566b0 và bao gồm phần ticker link/market enrichment
của PR #22. Kiểm tra/merge nhánh này như một thay đổi đầy đủ; không cần merge PR #22 trước.

## 2. Đọc trước khi chạy / allowed repair scope

- .github/copilot-instructions.md
- .github/agents/TestEngineer.agent.md
- .github/instructions/testing.instructions.md
- .github/instructions/python.instructions.md
- .github/skills/regression-testing/SKILL.md
- docs/development/Python_Execution_Conventions.md
- docs/architecture/Chart_Architecture.md — SmartMoney ticker detail popup

Chỉ sửa trong phạm vi:
src/webapp/{smart_money_tab,tradingview_links,smart_money_snapshot_query,ticker_detail_contract,ticker_detail_data,ticker_detail_dialog}.py;
src/Presentation/theme.py;
tests/test_{ticker_detail_contract,ticker_detail_dialog,tradingview_links,smart_money_snapshot_query}.py;
docs/architecture/{Chart_Architecture,theme}.md; runbook này.

Không sửa analytics engines/schema hoặc unrelated UI để làm smoke test chạy.

## 3. Safe sync

Từ root checkout CherryStock; dùng Python environment đang chạy được NiceGUI.
Dừng đúng process NiceGUI hiện tại, không kill mọi python.exe.

~~~powershell
git status --short
git branch --show-current
$previousBranch = git branch --show-current
$previousCommit = git rev-parse HEAD
git fetch origin
~~~

Nếu có thay đổi ngoài phạm vi: BLOCKED/STOP; không stash/reset tự động.
Nếu chưa có local feature branch:

~~~powershell
git switch --track origin/feature/smartmoney-ticker-detail
~~~

Nếu đã có:

~~~powershell
git switch feature/smartmoney-ticker-detail
git pull --ff-only origin feature/smartmoney-ticker-detail
~~~

Ghi lại git rev-parse HEAD. Sau merge, dùng main + pull --ff-only origin main.
Không kiểm tra main cũ rồi báo PASS cho feature branch.

## 4. Compile + tests hẹp

~~~powershell
python -m py_compile src\webapp\NiceGUI_chart.py src\webapp\smart_money_tab.py src\webapp\tradingview_links.py src\webapp\smart_money_snapshot_query.py src\webapp\ticker_detail_contract.py src\webapp\ticker_detail_data.py src\webapp\ticker_detail_dialog.py src\Presentation\theme.py
python -m pytest tests\test_ticker_detail_contract.py tests\test_ticker_detail_dialog.py tests\test_tradingview_links.py tests\test_smart_money_snapshot_query.py tests\test_smart_money_state_flow.py -q
~~~

Dự kiến 25 passed, exit=0:
- 89 fields có catalog diễn giải/ví dụ.
- Phần trăm thập phân, score, ratio, giá không lẫn đơn vị; NULL không thành 0.
- View allowlist, bound ticker parameter, isolation MWG/FPT, latest mỗi cấu hình.
- Widget khóa symbol, giữ attribution.
- Dựng popup NiceGUI và xóa iframe khi đóng.
- Kết quả MWG tải chậm không ghi đè popup FPT mới.
- Regression 16 cases ticker URL, snapshot query, state flow.

Collection/import failure: phân loại lỗi environment/import, không tự gọi REGRESSION.
Thiếu nicegui: dùng environment web hiện hữu; dependency đã khai báo trong
pyproject.toml [project.optional-dependencies].web. Không tự nâng phiên bản toàn project.

## 5. Dữ liệu thật, phạm vi 1 ticker trước

Invocation: chạy từ repository root. Lệnh dưới bootstrap src rõ ràng giống entry
point NiceGUI_chart.py, không yêu cầu biến PYTHONPATH toàn máy.

~~~powershell
python scripts\validate_smart_money_ui_snapshot.py
python -c "import sys; sys.path.insert(0,'src'); from webapp.ticker_detail_data import load_ticker_details; d=load_ticker_details('MWG'); print('ticker=',d['ticker'],'market=',d['market']); print('sections=',{k:len(v) for k,v in d['sections'].items()}); print('errors=',d['errors']); print('ladder=',None if d['ladder'] is None else (d['ladder'].ticker,str(d['ladder'].as_of_date),d['ladder'].current_price))"
~~~

Kỳ vọng: đúng MWG, ladder MWG, không có lỗi nguồn nếu views đã triển khai.
Không có record → UI “Chưa có dữ liệu”; missing view/query error → panel báo lỗi
và server log, các panel khác vẫn phải hoạt động. Không tự tạo dữ liệu giả.

## 6. Browser smoke (Chrome/Edge thường, tối đa 15 phút)

~~~powershell
python src\webapp\NiceGUI_chart.py
~~~

Mở http://127.0.0.1:8081 → SmartMoney.

1. Hover ticker: pointer + gạch chân + nền nhạt; không đổi độ đậm/kích thước/vị trí.
   Hai mã đầu mỗi bucket vẫn bold. Dừng khoảng 400ms hiện tooltip.
2. Tab tới ticker: focus ring rõ; Enter mở popup. Escape đóng và trả tương tác
   về danh sách. Tooltip field mở bằng focus; blur/Escape ẩn tooltip.
3. Click MWG: popup có HOSE:MWG, widget đúng mã, R/S và ba nhóm view đúng MWG.
   Chart không cho đổi sang ticker khác bên trong widget.
4. R/S: đối chiếu cùng ticker với tab R/S mặc định (ngày mới nhất, cluster 1%).
   So sánh as_of_date, current_price, S1/R1, Strength và Reward/Risk.
   Marker và chi tiết mức giá có tooltip giải nghĩa/ví dụ.
5. SmartMoney: kiểm tra Date, ModelCode, ModelVersion; đủ 21 fields.
   Profile: đủ 24 fields, cấu hình, AsOfConfirmedAtDate.
   Context: đủ 44 fields, ContextAsOfDate, ProfileAsOfConfirmedAtDate,
   CurrentLegAsOfDate; nhịp hiện tại ghi rõ là tạm thời.
   Nếu nhiều cấu hình, hiện riêng từng dòng latest, không ngầm LIMIT 1.
6. Đối chiếu giá trị với public view cùng Ticker/config/date.
   Movement 0.1 → 10%; ConfidenceScore 80 → 80; DirectionalBias 0.3 → 0.3;
   R/S Dist 2.5 đã là 2.5%, không thành 250%; NULL → “—”.
   Tooltip ghi rõ ví dụ minh họa, không nhầm với giá hiện tại.
7. Đóng MWG → mở SHS (HNX) → ACV (UPCOM) và một ticker MA200 N/A nếu có.
   Widget/R/S/ba view thay đồng bộ. Đóng/mở hai mã nhanh không bị kết quả
   trả về chậm của mã trước ghi đè.
8. Ctrl/Cmd-click link đã có sàn vẫn mở trực tiếp TradingView.
   Link “Mở trên TradingView” trong popup luôn sẵn. Nếu widget lỗi mạng/không hỗ trợ
   mã, link ngoài vẫn mở đúng mã; analytics local vẫn xem được.
9. Mã thiếu sàn nếu có: chọn HOSE/HNX/UPCOM trong popup; chỉ chart thay đổi,
   không sửa metadata DB. Nếu không có case thật: ghi N/A, không sửa DB production.
   Có thể dùng fixture/mock trong tests và ghi rõ đó là mock.
10. Refresh danh sách hai lần: counts/MA200/state anchors/order giữ đúng.
    Popup không tự refresh dữ liệu đang mở: đóng/mở lại để tải snapshot mới.
11. Desktop ~1440px: chart trái + ladder phải. Viewport 420px: xếp dọc, trường
    đọc được, không tràn ngang trang. Bật reduced-motion: ticker không transition.
    Chạy light/dark bằng CHERRYSTOCK_THEME theo runbook theme; focus/text đủ rõ.
12. Đóng popup: widget iframe được tháo. Dừng server smoke.
    Không đánh đồng mock với TradingView render thật.

Không cần mọi ticker: MWG + SHS + ACV + một N/A là đủ.
TradingView có thể khác nguồn/ngày/đơn vị so với CherryStock; so đúng ticker/sàn,
không yêu cầu hai nguồn có giá bằng nhau tuyệt đối.

## 7. Verdict / rollback / STOP

PASS: compile/tests + dữ liệu thật + browser render đã quan sát, đủ tooltip và
R/S đối chiếu đúng. KEEP; handoff PR review/merge; STOP.
FAIL/REGRESSION: thay đổi làm sai ticker, đơn vị, query, mất dữ liệu hoặc lỗi popup.
BLOCKED: thiếu dependency/view/quyền đọc/mạng widget/browser không quan sát được.
Không ghi PASS toàn bộ nếu widget/popup chưa quan sát được.

Sau FAIL/BLOCKED: dừng đúng server; với working tree sạch chuyển lại branch/SHA
đã lưu. Detached checkout: git switch --detach $previousCommit.
Không git reset --hard, không force push; không rollback DB vì không có DB writes.
Tối đa hai sửa chữa hẹp có bằng chứng mới, không chạy lại lỗi y nguyên.
Sau verdict kết thúc, không mở rộng sang giả thuyết khác.

## 8. Evidence / handoff

Developer verification of implementation commit:
25 pytest cases passed with in-memory source collection, real DuckDB fixtures,
and real NiceGUI component construction. UI DB/engine boundary was stubbed;
normal checkout collection, production DB, external widget/browser remain local gates.
Environment here was Python 3.12, not the user's Python 3.13 runtime.
One pytest assertion-rewrite warning for preloaded anyio; no failing case.
All source writes were direct GitHub writes.

Lưu bằng chứng an toàn dưới docs/reference/data/smart_money/ticker_detail_popup/.
Không đưa token, thông tin bí mật hoặc database dump vào evidence.

~~~text
SMARTMONEY TICKER DETAIL
HEAD / Branch:
Python / NiceGUI / Browser:
Compile:
25 focused tests:
Snapshot / ticker counts:
TradingView HOSE/HNX/UPCOM:
R/S vs existing tab:
SmartMoney 21 / Profile 24 / Context 44:
Units / NULL / separate dates / config identity:
Hover / focus / Enter / Escape / reduced motion:
Missing market: PASS / FAIL / N/A
Partial error / empty view:
Rapid ticker switching / close cleanup:
Desktop / 420px / dark / light:
Verdict: PASS / FAIL / BLOCKED / REGRESSION
Action: KEEP / ROLLBACK / STOP
Evidence:
~~~
