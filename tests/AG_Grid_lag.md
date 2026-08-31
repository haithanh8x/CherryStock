# AG Grid Column Resize Lag — Root Cause Investigation & Fix Playbook

## 1. Mục đích

Tài liệu này dùng để điều tra hiện tượng **AG Grid bị giật / lag / không mượt khi kéo resize column** trong CherryStock, đặc biệt tại Stock Screener được render bởi:

- `src/webapp/NiceGUI_chart.py`
- `src/webapp/NiceGUI_grid.py`
- `src/webapp/NiceGUI_grid_market_tb.py`
- `src/Presentation/theme.py`

Mục tiêu của tài liệu:

1. Ghi nhận đầy đủ các nguyên nhân có khả năng gây lag dựa trên source hiện tại.
2. Mô tả cơ chế kỹ thuật vì sao từng nguyên nhân có thể ảnh hưởng tới column resize.
3. Đưa ra fix cụ thể cho từng nguyên nhân.
4. Đưa ra **kịch bản test cô lập từng biến**.
5. Thực hiện điều tra theo thứ tự, không sửa tất cả cùng lúc.
6. Xác định **root cause thực tế** bằng evidence từ browser/runtime thay vì chỉ dựa trên cảm giác.
7. Sau khi tìm được nguyên nhân, giữ lại fix cần thiết và rollback các experiment không tạo cải thiện đáng kể.
8. Có regression checklist để đảm bảo fix performance không làm hỏng filter, Columns Tool Panel, saved view, tab navigation hoặc theme.

> Quy tắc quan trọng: **Không được apply nhiều thay đổi performance cùng lúc trong giai đoạn root-cause investigation.**
>
> Mỗi scenario chỉ thay đổi một biến, test lại, ghi kết quả, sau đó mới chuyển scenario tiếp theo.

---

# 2. Phạm vi hiện tượng

Hiện tượng cần đo:

- kéo boundary giữa hai column header bị giật;
- column width không bám sát con trỏ;
- có frame drop trong lúc drag;
- có nhịp khựng định kỳ;
- browser main thread tăng CPU trong lúc resize;
- UI có cảm giác repaint toàn bộ card/grid;
- resize mượt hơn hoặc kém hơn khi mở/đóng Columns Tool Panel;
- resize có thể bị ảnh hưởng bởi tab swipe handling.

Primary target:

`NiceGUI_chart.py -> market_tab_content() -> create_market_grid()`

Grid được tạo trong:

`src/webapp/NiceGUI_grid.py::create_market_grid()`

---

# 3. Evidence từ source hiện tại

## 3.1. AG Grid manual resize đã được bật

Trong `NiceGUI_grid.py`:

~~~python
"defaultColDef": {
    "sortable": True,
    "filter": True,
    "resizable": True,
    "minWidth": 70,
    "floatingFilter": True,
}
~~~

Và từng column cũng được ép:

~~~python
column_def["resizable"] = True
~~~

Đây là cấu hình đúng để người dùng resize column, nhưng có nghĩa là mọi chi phí layout/render khi width thay đổi sẽ xảy ra liên tục trong lúc drag.

---

## 3.2. Screener hiện đã loại bỏ flex khỏi column model

Trong `_create_grouped_column_defs()`:

~~~python
flex_value = column_def.pop("flex", None)
column_def.pop("maxWidth", None)
column_def["resizable"] = True

if "width" not in column_def:
    configured_min = int(column_def.get("minWidth", 140) or 140)
    column_def["width"] = max(configured_min, 160 if flex_value else 110)
~~~

Source đã có comment:

> Stock Screener ưu tiên manual sizing. Flex có thể co giãn lại theo viewport.

Kết luận hiện tại:

- `flex` là nguyên nhân hợp lý về mặt AG Grid nói chung;
- nhưng **không phải nghi phạm chính đối với Stock Screener hiện tại**, vì code đã pop `flex`;
- vẫn cần lưu ý các grid khác trong CherryStock còn dùng `flex: 1`.

---

## 3.3. Dashboard card đang dùng CSS backdrop blur

Trong `src/Presentation/theme.py::build_nicegui_css()`:

~~~css
.dashboard-card {
    overflow: hidden;
    backdrop-filter: blur(12px);
}
~~~

Stock Screener nằm trong:

~~~python
with ui.card().classes(card_classes("p-4 w-full")):
~~~

Trong khi `card_classes()` luôn thêm:

~~~text
dashboard-card
~~~

Do đó AG Grid đang nằm bên trong một compositor layer có `backdrop-filter`.

Đây là nghi phạm ưu tiên cao.

---

## 3.4. QTabPanels đang bật swipeable

Trong `src/webapp/NiceGUI_chart.py::build_page()`:

~~~python
with ui.tab_panels(tabs, value="overview").classes(
    "w-full bg-transparent p-0"
).props("animated keep-alive swipeable"):
~~~

