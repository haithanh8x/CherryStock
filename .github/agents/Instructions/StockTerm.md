# Giao Dịch Chủ Động AC 
Trong nền tảng phân tích tài chính FireAnt (cũng như trong phân tích dòng tiền Intraday nói chung), **Giao dịch chủ động** là thuật ngữ dùng để chỉ các lệnh mua hoặc bán được khớp **ngay lập tức** bằng cách ăn thẳng vào các mức giá đangchờ sẵn trên sổ lệnh (Order Book).
Số liệu này phản ánh sự quyết liệt của dòng tiền tại một thời điểm: bên mua hay bên bán đang "sốt ruột" và chấp nhận khớp lệnh bất chấp hơn.
Giao dịch chủ động được chia làm 2 loại rõ rệt:
### 1. Mua chủ động (Buy Up / BU)
* **Định nghĩa:** Là khi người mua chấp nhận trả mức giá mà **bên bán đang treo chờ sẵn** (ăn thẳng vào các mức Giá bán 1, Giá bán 2, Giá bán 3 trên bảng điện) để lệnh được khớp ngay lập cứ mà không cần chờ đợi.
* **Ý nghĩa:** Thể hiện lực cầu quyết liệt. Người mua kỳ vọng giá cổ phiếu sẽ còn tiếp tục tăng cao hơn nữa, nên họ sẵn sàng mua đuổi bằng mọi giá.
### 2. Bán chủ động (Sell Down / SD)

* **Định nghĩa:** Là khi người bán chấp nhận hạ giá xuống bằng mức giá mà **bên mua đang treo chờ sẵn** (bán thẳng vào các mức Giá mua 1, Giá mua 2, Giá mua 3 trên bảng điện) để thoát hàng ngay tức thì.
* **Ý nghĩa:** Thể hiện áp lực cung mạnh mẽ. Người bán lo ngại giá cổ phiếu sẽ tiếp tục giảm sâu, hoặc có nhu cầu rút vốn gấp nên chấp nhận bán hạ giá để được khớp luôn.
## Ứng dụng chỉ số BU/SD trên FireAnt trong phân tích
Khi xem tab "Dòng tiền" hoặc "Mức giá" của một cổ phiếu trên FireAnt, bạn sẽ thấy biểu đồ hình quạt hoặc thanh đo tỷ lệ giữa Mua chủ động (thường màu xanh) và Bán chủ động (thường màu đỏ).
> **Tỷ lệ $BU / SD$ (Mua chủ động / Bán chủ động):**
* **$BU / SD > 1$:** Bên mua chủ động chiếm ưu thế $\rightarrow$ Dòng tiền đang đẩy vào, giá có xu hướng dễ tăng.
* **$BU / SD < 1$:** Bên bán chủ động chiếm ưu thế $\rightarrow$ Áp lực chốt lời hoặc cắt lỗ lớn, giá có xu hướng dễ giảm.
* **Tỷ lệ cao đột biến (Từ 2 lần trở lên):** Thường là tín hiệu của "Big Boys" (cá mập, tạo lập) đang ra tay gom hàng quyết liệt hoặc xả hàng dứt khoát, là một chỉ báo rất đáng để theo dõi trong phiên.

# Giao Dịch Cung Cầu CC
Trong FireAnt, **Giao dịch cung cầu** (thường được hiển thị trực quan qua **Biểu đồ Cung cầu** hoặc **Nhiệt kế Cung cầu** trong phiên) là chỉ số đo lường **khối lượng lệnh đặt chờ thực tế** của bên mua và bên bán tại một thời điểm, chứ không phải các lệnh đã khớp.
Nếu như *Giao dịch chủ động* (BU/SD) phản ánh những gì **đã xảy ra** (lệnh đã khớp), thì *Giao dịch cung cầu* phản ánh **tâm lý chờ đợi và kỳ vọng** (lệnh đang treo) của thị trường.
Chỉ số này được tính toán dựa trên toàn bộ độ sâu của sổ lệnh (Order Book), chia thành hai vế rõ rệt:
### 1. Tổng Cầu (Khối lượng Mua chờ)
* **Định nghĩa:** Là tổng khối lượng cổ phiếu mà nhà đầu tư đang đặt lệnh mua ở tất cả các mức giá thấp hơn giá khớp hiện tại (đang xếp hàng chờ mua).
* **Ý nghĩa:** Đại diện cho lực đỡ của thị trường. Cầu càng dày cho thấy vùng giá phía dưới có lực gom hàng tốt, nhà đầu tư sẵn sàng "kê lệnh" để mua tích lũy.
### 2. Tổng Cung (Khối lượng Bán chờ)
* **Định nghĩa:** Là tổng khối lượng cổ phiếu mà nhà đầu tư đang đặt lệnh bán ở tất cả các mức giá cao hơn giá khớp hiện tại (đang xếp hàng chờ bán).
* **Ý nghĩa:** Đại diện cho áp lực kháng cự phía trên. Cung càng lớn cho thấy lượng hàng chốt lời hoặc kẹp hàng muốn thoát ra ở vùng giá cao rất nhiều.
## Cách đọc chỉ số Cung - Cầu trên FireAnt để "đọc vị" thị trường
FireAnt thường cụ thể hóa dữ liệu này bằng một thanh đo tỷ lệ phần trăm (hoặc biểu đồ cột) Cung vs Cầu. Bạn có thể phân tích nhanh dựa trên các trạng thái sau:
* **Cầu > Cung (Thanh màu xanh dài hơn):** Lực mua chờ áp đảo. Tâm lý thị trường chung đang kỳ vọng cổ phiếu có xu hướng tăng hoặc có bệ đỡ giá rất vững chắc ở phía dưới.
* **Cung > Cầu (Thanh màu đỏ dài hơn):** Lượng hàng chờ bán đè nặng phía trên. Điều này tạo ra áp lực tâm lý khiến giá khó bứt phá ngay lập tức nếu không có một dòng tiền cực mạnh (Mua chủ động) vào "quét sạch" các mức giá cao này.

> **Lưu ý quan trọng khi phân tích (Bẫy hủy/lệnh ảo):**
> Vì đây là lệnh *chờ khớp*, các "Big Boys" (đội lái, mập) hoàn toàn có thể sử dụng thủ thuật đặt các lệnh mua/bán với khối lượng cực lớn ở các mức giá xa (lệnh ảo) để làm lệch cán cân Cung - Cầu, nhằm tạo tâm lý FOMO hoặc hoảng loạn cho nhà đầu tư cá nhân, sau đó hủy lệnh trước khi giá chạm tới. Do đó, bạn nên kết hợp chỉ số Cung Cầu với **Giao dịch chủ động** để xem dòng tiền thực tế có chịu "xuống tiền" khớp lệnh hay không.