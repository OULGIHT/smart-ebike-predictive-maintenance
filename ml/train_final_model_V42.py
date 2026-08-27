import os
import json
import joblib
import pandas as pd

from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression


# ============================================================
# PATHS
# ============================================================

DATA_FILE = os.path.join(
    "data",
    "processed",
    "temporal_dataset_30d_V42.csv",
)

SCHEMA_FILE = os.path.join(
    "data",
    "processed",
    "temporal_feature_schema_V4.json",
)

MODEL_DIR = "models"

MODEL_FILE = os.path.join(
    MODEL_DIR,
    "logistic_temporal_V42.joblib",
)

METADATA_FILE = os.path.join(
    MODEL_DIR,
    "logistic_temporal_V42_metadata.json",
)


# ============================================================
# CONFIGURATION
# ============================================================

TARGET = "target_risk_30d"

RANDOM_STATE = 42

EXPECTED_CLASSES = [
    "NORMAL",
    "WARNING",
    "CRITICAL",
]


# ============================================================
# LOAD DATA
# ============================================================

def load_data():

    if not os.path.exists(DATA_FILE):

        raise FileNotFoundError(
            f"Dataset not found: {DATA_FILE}"
        )

    if not os.path.exists(SCHEMA_FILE):

        raise FileNotFoundError(
            f"Schema not found: {SCHEMA_FILE}"
        )

    print("Loading dataset...")

    df = pd.read_csv(
        DATA_FILE
    )

    with open(
        SCHEMA_FILE,
        "r",
        encoding="utf-8",
    ) as f:

        schema = json.load(f)

    features = schema[
        "features"
    ]

    return df, features


# ============================================================
# VALIDATION
# ============================================================

def validate_data(
    df,
    features,
):

    print()
    print("=" * 90)
    print("FINAL TRAINING VALIDATION")
    print("=" * 90)

    missing_features = [
        feature
        for feature in features
        if feature not in df.columns
    ]

    if missing_features:

        raise ValueError(
            "Missing features:\n"
            +
            "\n".join(
                missing_features
            )
        )

    if TARGET not in df.columns:

        raise ValueError(
            f"Target missing: {TARGET}"
        )

    forbidden_features = [
        feature
        for feature in features
        if (
            "latent" in feature.lower()
            or
            "target" in feature.lower()
            or
            "future" in feature.lower()
            or
            "degradation_profile" in feature.lower()
            or
            "bike_degradation_factor" in feature.lower()
        )
    ]

    if forbidden_features:

        raise RuntimeError(
            "Potential leakage features detected:\n"
            +
            "\n".join(
                forbidden_features
            )
        )

    non_numeric = []

    for feature in features:

        if not pd.api.types.is_numeric_dtype(
            df[feature]
        ):

            non_numeric.append(
                feature
            )

    if non_numeric:

        raise RuntimeError(
            "Non numeric features detected:\n"
            +
            "\n".join(
                non_numeric
            )
        )

    classes = sorted(
        df[TARGET]
        .dropna()
        .unique()
        .tolist()
    )

    expected = sorted(
        EXPECTED_CLASSES
    )

    if classes != expected:

        raise RuntimeError(
            f"Unexpected classes: {classes}"
        )

    print(
        f"Rows              : {len(df)}"
    )

    print(
        f"Features          : {len(features)}"
    )

    print(
        f"Missing features  : {len(missing_features)}"
    )

    print(
        f"Forbidden features: {len(forbidden_features)}"
    )

    print(
        f"Classes           : {classes}"
    )

    print()
    print(
        "Final validation : PASSED"
    )


# ============================================================
# MODEL
# ============================================================

def build_model():

    return Pipeline(
        steps=[
            (
                "imputer",
                SimpleImputer(
                    strategy="median",
                ),
            ),

            (
                "scaler",
                StandardScaler(),
            ),

            (
                "classifier",
                LogisticRegression(
                    max_iter=5000,
                    class_weight="balanced",
                    random_state=RANDOM_STATE,
                ),
            ),
        ]
    )


# ============================================================
# TRAIN
# ============================================================