AG Grid là component có interaction kéo ngang rất nhiều.

Tab container cũng đang có gesture ngang.

Do đó CherryStock đã phải thêm nhiều event blocker để ngăn thao tác trong grid vô tình đổi tab.

---

## 3.5. AG Grid đang bắt mouse/touch/pointer events để stop propagation

Trong `src/webapp/NiceGUI_grid.py::_stop_parent_swipe()`:

~~~python
swipe_events = (
    "touchstart",
    "touchmove",
    "touchend",
    "touchcancel",
    "mousedown",
    "mousemove",
    "mouseup",
    "mouseleave",
    "pointerdown",
    "pointermove",
    "pointerup",
    "pointercancel",
)

for event_name in swipe_events:
    element.on(
        event_name,
        js_handler="(event) => event.stopPropagation()",
    )
~~~

Đặc biệt:

- `mousemove`
- `pointermove`

có thể fire rất nhiều lần mỗi giây trong lúc user kéo column resize handle.

---

## 3.6. CherryStock còn có global QTabPanel event blocker

Trong `_install_global_tab_swipe_blocker()`:

~~~javascript
const eventNames = [
    'touchstart', 'touchmove', 'touchend', 'touchcancel',
    'mousedown', 'mousemove', 'mouseup', 'mouseleave',
    'pointerdown', 'pointermove', 'pointerup', 'pointercancel'
];
~~~

Sau đó áp dụng cho mọi:

~~~javascript
document.querySelectorAll('.q-tab-panel')
~~~

Như vậy cùng một pointer/mouse drag có thể đi qua:

1. AG Grid internal resize handling.
2. NiceGUI listener của `_stop_parent_swipe()`.
3. Global listener trên `.q-tab-panel`.
4. Quasar swipeable machinery.

Đây là nghi phạm ưu tiên cao.

---

## 3.7. Grid state được poll mỗi 1.5 giây

Cuối `create_market_grid()`:

~~~python
ui.timer(1.5, persist_state)
~~~

`persist_state()` chạy:

~~~python
grid_state = await grid.run_grid_method("getState")
column_state = await grid.run_grid_method("getColumnState")
~~~

Sau đó:

~~~python
signature = json.dumps(...)
~~~

và khi state thay đổi:

~~~python
_save_session_grid_state(...)
~~~

Cache được ghi xuống:

~~~text
Build/cache/stock_screener_grid_state.json
~~~

Resize column trực tiếp thay đổi column state, vì vậy lúc user đang drag, timer có thể đọc/serialize/persist state giữa chừng.

Nếu lag xuất hiện theo nhịp khoảng 1–2 giây, đây là nghi phạm rất quan trọng.

---

## 3.8. Enterprise Columns Tool Panel mặc định mở

Grid options hiện có:

~~~python
"sideBar": {
    "toolPanels": [
        {
            "id": "columns",
            ...
            "toolPanel": "agColumnsToolPanel",
            ...
        }
    ],
    "defaultToolPanel": "columns",
    "position": "right",
},
~~~

Và grid load:

~~~python
modules="enterprise"
~~~

Column definitions của Screener không chỉ gồm column visible mà còn toàn bộ các field từ DataFrame / `vw_Ticker`, kể cả hidden.

Khi số indicator tăng, số column definition sẽ tiếp tục tăng.

Tool Panel phải giữ column tree và update state tương ứng.

Đây là nghi phạm trung bình-cao, đặc biệt nếu lag tăng khi `vw_Ticker` có nhiều field.

---

## 3.9. Floating filters đang bật trên toàn bộ column

~~~python
"defaultColDef": {
    ...
    "floatingFilter": True,
}
~~~

Mỗi visible column không chỉ có header mà còn thêm floating filter UI.

Resize column có thể gây layout lại:

- header cell;
- filter row;
- content viewport;
- horizontal viewport.

Đây là nghi phạm trung bình.

---

## 3.10. Row animation đang bật

~~~python
"animateRows": True
~~~

`animateRows` không phải nguyên nhân trực tiếp phổ biến nhất của column resize, nhưng financial terminal ưu tiên latency thấp hơn animation.

Đây là optimization candidate, không phải root-cause candidate số 1.

---

# 4. Root cause hypotheses

| ID | Hypothesis | Mức nghi ngờ ban đầu |
|---|---|---:|
| H1 | `backdrop-filter: blur(12px)` làm browser repaint/composite nặng khi column width thay đổi | Rất cao |
| H2 | `swipeable` của QTabPanels tạo gesture processing cạnh tranh với AG Grid drag | Cao |
| H3 | Local + global mouse/pointer blockers làm tăng event processing trong mỗi drag frame | Rất cao |
| H4 | `persist_state()` polling 1.5s tạo nhịp khựng do WebSocket/state serialization/file write | Cao |
| H5 | Enterprise Columns Tool Panel luôn mở làm column-model work lớn hơn cần thiết | Khá cao |
| H6 | `floatingFilter=True` làm header/layout tree nặng hơn | Trung bình |
| H7 | `animateRows=True` tạo overhead phụ | Thấp-Trung bình |
| H8 | Flex sizing conflict | Thấp với Stock Screener hiện tại; cần test ở grid khác |

