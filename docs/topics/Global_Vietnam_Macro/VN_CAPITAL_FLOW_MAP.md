# Bản đồ dòng vốn Việt Nam: quốc tế → trung gian tài chính → nền kinh tế → thị trường tài sản

**Ngày lập:** 2026-10-24 · **Loại:** Khung nghiên cứu kinh tế vĩ mô / capital flow mapping · **Trạng thái:** Mô hình khái niệm, **không phải thống kê tỷ trọng vốn thực tế**.

## 1. Nguyên tắc đọc sơ đồ

- **VIFC (Vietnam International Financial Centre)** được nghiên cứu như **hạ tầng pháp lý, dịch vụ, sản phẩm và kết nối huy động vốn quốc tế**, không phải một quỹ ngân sách hay một tổ chức tự động cấp phát vốn. Không được cộng VIFC như một nguồn vốn độc lập bên cạnh FDI/FII/vay nợ, vì sẽ **đếm trùng**.
- Phân biệt **dòng vốn sơ cấp** (doanh nghiệp/chính phủ thực nhận khi phát hành, vay hoặc nhận đầu tư), **giao dịch thứ cấp** (tiền đổi chủ giữa nhà đầu tư), **tín dụng** (ngân hàng tạo khoản vay kèm nghĩa vụ nợ), và **chi tiêu ngân sách**.
- Dòng vốn xuyên biên giới có **chiều vào và chiều ra**; lợi nhuận, cổ tức, lãi vay, trả nợ gốc và thoái vốn làm thay đổi dòng ròng. Tiền có thể chuyển qua ngân hàng hoặc hạ tầng tài chính mà không tạo thêm vốn thực.
- BĐS, cổ phiếu, trái phiếu là **tài sản/kênh huy động và giao dịch**; doanh nghiệp sản xuất, hộ gia đình, dự án hạ tầng là **bên sử dụng vốn cuối cùng**. Không cộng toàn bộ giá trị giao dịch chứng khoán/BĐS vào vốn đầu tư thực.
- Sơ đồ dưới đây là **mối quan hệ**, độ rộng mũi tên **không biểu thị tỷ trọng**. Để tính tỷ trọng phải xác định kỳ, mẫu số và dữ liệu thực.

## 2. Sơ đồ tổng thể: nguồn → kênh → nơi sử dụng vốn

```mermaid
flowchart TB
  subgraph G["NGUỒN VỐN QUỐC TẾ"]
    FDI["FDI: vốn góp / dự án / M&A"]
    FII["Đầu tư gián tiếp: cổ phiếu, trái phiếu, quỹ"]
    LOAN["Vay quốc tế / tài trợ thương mại / ODA"]
    REMIT["Kiều hối / thu nhập, thanh toán quốc tế"]
  end
  IFC["VIFC: hạ tầng pháp lý + dịch vụ tài chính + kết nối nhà đầu tư\nKHÔNG phải quỹ phân bổ vốn"]
  subgraph D["NGUỒN VÀ ĐỊNH CHẾ TRONG NƯỚC"]
    SAVE["Tiết kiệm hộ gia đình / tiền gửi"]
    RETAIN["Lợi nhuận giữ lại / vốn chủ doanh nghiệp"]
    TAX["Thuế, phí, thu ngân sách"]
    BANK["Ngân hàng / tổ chức tín dụng"]
    FUNDS["Quỹ đầu tư / bảo hiểm / hưu trí / công ty chứng khoán"]
    STATE["Ngân sách nhà nước / đầu tư công"]
  end
  subgraph P["KÊNH HUY ĐỘNG SƠ CẤP"]
    CREDIT["Cho vay doanh nghiệp / hộ gia đình / thế chấp"]
    BOND["Trái phiếu doanh nghiệp phát hành mới"]
    EQUITY["IPO / phát hành thêm cổ phiếu / góp vốn"]
    GOVB["Trái phiếu chính phủ"]
  end
  subgraph U["NƠI SỬ DỤNG VỐN CUỐI CÙNG"]
    PROD["Sản xuất, xuất khẩu, công nghệ, logistics"]
    RE["Dự án BĐS / xây dựng / nhà ở"]
    INFRA["Hạ tầng, năng lượng, giao thông"]
    HOUSE["Tiêu dùng, mua nhà, hoạt động hộ gia đình"]
  end
  subgraph S["THỊ TRƯỜNG THỨ CẤP — CHUYỂN NHƯỢNG TÀI SẢN"]
    STOCK["Giao dịch cổ phiếu niêm yết"]
    TBOND["Giao dịch trái phiếu đang lưu hành"]
    PROP["Mua bán BĐS hiện hữu"]
  end
  FDI --> IFC
  FII --> IFC
  LOAN --> IFC
  IFC --> BANK
  IFC --> FUNDS
  IFC --> BOND
  IFC --> EQUITY
  FDI --> PROD
  FDI --> RE
  LOAN --> BANK
  REMIT --> SAVE
  SAVE --> BANK
  SAVE --> FUNDS
  RETAIN --> PROD
  RETAIN --> RE
  TAX --> STATE
  BANK --> CREDIT
  FUNDS --> BOND
  FUNDS --> EQUITY
  FUNDS --> GOVB
  STATE --> INFRA
  GOVB --> STATE
  CREDIT --> PROD
  CREDIT --> RE
  CREDIT --> HOUSE
  BOND --> PROD
  BOND --> RE
  BOND --> INFRA
  EQUITY --> PROD
  EQUITY --> RE
  EQUITY --> INFRA
  FII --> STOCK
  FII --> TBOND
  SAVE --> STOCK
  SAVE --> PROP
  STOCK -. "chủ yếu đổi chủ; không tự cấp vốn cho DN" .-> EQUITY
  TBOND -. "giá / lợi suất tác động phát hành mới" .-> BOND
  PROP -. "giá / thanh khoản ảnh hưởng thế chấp và dự án" .-> RE
```

