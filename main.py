import argparse
import json

from db import get_connection, list_epds
from pipeline import process_pdf


def main() -> None:
    parser = argparse.ArgumentParser(description="EPD PDF -> LLM -> SQLite pipeline")
    parser.add_argument("pdf", nargs="?", help="Path to an EPD PDF to process")
    parser.add_argument("--db", default="lca.db", help="SQLite database path")
    parser.add_argument("--model", default="gpt-4o-mini", help="OpenAI model name")
    parser.add_argument("--list", action="store_true", help="List EPDs already in the database")
    args = parser.parse_args()

    if args.list:
        conn = get_connection(args.db)
        try:
            print(json.dumps(list_epds(conn), indent=2, ensure_ascii=False))
        finally:
            conn.close()
        return

    if not args.pdf:
        parser.error("provide a PDF path or use --list")

    record = process_pdf(args.pdf, db_path=args.db, model=args.model)
    print(record.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
