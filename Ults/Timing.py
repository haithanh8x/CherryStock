import os
import sys
import time
from functools import wraps

def timeit(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)  # Thực thi function gốc
        end_time = time.time()
        print(f"⏱️   [Duration] '{func.__name__}' total time: {end_time - start_time:.1f} seconds")
        return result
    return wrapper

def toggle_print(allow_print=True):
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