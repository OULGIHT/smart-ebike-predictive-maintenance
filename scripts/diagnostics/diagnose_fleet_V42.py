from sqlalchemy import text

from database.db import engine
from services.prediction_service_V42 import predict_bike


# ============================================================
# GET ALL BIKES
# ============================================================

with engine.connect() as connection:

    rows = connection.execute(
        text(
            """
            SELECT bike_id
            FROM bikes
            ORDER BY bike_id
            """
        )
    ).fetchall()


bike_ids = [
    row[0]
    for row in rows
]


# ============================================================
# PREDICT FLEET
# ============================================================

print()
print("=" * 90)
print("FLEET RISK DIAGNOSTIC V4.2")
print("=" * 90)

for bike_id in bike_ids:

    try:

        prediction = predict_bike(
            bike_id
        )

        print(
            f"{bike_id:10s} "
            f"{prediction['predicted_risk']:10s} "
            f"N={prediction['probability_normal']:.4f}  "
            f"W={prediction['probability_warning']:.4f}  "
            f"C={prediction['probability_critical']:.4f}"
        )

    except Exception as error:

        print(
            f"{bike_id:10s} ERROR: {error}"
        )


print("=" * 90)