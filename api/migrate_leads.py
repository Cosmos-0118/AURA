import os
import psycopg
from dotenv import load_dotenv

def main():
    # Load .env
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
    
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("DATABASE_URL not set in .env")
        return
        
    try:
        with psycopg.connect(database_url, autocommit=True) as conn:
            with conn.cursor() as cur:
                # Add columns if they don't exist
                columns = {
                    "external_place_id": "text unique",
                    "products": "jsonb not null default '[]'",
                    "specialties": "jsonb not null default '[]'",
                    "fit_reasons": "jsonb not null default '[]'",
                    "last_verified_at": "timestamptz",
                }
                for col_name, col_def in columns.items():
                    try:
                        cur.execute(f"ALTER TABLE leads ADD COLUMN {col_name} {col_def};")
                        print(f"Added column {col_name}")
                    except psycopg.errors.DuplicateColumn:
                        print(f"Column {col_name} already exists.")
                    except Exception as e:
                        print(f"Error adding {col_name}: {e}")
    except Exception as e:
        print(f"Database connection error: {e}")

if __name__ == "__main__":
    main()
