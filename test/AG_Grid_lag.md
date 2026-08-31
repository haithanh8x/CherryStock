# AG Grid Column Resize Lag — Root Cause Investigation & Fix Plan

> **Repository:** CherryStock  
> **Primary scope:** `src/webapp/NiceGUI_grid.py`, `src/webapp/NiceGUI_chart.py`, `src/Presentation/theme.py`  
> **Target grid:** Stock Screener created by `create_market_grid()`  
> **Problem:** kéo resize độ rộng column trong AG Grid có cảm giác giật, khựng, không theo chuột mượt như native AG Grid.  
> **Purpose of this document:** xác định **nguyên nhân gốc** bằng thử nghiệm tuần tự, sau đó mới áp dụng fix lâu dài.

---

# 1. Problem statement

Trong CherryStock, AG Grid ở tab Screener cho phép resize column:

```python
"defaultColDef": {
    "sortable": True,
    "filter": True,
    "resizable": True,
    "minWidth": 70,
    "floatingFilter": True,
}
```

và được render bằng:

```python
grid = ui.aggrid(
    grid_options,
    theme=get_ag_grid_theme(),
    auto_size_columns=False,
    modules="enterprise",
)
```

Triệu chứng quan sát được:

- kéo divider giữa hai column nhưng column không bám chuột liên tục;
- có cảm giác khựng theo từng nhịp;
- đôi khi drag nhanh thì width cập nhật chậm hơn con trỏ;
- grid vẫn hoạt động đúng chức năng nhưng interaction không mượt;
- vấn đề rõ hơn ở Stock Screener so với grid đơn giản.

Mục tiêu không chỉ là “làm cho đỡ lag”, mà phải xác định được:

1. bottleneck nằm ở browser rendering;
2. bottleneck nằm ở Quasar/NiceGUI event propagation;
3. bottleneck nằm ở Python/WebSocket round-trip;
4. bottleneck nằm ở state persistence;
5. bottleneck nằm ở AG Grid Enterprise feature overhead;
6. hoặc nhiều yếu tố cộng hưởng.

---

# 2. Nguyên tắc điều tra

## 2.1. Không fix nhiều thứ cùng lúc

Mỗi test chỉ thay **một biến**.

Sai cách:

```text
bỏ blur
+ bỏ swipeable
+ bỏ floating filter
+ bỏ persistence
+ đóng side panel
=> thấy mượt
=> không biết nguyên nhân nào thực sự gây lag
```

Đúng cách:

```text
Baseline
  ↓
Test A: chỉ bỏ backdrop-filter
  ↓
ghi kết quả
  ↓
rollback nếu không cải thiện đáng kể
  ↓
Test B: chỉ bỏ swipeable
  ↓
ghi kết quả
...
```

## 2.2. Mỗi test phải có cùng điều kiện

Cố định:

- cùng browser;
- cùng viewport;
- cùng dữ liệu;
- cùng số column visible;
- cùng tab Screener;
- cùng zoom browser 100%;
- không mở DevTools trong test cảm nhận thông thường;
- nếu dùng Performance profiler thì profile ở vòng riêng;
- kéo cùng một column, ví dụ `Company Name` hoặc `Industry`;
- kéo tối thiểu 5 lần trái/phải trong 3–5 giây.

## 2.3. Kết quả phải được phân loại

Mỗi scenario ghi một trong bốn mức:

| Kết quả | Ý nghĩa |
|---|---|
| **No change** | không phải root cause đáng kể |
| **Minor improvement** | yếu tố phụ |
| **Major improvement** | nghi phạm mạnh |
| **Problem disappears** | root cause hoặc thành phần chính của root cause |

---

# 3. Baseline trước khi thay đổi code

Trước mọi fix, chạy baseline.

## 3.1. Test thao tác

1. Start CherryStock.
2. Mở tab **Screener**.
3. Đảm bảo Columns Tool Panel đang ở trạng thái mặc định hiện tại.
4. Chọn column có width tương đối lớn, ví dụ:
   - Company Name;
   - Industry;
   - Book Value.
