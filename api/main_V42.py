from fastapi import FastAPI, HTTPException, Query
from sqlalchemy import text

from database.db import engine
from services.prediction_service_V42 import predict_and_save


app = FastAPI(
    title="Smart E-Bike Platform API",
    version="4.2",
)


# ============================================================
# HEALTH
# ============================================================

@app.get("/health")
def health():

    return {
        "status": "ok",
        "service": "smart-ebike-api",
        "version": "V4.2",
    }


# ============================================================
# FLEET SNAPSHOT
# ============================================================

@app.get("/bikes")
def get_bikes():

    query = text(
        """
        SELECT
            b.bike_id,
            b.status,

            t.timestamp AS last_telemetry,

            t.average_speed_kmh,
            t.battery_temperature_c,
            t.initial_soc,
            t.final_soc,
            t.consumption_wh_km,
            t.traffic_factor,
            t.slope_percent,

            p.prediction_timestamp,
            p.predicted_risk,
            p.probability_normal,
            p.probability_warning,
            p.probability_critical

        FROM bikes b

        LEFT JOIN LATERAL (

            SELECT
                timestamp,
                average_speed_kmh,
                battery_temperature_c,
                initial_soc,
                final_soc,
                consumption_wh_km,
                traffic_factor,
                slope_percent

            FROM telemetry

            WHERE bike_id = b.bike_id

            ORDER BY
                timestamp DESC,
                telemetry_id DESC

            LIMIT 1

        ) t ON TRUE

        LEFT JOIN LATERAL (

            SELECT
                prediction_timestamp,
                predicted_risk,
                probability_normal,
                probability_warning,
                probability_critical

            FROM predictions

            WHERE bike_id = b.bike_id

            ORDER BY
                prediction_id DESC

            LIMIT 1

        ) p ON TRUE

        ORDER BY b.bike_id;
        """
    )

    with engine.connect() as connection:

        rows = (
            connection.execute(query)
            .mappings()
            .all()
        )

    return [
        dict(row)
        for row in rows
    ]


# ============================================================
# BIKE DETAILS
# ============================================================

@app.get("/bikes/{bike_id}")
def get_bike(
    bike_id: str,
):

    query = text(
        """
        SELECT
            b.bike_id,
            b.status,

            t.timestamp,
            t.distance_km,
            t.duration_minutes,
            t.slope_percent,
            t.ambient_temperature_c,
            t.traffic_factor,
            t.average_speed_kmh,
            t.acceleration_mps2,
            t.mechanical_power_w,
            t.battery_power_w,
            t.battery_temperature_c,
            t.energy_consumed_wh,
            t.consumption_wh_km,
            t.initial_soc,
            t.final_soc,

            p.prediction_timestamp,
            p.prediction_horizon_days,
            p.predicted_risk,
            p.probability_normal,
            p.probability_warning,
            p.probability_critical,
            p.model_version

        FROM bikes b

        LEFT JOIN LATERAL (

            SELECT *

            FROM telemetry

            WHERE bike_id = b.bike_id

            ORDER BY
                timestamp DESC,
                telemetry_id DESC

            LIMIT 1

        ) t ON TRUE

        LEFT JOIN LATERAL (

            SELECT *

            FROM predictions

            WHERE bike_id = b.bike_id

            ORDER BY
                prediction_id DESC

            LIMIT 1

        ) p ON TRUE

        WHERE b.bike_id = :bike_id;
        """
    )

    with engine.connect() as connection:

        row = (
            connection.execute(
                query,
                {
                    "bike_id":
                        bike_id
                },
            )
            .mappings()
            .first()
        )

    if row is None:

        raise HTTPException(
            status_code=404,
            detail="Bike not found",
        )

    return dict(row)


# ============================================================
# TELEMETRY HISTORY
# ============================================================

