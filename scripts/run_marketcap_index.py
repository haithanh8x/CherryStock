"""Full initload or incremental market-cap indices.

python scripts/run_marketcap_index.py
python scripts/run_marketcap_index.py --days 10
"""
import argparse
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))
from src.calcEngine.marketCapIndex import refresh_marketcap_index
from src.cherrystock.infrastructure.database.connection import DuckDBConnectionFactory
from src.cherrystock.infrastructure.database.unit_of_work import DuckDBUnitOfWork


def main(argv=None):
    parser=argparse.ArgumentParser()
    parser.add_argument("--days",type=int,default=None,
                        help="Latest N trading sessions; omit for full initload")
    args=parser.parse_args(argv)
    with DuckDBUnitOfWork(DuckDBConnectionFactory()) as uow:
        summary=refresh_marketcap_index(connection=uow.connection,days=args.days)
    print("[MarketCapIndex]",summary)
    return summary


if __name__=="__main__":
    main()