def train_model(
    df,
    features,
):

    X = df[
        features
    ].copy()

    y = df[
        TARGET
    ].copy()

    model = build_model()

    print()
    print("=" * 90)
    print("TRAINING FINAL LOGISTIC MODEL V4.2")
    print("=" * 90)

    print()
    print(
        f"Training observations : {len(X)}"
    )

    print(
        f"Number of features     : {len(features)}"
    )

    print()
    print(
        "Target distribution:"
    )

    print(
        y.value_counts()
    )

    print()
    print(
        "Training..."
    )

    model.fit(
        X,
        y,
    )

    print(
        "Training completed."
    )

    return model


# ============================================================
# SAVE MODEL
# ============================================================

def save_model(
    model,
    df,
    features,
):

    os.makedirs(
        MODEL_DIR,
        exist_ok=True,
    )

    artifact = {
        "model":
            model,

        "features":
            features,

        "target":
            TARGET,

        "model_version":
            "V4.2",

        "prediction_horizon_days":
            30,
    }

    joblib.dump(
        artifact,
        MODEL_FILE,
    )

    classifier = model.named_steps[
        "classifier"
    ]

    metadata = {

        "model_name":
            "Smart E-Bike 30-Day Risk Classifier",

        "model_type":
            "LogisticRegression",

        "model_version":
            "V4.2",

        "prediction_horizon_days":
            30,

        "target":
            TARGET,

        "classes":
            classifier.classes_.tolist(),

        "n_features":
            len(features),

        "features":
            features,

        "training_rows":
            int(
                len(df)
            ),

        "training_bikes":
            int(
                df[
                    "bike_id"
                ].nunique()
            ),

        "training_start":
            str(
                df[
                    "timestamp"
                ].min()
            ),

        "training_end":
            str(
                df[
                    "timestamp"
                ].max()
            ),

        "evaluation":
            {
                "protocol":
                    "purged_spatiotemporal_cross_validation",

                "accuracy":
                    0.9313,

                "balanced_accuracy":
                    0.8788,

                "macro_f1":
                    0.9121,

                "critical_recall":
                    1.0,

                "normal_warning_recall":
                    1.0,

                "warning_critical_recall":
                    1.0,
            },

        "important_note":
            (
                "Evaluation performed on synthetic "
                "digital-twin telemetry using strict "
                "bike holdout and 30-day target-horizon purge."
            ),
    }

    with open(
        METADATA_FILE,
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            metadata,
            f,
            indent=4,
            ensure_ascii=False,
        )

    print()
    print("=" * 90)
    print("MODEL ARTIFACTS SAVED")
    print("=" * 90)

    print(
        f"Model    : {MODEL_FILE}"
    )

    print(
        f"Metadata : {METADATA_FILE}"
    )


# ============================================================
# RELOAD TEST
# ============================================================

def reload_test(
    df,
):

    print()
    print("=" * 90)
    print("MODEL RELOAD TEST")
    print("=" * 90)

    artifact = joblib.load(
        MODEL_FILE
    )

    model = artifact[
        "model"
    ]

    features = artifact[
        "features"
    ]

    sample = df.iloc[
        [0]
    ]

    X_sample = sample[
        features
    ]

    prediction = model.predict(
        X_sample
    )[0]

    probabilities = model.predict_proba(
        X_sample
    )[0]

    classifier = model.named_steps[
        "classifier"
    ]

    classes = (
        classifier.classes_
    )

    print()
    print(
        f"Bike ID : "
        f"{sample.iloc[0]['bike_id']}"
    )

    print(
        f"Prediction : {prediction}"
    )

    print()

    print(
        "Probabilities:"
    )

    for (
        class_name,
        probability,
    ) in zip(
        classes,
        probabilities,
    ):

        print(
            f"{class_name:<10} : "
            f"{probability * 100:.2f}%"
        )

    probability_sum = (
        probabilities.sum()
    )

    print()
    print(
        f"Probability sum : "
        f"{probability_sum:.6f}"
    )

    if not (
        0.999
        <=
        probability_sum
        <=
        1.001
    ):

        raise RuntimeError(
            "Invalid probability output."
        )

    print()
    print(
        "Reload test : PASSED"
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 90)
    print(
        "FINAL MODEL TRAINING V4.2"
    )
    print("=" * 90)

    df, features = load_data()

    validate_data(
        df,
        features,
    )

    model = train_model(
        df,
        features,
    )

    save_model(
        model,
        df,
        features,
    )

    reload_test(
        df
    )

    print()
    print("=" * 90)
    print("FINAL MODEL READY FOR DEPLOYMENT")
    print("=" * 90)


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    main()