---

# 5. Nguyên tắc điều tra

## 5.1. Không thay nhiều biến cùng lúc

Sai:

~~~text
remove blur
+ remove swipeable
+ remove blockers
+ disable persistence
+ close sidebar
~~~

Sau đó thấy mượt hơn.

Kết quả trên chỉ chứng minh "một hoặc nhiều thay đổi có tác dụng", không xác định được root cause.

Đúng:

~~~text
Baseline
↓
thay H1 duy nhất
↓
measure
↓
rollback H1
↓
thay H2 duy nhất
↓
measure
...
~~~

Sau khi đã định lượng từng nguyên nhân mới build final fix combination.

---

## 5.2. Mỗi scenario phải test cùng một workload

Khuyến nghị dùng cùng môi trường:

- Chrome/Edge cùng version;
- cùng window size;
- zoom 100%;
- cùng CherryStock theme;
- cùng ticker dataset;
- cùng số visible columns;
- cùng Columns Tool Panel state;
- DevTools không mở ở scenario này nhưng đóng ở scenario khác;
- không chạy workload CPU nặng song song.

---

## 5.3. Không dùng chỉ cảm giác

Mỗi scenario ghi tối thiểu:

- perceived smoothness: 1–5;
- có freeze rõ ràng hay không;
- có nhịp freeze định kỳ hay không;
- Chrome Performance: dropped frames / long tasks;
- CPU main thread khi drag;
- browser console error;
- có regression chức năng hay không.

Nếu có thể, record Performance trace 5–10 giây.

---

# 6. Chuẩn bị baseline

## 6.1. Sync main

~~~powershell
cd C:\Github\CherryStock
git status
git fetch origin
git checkout main
git pull --ff-only origin main
git log -5 --oneline
~~~

Expected:

- working tree sạch;
- đúng commit cần test;
- không có experiment cũ chưa rollback.

---

## 6.2. Chạy app

Nếu dùng venv:

~~~powershell
.\.venv\Scripts\Activate.ps1
python --version
~~~

Chạy:

~~~powershell
python src\webapp\NiceGUI_chart.py
~~~

Mở:

~~~text
http://localhost:8081
~~~

Vào:

~~~text
Screener
~~~

---

## 6.3. Baseline interaction

1. Đợi grid load ổn định.
2. Không filter.
3. Giữ Columns Tool Panel ở state mặc định.
4. Chọn một boundary giữa hai cột ở vùng giữa viewport.
5. Kéo trái/phải liên tục 5 giây.
6. Thả chuột.
7. Lặp lại 5 lần.
8. Test thêm resize cột pinned `Ticker`.
9. Test thêm resize khi scroll ngang đến nhóm FA.

Ghi:

~~~text
Baseline Result
===============
Commit:
Browser:
OS:
Screen resolution:
Zoom:
Theme:
Visible columns:
Total source columns:
Columns Tool Panel: OPEN/CLOSED

Smoothness score 1-5:
Visible frame drop: YES/NO
Periodic freeze: YES/NO
Approx freeze interval:
Pointer follows resize handle: GOOD/POOR
Console errors:
Notes:
~~~

---

# 7. Scenario 1 — Isolate CSS backdrop blur

## Hypothesis H1

`backdrop-filter: blur(12px)` trên parent card làm compositor phải xử lý lại layer khi AG Grid resize liên tục.

### Cơ chế có thể gây lag

Column resize gây:

~~~text
pointermove
→ AG Grid calculates width
→ header geometry changes
→ cell viewport geometry changes
→ browser layout
→ paint
→ composite
→ backdrop-filter recomposition
~~~

Nếu browser phải làm bước blur/composite nhiều lần mỗi frame, FPS sẽ giảm.

---

## Thay đổi test tối thiểu

Trong:

`src/Presentation/theme.py`

Tạm đổi:

~~~css
.dashboard-card {
    overflow: hidden;
    backdrop-filter: blur(12px);
}
~~~

thành:

~~~css
.dashboard-card {
    overflow: hidden;
}
~~~

Không đổi bất kỳ cấu hình AG Grid nào khác.

---

## Test

1. Restart app.
2. Hard refresh browser.
3. Lặp đúng baseline workload.
4. Record Performance trace.
5. So với baseline.

### PASS cho hypothesis

H1 được xem là **confirmed contributor** nếu:

- resize rõ ràng mượt hơn;
- dropped frames giảm đáng kể;
- long task/compositor cost giảm;
- lag biến mất hoặc giảm mạnh mà không đổi biến khác.

### FAIL cho hypothesis

Nếu khác biệt không đáng kể hoặc không lặp lại được qua 3 lần test.

---

## Fix production đề xuất nếu H1 confirmed

Không áp `backdrop-filter` cho card chứa data grid.

Có thể tách class:

~~~css
.dashboard-card {
    overflow: hidden;
}

.dashboard-card--glass {
    backdrop-filter: blur(12px);
}
~~~

Chỉ dùng glass effect cho card nhỏ/static.

Hoặc thêm class dành riêng cho grid:

~~~css
.dashboard-data-card {
    backdrop-filter: none;
}
~~~

### Regression test

- dark theme vẫn đúng;
- light theme vẫn đúng;
- border card đúng;
- hover border đúng;
- grid không xuất hiện vùng transparent/white bất thường;
- các metric card khác giữ appearance mong muốn.

Sau khi ghi kết quả, **rollback experiment** trước Scenario 2 nếu đang trong phase xác định root cause độc lập.

---

# 8. Scenario 2 — Isolate QTabPanels `swipeable`

## Hypothesis H2

Quasar QTabPanels đang xử lý swipe gesture trong cùng interaction tree với AG Grid horizontal drag.

Current:

~~~python
.props("animated keep-alive swipeable")
~~~

---

## Thay đổi test tối thiểu

Trong:

`src/webapp/NiceGUI_chart.py::build_page()`

đổi:

~~~python
.props("animated keep-alive swipeable")
~~~

thành:

~~~python
.props("animated keep-alive")
~~~

Giữ nguyên local/global blockers trong scenario này để chỉ isolate `swipeable`.

---

## Test

Lặp baseline workload.

Test thêm:

1. kéo resize nhanh;
2. kéo resize rất chậm;
3. drag horizontal scrollbar;
4. click tab bình thường;
5. kiểm tra tab không tự đổi ngoài ý muốn.

### PASS cho hypothesis

- column resize mượt hơn đáng kể chỉ bằng việc bỏ `swipeable`;
- CPU/event cost giảm;
- không còn gesture conflict.

### Fix production đề xuất

Đối với desktop financial terminal, tab swipe không phải interaction cốt lõi.

Ưu tiên:

~~~python
.props("animated keep-alive")
~~~

Thay tab bằng click/navigation rõ ràng.

### Regression

- click các tab vẫn hoạt động;
- `keep-alive` giữ state đúng;
- animation tab còn hoạt động;
- mobile UX chấp nhận được.

Rollback trước Scenario 3 nếu cần isolate độc lập.

---

# 9. Scenario 3 — Isolate mouse/pointer event blockers

## Hypothesis H3

CherryStock đăng ký quá nhiều event listener trong đường đi của drag.

Hai lớp:

1. `_stop_parent_swipe(grid)`
2. `_install_global_tab_swipe_blocker()`

Đặc biệt `mousemove` và `pointermove` có tần suất rất cao.

---

## Scenario 3A — local grid blocker

Tạm bỏ:

~~~python
_stop_parent_swipe(grid)
~~~

Không thay global blocker.

Test lại resize.

### Expected evidence

Nếu mượt lên rõ:

- local NiceGUI event binding là contributor;
- cần xem listener này có được chuyển qua client-side strategy nhẹ hơn hay loại bỏ sau khi bỏ `swipeable`.

---

## Scenario 3B — global QTabPanel blocker

Khôi phục 3A về baseline.

Tạm vô hiệu:

~~~python
_install_global_tab_swipe_blocker()
~~~

hoặc không inject script.

Test lại.

---

## Scenario 3C — cả hai blocker

Chỉ sau khi đã ghi độc lập 3A/3B.

Disable cả:

- local blocker;
- global blocker.

Scenario này dùng để đo interaction effect.

---

## Fix production đề xuất nếu H3 confirmed

Nếu Scenario 2 đã quyết định bỏ `swipeable`, mục tiêu là xóa luôn phần lớn gesture workaround.

Ideal:

~~~text
AG Grid receives drag directly
→ no parent swipe navigation
→ no mousemove/pointermove stopPropagation workaround
~~~

Nếu vẫn cần chặn mobile swipe:

- chỉ chặn touch events;
- tránh `mousemove`;
- tránh `pointermove` nếu không thật sự cần;
- ưu tiên CSS / structural solution hơn high-frequency handlers.

### Regression

- resize column;
- drag horizontal scrollbar;
- scroll mouse wheel;
- cell click;
- text/filter interaction;
- touch scroll nếu có thiết bị;
- tab navigation không vô tình kích hoạt.

---

# 10. Scenario 4 — Isolate state persistence polling

