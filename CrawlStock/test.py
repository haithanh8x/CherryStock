from datetime import datetime

def convert_quarter_to_date(qstr: str) -> str:
    """
    Convert 'Quý X/YYYY' -> 'DD-MON-YYYY'
    Return first day of that quarter
    Example: 'Quý 1/2021' -> '01-JAN-2021'
    """

    qstr = qstr.strip()

    # Tách quý và năm
    quarter_part, year = qstr.replace("Quý", "").strip().split("/")
    quarter = int(quarter_part)

    # Map quý -> tháng bắt đầu
    quarter_month_map = {
        1: 1,
        2: 4,
        3: 7,
        4: 10
    }

    if quarter not in quarter_month_map:
        raise ValueError("Quarter must be 1-4")

    month = quarter_month_map[quarter]

    date_obj = datetime(int(year), month, 1)

    return date_obj.strftime("%Y%m%d").upper()

print(convert_quarter_to_date('Quý 1/2021'))