5. Kéo divider liên tục trái/phải.
6. Lặp lại 5 lần.
7. Ghi lại:
   - cảm giác drag có bám chuột không;
   - có khựng định kỳ không;
   - có lúc đứng hình >100 ms không;
   - scrollbar/header/body có repaint lệch nhau không.

## 3.2. Browser Performance profile

Dùng Chrome DevTools:

```text
Performance
→ Record
→ resize column liên tục 5 giây
→ Stop
```

Quan sát:

- Main thread activity;
- Long Task > 50 ms;
- Layout;
- Recalculate Style;
- Paint;
- Composite Layers;
- Event Handler;
- requestAnimationFrame;
- scripting time;
- rendering time.

Nếu thấy nhiều:

```text
Paint
Composite Layers
Layout
```

=> ưu tiên nghi ngờ CSS/rendering.

Nếu thấy nhiều:

```text
Event
Function Call
WebSocket / JS interaction
```

=> ưu tiên nghi ngờ event propagation / NiceGUI communication.

## 3.3. Baseline record template

```text
Date:
Commit SHA:
Browser:
Viewport:
Rows:
Visible columns:

Subjective smoothness: /10
Long tasks:
Largest long task:
Rendering/Paint:
Scripting:
Periodic stutter: Yes/No
Approx interval:
Notes:
```

---

# 4. Hypothesis A — CSS `backdrop-filter: blur(12px)`

## 4.1. Current code

File:

```text
src/Presentation/theme.py
```

CherryStock đang áp dụng:

```css
.dashboard-card {
    overflow: hidden;
    backdrop-filter: blur(12px);
}
```

Stock Screener được đặt trong card có class `dashboard-card`.

## 4.2. Vì sao có thể gây lag

Column resize tạo layout update liên tục.

Luồng có thể là:

```text
pointermove
    ↓
AG Grid đổi width
    ↓
header layout
    ↓
cell viewport layout
    ↓
horizontal content changes
    ↓
paint/composite
    ↓
backdrop-filter phải composite lại card
```

`backdrop-filter` là một hiệu ứng GPU/compositor tương đối đắt, đặc biệt khi:

- element lớn;
- nội dung bên trong thay đổi liên tục;
- grid cao ~1000 px;
- nhiều layer đang repaint.

AG Grid vốn tối ưu resize ở client, nhưng nếu parent container buộc browser composite lại một vùng lớn sau mỗi frame, cảm giác drag sẽ kém mượt.

---

## 4.3. Isolation test A

Chỉ tạm thời bỏ:

```css
backdrop-filter: blur(12px);
```

Thành:

```css
.dashboard-card {
    overflow: hidden;
}
```

Không thay bất kỳ AG Grid option nào.

### Test

1. Reload app hoàn toàn.
2. Vào Screener.
3. Resize cùng column baseline.
4. Record Performance 5 giây.
5. So sánh với baseline.

### Pass criterion

Nếu:

- drag rõ ràng bám chuột hơn;
- Paint/Composite giảm;
- long task giảm;
- smoothness tăng >= 2 điểm /10;

thì CSS blur là yếu tố đáng kể.

### Root-cause conclusion

- **Problem disappears:** blur là root cause chính.
- **Major improvement:** blur là một root cause lớn nhưng có thể còn bottleneck khác.
- **Minor/no improvement:** rollback và sang test B.

---

## 4.4. Fix lâu dài nếu A được xác nhận

### Option A1 — bỏ blur khỏi card chứa grid

Khuyến nghị.

Tạo class riêng:

```css
.dashboard-card {
    overflow: hidden;
}

.dashboard-card-glass {
    backdrop-filter: blur(12px);
}

.dashboard-data-grid-card {
    backdrop-filter: none;
}
```

Grid/data table không nên dùng glass effect nếu ưu tiên responsiveness.

### Option A2 — chỉ blur vùng header/card nhỏ

