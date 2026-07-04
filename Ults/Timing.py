import os
import sys
import time
from functools import wraps


def timeit(func):
    """Measure the execution time of a function."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        print(f"⏱️   [Duration] '{func.__name__}' total time: {end_time - start_time:.1f} seconds")
        return result

    return wrapper


def toggle_print(allow_print=True):
    """Silence stdout for wrapped functions when requested."""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not allow_print:
                old_stdout = sys.stdout
                # SỬA TẠI ĐÂY: Thêm encoding="utf-8" để đọc được tiếng Việt
                sys.stdout = open(os.devnull, "w", encoding="utf-8")
                try:
                    return func(*args, **kwargs)
                finally:
                    sys.stdout.close()
                    sys.stdout = old_stdout
            else:
                return func(*args, **kwargs)
        return wrapper
    return decorator


def get_nearest_working_date(con, from_date):
    """Lấy ngày làm việc gần nhất theo dimCalendar và ngày tham số."""
    if isinstance(from_date, str):
        from_date_str = from_date.strip()
    elif hasattr(from_date, 'isoformat'):
        from_date_str = from_date.isoformat()
    else:
        raise ValueError("from_date phải ở định dạng YYYY-MM-DD hoặc một object date")

    sql = f"""
        SELECT
            CAST(FullDate AS DATE) AS nearest_working_date
        FROM "CherryMon"."main"."dimCalendar"
        WHERE IsHoliday = 'N'
        ORDER BY abs(date_diff('day', CAST(FullDate AS DATE), DATE '{from_date_str}')) ASC
        LIMIT 1;
    """

    # Import lazily to avoid a circular dependency with Ults.DuckLib.
    from Ults import DuckLib

    df = DuckLib.returnSQL(con, sql)
    if df is not None and not df.empty:
        return df["nearest_working_date"].iloc[0]
    return None

