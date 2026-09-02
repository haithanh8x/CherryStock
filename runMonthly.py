import sys
import io

from src.Ults.Timing import timeit
from src.Orchestrator.rs_v2_4_full_evaluation import main as run_rs_v2_4_full_evaluation


def _run_all_steps() -> None:
    """
    Chạy toàn bộ monthly jobs theo thứ tự cấu hình.

    Giai đoạn 1:
    - R/S V2.4 Full Source Effectiveness Evaluation

    Sau này có thể bổ sung thêm monthly jobs vào tuple steps bên dưới,
    tương tự cơ chế Run All của run.py.
    """
    steps = (
        (
            "R/S V2.4 Full Source Effectiveness Evaluation",
            run_rs_v2_4_full_evaluation,
        ),
    )

    for index, (title, step) in enumerate(steps, start=1):
        print(f"[{index}/{len(steps)}] ▶ {title}")
        step()
        print(f"[{index}/{len(steps)}] ✓ {title}")


@timeit
def main():
    """
    CherryStock monthly runner.

    Chạy thủ công mỗi tháng bằng:
        python runMonthly.py
    """
    print("CherryStock Monthly Run All")

    _run_all_steps()

    print("✓ Monthly Run All hoàn tất.")


if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(
        sys.stdout.buffer,
        encoding="utf-8",
        line_buffering=True,
    )
    sys.stderr = io.TextIOWrapper(
        sys.stderr.buffer,
        encoding="utf-8",
        line_buffering=True,
    )
    main()
