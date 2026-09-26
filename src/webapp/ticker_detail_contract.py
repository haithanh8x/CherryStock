"""Read-only ticker detail contracts and Vietnamese field explanations."""
from __future__ import annotations

import math
import re
from datetime import date, datetime
from urllib.parse import urlencode

FIELDS = {
    "vw_Ticker_SmartMoney": [
        "Ticker",
        "Date",
        "ModelCode",
        "ModelVersion",
        "SmartMoneyScore",
        "ConfidenceScore",
        "MarketState",
        "FactorCoverage",
        "DataQualityStatus",
        "TradeAction",
        "TradeActionConfidenceScore",
        "FreshFlowScore",
        "RelativeLiquidityScore",
        "LiquidityAccelerationScore",
        "RelativeStrengthScore",
        "AccumulationScore",
        "AccumulationMemoryScore",
        "SupplyLockScore",
        "LimitUpScore",
        "TrendScore",
        "DistributionScore"
    ],
    "vw_Ticker_Movement_Profile": [
        "PriceMovementConfigCode",
        "PriceMovementModelVersion",
        "Timeframe",
        "PriceMovementConfigId",
        "ZigZagConfigId",
        "ZigZagConfigCode",
        "Ticker",
        "AsOfConfirmedAtDate",
        "ProfileLookbackSwings",
        "ConfirmedSwingCount",
        "LastSwingSeq",
        "LastSwingDirection",
        "LastSwingPct",
        "MedianUpSwingPct",
        "MedianDownSwingAbsPct",
        "MedianAbsSwingPct",
        "MedianTradingBars",
        "MedianAbsVelocityPctPerBar",
        "MedianATRNormalizedMove",
        "MedianPathEfficiency",
        "MedianDirectionalPersistenceRate",
        "DirectionalBias",
        "MovementCharacter",
        "CalculatedAt"
    ],
    "vw_Ticker_Movement_Context": [
        "MovementContextConfigId",
        "MovementContextConfigCode",
        "MovementContextModelVersion",
        "Timeframe",
        "PriceMovementConfigCode",
        "PriceMovementModelVersion",
        "ZigZagConfigCode",
        "Ticker",
        "ContextAsOfDate",
        "ProfileAsOfConfirmedAtDate",
        "CurrentLegAsOfDate",
        "ContextStatus",
        "TrendRegime",
        "TrendQuality",
        "TypicalSwingPct",
        "TypicalSwingBars",
        "TypicalMoveSpeedPctPerBar",
        "MedianATRNormalizedMove",
        "MedianPathEfficiency",
        "MedianDirectionalPersistenceRate",
        "DirectionalBias",
        "ProfileLookbackSwings",
        "ConfirmedSwingCount",
        "LastSwingSeq",
        "LastSwingDirection",
        "LastSwingPct",
        "LastSwingTypicalPct",
        "LastSwingExtentRatio",
        "LastSwingState",
        "CurrentLegDirection",
        "CurrentMovePct",
        "CurrentTradingBars",
        "CurrentMoveSpeedPctPerBar",
        "CurrentMoveSpeedRatio",
        "CurrentMoveSpeedState",
        "CurrentLegStatus",
        "CurrentStartPivotSeq",
        "CurrentStartPivotDate",
        "CurrentStartPivotPrice",
        "CurrentCandidatePivotType",
        "CurrentCandidatePivotDate",
        "CurrentCandidatePivotPrice",
        "CurrentLastClose",
        "ReversalFromCandidatePct"
    ]
}
# label, meaning, illustrative example (never a live quote)
FIELD_HINTS = {
    "Ticker": [
        "Mã chứng khoán",
        "Mã đang được phân tích; mọi khối trong popup dùng cùng mã.",
        "MWG là mã Thế Giới Di Động."
    ],
    "Date": [
        "Ngày SmartMoney",
        "Ngày phiên của bản ghi SmartMoney; có thể khác ngày dữ liệu Movement.",
        "2026-09-25 là ngày dữ liệu, không phải thời điểm mở popup."
    ],
    "ModelCode": [
        "Mã mô hình",
        "Định danh mô hình tính SmartMoney.",
        "SMART_MONEY_V1."
    ],
    "ModelVersion": [
        "Phiên bản",
        "Phiên bản công thức SmartMoney.",
        "1.0.0 phân biệt với một phiên bản mô hình khác."
    ],
    "SmartMoneyScore": [
        "Điểm SmartMoney",
        "Điểm tổng hợp bằng chứng dòng tiền, thang 0–100; cần đọc cùng trạng thái và chất lượng.",
        "80 điểm không có nghĩa xác suất tăng giá 80%."
    ],
    "ConfidenceScore": [
        "Độ tin cậy dữ liệu",
        "Điểm tin cậy bằng chứng đầu vào, thang 0–100.",
        "Điểm 85 thể hiện độ tin cậy mô hình, không phải tỷ lệ thắng."
    ],
    "MarketState": [
        "Trạng thái dòng tiền",
        "Trạng thái chính do SmartMoney phân loại.",
        "ACCUMULATION = tích lũy; DISTRIBUTION = phân phối."
    ],
    "FactorCoverage": [
        "Độ phủ yếu tố",
        "Tỷ lệ yếu tố có dữ liệu sử dụng được; lưu dạng 0–1.",
        "0.8 được hiển thị 80% độ phủ."
    ],
    "DataQualityStatus": [
        "Chất lượng dữ liệu",
        "Kết quả kiểm tra dữ liệu SmartMoney: PASS, WARNING hoặc INVALID.",
        "WARNING cần xem đầu vào; không được hiểu là BUY đã xác nhận."
    ],
    "TradeAction": [
        "Hành động mô hình",
        "BUY/HOLD/SELL theo SmartMoney Strategy; HOLD cũng có nghĩa chờ khi chưa nắm giữ.",
        "MARKUP có thể là HOLD dù giá đang tăng."
    ],
    "TradeActionConfidenceScore": [
        "Tin cậy hành động",
        "Điểm bằng chứng cho hành động, không vượt ConfidenceScore; không phải xác suất lợi nhuận.",
        "BUY + 82 là bằng chứng mạnh hơn BUY + 62, không phải cam kết thắng."
    ],
    "FreshFlowScore": [
        "Dòng tiền mới",
        "Điểm 0–100 về dòng tiền mới từ vị trí đóng cửa, lợi suất, sức mạnh tương đối và giá trị giao dịch.",
        "80 điểm cần được đọc cùng thanh khoản để đánh giá BREAKOUT."
    ],
    "RelativeLiquidityScore": [
        "Thanh khoản tương đối",
        "Điểm 0–100 so sánh thanh khoản với nền tham chiếu.",
        "80 điểm không có nghĩa khối lượng bằng 80% trung bình."
    ],
    "LiquidityAccelerationScore": [
        "Gia tốc thanh khoản",
        "Điểm 0–100 phản ánh tăng tốc giá trị giao dịch ngắn hạn so với nền dài hơn.",
        "ALV5/ALV20 tăng cho thấy thanh khoản gần đây mở rộng."
    ],
    "RelativeStrengthScore": [
        "Sức mạnh tương đối",
        "Điểm 0–100 sức mạnh giá so với VNINDEX.",
        "Điểm cao thể hiện mạnh tương đối, không phải RSI."
    ],
    "AccumulationScore": [
        "Tích lũy",
        "Điểm 0–100 của bằng chứng tích lũy.",
        "70 điểm đọc cùng AccumulationMemoryScore để hiểu độ bền."
    ],
    "AccumulationMemoryScore": [
        "Bộ nhớ tích lũy",
        "Điểm 0–100 tổng hợp dấu vết tích lũy qua nhiều phiên.",
        "Một phiên mạnh chưa chắc tạo bộ nhớ tích lũy cao."
    ],
    "SupplyLockScore": [
        "Co nguồn cung",
        "Điểm 0–100 tổng hợp bằng chứng cung co lại trong nền tích lũy.",
        "Điểm cao cần đi cùng bộ nhớ tích lũy; thanh khoản thấp đơn lẻ chưa đủ."
    ],
    "LimitUpScore": [
        "Bằng chứng tăng trần",
        "Điểm 0–100 về trạng thái tăng trần từ nguồn thị trường phù hợp; thiếu nguồn có thể NULL.",
        "— nghĩa chưa có dữ liệu, không phải không có tăng trần."
    ],
    "TrendScore": [
        "Xu hướng",
        "Điểm 0–100 về xu hướng theo mô hình.",
        "Xu hướng mạnh không tự động là điểm mua mới."
    ],
    "DistributionScore": [
        "Phân phối",
        "Điểm 0–100 bằng chứng phân phối; điểm cao là rủi ro theo mô hình.",
        "DISTRIBUTION và chất lượng PASS có thể cho SELL."
    ],
    "Timeframe": [
        "Khung thời gian",
        "Khung dữ liệu của cấu hình phân tích.",
        "D = ngày; W = tuần; M = tháng."
    ],
    "AsOfConfirmedAtDate": [
        "Ngày xác nhận profile",
        "Ngày xác nhận mới nhất của các sóng được dùng trong profile; không phải ngày chạm đỉnh/đáy.",
        "Đỉnh xuất hiện ngày 20 nhưng xác nhận ngày 23 thì chỉ biết từ ngày 23."
    ],
    "ProfileAsOfConfirmedAtDate": [
        "Ngày xác nhận lịch sử",
        "Ngày profile sóng đã xác nhận dùng trong context.",
        "Có thể cũ hơn CurrentLegAsOfDate mà không phải lỗi."
    ],
    "ContextAsOfDate": [
        "Ngày context",
        "Ngày nhịp hiện tại nếu có, nếu không dùng ngày profile xác nhận.",
        "Context mới ngày 25 nhưng profile xác nhận ngày 23."
    ],
    "CurrentLegAsOfDate": [
        "Ngày nhịp hiện tại",
        "Ngày dữ liệu của nhịp ZigZag còn đang hình thành.",
        "Ngày 25 là snapshot; nhịp vẫn có thể thay đổi ở phiên sau."
    ],
    "CalculatedAt": [
        "Thời điểm tính",
        "Timestamp hệ thống tính profile; khác ngày phiên hoặc ngày xác nhận.",
        "Chạy lại hôm nay không làm ngày xác nhận sóng thành hôm nay."
    ],
    "ProfileLookbackSwings": [
        "Cửa sổ sóng",
        "Số sóng gần nhất tối đa được dùng để tổng hợp profile.",
        "20 nghĩa lấy tối đa 20 sóng xác nhận gần nhất."
    ],
    "ConfirmedSwingCount": [
        "Số sóng xác nhận",
        "Số sóng xác nhận thực tế có trong mẫu profile.",
        "Có 4 sóng khi cần tối thiểu 6 thì lịch sử chưa đủ."
    ],
    "LastSwingSeq": [
        "Thứ tự sóng cuối",
        "Số thứ tự của sóng đã xác nhận gần nhất.",
        "42 là ID thứ tự sóng, không phải số ngày."
    ],
    "LastSwingDirection": [
        "Hướng sóng cuối",
        "Hướng UP hoặc DOWN của sóng đã xác nhận cuối.",
        "DOWN là sóng giảm đã xác nhận."
    ],
    "LastSwingPct": [
        "Biên độ sóng cuối",
        "EndPrice/StartPrice − 1; lưu tỷ lệ thập phân có dấu.",
        "Từ 100 xuống 90: −0.10 được hiển thị −10%."
    ],
    "MedianUpSwingPct": [
        "Sóng tăng trung vị",
        "Trung vị biên độ các sóng tăng đã xác nhận.",
        "0.12 hiển thị 12%; là lịch sử, không phải mục tiêu tăng."
    ],
    "MedianDownSwingAbsPct": [
        "Sóng giảm trung vị",
        "Trung vị độ lớn tuyệt đối của các sóng giảm.",
        "0.08 hiển thị 8%, dù đó là sóng giảm."
    ],
    "MedianAbsSwingPct": [
        "Biên độ trung vị",
        "Trung vị độ lớn tuyệt đối các sóng đã xác nhận.",
        "0.10 hiển thị 10%."
    ],
    "MedianTradingBars": [
        "Độ dài sóng trung vị",
        "Trung vị số khoảng giao dịch trong một sóng; không phải ngày lịch.",
        "10 bars D là 10 khoảng giao dịch."
    ],
    "MedianAbsVelocityPctPerBar": [
        "Tốc độ trung vị",
        "Trung vị độ lớn tốc độ SwingPct/TradingBars.",
        "0.01 hiển thị 1%/bar."
    ],
    "MedianATRNormalizedMove": [
        "Biên độ / ATR",
        "Trung vị abs(SwingPct)/ATR% trung bình trong sóng, đơn vị lần.",
        "Sóng 10%, ATR bình quân 2% → 5 lần."
    ],
    "MedianPathEfficiency": [
        "Hiệu quả đường giá",
        "Trung vị abs(EndPrice−StartPrice)/tổng TrueRange, giới hạn 0–1.",
        "0.4 hiển thị 40%; tỷ lệ cao hơn nghĩa đường đi ít vòng hơn."
    ],
    "MedianDirectionalPersistenceRate": [
        "Độ bền hướng",
        "Trung vị tỷ lệ khoảng close-to-close đi đúng hướng của sóng.",
        "0.7 hiển thị 70% khoảng giao dịch cùng hướng."
    ],
    "DirectionalBias": [
        "Thiên lệch hướng",
        "Tổng SwingPct/tổng abs(SwingPct), từ −1 tới +1.",
        "+0.3 nghĩa lịch sử nghiêng tăng; không phải lợi suất +30%."
    ],
    "MovementCharacter": [
        "Đặc tính chuyển động",
        "Phân loại lịch sử: TRENDING_UP/DOWN, RANGE_BOUND, MIXED, INSUFFICIENT_HISTORY.",
        "MIXED nghĩa chưa có hướng thống trị rõ."
    ],
    "ContextStatus": [
        "Độ đầy đủ context",
        "PROFILE_PLUS_CURRENT có cả lịch sử và nhịp tạm thời; PROFILE_ONLY chỉ có lịch sử.",
        "PROFILE_ONLY không có nghĩa dữ liệu lịch sử vô dụng."
    ],
    "TrendRegime": [
        "Chế độ xu hướng",
        "Kế thừa MovementCharacter, không tạo bộ phân loại mới.",
        "TRENDING_DOWN mô tả lịch sử nghiêng giảm."
    ],
    "TrendQuality": [
        "Chất lượng xu hướng",
        "Độ sạch và bền của các sóng, không biểu thị tăng hay giảm.",
        "MIXED + MODERATE_HIGH vẫn hợp lệ: hướng trộn nhưng từng sóng khá rõ."
    ],
    "TypicalSwingPct": [
        "Biên độ điển hình",
        "Kế thừa MedianAbsSwingPct; tỷ lệ thập phân của lịch sử xác nhận.",
        "0.10 hiển thị 10%; không dùng như target mặc định."
    ],
    "TypicalSwingBars": [
        "Độ dài điển hình",
        "Kế thừa MedianTradingBars của profile.",
        "12 bars là mốc mô tả lịch sử, không dự báo ngày đảo chiều."
    ],
    "TypicalMoveSpeedPctPerBar": [
        "Tốc độ điển hình",
        "Kế thừa MedianAbsVelocityPctPerBar.",
        "0.008 hiển thị 0.8%/bar."
    ],
    "LastSwingTypicalPct": [
        "Chuẩn cùng hướng",
        "Trung vị sóng tăng nếu sóng cuối UP; độ lớn trung vị sóng giảm nếu DOWN.",
        "Sóng cuối DOWN phải so với lịch sử DOWN."
    ],
    "LastSwingExtentRatio": [
        "Độ mở rộng sóng",
        "abs(LastSwingPct)/LastSwingTypicalPct, đơn vị lần.",
        "Sóng 12% / chuẩn 8% = 1.5 lần."
    ],
    "LastSwingState": [
        "Mức độ sóng cuối",
        "Nhãn độ mở rộng theo cấu hình, giữ hướng của sóng.",
        "EXTENDED_UP_SWING là sóng tăng rộng hơn điển hình."
    ],
    "CurrentLegDirection": [
        "Hướng nhịp tạm thời",
        "Hướng nhịp ZigZag chưa xác nhận; có thể thay đổi.",
        "UP hiện tại không đồng nghĩa sóng tăng đã hoàn tất."
    ],
    "CurrentMovePct": [
        "Biến động nhịp hiện tại",
        "Biên độ có dấu của nhịp ZigZag hiện tại; chưa xác nhận.",
        "0.06 hiển thị +6%; giá trị có thể thay đổi."
    ],
    "CurrentTradingBars": [
        "Số khoảng nhịp hiện tại",
        "Số dòng OHLC từ pivot bắt đầu tới ngày hiện tại trừ 1.",
        "6 dòng giao dịch tạo 5 khoảng."
    ],
    "CurrentMoveSpeedPctPerBar": [
        "Tốc độ nhịp hiện tại",
        "CurrentMovePct/CurrentTradingBars, có dấu.",
        "6% / 3 bars = 2%/bar."
    ],
    "CurrentMoveSpeedRatio": [
        "Tốc độ / điển hình",
        "abs(tốc độ hiện tại)/tốc độ điển hình, đơn vị lần.",
        "2%/bar / 1%/bar = 2 lần."
    ],
    "CurrentMoveSpeedState": [
        "Nhãn tốc độ hiện tại",
        "VERY_SLOW/SLOW/NORMAL/FAST/EXTREME theo cấu hình; UNKNOWN nếu thiếu dữ liệu.",
        "FAST chỉ nhanh hơn lịch sử, không phải lệnh BUY."
    ],
    "CurrentLegStatus": [
        "Trạng thái nhịp",
        "Trạng thái dữ liệu của nhịp ZigZag hiện tại; đọc cùng ContextStatus.",
        "Nhịp đang hình thành khác sóng đã xác nhận."
    ],
    "CurrentStartPivotSeq": [
        "Thứ tự pivot đầu",
        "ID thứ tự pivot bắt đầu nhịp hiện tại.",
        "41 là thứ tự pivot, không phải giá."
    ],
    "CurrentStartPivotDate": [
        "Ngày pivot đầu",
        "Ngày xuất hiện pivot bắt đầu nhịp hiện tại.",
        "Có thể sớm hơn ngày pivot được xác nhận."
    ],
    "CurrentStartPivotPrice": [
        "Giá pivot đầu",
        "Giá pivot đầu nhịp; theo đơn vị giá nguồn CherryStock (nghìn đồng/cp).",
        "100 tương ứng 100,000 đồng/cp."
    ],
    "CurrentCandidatePivotType": [
        "Loại pivot ứng viên",
        "Loại đỉnh/đáy đang theo dõi; chưa được xác nhận.",
        "Ứng viên đỉnh có thể tiếp tục dời khi giá tăng."
    ],
    "CurrentCandidatePivotDate": [
        "Ngày pivot ứng viên",
        "Ngày cực trị ứng viên hiện tại; còn có thể thay đổi.",
        "Đỉnh mới ở phiên sau sẽ đổi ngày ứng viên."
    ],
    "CurrentCandidatePivotPrice": [
        "Giá pivot ứng viên",
        "Giá cực trị ứng viên, nghìn đồng/cp; chưa xác nhận.",
        "105 tương ứng 105,000 đồng/cp."
    ],
    "CurrentLastClose": [
        "Đóng cửa gần nhất",
        "Giá đóng cửa snapshot nhịp hiện tại, nghìn đồng/cp.",
        "102 tương ứng 102,000 đồng/cp."
    ],
    "ReversalFromCandidatePct": [
        "Đảo chiều từ ứng viên",
        "Mức đảo chiều khỏi cực trị ứng viên theo ZigZag; lưu tỷ lệ thập phân.",
        "0.02 hiển thị 2%; chưa tự suy ra pivot đã xác nhận."
    ],
    "PriceMovementConfigCode": [
        "Mã cấu hình Price Movement",
        "Định danh chính sách Price Movement dùng để đối chiếu đúng dòng dữ liệu.",
        "PM_ZZ_D_V2."
    ],
    "PriceMovementModelVersion": [
        "Phiên bản Price Movement",
        "Phiên bản định nghĩa/công thức của Price Movement.",
        "V2.0 phân biệt kết quả giữa các phiên bản."
    ],
    "PriceMovementConfigId": [
        "ID cấu hình Price Movement",
        "Khóa nội bộ cấu hình Price Movement; không phải điểm số hay thứ hạng.",
        "ID 7 là định danh, lớn hơn không có nghĩa tốt hơn."
    ],
    "ZigZagConfigId": [
        "ID cấu hình ZigZag",
        "Khóa nội bộ cấu hình ZigZag; không phải điểm số hay thứ hạng.",
        "ID 7 là định danh, lớn hơn không có nghĩa tốt hơn."
    ],
    "ZigZagConfigCode": [
        "Mã cấu hình ZigZag",
        "Định danh chính sách ZigZag dùng để đối chiếu đúng dòng dữ liệu.",
        "ZZ_D_5_MVP."
    ],
    "MovementContextConfigId": [
        "ID cấu hình Movement Context",
        "Khóa nội bộ cấu hình Movement Context; không phải điểm số hay thứ hạng.",
        "ID 7 là định danh, lớn hơn không có nghĩa tốt hơn."
    ],
    "MovementContextConfigCode": [
        "Mã cấu hình Movement Context",
        "Định danh chính sách Movement Context dùng để đối chiếu đúng dòng dữ liệu.",
        "MC_PM_ZZ_D_V1."
    ],
    "MovementContextModelVersion": [
        "Phiên bản Movement Context",
        "Phiên bản định nghĩa/công thức của Movement Context.",
        "V2.0 phân biệt kết quả giữa các phiên bản."
    ]
}
VIEW_LABELS = {
    "vw_Ticker_SmartMoney": "SmartMoney · dòng tiền",
    "vw_Ticker_Movement_Profile": "Movement Profile · sóng đã xác nhận",
    "vw_Ticker_Movement_Context": "Movement Context · lịch sử và nhịp tạm thời",
}
DATE_FIELDS = {
    "vw_Ticker_SmartMoney": "Date",
    "vw_Ticker_Movement_Profile": "AsOfConfirmedAtDate",
    "vw_Ticker_Movement_Context": "ContextAsOfDate",
}
PARTITIONS = {
    "vw_Ticker_SmartMoney": ("ModelCode", "ModelVersion"),
    "vw_Ticker_Movement_Profile": ("PriceMovementConfigId", "ZigZagConfigId"),
    "vw_Ticker_Movement_Context": ("MovementContextConfigId",),
}
PERCENT_FIELDS = {
    "FactorCoverage", "LastSwingPct", "MedianUpSwingPct",
    "MedianDownSwingAbsPct", "MedianAbsSwingPct", "MedianPathEfficiency",
    "MedianDirectionalPersistenceRate", "TypicalSwingPct", "LastSwingTypicalPct",
    "CurrentMovePct", "ReversalFromCandidatePct",
}
SPEED_FIELDS = {
    "MedianAbsVelocityPctPerBar", "TypicalMoveSpeedPctPerBar",
    "CurrentMoveSpeedPctPerBar",
}
PRICE_FIELDS = {"CurrentStartPivotPrice", "CurrentCandidatePivotPrice", "CurrentLastClose"}
RATIO_FIELDS = {"MedianATRNormalizedMove", "LastSwingExtentRatio", "CurrentMoveSpeedRatio"}