## Hypothesis H4

Current:

~~~python
ui.timer(1.5, persist_state)
~~~

Mỗi lần timer chạy có thể:

~~~text
NiceGUI timer
→ WebSocket/server interaction
→ grid.getState()
→ grid.getColumnState()
→ JSON serialize
→ signature compare
→ file cache write nếu changed
~~~

Resize làm width thay đổi nên column state thay đổi liên tục.

Nếu symptom là:

~~~text
smooth
→ short freeze
→ smooth
→ short freeze
~~~

với chu kỳ gần 1.5 giây, H4 đặc biệt đáng nghi.

---

## Thay đổi test tối thiểu

Tạm comment:

~~~python
ui.timer(1.5, persist_state)
~~~

Giữ one-time restore:

~~~python
ui.timer(0.1, initialise_persisted_state, once=True)
~~~

Không đổi saved-view code.

---

## Test

1. kéo resize liên tục ít nhất 10 giây;
2. quan sát có mất periodic freeze không;
3. record Performance;
4. sau resize thử filter và các controls.

### PASS cho hypothesis

- nhịp freeze định kỳ biến mất;
- responsiveness tốt hơn;
- trace cho thấy trước đây timer/state call trùng với freeze.

---

## Fix production đề xuất

Không polling grid state trong lúc user interaction.

Chuyển sang event-driven persistence.

Concept:

~~~text
column resized (intermediate)
    → DO NOT persist

column resize finished
    → debounce
    → persist once
~~~

Các event cần cân nhắc:

- columnResized khi `finished == true`;
- columnMoved;
- columnVisible;
- columnPinned;
- sortChanged;
- filterChanged;
- rowGroupChanged / pivot change nếu cần.

Debounce ví dụ:

~~~text
300–800 ms
~~~

State persistence phải xảy ra **sau interaction**, không nằm trong critical drag path.

### Lưu ý

NiceGUI event API cần được kiểm tra theo version thực tế trước implementation final.

Không invent event signature nếu chưa verify.

---

## Regression

Sau fix event-driven:

1. resize cột;
2. đợi debounce;
3. F5;
4. width phải restore;
5. move column;
6. F5;
7. order restore;
8. pin/unpin;
9. F5;
10. state restore;
11. filter model restore;
12. saved view vẫn hoạt động.

---

# 11. Scenario 5 — Enterprise Columns Tool Panel

## Hypothesis H5

Tool Panel luôn mở và theo dõi toàn bộ column model.

Current:

~~~python
"defaultToolPanel": "columns"
~~~

---

## Thay đổi test tối thiểu

Giữ sideBar nhưng không mở mặc định.

Tùy AG Grid version, dùng cấu hình phù hợp để panel khởi đầu ở trạng thái closed.

Mục tiêu experiment:

~~~text
same column model
same rowData
same filters
same enterprise modules
only Columns Tool Panel is not rendered/open
~~~

---

## Test

Test hai trạng thái:

A. Tool Panel closed  
B. Tool Panel open

Lặp cùng resize workload.

### PASS cho hypothesis

Nếu closed mượt hơn rõ rệt và mở panel làm lag quay lại.

---

## Fix production đề xuất

Không mở Columns Tool Panel mặc định.

User cần mới mở.

Lợi ích:

- giảm DOM;
- giảm column tree UI update;
- tăng diện tích data viewport;
- phù hợp terminal workflow.

### Regression

- user mở panel được;
- General/FA/TA/Other groups đúng;
- show/hide column đúng;
- row group/pivot/value tools đúng;
- saved views restore đúng.

---

# 12. Scenario 6 — Floating Filter

## Hypothesis H6

Floating filter tạo thêm UI component cho mỗi visible column và bị layout lại khi width đổi.

---

## Thay đổi test tối thiểu

Tạm đổi:

~~~python
"floatingFilter": True
~~~

thành:

~~~python
"floatingFilter": False
~~~

Không thay `filter=True`.

---

## Test

- resize cùng workload;
- sort;
- mở filter menu;
- filter một numeric field;
- filter một text field.

### PASS cho hypothesis

Nếu resize mượt hơn rõ rệt nhưng filter menu vẫn đủ chức năng.

---

## Fix options

### Option A — bỏ floating filter

Phù hợp nếu toolbar filter phía trên đã đáp ứng phần lớn use case.

### Option B — chỉ bật cho các column quan trọng

Ví dụ:

- Ticker
- Industry
- PE
- ROE

Không bật cho mọi indicator.

### Option C — user preference

Advanced view mới bật floating filters.

---

# 13. Scenario 7 — Row animation

## Hypothesis H7

`animateRows=True` tạo overhead phụ không cần thiết cho financial screener.

---

## Experiment

Đổi:

~~~python
"animateRows": True
~~~

thành:

~~~python
"animateRows": False
~~~

---

## Test

- resize;
- sort;
- filter;
- pagination;
- replace rowData.

Nếu resize cải thiện ít nhưng sort/filter responsive hơn, ghi đây là optimization chứ không phải root cause.

---

# 14. Scenario 8 — Flex sizing ở các AG Grid khác

Stock Screener đã remove flex.

Nhưng các grid khác vẫn có cấu hình dạng:

~~~python
{
    "field": "sources",
    "minWidth": 170,
    "flex": 1,
}
~~~

Ví dụ R/S Level Details.

Nếu user report lag ở grid đó:

1. đổi `flex: 1` sang initial `width`;
2. giữ `resizable=True`;
3. test lại.

Không dùng kết quả này để kết luận nguyên nhân của Stock Screener.

---

# 15. Thứ tự thực thi bắt buộc

Thực hiện theo thứ tự:

~~~text
S0  Baseline
 ↓
S1  Backdrop filter
 ↓ rollback
S2  QTabPanels swipeable
 ↓ rollback
S3A Local event blocker
 ↓ rollback
S3B Global event blocker
 ↓ rollback
S3C Combined blockers
 ↓ rollback
S4  Persistence timer
 ↓ rollback
S5  Columns Tool Panel
 ↓ rollback
S6  Floating filter
 ↓ rollback
S7  Row animation
 ↓
S8  Flex only if testing another grid
~~~

Sau mỗi scenario:

1. ghi result;
2. chụp Performance trace nếu có;
3. ghi improvement;
4. rollback;
5. xác nhận `git diff` chỉ chứa thay đổi scenario tiếp theo.

---

# 16. Performance measurement với Chrome DevTools

## 16.1. Record

Chrome DevTools:

~~~text
Performance
→ Record
→ drag column 5–10 seconds
→ Stop
~~~

Quan sát:

- FPS;
- Main thread;
- long task > 50 ms;
- Event;
- Recalculate Style;
- Layout;
- Paint;
- Composite Layers;
- scripting.

---

## 16.2. Dấu hiệu H1

Nếu `backdrop-filter` là root contributor:

- Paint / Composite cost cao;
- layer/compositor activity cao khi drag;
- remove blur làm timeline nhẹ đi rõ rệt.

---

## 16.3. Dấu hiệu H2/H3

Nếu gesture/event handling là contributor:

- Scripting/Event activity dày trong pointer move;
- remove swipe/blockers giảm scripting;
- layout cost tương tự nhưng frame pacing tốt hơn.

---

## 16.4. Dấu hiệu H4

Nếu persistence timer là contributor:

- freeze xuất hiện gần chu kỳ timer;
- có scripting/network/server round-trip gần freeze;
- disable timer làm periodic hitch biến mất.

---

# 17. Root cause decision rules

## Root cause chính

Một hypothesis chỉ được đánh dấu **ROOT CAUSE** khi:

1. thay đổi riêng hypothesis đó cải thiện rõ ràng;
2. kết quả lặp lại ít nhất 3 lần;
3. rollback làm lag quay lại;
4. re-apply làm lag giảm lại;
5. có evidence từ Performance trace hoặc runtime behavior.

Đây là A/B/A verification.

---

## Contributing factor

Đánh dấu **CONTRIBUTOR** khi:

- improvement có nhưng nhỏ;
- không đủ để giải thích toàn bộ symptom;
- chỉ đáng kể khi kết hợp với root cause.

---

## Not significant

Đánh dấu **NOT SIGNIFICANT** khi:

- không có improvement rõ;
- variance giữa run lớn hơn improvement;
- trace không cho thấy difference meaningful.

---

# 18. Expected likely root-cause ranking trước khi runtime test

Dựa trên static source review hiện tại:

~~~text
1. backdrop-filter blur
2. high-frequency mouse/pointer blockers + swipeable interaction
3. persistence polling during resize
4. enterprise Columns Tool Panel open
5. floatingFilter
6. animateRows
7. flex — unlikely for current Screener
~~~

Đây chỉ là **hypothesis ranking**, chưa phải kết luận runtime.

Local agent không được ghi "root cause confirmed" chỉ từ ranking này.

---

# 19. Final production architecture mục tiêu

Critical interaction path lý tưởng:

~~~text
Mouse / pointer drag
        ↓
Browser
        ↓
AG Grid resize engine
        ↓
DOM/layout only
        ↓
requestAnimationFrame
        ↓
render
~~~

Trong lúc đang drag phải tránh:

~~~text
Python callback
WebSocket round trip
disk write
getState polling
JSON serialization
parent swipe detection
global pointermove handlers
expensive backdrop composition
~~~

Sau khi user thả chuột:

~~~text
columnResize finished
        ↓
debounce
        ↓
persist state once
~~~

---

