import os
from sqlalchemy import create_engine
from aegis_eval.data.schema import Base

def init_db():
    # Use environment variable or default local postgres connection
    db_url = os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/postgres")
    
    print(f"Connecting to database at {db_url}...")
    engine = create_engine(db_url)
    
    # Create all tables
    print("Creating tables...")
    Base.metadata.create_all(engine)
    print("Tables created successfully.")

if __name__ == "__main__":
    init_db()