def normalize_ticker(ticker: str) -> str:
    value = str(ticker).strip().upper()
    if not re.fullmatch(r"[A-Z0-9]{1,20}", value):
        raise ValueError("Ticker phải gồm 1–20 chữ cái/số.")
    return value


def detail_query(view: str) -> str:
    """All identifiers are allowlisted; bind the ticker, never interpolate input."""
    columns = ", ".join(f'"{column}"' for column in FIELDS[view])
    keys = ", ".join(f'"{column}"' for column in PARTITIONS[view])
    as_of = DATE_FIELDS[view]
    return (
        f'SELECT {columns} FROM "CherryMon"."main"."{view}" '
        'WHERE "Ticker" = ? '
        f'QUALIFY ROW_NUMBER() OVER (PARTITION BY {keys} '
        f'ORDER BY "{as_of}" DESC NULLS LAST) = 1 '
        f'ORDER BY {keys}'
    )


def field_hint(field: str) -> str:
    label, meaning, example = FIELD_HINTS[field]
    return f"{label} ({field}). {meaning} Ví dụ minh họa: {example}"


def format_field(field: str, value: object) -> str:
    if value is None:
        return "—"
    if isinstance(value, float) and not math.isfinite(value):
        return "—"
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if field in PERCENT_FIELDS:
            return f"{value * 100:,.2f}%"
        if field in SPEED_FIELDS:
            return f"{value * 100:,.2f}%/bar"
        if field in PRICE_FIELDS:
            return f"{value:,.2f} nghìn đồng"
        if field in RATIO_FIELDS:
            return f"{value:,.2f} lần"
        return f"{value:,.4f}".rstrip("0").rstrip(".")
    return str(value)