Giữ glass effect ở:

- metric cards;
- toolbar;
- navigation;

nhưng tránh blur quanh:

- AG Grid;
- ECharts canvas lớn;
- iframe chart lớn.

### Regression tests

- theme dark/light vẫn đúng;
- card border vẫn đúng;
- không thay đổi spacing;
- AG Grid không bị mất clipping;
- hover card vẫn hoạt động.

---

# 5. Hypothesis B — `QTabPanels swipeable` cạnh tranh với AG Grid drag

## 5.1. Current code

File:

```text
src/webapp/NiceGUI_chart.py
```

Hiện có:

```python
with ui.tab_panels(
    tabs,
    value="overview",
).classes(
    "w-full bg-transparent p-0"
).props(
    "animated keep-alive swipeable"
):
```

AG Grid nằm bên trong một swipeable panel.

## 5.2. Vì sao có thể gây lag

Column resize bản chất là horizontal pointer drag.

Quasar `QTabPanels swipeable` cũng quan tâm tới horizontal gesture.

Do đó cùng một pointer sequence có thể đi qua nhiều tầng:

```text
pointerdown
pointermove
pointermove
pointermove
...
```

AG Grid muốn dùng chuỗi event này để resize.

Parent QTabPanels cũng có gesture machinery phục vụ swipe tab.

Ngay cả khi cuối cùng tab không bị đổi, việc có thêm recognizer/handler trên event path vẫn tạo overhead và có thể gây interaction conflict.

---

## 5.3. Isolation test B

Chỉ bỏ `swipeable`.

Từ:

```python
.props("animated keep-alive swipeable")
```

thành:

```python
.props("animated keep-alive")
```

Không sửa blocker trong test này.

### Test

1. Reload.
2. Vào Screener.
3. Resize column giống baseline.
4. Quan sát:
   - drag;
   - horizontal scroll;
   - click cell;
   - resize pinned/unpinned column.
5. Performance profile 5 giây.

### Pass criterion

Nếu resize mượt rõ rệt sau khi bỏ swipeable:

=> parent gesture recognizer là nguyên nhân quan trọng.

---

## 5.4. Fix lâu dài nếu B được xác nhận

Đối với desktop financial terminal, swipe đổi tab không có nhiều giá trị.

Khuyến nghị giữ:

```python
.props("animated keep-alive")
```

và điều hướng tab bằng:

- click tab;
- keyboard;
- explicit navigation.

### Regression tests

- click tab chuyển panel bình thường;
- keep-alive vẫn giữ state;
- chart không rebuild ngoài ý muốn;
- mobile vẫn dùng được tab;
- horizontal scrollbar AG Grid hoạt động bình thường.

---

# 6. Hypothesis C — Event blockers đang bắt quá nhiều `mousemove/pointermove`

## 6.1. Current code

File:

```text
src/webapp/NiceGUI_grid.py
```

Function:

```python
def _stop_parent_swipe(element: Any) -> None:
```

đăng ký nhiều event:

```python
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
```

mỗi event gọi:

```javascript
(event) => event.stopPropagation()
```

Ngoài ra còn có global blocker:

```python
_install_global_tab_swipe_blocker()
```

và JavaScript listener cho tất cả `.q-tab-panel`.

## 6.2. Vì sao có thể gây lag

Trong một drag 5 giây, browser có thể phát hàng trăm `pointermove` / `mousemove`.

Hiện một event có thể đi qua:

```text
AG Grid resize handler
   ↓
NiceGUI element event listener
   ↓
_stop_parent_swipe
   ↓
q-tab-panel listener
   ↓
Quasar event tree
```

Nếu `swipeable` đã được bỏ, phần lớn blocker desktop không còn cần thiết.

Mục tiêu lý tưởng:

```text
column resize drag
→ browser + AG Grid client side only
```

---

# 7. Isolation test C1 — bỏ grid-level mouse/pointer blocker

> Chỉ thực hiện sau Test B để tách biến.

