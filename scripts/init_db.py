import os
from sqlalchemy import create_engine
from aegis_eval.data.schema import Base
from aegis_eval.config import get_db_url

def init_db():
    db_url = get_db_url()
    
    print(f"Connecting to database at {db_url}...")
    engine = create_engine(db_url)
    
    # Create vector extension if not exists
    from sqlalchemy import text
    try:
        with engine.connect() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
            conn.commit()
            print("Vector extension ensured.")
    except Exception as e:
        print(f"Could not create vector extension (is pgvector installed?): {e}")

    # Create all tables
    print("Creating tables...")
    Base.metadata.create_all(engine)
    print("Tables created successfully.")

if __name__ == "__main__":
    init_db()
