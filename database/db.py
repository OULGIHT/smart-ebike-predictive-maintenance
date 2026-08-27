import os

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
from sqlalchemy.engine import URL

# ============================================================
# ENVIRONMENT
# ============================================================

load_dotenv()


# ============================================================
# DATABASE CONFIG
# ============================================================

DB_HOST = os.getenv(
    "POSTGRES_HOST",
    "localhost",
)

DB_PORT = os.getenv(
    "POSTGRES_PORT",
    "5432",
)

DB_NAME = os.getenv(
    "POSTGRES_DB",
    "smart_ebike",
)

DB_USER = os.getenv(
    "POSTGRES_USER",
    "postgres",
)

DB_PASSWORD = os.getenv(
    "POSTGRES_PASSWORD",
)


if not DB_PASSWORD:

    raise RuntimeError(
        "POSTGRES_PASSWORD is not defined."
    )


DATABASE_URL = URL.create(
    drivername="postgresql+psycopg2",
    username=DB_USER,
    password=DB_PASSWORD,
    host=DB_HOST,
    port=int(DB_PORT),
    database=DB_NAME,
)




# ============================================================
# ENGINE
# ============================================================

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
)


# ============================================================
# SESSION
# ============================================================

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


# ============================================================
# CONNECTION TEST
# ============================================================

def test_connection():

    print()
    print("=" * 80)
    print("POSTGRESQL CONNECTION TEST")
    print("=" * 80)

    with engine.connect() as connection:

        result = connection.execute(
            text(
                """
                SELECT
                    current_database(),
                    current_user,
                    version();
                """
            )
        )

        row = result.fetchone()

        print()
        print(
            f"Database : {row[0]}"
        )

        print(
            f"User     : {row[1]}"
        )

        print()
        print(
            "PostgreSQL version:"
        )

        print(
            row[2]
        )

        # ====================================================
        # TABLE CHECK
        # ====================================================

        tables = connection.execute(
            text(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                ORDER BY table_name;
                """
            )
        ).fetchall()

        print()
        print(
            "Tables:"
        )

        for table in tables:

            print(
                f"- {table[0]}"
            )

    print()
    print(
        "Connection test : PASSED"
    )

    print()
    print("=" * 80)


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    test_connection()