Tạm thời không gọi:

```python
_stop_parent_swipe(grid)
```

Giữ global blocker nguyên trạng.

### Test

- resize;
- horizontal scroll;
- column move;
- click/selection;
- tab switching.

### Expected

Nếu mượt hơn:

=> grid-level event hooks có overhead.

Nếu tab vô tình swipe sau khi bỏ hook:

=> blocker từng giải quyết conflict thật, nhưng hướng đúng vẫn là bỏ `swipeable` thay vì chặn toàn bộ pointer stream.

---

# 8. Isolation test C2 — bỏ global QTabPanel blocker

Tạm disable:

```python
_install_global_tab_swipe_blocker()
```

Chỉ test sau khi `swipeable` đã tắt.

### Expected

Nếu tab không swipe nữa vì `swipeable` đã tắt, global blocker là không cần thiết.

### Fix lâu dài

Nếu B + C xác nhận:

1. bỏ `swipeable`;
2. xóa hoặc thu gọn `_stop_parent_swipe`;
3. xóa global blocker desktop;
4. chỉ giữ touch-specific handling nếu thực sự cần trên mobile.

---

# 9. Hypothesis D — `persist_state()` polling mỗi 1.5 giây gây periodic stutter

## 9.1. Current code

Cuối `create_market_grid()`:

```python
ui.timer(1.5, persist_state)
```

Function:

```python
async def persist_state(*, force: bool = False) -> None:
    grid_state = await grid.run_grid_method("getState")
    column_state = await grid.run_grid_method("getColumnState")
```

sau đó:

```python
signature = json.dumps(...)
```

và nếu state đổi:

```python
_save_session_grid_state(...)
```

cuối cùng ghi JSON xuống:

```text
Build/cache/stock_screener_grid_state.json
```

## 9.2. Vì sao resize đặc biệt nhạy với persistence

Resize column làm thay đổi `column_state.width`.

Nếu timer chạy giữa lúc drag:

```text
User drag
 ├─ width 181
 ├─ width 184
 ├─ width 190
 ├─ width 196
 │
 ├─ TIMER FIRES
 │    ├─ getState()
 │    ├─ getColumnState()
 │    ├─ WebSocket request/response
 │    ├─ JSON serialization
 │    ├─ compare signature
 │    └─ write file
 │
 ├─ width 203
 ├─ width 209
...
```

Triệu chứng điển hình:

- resize phần lớn thời gian tương đối ổn;
- cứ khoảng 1–2 giây lại khựng một nhịp;
- stutter mang tính periodic.

---

# 10. Isolation test D

Chỉ disable:

```python
ui.timer(1.5, persist_state)
```

Không bỏ restore state.

### Test

Kéo liên tục 10 giây.

Đặc biệt quan sát xem còn nhịp khựng gần chu kỳ 1.5 giây hay không.

### Pass criterion

Nếu periodic stutter biến mất:

=> polling persistence là root cause trực tiếp của nhịp khựng.

---

# 11. Fix lâu dài cho persistence

Không polling state trong lúc user interaction.

## 11.1. Target architecture

```text
User starts resize
    ↓
AG Grid client-side resize
    ↓
NO Python
NO WebSocket
NO disk write
    ↓
User releases mouse
    ↓
columnResized(event.finished == true)
    ↓
debounce
    ↓
persist state once
```

## 11.2. Event-driven candidates

Persist khi:

- column resized finished;
- column moved;
- column visible changed;
- sort changed;
- filter changed;
- row group changed;
- pivot changed.

Không persist cho mọi intermediate drag frame.

## 11.3. Debounce

Nên có debounce khoảng:

```text
300–800 ms
```

sau event cuối cùng.

Ví dụ conceptual logic:

```javascript
onColumnResized(event) {
    if (!event.finished) return;
    schedulePersist();
}
```

Không nhất thiết dùng đúng API trên nếu NiceGUI wrapper yêu cầu syntax khác; mục tiêu là behavior.

