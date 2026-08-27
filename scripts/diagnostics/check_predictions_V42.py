from sqlalchemy import text

from database.db import engine


BIKE_ID = "DTB0022"


query = text("""
    SELECT
        prediction_id,
        prediction_timestamp,
        predicted_risk,
        probability_warning,
        probability_critical
    FROM predictions
    WHERE bike_id = :bike_id
    ORDER BY prediction_id;
""")


with engine.connect() as connection:

    rows = connection.execute(
        query,
        {
            "bike_id": BIKE_ID
        },
    ).fetchall()


print()
print("=" * 90)
print(f"PREDICTION HISTORY — {BIKE_ID}")
print("=" * 90)

for row in rows:

    print(
        f"ID={row.prediction_id:3d} "
        f"| {row.prediction_timestamp} "
        f"| {row.predicted_risk:8s} "
        f"| WARNING={row.probability_warning * 100:7.2f}% "
        f"| CRITICAL={row.probability_critical * 100:7.2f}%"
    )

print("=" * 90)
print(f"Total predictions : {len(rows)}")