# 20. Candidate final fix nếu nhiều hypothesis cùng confirmed

Không apply trước khi hoàn thành isolate tests.

Candidate architecture:

1. Không dùng `backdrop-filter` trên data-grid cards.
2. Bỏ `swipeable` cho main financial terminal tabs.
3. Xóa local/global high-frequency swipe blockers nếu không còn cần.
4. Thay `ui.timer(1.5, persist_state)` bằng event-driven + debounce persistence.
5. Columns Tool Panel closed by default.
6. Cân nhắc floating filters chỉ cho field quan trọng.
7. `animateRows=False` cho Screener.
8. Giữ fixed initial width cho manually resizable Screener columns.

---

# 21. Functional regression suite sau mỗi candidate fix

## 21.1. Grid core

- [ ] grid render;
- [ ] resize column;
- [ ] resize pinned Ticker;
- [ ] horizontal scroll;
- [ ] vertical scroll;
- [ ] pagination;
- [ ] sort ascending;
- [ ] sort descending;
- [ ] numeric filter;
- [ ] text filter;
- [ ] floating filter nếu còn enabled.

---

## 21.2. Custom filters phía trên grid

- [ ] Ticker multiselect;
- [ ] Stock multiselect;
- [ ] Industry multiselect;
- [ ] multiple selectors kết hợp AND;
- [ ] Xóa bộ lọc;
- [ ] rowData update không reset column width ngoài ý muốn.

---

## 21.3. Saved Filters

- [ ] save filter;
- [ ] load filter;
- [ ] delete filter;
- [ ] AG Grid filter model restore.

---

## 21.4. Saved Views

- [ ] save view;
- [ ] load view;
- [ ] delete view;
- [ ] column visibility restore;
- [ ] order restore;
- [ ] width restore;
- [ ] pin restore;
- [ ] sort restore;
- [ ] row group restore;
- [ ] pivot mode restore.

---

## 21.5. Session state

- [ ] resize width;
- [ ] F5;
- [ ] width restore;
- [ ] filter;
- [ ] F5;
- [ ] filter state restore;
- [ ] new browser tab có session độc lập theo design hiện tại.

---

## 21.6. Tab behavior

- [ ] click Overview;
- [ ] click Screener;
- [ ] click Portfolio;
- [ ] click R/S;
- [ ] click Operations;
- [ ] grid drag không đổi tab;
- [ ] scrollbar drag không đổi tab;
- [ ] mobile/touch test nếu bỏ swipeable.

---

## 21.7. Theme regression

Test:

~~~powershell
$env:CHERRYSTOCK_THEME = "cherry_dark"
python src\webapp\NiceGUI_chart.py
~~~

và:

~~~powershell
$env:CHERRYSTOCK_THEME = "cherry_light"
python src\webapp\NiceGUI_chart.py
~~~

Expected:

- grid readable;
- header/background/border đúng;
- fix performance không tạo hard-code theme mới;
- nếu remove blur thì appearance vẫn acceptable cả dark/light.

---

# 22. Automated regression

Các thay đổi performance chủ yếu là UI interaction nên automated test không thay thế manual performance test.

Tuy vậy vẫn phải chạy:

~~~powershell
python -m pytest tests -v
~~~

Tối thiểu:

~~~powershell
python -m pytest tests/test_theme.py tests/test_rs_ladder.py -v
~~~

Nếu sửa logic persistence, bổ sung unit/integration test tương ứng thay vì chỉ manual.

Không report PASS nếu test suite chưa chạy.

---

# 23. Scenario result worksheet

Copy block này cho mỗi scenario:

~~~text
AG Grid Lag Investigation
=========================

Scenario:
Hypothesis:
Commit:
Temporary change:
Files changed:

Environment
-----------
OS:
Browser/version:
Resolution:
Zoom:
Theme:
Rows:
Source columns:
Visible columns:
Tool Panel open: YES/NO

Before
------
Smoothness 1-5:
Periodic hitch:
FPS notes:
Main-thread notes:
Paint/composite notes:

After
-----
Smoothness 1-5:
Periodic hitch:
FPS notes:
Main-thread notes:
Paint/composite notes:

Regression
----------
Resize: PASS/FAIL
Horizontal scroll: PASS/FAIL
Filters: PASS/FAIL
Columns panel: PASS/FAIL
Saved state: PASS/FAIL
Tabs: PASS/FAIL
Theme: PASS/FAIL

A/B verification
----------------
Apply improves: YES/NO
Rollback regresses: YES/NO
Re-apply improves: YES/NO

Verdict
-------
ROOT CAUSE / CONTRIBUTOR / NOT SIGNIFICANT / INCONCLUSIVE

Evidence:
Notes:
~~~

---

# 24. Summary matrix cần hoàn thành