**Lưu ý kỹ thuật:** Mũi tên từ giao dịch thứ cấp về kênh sơ cấp là **tác động gián tiếp thông qua giá, định giá, thanh khoản**, không phải dòng tiền tự động chảy vào doanh nghiệp. Một số dòng vốn quốc tế có thể đi thẳng tới doanh nghiệp, không bắt buộc qua VIFC. Các mũi tên vào VIFC chỉ biểu thị **kênh có thể được hỗ trợ**, không hàm ý tất cả FDI/FII/ODA thực tế phải đi qua trung tâm này.

## 3. Bốn vòng tuần hoàn vốn quan trọng

### A. Vòng tín dụng ngân hàng
Tiền gửi/vốn ngân hàng → cấp tín dụng doanh nghiệp, BĐS, hộ gia đình → đầu tư/sản xuất/mua nhà → doanh thu, thu nhập → trả nợ gốc/lãi → ngân hàng tái phân bổ. **Không đồng nhất tăng trưởng tín dụng với dòng tiền ròng vào chứng khoán.** Ngân hàng tạo tiền gửi khi giải ngân tín dụng trong hệ thống; mô tả trên là khung luồng sử dụng vốn, không phải cơ chế nhân quả đơn giản tiền gửi có trước khoản vay.

### B. Vòng trái phiếu doanh nghiệp
Nhà đầu tư/quỹ/ngân hàng (trong giới hạn pháp lý) → mua **trái phiếu phát hành sơ cấp** → doanh nghiệp nhận vốn → dự án/vốn lưu động/tái cấp vốn → trả coupon, gốc hoặc tái phát hành. Mua bán trái phiếu **thứ cấp** không cấp tiền trực tiếp cho tổ chức phát hành.

### C. Vòng thị trường cổ phiếu
Nhà đầu tư → **IPO/phát hành thêm** → doanh nghiệp nhận vốn chủ → đầu tư và tăng năng lực sản xuất. Với **khớp lệnh cổ phiếu hiện hữu**, tiền chủ yếu chuyển giữa người mua và người bán; giá cổ phiếu vẫn ảnh hưởng chi phí vốn, khả năng huy động mới và tài sản bảo đảm.

### D. Vòng vốn nhà nước và quốc tế
Thuế + phát hành TPCP + nguồn hợp pháp khác → ngân sách/đầu tư công → hạ tầng → năng suất, logistics, việc làm → thu nhập và nguồn thu thuế. FDI góp vốn trực tiếp vào dự án/doanh nghiệp; FII có thể tham gia phát hành sơ cấp hoặc mua bán thứ cấp; vay quốc tế đi kèm nghĩa vụ trả nợ. Cần theo dõi **dòng ròng** và rủi ro tỷ giá.

## 4. Bảng phân loại kênh vốn, nơi đến và dữ liệu cần đo