## 11.4. Persistence regression tests

1. Resize column.
2. Release.
3. Reload browser tab.
4. Width phải được restore.
5. Move column.
6. Reload.
7. Order phải được restore.
8. Hide/show.
9. Reload.
10. Visibility phải restore.
11. Filter.
12. Reload.
13. Filter state phải restore.

---

# 12. Hypothesis E — Enterprise Columns Tool Panel luôn mở

## 12.1. Current code

```python
"sideBar": {
    "toolPanels": [
        {
            "id": "columns",
            ...
            "toolPanel": "agColumnsToolPanel",
        }
    ],
    "defaultToolPanel": "columns",
    "position": "right",
}
```

Ngoài ra mỗi column có thể bật:

- row grouping;
- pivot;
- aggregation;
- values.

## 12.2. Vì sao có thể tăng resize cost

Stock Screener không chỉ có số cột đang nhìn thấy.

`_create_grouped_column_defs()` build definition từ toàn bộ DataFrame columns, bao gồm hidden columns.

Khi `vw_Ticker` tăng số indicator:

```text
GENERAL
FA
TA
MA20_D
MA50_D
MA100_D
MA200_D
RSI
MACD
...
```

Columns Tool Panel phải duy trì model tương ứng.

Nếu panel đang mở, UI của panel cũng có thể phải sync column width/state changes.

---

# 13. Isolation test E

Đóng tool panel mặc định.

Thay:

```python
"defaultToolPanel": "columns"
```

bằng cấu hình không auto-open panel.

Tùy AG Grid version, có thể:

- bỏ `defaultToolPanel`;
- hoặc set trạng thái sidebar đóng sau grid ready.

### Test

- resize;
- open sidebar bằng tay;
- resize khi sidebar đóng;
- resize khi sidebar mở.

### Interpretation

Nếu:

```text
sidebar closed = smooth
sidebar open   = lag
```

=> Tool Panel là overhead đáng kể.

### Fix

Default sidebar = closed.

Người dùng chỉ mở khi:

- chọn column;
- group;
- pivot;
- customize view.

---

# 14. Hypothesis F — `floatingFilter=True` trên mọi column

## 14.1. Current code

```python
"defaultColDef": {
    "filter": True,
    "floatingFilter": True,
}
```

## 14.2. Cơ chế

Header thường chỉ cần:

```text
column header
```

Floating filter tạo thêm component:

```text
column header
+
filter input/component
```

Resize phải layout cả:

- header;
- floating filter;
- filter icon;
- input;
- text;
- border.

Với nhiều visible columns, chi phí layout tăng.

---

# 15. Isolation test F

Tạm:

```python
"floatingFilter": False
```

Không thay filter capability.

### Test

- resize;
- sort;
- filter qua menu;
- filter selectors ngoài grid.

### Fix nếu xác nhận

Các option:

1. disable floating filter toàn bộ;
2. chỉ enable cho column quan trọng;
3. dùng external filters phía trên grid làm primary filter UI;
4. enable floating filters trong saved view chuyên phân tích.

CherryStock hiện đã có filter controls riêng phía trên grid cho Ticker/Stock/Industry, nên không nhất thiết mọi column đều có floating filter mặc định.

---

# 16. Hypothesis G — `animateRows=True`

## 16.1. Current code

```python
"animateRows": True
```

Animation không phải nghi phạm số 1 của column resize, nhưng với financial terminal, responsiveness quan trọng hơn animation.

## 16.2. Isolation test G

Tạm:

```python
"animateRows": False
```

### Expected

- nếu không thay đổi resize: giữ kết luận “not root cause”;
- nếu có improvement nhỏ: có thể giữ false như optimization phụ.

---

# 17. Hypothesis H — Flex sizing

## 17.1. Stock Screener hiện đã có mitigation

Trong `_create_grouped_column_defs()`:

```python
flex_value = column_def.pop("flex", None)
column_def.pop("maxWidth", None)
column_def["resizable"] = True
```