| Scenario | Hypothesis | Before | After | Improvement | Regression | Verdict |
|---|---|---:|---:|---:|---|---|
| S0 | Baseline | | | | | BASELINE |
| S1 | Backdrop blur | | | | | |
| S2 | QTabPanels swipeable | | | | | |
| S3A | Local blocker | | | | | |
| S3B | Global blocker | | | | | |
| S3C | Combined blockers | | | | | |
| S4 | Persistence timer | | | | | |
| S5 | Columns Tool Panel | | | | | |
| S6 | Floating filter | | | | | |
| S7 | animateRows | | | | | |
| S8 | flex on other grid | | | | | |

---

# 25. Stop conditions

Có thể dừng investigation sớm nếu tìm được root cause có A/B/A verification rất mạnh và fix giải quyết hoàn toàn symptom.

Tuy nhiên vẫn nên test tối thiểu:

- S1 backdrop blur;
- S2/S3 gesture stack;
- S4 persistence timer.

Đây là ba nhóm nghi phạm độc lập có evidence trực tiếp trong source hiện tại.

---

# 26. Không được làm trong phase điều tra

Không:

- rewrite toàn bộ `NiceGUI_grid.py`;
- đổi AG Grid version ngay;
- đổi NiceGUI version ngay;
- remove Enterprise module ngay;
- chuyển framework;
- thêm virtualization custom;
- thêm debounce ngẫu nhiên vào pointer events;
- sửa nhiều theme/grid/tab features một lần;
- kết luận "AG Grid chậm" mà chưa isolate CherryStock wrapper behavior.

AG Grid phải được benchmark trong context tối giản trước khi quy lỗi cho library.

---

# 27. Nếu tất cả scenario trên không giải quyết được

Thực hiện Phase 2.

## 27.1. Minimal AG Grid reproduction

Tạo page tạm chỉ chứa:

~~~text
NiceGUI
└── AG Grid
    ├── same rowData
    ├── same columnDefs
    └── no tabs / no dashboard card / no persistence / no sideBar
~~~

So sánh với Screener.

Nếu minimal grid mượt:

~~~text
root cause nằm trong CherryStock wrapper/layout/integration
~~~

Nếu minimal grid vẫn lag:

~~~text
investigate AG Grid/NiceGUI/browser/row-column scale/version
~~~

---

## 27.2. Scale test

Test matrix:

~~~text
Rows:     20 / 100 / 500 / full
Columns:  10 / 25 / 50 / full
~~~

Mục tiêu xác định lag scale theo:

- rows;
- columns;
- hidden column model;
- tool panel;
- renderer/filter complexity.

---

## 27.3. Browser comparison

Test:

- Chrome;
- Edge;
- Firefox nếu AG Grid/NiceGUI support behavior tương đương.

Nếu chỉ một Chromium profile lag, kiểm tra:

- browser extensions;
- hardware acceleration;
- GPU driver;
- device scale factor.

---

# 28. Root Cause Report cuối cùng

Sau khi hoàn tất, cập nhật ngay trong file này:

~~~text
ROOT CAUSE REPORT
=================

Date:
Commit tested:
Tester:

Primary root cause:
Secondary contributors:

Evidence:
1.
2.
3.

Rejected hypotheses:
1.
2.

Final code changes:
1.
2.
3.

Performance before:
Performance after:

Regression status:
Automated tests:
Manual tests:

Remaining known limitations:
~~~

Không merge performance fix final nếu Root Cause Report chưa được điền.

---

# 29. Current investigation status

Tại thời điểm tạo tài liệu:

- static source review: DONE;
- hypotheses identified: DONE;
- baseline runtime measurement: NOT RUN;
- isolated scenarios: NOT RUN;
- root cause: NOT YET CONFIRMED;
- production fix: NOT YET APPLIED.

Lý do chưa đánh dấu runtime result:

Tài liệu được tạo từ repository review. Việc xác định root cause performance cần chạy CherryStock trong browser local và record interaction thực tế. Local agent/developer phải thực hiện sequence ở trên và cập nhật bảng kết quả.

---

# 30. Completion criteria

Investigation chỉ hoàn tất khi:

- [ ] S0 baseline có kết quả;
- [ ] S1 đã test;
- [ ] S2/S3 đã test;
- [ ] S4 đã test;
- [ ] mọi thay đổi được isolate;
- [ ] ít nhất một hypothesis có A/B/A evidence hoặc tất cả bị reject;
- [ ] root cause report được điền;
- [ ] final fix chỉ giữ thay đổi có evidence;
- [ ] resize mượt đạt mức chấp nhận;
- [ ] saved state vẫn hoạt động;
- [ ] filters/saved views vẫn hoạt động;
- [ ] tabs không regression;
- [ ] dark/light theme không regression;
- [ ] `python -m pytest tests -v` được chạy;
- [ ] commit final ghi rõ root cause + fix + test evidence.
