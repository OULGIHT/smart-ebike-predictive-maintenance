import os
import joblib
import numpy as np
import pandas as pd

from sqlalchemy import text

from database.db import engine
from services.feature_builder_V42 import build_features_for_bike


# ============================================================
# PATHS
# ============================================================

MODEL_FILE = os.path.join(
    "models",
    "logistic_temporal_V42.joblib",
)


# ============================================================
# LOAD MODEL ARTIFACT
# ============================================================

def load_model_artifact():

    if not os.path.exists(
        MODEL_FILE
    ):

        raise FileNotFoundError(
            f"Model not found: {MODEL_FILE}"
        )

    artifact = joblib.load(
        MODEL_FILE
    )

    required_keys = [
        "model",
        "features",
        "target",
        "model_version",
        "prediction_horizon_days",
    ]

    missing_keys = [
        key
        for key in required_keys
        if key not in artifact
    ]

    if missing_keys:

        raise RuntimeError(
            "Invalid model artifact. "
            f"Missing keys: {missing_keys}"
        )

    return artifact


# ============================================================
# MODEL METADATA
# ============================================================

def get_model_metadata(
    artifact,
):

    model = artifact[
        "model"
    ]

    classifier = model.named_steps[
        "classifier"
    ]

    classes = (
        classifier
        .classes_
        .tolist()
    )

    return {
        "model_version":
            artifact[
                "model_version"
            ],

        "prediction_horizon_days":
            artifact[
                "prediction_horizon_days"
            ],

        "target":
            artifact[
                "target"
            ],

        "n_features":
            len(
                artifact[
                    "features"
                ]
            ),

        "classes":
            classes,
    }


# ============================================================
# PREDICT
# ============================================================

def predict_bike(
    bike_id,
    prediction_timestamp=None,
):

    artifact = (
        load_model_artifact()
    )

    model = artifact[
        "model"
    ]

    expected_features = artifact[
        "features"
    ]

    # --------------------------------------------------------
    # Build the 57 V4.2 features from PostgreSQL history
    # --------------------------------------------------------

    X = build_features_for_bike(
        bike_id=
            bike_id,

        prediction_timestamp=
            prediction_timestamp,
    )

    # --------------------------------------------------------
    # Strict schema validation
    # --------------------------------------------------------

    actual_features = (
        X.columns.tolist()
    )

    if (
        actual_features
        !=
        expected_features
    ):

        raise RuntimeError(
            "Feature order mismatch between "
            "production builder and trained model."
        )

    if X.shape[1] != 57:

        raise RuntimeError(
            f"Expected 57 features, "
            f"received {X.shape[1]}."
        )

    # --------------------------------------------------------
    # Prediction
    # --------------------------------------------------------

    predicted_class = (
        model.predict(
            X
        )[0]
    )

    probabilities = (
        model.predict_proba(
            X
        )[0]
    )

    classifier = (
        model.named_steps[
            "classifier"
        ]
    )

    classes = (
        classifier
        .classes_
        .tolist()
    )

    # --------------------------------------------------------
    # Explicit class -> probability mapping
    # --------------------------------------------------------

    probability_map = {
        class_name:
            float(
                probability
            )

        for (
            class_name,
            probability
        )
        in zip(
            classes,
            probabilities,
        )
    }

    required_classes = {
        "NORMAL",
        "WARNING",
        "CRITICAL",
    }

    if (
        set(
            probability_map.keys()
        )
        !=
        required_classes
    ):

        raise RuntimeError(
            "Unexpected model classes: "
            f"{classes}"
        )

    probability_sum = sum(
        probability_map.values()
    )

    if not np.isclose(
        probability_sum,
        1.0,
        atol=1e-6,
    ):

        raise RuntimeError(
            f"Invalid probability sum: "
            f"{probability_sum}"
        )

    # --------------------------------------------------------
    # Determine prediction timestamp from latest telemetry
    # --------------------------------------------------------

    if prediction_timestamp is None:

        latest_timestamp_query = text(
            """
            SELECT MAX(timestamp)
            FROM telemetry
            WHERE bike_id = :bike_id
            """
        )

        with engine.connect() as connection:

            latest_timestamp = (
                connection.execute(
                    latest_timestamp_query,
                    {
                        "bike_id":
                            bike_id
                    },
                )
                .scalar()
            )

        if latest_timestamp is None:

            raise RuntimeError(
                f"No telemetry timestamp "
                f"found for bike {bike_id}."
            )

        prediction_timestamp = (
            pd.Timestamp(
                latest_timestamp
            )
        )

    else:

        prediction_timestamp = (
            pd.Timestamp(
                prediction_timestamp
            )
        )

    return {
        "bike_id":
            bike_id,

        "prediction_timestamp":
            prediction_timestamp,

        "predicted_risk":
            str(
                predicted_class
            ),

        "probability_normal":
            probability_map[
                "NORMAL"
            ],

        "probability_warning":
            probability_map[
                "WARNING"
            ],

        "probability_critical":
            probability_map[
                "CRITICAL"
            ],

        "prediction_horizon_days":
            int(
                artifact[
                    "prediction_horizon_days"
                ]
            ),

        "model_version":
            str(
                artifact[
                    "model_version"
                ]
            ),
    }


