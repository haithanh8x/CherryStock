import time
from functools import wraps

def timeit(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)  # Thực thi function gốc
        end_time = time.time()
        print(f"⏱️   [Đo thời gian] Function '{func.__name__}' chạy hết: {end_time - start_time:.4f} giây")
        return result
    return wrapper