Comment hiện tại đã ghi rõ:

```text
Stock Screener ưu tiên manual sizing.
Flex có thể co giãn lại theo viewport,
vì vậy loại flex khỏi grid này.
```

Vì vậy đối với Stock Screener, `flex` **không phải nghi phạm chính ở code hiện tại**.

## 17.2. Nhưng phải kiểm tra grid khác

Trong các grid khác có thể vẫn có:

```python
{
    "minWidth": 170,
    "flex": 1,
}
```

Nếu lag xuất hiện ở R/S Level Details hoặc grid khác:

- test bỏ flex;
- chuyển thành width cố định;
- dùng manual resize.

---

# 18. Hypothesis I — quá nhiều column definitions / hidden columns

Ngay cả khi pagination = 20 rows, column model vẫn có thể lớn.

Đặc biệt khi source `vw_Ticker` ngày càng tích hợp nhiều indicator.

## Isolation test I

Tạo temporary minimal grid chỉ với:

```text
Ticker
Stock
Company Name
Industry
PE
EPS
ROE
```

Giữ toàn bộ option khác giống Screener.

### Interpretation

Nếu minimal grid cực mượt nhưng full grid lag:

=> số lượng column definitions / tool panel / filter components là yếu tố chính.

### Follow-up

Test lần lượt:

```text
10 columns
20 columns
40 columns
80 columns
all columns
```

Xác định điểm performance degradation.

---

# 19. Hypothesis J — rowData size

Pagination không đồng nghĩa browser chỉ biết 20 row.

Nếu `rowData` chứa toàn bộ dataset, client-side row model vẫn giữ toàn bộ rows.

Với số mã chứng khoán Việt Nam hiện tại đây có thể chưa phải vấn đề lớn, nhưng phải benchmark nếu:

- source tăng;
- pivot/grouping;
- nhiều calculated values;
- nhiều custom renderer.

## Isolation test J

Giữ full column set nhưng chỉ đưa 20–50 rows.

Nếu resize không thay đổi đáng kể:

=> rows không phải root cause.

Nếu cải thiện mạnh:

=> cần xem row model / renderer / value formatter.

---

# 20. Hypothesis K — valueFormatter / formatting cost

Field config có nhiều formatter:

```javascript
params => params.value.toLocaleString(...)
```

AG Grid thường không re-evaluate toàn bộ formatter trên mọi resize, nhưng layout/redraw có thể kích hoạt một số render path.

## Isolation test K

Temporary build cùng columns nhưng bỏ tất cả `:valueFormatter`.

Nếu không thay đổi:

=> loại trừ.

Nếu improvement:

=> profile formatter hot path, cân nhắc preformatted display fields hoặc formatter nhẹ hơn.

---

# 21. Recommended test order

Thứ tự dưới đây ưu tiên:

- thay đổi nhỏ;
- dễ rollback;
- xác suất cao;
- ít làm biến dạng behavior.

```text
BASELINE
   │
   ├─ A. Disable backdrop-filter
   │
   ├─ B. Disable QTabPanels swipeable
   │
   ├─ C1. Disable grid pointer blockers
   │
   ├─ C2. Disable global tab blockers
   │
   ├─ D. Disable 1.5s persistence polling
   │
   ├─ E. Close Enterprise Columns panel
   │
   ├─ F. Disable floatingFilter
   │
   ├─ G. Disable animateRows
   │
   ├─ I. Reduce column count
   │
   ├─ J. Reduce row count
   │
   └─ K. Remove valueFormatter
```

---

# 22. Decision tree

```text
Does removing backdrop-filter fix it?
 ├─ YES → optimize card CSS
 └─ NO
      ↓
Does removing swipeable fix it?
 ├─ YES → remove parent swipe gestures
 └─ NO
      ↓
Does removing pointer blockers fix it?
 ├─ YES → simplify event interception
 └─ NO
      ↓
Does removing 1.5s persistence timer remove periodic stutter?
 ├─ YES → convert persistence to event-driven
 └─ NO
      ↓
Does closing Columns panel help?
 ├─ YES → default sidebar closed
 └─ NO
      ↓
Does removing floating filters help?
 ├─ YES → selective floating filters
 └─ NO
      ↓
Does minimal-column grid become smooth?
 ├─ YES → column-model complexity
 └─ NO
      ↓
Profile browser main thread / GPU again
```