| Kênh | Bên cấp vốn | Bên nhận vốn trực tiếp | Chỉ số cần theo dõi | Cảnh báo |
|---|---|---|---|---|
| FDI | Nhà đầu tư nước ngoài | DN/dự án nhận góp vốn, M&A | FDI đăng ký, giải ngân, vốn góp/M&A | Đăng ký khác giải ngân; M&A không nhất thiết là CAPEX mới |
| FII | Quỹ/NĐT nước ngoài | DN khi phát hành; NĐT bán khi giao dịch thứ cấp | Mua bán ròng, sở hữu, phát hành | Mua ròng trên sàn ≠ vốn mới vào DN |
| Vay nước ngoài / ODA | Chủ nợ/tổ chức tài trợ | Chính phủ/DN/dự án | Giải ngân, trả nợ, lãi, kỳ hạn, FX | Nợ gốc và chi phí vốn |
| Tín dụng ngân hàng | Ngân hàng | DN, hộ gia đình | Dư nợ và tăng trưởng tín dụng theo ngành, NPL | Dư nợ là stock, giải ngân là flow |
| TPDN sơ cấp | Trái chủ | DN phát hành | Giá trị phát hành, đáo hạn, mua lại, lãi suất | Tái cấp vốn không đồng nghĩa đầu tư mới |
| Cổ phiếu sơ cấp | NĐT | DN phát hành | IPO, phát hành thêm, tiền thu ròng | Khác giá trị giao dịch HOSE/HNX/UPCoM |
| TPCP | Trái chủ | Kho bạc/NSNN | Phát hành ròng, kỳ hạn, lợi suất, giải ngân ĐTC | Phát hành gộp khác vay ròng |
| Giao dịch BĐS | Người mua / ngân hàng tài trợ | Chủ tài sản bán; chủ đầu tư nếu bán sơ cấp | Giao dịch sơ/thứ cấp, tín dụng BĐS, giá | Bán lại tài sản không phải xây dựng mới |
| VIFC | Không phải nguồn vốn độc lập | Hệ sinh thái hỗ trợ giao dịch/huy động | Số tổ chức, sản phẩm, phát hành/huy động qua trung tâm | Tránh đếm trùng FDI/FII/vay |

## 5. Có thể tính “phân bổ vốn” như thế nào?

**Chưa có tỷ lệ thực tế được kiểm chứng trong transcript**, nên **không gán** ví dụ như “30% vào BĐS, 20% vào chứng khoán”. Có thể dùng ba góc nhìn độc lập:

1. **Theo nguồn vốn mới:** FDI giải ngân, phát hành cổ phiếu sơ cấp, TPDN phát hành ròng, giải ngân vốn đầu tư công, tín dụng giải ngân ròng… **Không cộng máy móc** vì các nguồn có thể tài trợ lẫn nhau hoặc phản ánh cùng một khoản đầu tư.
2. **Theo nơi sử dụng vốn cuối cùng:** đầu tư vào sản xuất, BĐS, hạ tầng, công nghệ, tiêu dùng… phù hợp hơn để hiểu cơ cấu kinh tế, nhưng cần số liệu sử dụng vốn thực tế của bên nhận.
3. **Theo biến động tài sản tài chính:** dư nợ tín dụng, vốn hóa cổ phiếu, giá trị trái phiếu lưu hành, AUM, giá trị giao dịch. Đây là **stocks/turnover**, không phải dòng vốn đầu tư mới; phải thể hiện ở dashboard riêng.

Công thức nghiên cứu gợi ý (chỉ khi các hạng mục loại trừ đếm trùng và cùng phạm vi):

`Allocation_Share_i,t = Verified_Final_Use_Flow_i,t / Sum(Verified_Final_Use_Flow_j,t)`

Cần công bố: đơn vị (tỷ VND/USD), kỳ (quý/năm), danh nghĩa hay thực, flow hay stock, gross hay net, nguồn, ngày cập nhật, phương pháp phân bổ và phần **Unallocated/Unknown**.

## 6. Truyền dẫn tới các lớp tài sản / chế độ thị trường