@app.get("/bikes/{bike_id}/telemetry")
def get_bike_telemetry(
    bike_id: str,
    limit: int = Query(
        default=100,
        ge=1,
        le=1000,
    ),
):

    bike_exists_query = text(
        """
        SELECT 1
        FROM bikes
        WHERE bike_id = :bike_id;
        """
    )

    telemetry_query = text(
        """
        SELECT
            telemetry_id,
            bike_id,
            timestamp,
            distance_km,
            duration_minutes,
            average_speed_kmh,
            acceleration_mps2,
            mechanical_power_w,
            battery_power_w,
            battery_temperature_c,
            energy_consumed_wh,
            consumption_wh_km,
            initial_soc,
            final_soc,
            ambient_temperature_c,
            traffic_factor,
            slope_percent

        FROM telemetry

        WHERE bike_id = :bike_id

        ORDER BY
            timestamp DESC,
            telemetry_id DESC

        LIMIT :limit;
        """
    )

    with engine.connect() as connection:

        exists = (
            connection.execute(
                bike_exists_query,
                {
                    "bike_id":
                        bike_id
                },
            )
            .scalar()
        )

        if exists is None:

            raise HTTPException(
                status_code=404,
                detail="Bike not found",
            )

        rows = (
            connection.execute(
                telemetry_query,
                {
                    "bike_id":
                        bike_id,

                    "limit":
                        limit,
                },
            )
            .mappings()
            .all()
        )

    return [
        dict(row)
        for row in rows
    ]


# ============================================================
# MANUAL PREDICTION
# ============================================================

@app.post("/predict/{bike_id}")
def predict(
    bike_id: str,
):

    try:

        prediction = (
            predict_and_save(
                bike_id=bike_id
            )
        )

        return prediction

    except ValueError as error:

        raise HTTPException(
            status_code=400,
            detail=str(error),
        )

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=str(error),
        )


# ============================================================
# PREDICTION HISTORY
# ============================================================

@app.get("/predictions/{bike_id}")
def get_predictions(
    bike_id: str,
    limit: int = Query(
        default=50,
        ge=1,
        le=500,
    ),
):

    bike_exists_query = text(
        """
        SELECT 1
        FROM bikes
        WHERE bike_id = :bike_id;
        """
    )

    prediction_query = text(
        """
        SELECT
            prediction_id,
            bike_id,
            prediction_timestamp,
            prediction_horizon_days,
            predicted_risk,
            probability_normal,
            probability_warning,
            probability_critical,
            model_version

        FROM predictions

        WHERE bike_id = :bike_id

        ORDER BY
            prediction_id DESC

        LIMIT :limit;
        """
    )

    with engine.connect() as connection:

        exists = (
            connection.execute(
                bike_exists_query,
                {
                    "bike_id":
                        bike_id
                },
            )
            .scalar()
        )

        if exists is None:

            raise HTTPException(
                status_code=404,
                detail="Bike not found",
            )

        rows = (
            connection.execute(
                prediction_query,
                {
                    "bike_id":
                        bike_id,

                    "limit":
                        limit,
                },
            )
            .mappings()
            .all()
        )

    return [
        dict(row)
        for row in rows
    ]


# ============================================================
# FLEET SUMMARY
# ============================================================

@app.get("/fleet/summary")
def fleet_summary():

    query = text(
        """
        WITH latest_predictions AS (

            SELECT DISTINCT ON (bike_id)

                bike_id,
                predicted_risk,
                probability_normal,
                probability_warning,
                probability_critical,
                prediction_timestamp

            FROM predictions

            ORDER BY
                bike_id,
                prediction_id DESC
        )

        SELECT

            (
                SELECT COUNT(*)
                FROM bikes
            ) AS total_bikes,

            (
                SELECT COUNT(*)
                FROM telemetry
            ) AS total_telemetry,

            (
                SELECT COUNT(*)
                FROM predictions
            ) AS total_predictions,

            (
                SELECT COUNT(*)
                FROM latest_predictions
                WHERE predicted_risk = 'NORMAL'
            ) AS normal_count,

            (
                SELECT COUNT(*)
                FROM latest_predictions
                WHERE predicted_risk = 'WARNING'
            ) AS warning_count,

            (
                SELECT COUNT(*)
                FROM latest_predictions
                WHERE predicted_risk = 'CRITICAL'
            ) AS critical_count,

            (
                SELECT MAX(timestamp)
                FROM telemetry
            ) AS last_telemetry,

            (
                SELECT MAX(prediction_timestamp)
                FROM predictions
            ) AS last_prediction;
        """
    )

    with engine.connect() as connection:

        row = (
            connection.execute(query)
            .mappings()
            .one()
        )

    return {

        "total_bikes":
            row["total_bikes"],

        "total_telemetry":
            row["total_telemetry"],

        "total_predictions":
            row["total_predictions"],

        "risk_distribution": {

            "NORMAL":
                row["normal_count"],

            "WARNING":
                row["warning_count"],

            "CRITICAL":
                row["critical_count"],
        },

        "last_telemetry":
            row["last_telemetry"],

        "last_prediction":
            row["last_prediction"],

        "model_version":
            "V4.2",

        "prediction_horizon_days":
            30,
    }