---

# 23. Root-cause matrix

| Hypothesis | Current CherryStock evidence | Expected symptom | Test priority |
|---|---|---|---|
| Backdrop blur | `.dashboard-card { backdrop-filter: blur(12px) }` | continuous repaint/composite lag | P0 |
| QTabPanels swipeable | `animated keep-alive swipeable` | horizontal drag conflict | P0 |
| Mouse/pointer blockers | local + global stopPropagation | drag event overhead | P0 |
| Persistence polling | `ui.timer(1.5, persist_state)` | periodic stutter ~1.5s | P0 |
| Columns Tool Panel | Enterprise + default open | header/column-model overhead | P1 |
| Floating filters | enabled globally | heavier header layout | P1 |
| animateRows | enabled | general UI overhead | P2 |
| Many columns | full DataFrame definitions | degradation with column count | P1 |
| Many rows | client-side rowData | degradation with dataset size | P2 |
| valueFormatter | multiple JS formatters | render/redraw CPU | P2 |
| Flex sizing | removed in Screener | unlikely in Screener | P3 |

---

# 24. Recommended target architecture

Đối với Stock Screener, interaction lý tưởng:

```text
Mouse / Pointer
      ↓
Browser
      ↓
AG Grid
      ↓
DOM width update
      ↓
requestAnimationFrame
```

Trong lúc drag KHÔNG nên có:

```text
Python callback
WebSocket state request
disk persistence
parent swipe recognizer
expensive backdrop compositing
full grid update()
```

Sau khi interaction hoàn thành:

```text
resize finished
    ↓
debounce
    ↓
capture column state
    ↓
persist once
```

---

# 25. Proposed final optimization package

Chỉ áp dụng sau khi test xác nhận.

## P0 — Interaction

- bỏ `swipeable` khỏi panel chứa AG Grid;
- bỏ mouse/pointer propagation blockers không còn cần;
- đảm bảo resize chạy client-side hoàn toàn.

## P0 — Rendering

- không dùng `backdrop-filter` trên card chứa AG Grid;
- tránh CSS filter/blur trên viewport lớn.

## P0 — Persistence

- bỏ polling `ui.timer(1.5, persist_state)`;
- persist theo event finished + debounce;
- không ghi file trong drag.

## P1 — AG Grid configuration

- Columns Tool Panel mặc định đóng;
- cân nhắc selective floating filter;
- `animateRows=False` cho terminal UI;
- giữ `auto_size_columns=False` để tránh layout tự động không cần thiết.

## P1 — Scale

- chỉ tạo column definitions cần thiết cho active analytical view nếu số columns tăng lớn;
- benchmark threshold theo 10/20/40/80/all columns.

---

# 26. Regression test suite sau khi fix

## 26.1. Column resize

- kéo chậm;
- kéo nhanh;
- kéo qua lại liên tục;
- resize pinned column;
- resize normal column;
- resize column sát minWidth.

Expected:

- width bám pointer;
- không có periodic freeze;
- header và body align.

## 26.2. Column move

- drag column sang vị trí khác;
- move qua pinned boundary nếu được phép;
- reload.

Expected:

- order được restore.

## 26.3. Column visibility

- hide/show từ Columns panel;
- reload.

Expected:

- visibility state đúng.

## 26.4. Filter

- external select filters;
- AG Grid filter;
- clear filters;
- saved filter preset.

Expected:

- không regression.

## 26.5. Saved views

- resize;
- move;
- pin;
- sort;
- group;
- pivot;
- save view;
- reload/load view.

Expected:

- state chính xác.