| Cú sốc / thay đổi | Kênh truyền dẫn khả dĩ | Tài sản/ngành theo dõi | Điều kiện xác nhận |
|---|---|---|---|
| FDI và đơn hàng xuất khẩu tăng | CAPEX, thuê KCN, logistics, thu nhập | KCN, cảng, sản xuất, ngân hàng | FDI giải ngân, xuất khẩu, PMI, TEU |
| Tín dụng tăng nhanh | Chi phí vốn, doanh số, đòn bẩy | Ngân hàng, BĐS, tiêu dùng | Phân bổ tín dụng, lãi suất, NPL |
| TPDN hồi phục | Tái cấp vốn, dự án được tài trợ | BĐS, xây dựng, DN phát hành | Phát hành ròng, đáo hạn, spread |
| Lãi suất giảm | Chi phí vốn/định giá tài sản | Trái phiếu, cổ phiếu, BĐS | Lãi suất thực, thanh khoản, tín dụng |
| VIFC triển khai sản phẩm thực | Mở rộng kênh huy động và dịch vụ | Ngân hàng, chứng khoán, quỹ, fintech | Giấy phép, giao dịch, vốn huy động thực |
| Dòng vốn ngoại đảo chiều | FX, thanh khoản, định giá | Cổ phiếu, trái phiếu, tỷ giá | Dòng ròng, dự trữ, FX, lợi suất |
| Đầu tư công tăng giải ngân | Đơn hàng, hạ tầng, năng suất | Xây dựng, vật liệu, logistics | Giải ngân thực, tiến độ dự án |

**Không khẳng định quan hệ nhân quả chỉ từ tương quan**; cần kiểm soát chu kỳ kinh tế, độ trễ, yếu tố chính sách và giá đã phản ánh kỳ vọng.

## 7. Kiến trúc dữ liệu đề xuất cho CherryStock

**Tên feature/topic:** `VN_CAPITAL_FLOW_MAP`.

- `dim_Capital_Flow_Channel`: Channel_ID, Channel_Type, Source_Sector, Intermediary, Destination_Sector, Primary_Secondary, Debt_Equity, Gross_Net_Rule, Double_Count_Risk.
- `fact_VN_Capital_Flow`: Period, Frequency, Channel_ID, Amount, Currency, Unit, Flow_Stock, Gross_Net, Sector, Source_URL, Published_At, Observed_At, Data_Status.
- `fact_VN_Financial_Stock`: Period, Indicator, Outstanding_Amount, Currency, Source_URL, Data_Status.
- `map_Capital_Flow_Market_Exposure`: Channel_ID, Industry, Ticker, Exposure_Type, Evidence, Confidence, Review_Date.
- Dashboard: **Sankey** nguồn → trung gian → bên nhận vốn (chỉ dựng khi có dữ liệu đã đối soát), **time series** dòng ròng, **stock vs flow**, **funding stress** (TPDN đáo hạn, spread, tín dụng, tỷ giá), và **watchlist exposure**.

**Chỉ báo ưu tiên nhập trước:** FDI giải ngân, tín dụng theo ngành, TPDN phát hành/đáo hạn/mua lại, phát hành cổ phiếu sơ cấp, phát hành TPCP ròng, giải ngân đầu tư công, dòng mua bán ròng khối ngoại, lãi suất liên ngân hàng/trái phiếu, tỷ giá USD/VND.

**Nguồn cần kiểm chứng khi triển khai dữ liệu:** NHNN (tín dụng, lãi suất), Bộ Tài chính/Kho bạc (ngân sách, TPCP), Cục Thống kê (đầu tư, FDI, GDP), cơ quan quản lý chứng khoán và sở giao dịch (phát hành, giao dịch), báo cáo doanh nghiệp, dữ liệu thị trường trái phiếu có phương pháp rõ ràng. Không lấy số liệu phát biểu trong podcast làm chuỗi dữ liệu chính thức.

## 8. Cơ sở từ cuộc trao đổi về VIFC

Podcast *Vietnam Innovators – Vietnam 2.0, EP 394*, [This Is Why Vietnam Built An International Financial Center](https://www.youtube.com/watch?v=_egJXqDKL-U) (transcript tự động):

- Khoảng **10:00**: xây dựng IFC là chương trình dài hạn, khoảng 10 năm, không phải 1–2 năm.
- Khoảng **19:00–21:00**: ưu tiên ngân hàng, quản lý tài sản/quỹ, trái phiếu doanh nghiệp và hạ tầng giao dịch hàng hóa.
- Khoảng **30:00–36:00**: Thủ Thiêm và phân biệt hiện diện vật lý với tư cách tham gia pháp lý.
- Khoảng **49:00–52:00**: sandbox pháp lý cho đổi mới tài chính.

**Phân loại:** Những ý trên là **phát biểu/kỳ vọng của khách mời**, không phải số liệu thực tế về lượng vốn VIFC đã huy động hay phân bổ. Toàn bộ sơ đồ và cơ chế truyền dẫn trong tài liệu là **khung phân tích do CherryStock đề xuất**, cần kiểm định và đối soát.

**Liên quan:** [README](README.md) · [Dự báo từ 2027](DU_BAO_2027_TRO_DI.md) · [Global Champions 2030](VN_GLOBAL_CHAMPIONS_2030.md).