# ============================================================
# SAVE PREDICTION
# ============================================================

INSERT_PREDICTION_SQL = text(
    """
    INSERT INTO predictions (
        bike_id,
        prediction_timestamp,
        prediction_horizon_days,
        predicted_risk,
        probability_normal,
        probability_warning,
        probability_critical,
        model_version
    )
    VALUES (
        :bike_id,
        :prediction_timestamp,
        :prediction_horizon_days,
        :predicted_risk,
        :probability_normal,
        :probability_warning,
        :probability_critical,
        :model_version
    )
    RETURNING prediction_id
    """
)


def save_prediction(
    prediction,
):

    with engine.begin() as connection:

        prediction_id = (
            connection.execute(
                INSERT_PREDICTION_SQL,
                prediction,
            )
            .scalar_one()
        )

    return prediction_id


# ============================================================
# PREDICT + SAVE
# ============================================================

def predict_and_save(
    bike_id,
    prediction_timestamp=None,
):

    prediction = predict_bike(
        bike_id=
            bike_id,

        prediction_timestamp=
            prediction_timestamp,
    )

    prediction_id = (
        save_prediction(
            prediction
        )
    )

    prediction[
        "prediction_id"
    ] = prediction_id

    return prediction


# ============================================================
# CLI DISPLAY
# ============================================================

def display_prediction(
    prediction,
):

    print()
    print("=" * 90)
    print(
        "SMART E-BIKE RISK PREDICTION V4.2"
    )
    print("=" * 90)

    print()
    print(
        f"Prediction ID   : "
        f"{prediction['prediction_id']}"
    )

    print(
        f"Bike            : "
        f"{prediction['bike_id']}"
    )

    print(
        f"Timestamp       : "
        f"{prediction['prediction_timestamp']}"
    )

    print(
        f"Horizon         : "
        f"+{prediction['prediction_horizon_days']} days"
    )

    print(
        f"Model           : "
        f"{prediction['model_version']}"
    )

    print()
    print(
        f"Predicted risk  : "
        f"{prediction['predicted_risk']}"
    )

    print()
    print(
        "PROBABILITIES"
    )

    print("-" * 50)

    print(
        f"NORMAL   : "
        f"{prediction['probability_normal'] * 100:.2f}%"
    )

    print(
        f"WARNING  : "
        f"{prediction['probability_warning'] * 100:.2f}%"
    )

    print(
        f"CRITICAL : "
        f"{prediction['probability_critical'] * 100:.2f}%"
    )

    probability_sum = (
        prediction[
            "probability_normal"
        ]
        +
        prediction[
            "probability_warning"
        ]
        +
        prediction[
            "probability_critical"
        ]
    )

    print()
    print(
        f"Probability sum : "
        f"{probability_sum:.6f}"
    )

    print()
    print(
        "Prediction saved to PostgreSQL."
    )


# ============================================================
# MAIN
# ============================================================

def main():

    import sys

    if len(
        sys.argv
    ) < 2:

        print(
            "Usage:"
        )

        print(
            "python -m "
            "services.prediction_service_V42 "
            "DTB0001"
        )

        raise SystemExit(
            1
        )

    bike_id = (
        sys.argv[
            1
        ]
    )

    prediction = (
        predict_and_save(
            bike_id
        )
    )

    display_prediction(
        prediction
    )


if __name__ == "__main__":

    main()