## 26.6. Tab behavior

Sau khi bỏ `swipeable`:

- click tabs;
- switch Overview → Screener → Portfolio → R/S;
- quay lại Screener.

Expected:

- grid state giữ;
- no accidental panel rebuild.

## 26.7. Horizontal scroll

- scrollbar kéo mượt;
- shift-wheel nếu browser hỗ trợ;
- trackpad horizontal scroll.

Expected:

- không đổi tab;
- không mất pointer interaction.

## 26.8. Theme

- cherry_dark;
- cherry_light.

Expected:

- contrast;
- border;
- background;
- hover;
- no visual regression sau khi bỏ blur.

---

# 27. Test result log

Sử dụng bảng này trong quá trình điều tra.

| Test | Change | Smoothness before | Smoothness after | Perf change | Result | Decision |
|---|---|---:|---:|---|---|---|
| Baseline | none |  |  |  |  |  |
| A | remove backdrop blur |  |  |  |  |  |
| B | remove swipeable |  |  |  |  |  |
| C1 | remove grid blockers |  |  |  |  |  |
| C2 | remove global blocker |  |  |  |  |  |
| D | disable 1.5s persistence |  |  |  |  |  |
| E | close Columns panel |  |  |  |  |  |
| F | floatingFilter=false |  |  |  |  |  |
| G | animateRows=false |  |  |  |  |  |
| I | minimal columns |  |  |  |  |  |
| J | minimal rows |  |  |  |  |  |
| K | remove formatters |  |  |  |  |  |

---

# 28. Root cause acceptance criteria

Chỉ kết luận root cause khi đạt ít nhất một trong các điều kiện:

1. single-variable change làm vấn đề biến mất;
2. single-variable change cải thiện rõ rệt và profiler xác nhận giảm bottleneck tương ứng;
3. bật lại biến đó làm lag quay trở lại;
4. kết quả lặp lại ít nhất 3 lần.

Quy trình xác nhận mạnh nhất:

```text
Baseline = lag
↓
Disable suspect = smooth
↓
Re-enable suspect = lag
↓
Disable suspect again = smooth
```

Đây là A/B/A/B validation.

---

# 29. Definition of Done

Issue AG Grid resize lag chỉ được xem là hoàn tất khi:

- resize column đạt cảm giác gần native AG Grid;
- không có stutter định kỳ;
- interaction không gọi server trong drag;
- saved column width vẫn restore sau reload;
- filter/view preset không regression;
- horizontal scroll không đổi tab;
- theme không regression;
- root cause đã được ghi vào bảng Test result log;
- fix cuối cùng chỉ giữ những thay đổi có bằng chứng performance.

---

# 30. Initial assessment from current code

Dựa trên code hiện tại, thứ tự nghi ngờ ban đầu:

```text
1. backdrop-filter: blur(12px)
2. QTabPanels swipeable + pointer/mouse blockers
3. persist_state polling mỗi 1.5 giây
4. Enterprise Columns Tool Panel mở mặc định
5. floatingFilter trên toàn bộ columns
6. animateRows
7. column count / hidden column model
8. row count / formatters
```

Lưu ý: đây là **hypothesis ranking**, chưa phải root-cause conclusion.

Root cause chỉ được xác nhận sau khi chạy tuần tự các scenario trong tài liệu này.

---

# 31. Recommended first execution sequence

Phiên test đầu tiên nên chạy đúng thứ tự:

```text
Run baseline
    ↓
Test A
    ↓
rollback/record
    ↓
Test B
    ↓
Test C1
    ↓
Test C2
    ↓
Test D
```

Bốn nhóm đầu đủ để kiểm tra các nghi phạm mạnh nhất mà không thay đổi business logic của Screener.

Nếu vẫn lag sau đó mới chạy:

```text
E → F → G → I → J → K
```

Mọi kết quả phải ghi vào **Test result log** để lần thay đổi tiếp theo dựa trên dữ liệu, không dựa trên cảm giác.
