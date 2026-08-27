# ============================================================
# FINAL PURGED SPATIO-TEMPORAL CROSS-VALIDATION V4.2
# ============================================================

import os
import json
import warnings

import numpy as np
import pandas as pd

from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    f1_score,
    recall_score,
    confusion_matrix,
    classification_report,
)

warnings.filterwarnings("ignore")


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

OUTPUT_FILE = os.path.join(
    "data",
    "processed",
    "final_purged_spatiotemporal_cv_V42.csv",
)


# ============================================================
# CONSTANTS
# ============================================================

LABELS = [
    "NORMAL",
    "WARNING",
    "CRITICAL",
]

RANDOM_STATE = 42


# ============================================================
# FOLDS
# ============================================================

# IMPORTANT:
#
# Train observations are first restricted by timestamp.
#
# Then we PURGE every training observation whose
# +30-day target timestamp reaches or crosses test_start.
#
# Therefore:
#
# target_timestamp_30d < test_start
#
# This prevents target-horizon leakage.


FOLDS = [
    {
        "name": "FOLD_1",
        "train_start": "2026-01-01",
        "train_end": "2026-03-01",
        "test_start": "2026-03-01",
        "test_end": "2026-04-01",
    },
    {
        "name": "FOLD_2",
        "train_start": "2026-01-01",
        "train_end": "2026-04-01",
        "test_start": "2026-04-01",
        "test_end": "2026-05-01",
    },
    {
        "name": "FOLD_3",
        "train_start": "2026-01-01",
        "train_end": "2026-05-01",
        "test_start": "2026-05-01",
        "test_end": "2026-06-01",
    },
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

    df = pd.read_csv(DATA_FILE)

    df["timestamp"] = pd.to_datetime(
        df["timestamp"]
    )

    df["target_timestamp_30d"] = pd.to_datetime(
        df["target_timestamp_30d"]
    )

    df = df.sort_values(
        ["timestamp", "bike_id"]
    ).reset_index(drop=True)

    with open(
        SCHEMA_FILE,
        "r",
        encoding="utf-8",
    ) as f:

        schema = json.load(f)

    features = schema["features"]

    missing_features = [
        feature
        for feature in features
        if feature not in df.columns
    ]

    if missing_features:

        raise ValueError(
            "Missing features:\n"
            +
            "\n".join(missing_features)
        )

    return df, features


# ============================================================
# MODEL
# ============================================================

def build_model():

    return Pipeline(
        steps=[
            (
                "scaler",
                StandardScaler(),
            ),
            (
                "model",
                LogisticRegression(
                    max_iter=5000,
                    class_weight="balanced",
                    random_state=RANDOM_STATE,
                ),
            ),
        ]
    )


# ============================================================
# METRICS
# ============================================================

def compute_metrics(
    y_true,
    y_pred,
):

    accuracy = accuracy_score(
        y_true,
        y_pred,
    )

    balanced_accuracy = balanced_accuracy_score(
        y_true,
        y_pred,
    )

    macro_f1 = f1_score(
        y_true,
        y_pred,
        labels=LABELS,
        average="macro",
        zero_division=0,
    )

    if (
        np.asarray(y_true)
        ==
        "CRITICAL"
    ).sum() > 0:

        critical_recall = recall_score(
            y_true,
            y_pred,
            labels=["CRITICAL"],
            average="macro",
            zero_division=0,
        )

    else:

        critical_recall = np.nan

    return {
        "accuracy": accuracy,
        "balanced_accuracy": balanced_accuracy,
        "macro_f1": macro_f1,
        "critical_recall": critical_recall,
    }


# ============================================================
# TRANSITION RECALL
# ============================================================

def transition_recall(
    test_df,
    y_pred,
    transition_name,
    expected_target,
):

    mask = (
        test_df[
            "future_transition_30d"
        ].to_numpy()
        ==
        transition_name
    )

    n = int(
        mask.sum()
    )

    if n == 0:

        return {
            "n": 0,
            "recall": np.nan,
        }

    pred = np.asarray(
        y_pred
    )[mask]

    recall = np.mean(
        pred
        ==
        expected_target
    )

    return {
        "n": n,
        "recall": float(recall),
    }


# ============================================================
# SAFE FORMAT
# ============================================================

def format_percent(value):

    if pd.isna(value):
        return "N/A"

    return (
        f"{value * 100:.2f}%"
    )


# ============================================================
# SELECT UNSEEN BIKES
# ============================================================

def select_test_bikes(
    candidate_test,
    n_bikes=5,
):

    """
    Select 5 bikes deterministically.

    Priority is given to bikes containing actual transitions
    in the test month.

    This is NOT used to optimize model performance.

    It is only used to make the strict test informative enough
    to evaluate transition prediction.
    """

    stats = []

    for bike_id, group in candidate_test.groupby(
        "bike_id"
    ):

        nw = (
            group[
                "future_transition_30d"
            ]
            ==
            "NORMAL->WARNING"
        ).sum()

        wc = (
            group[
                "future_transition_30d"
            ]
            ==
            "WARNING->CRITICAL"
        ).sum()

        transitions = (
            nw
            +
            wc
        )

        stats.append(
            {
                "bike_id": bike_id,
                "normal_warning": int(nw),
                "warning_critical": int(wc),
                "transitions": int(transitions),
                "rows": len(group),
            }
        )

    stats = pd.DataFrame(
        stats
    )

    if len(stats) < n_bikes:

        raise ValueError(
            "Not enough bikes in test period."
        )

    stats = stats.sort_values(
        [
            "transitions",
            "normal_warning",
            "warning_critical",
            "rows",
            "bike_id",
        ],
        ascending=[
            False,
            False,
            False,
            False,
            True,
        ],
    )

    selected = (
        stats
        .head(n_bikes)[
            "bike_id"
        ]
        .tolist()
    )

    return selected, stats


# ============================================================
# BUILD PURGED FOLD
# ============================================================

def build_purged_fold(
    df,
    config,
):

    train_start = pd.Timestamp(
        config["train_start"]
    )

    train_end = pd.Timestamp(
        config["train_end"]
    )

    test_start = pd.Timestamp(
        config["test_start"]
    )

    test_end = pd.Timestamp(
        config["test_end"]
    )

    # --------------------------------------------------------
    # Candidate test period
    # --------------------------------------------------------

    candidate_test = df[
        (df["timestamp"] >= test_start)
        &
        (df["timestamp"] < test_end)
    ].copy()

    if candidate_test.empty:

        raise ValueError(
            f"{config['name']}: empty test period."
        )

    # --------------------------------------------------------
    # Select 5 unseen bikes
    # --------------------------------------------------------

    test_bikes, bike_stats = select_test_bikes(
        candidate_test,
        n_bikes=5,
    )

    # --------------------------------------------------------
    # Test = selected bikes only
    # --------------------------------------------------------

    test = candidate_test[
        candidate_test[
            "bike_id"
        ].isin(test_bikes)
    ].copy()

    # --------------------------------------------------------
    # Candidate train
    #
    # Exclude ALL test bikes.
    # --------------------------------------------------------

    train_before_purge = df[
        (df["timestamp"] >= train_start)
        &
        (df["timestamp"] < train_end)
        &
        (
            ~df["bike_id"].isin(
                test_bikes
            )
        )
    ].copy()

    # --------------------------------------------------------
    # TARGET-HORIZON PURGE
    #
    # Critical condition:
    #
    # target_timestamp_30d < test_start
    #
    # --------------------------------------------------------

    train = train_before_purge[
        train_before_purge[
            "target_timestamp_30d"
        ]
        <
        test_start
    ].copy()

    purged_rows = (
        len(train_before_purge)
        -
        len(train)
    )

    return {
        "train": train,
        "test": test,
        "test_bikes": test_bikes,
        "bike_stats": bike_stats,
        "purged_rows": purged_rows,
        "test_start": test_start,
    }


# ============================================================
# VALIDATE FOLD
# ============================================================

def validate_fold(
    train,
    test,
    test_start,
):

    if train.empty:
        raise ValueError(
            "Training set is empty."
        )

    if test.empty:
        raise ValueError(
            "Test set is empty."
        )

    train_bikes = set(
        train["bike_id"].unique()
    )

    test_bikes = set(
        test["bike_id"].unique()
    )

    overlap = (
        train_bikes
        &
        test_bikes
    )

    if overlap:

        raise RuntimeError(
            f"Bike leakage detected: {overlap}"
        )

    max_train_timestamp = (
        train[
            "timestamp"
        ].max()
    )

    max_train_target = (
        train[
            "target_timestamp_30d"
        ].max()
    )

    min_test_timestamp = (
        test[
            "timestamp"
        ].min()
    )

    if not (
        max_train_timestamp
        <
        min_test_timestamp
    ):

        raise RuntimeError(
            "Observation-time leakage detected."
        )

    if not (
        max_train_target
        <
        test_start
    ):

        raise RuntimeError(
            "TARGET-HORIZON LEAKAGE DETECTED."
        )

    return {
        "bike_overlap": len(overlap),
        "max_train_timestamp": max_train_timestamp,
        "max_train_target": max_train_target,
        "min_test_timestamp": min_test_timestamp,
    }


# ============================================================
# MAIN
# ============================================================

def main():

    print(
        "\n"
        +
        "=" * 120
    )

    print(
        "FINAL PURGED SPATIO-TEMPORAL CROSS-VALIDATION V4.2"
    )

    print(
        "=" * 120
    )

    df, features = load_data()

    print(
        f"\nObservations : {len(df)}"
    )

    print(
        f"Features     : {len(features)}"
    )

    print(
        f"Bikes        : {df['bike_id'].nunique()}"
    )

    fold_results = []

    all_true = []
    all_pred = []
    all_persistence = []
    all_test_frames = []

    # ========================================================
    # FOLDS
    # ========================================================

    for config in FOLDS:

        print(
            "\n"
            +
            "=" * 120
        )

        print(
            config["name"]
        )

        print(
            "=" * 120
        )

        fold_data = build_purged_fold(
            df,
            config,
        )

        train = fold_data[
            "train"
        ]

        test = fold_data[
            "test"
        ]

        test_bikes = fold_data[
            "test_bikes"
        ]

        purged_rows = fold_data[
            "purged_rows"
        ]

        test_start = fold_data[
            "test_start"
        ]

        integrity = validate_fold(
            train,
            test,
            test_start,
        )

        print(
            "\nSTRICT PURGED SPLIT"
        )

        print(
            "-" * 70
        )

        print(
            f"Train rows          : {len(train)}"
        )

        print(
            f"Test rows           : {len(test)}"
        )

        print(
            f"Purged train rows   : {purged_rows}"
        )

        print(
            f"Train bikes         : {train['bike_id'].nunique()}"
        )

        print(
            f"Test bikes          : {test['bike_id'].nunique()}"
        )

        print(
            f"Bike overlap        : {integrity['bike_overlap']}"
        )

        print(
            f"Last train obs      : {integrity['max_train_timestamp']}"
        )

        print(
            f"Last train TARGET   : {integrity['max_train_target']}"
        )

        print(
            f"Test boundary       : {test_start}"
        )

        print(
            f"First test obs      : {integrity['min_test_timestamp']}"
        )

        print(
            "\nTEST BIKES"
        )

        print(
            "-" * 70
        )

        print(
            ", ".join(
                test_bikes
            )
        )

        print(
            "\nTARGET DISTRIBUTION"
        )

        print(
            "-" * 70
        )

        print(
            test[
                "target_risk_30d"
            ].value_counts()
        )

        print(
            "\nTRANSITIONS"
        )

        print(
            "-" * 70
        )

        print(
            test[
                "future_transition_30d"
            ].value_counts()
        )

        # ====================================================
        # TRAIN MODEL
        # ====================================================

        X_train = train[
            features
        ]

        y_train = train[
            "target_risk_30d"
        ]

        X_test = test[
            features
        ]

        y_test = test[
            "target_risk_30d"
        ]

        if y_train.nunique() < 2:

            raise RuntimeError(
                f"{config['name']}: "
                "training data contains fewer than 2 classes."
            )

        model = build_model()

        print(
            "\nTraining Logistic Regression..."
        )

        model.fit(
            X_train,
            y_train,
        )

        y_pred = model.predict(
            X_test
        )

        # ====================================================
        # MODEL METRICS
        # ====================================================

        metrics = compute_metrics(
            y_test,
            y_pred,
        )

        nw = transition_recall(
            test,
            y_pred,
            "NORMAL->WARNING",
            "WARNING",
        )

        wc = transition_recall(
            test,
            y_pred,
            "WARNING->CRITICAL",
            "CRITICAL",
        )

        print(
            "\nLOGISTIC RESULTS"
        )

        print(
            "-" * 70
        )

        print(
            f"Accuracy          : "
            f"{metrics['accuracy'] * 100:.2f}%"
        )

        print(
            f"Balanced accuracy : "
            f"{metrics['balanced_accuracy'] * 100:.2f}%"
        )

        print(
            f"Macro F1          : "
            f"{metrics['macro_f1'] * 100:.2f}%"
        )

        print(
            f"Critical recall   : "
            f"{format_percent(metrics['critical_recall'])}"
        )

        print(
            f"NORMAL->WARNING   : "
            f"n={nw['n']} | "
            f"recall={format_percent(nw['recall'])}"
        )

        print(
            f"WARNING->CRITICAL : "
            f"n={wc['n']} | "
            f"recall={format_percent(wc['recall'])}"
        )

        # ====================================================
        # PERSISTENCE
        # ====================================================

        persistence_pred = test[
            "current_risk_class"
        ].to_numpy()

        persistence_metrics = compute_metrics(
            y_test,
            persistence_pred,
        )

        print(
            "\nPERSISTENCE"
        )

        print(
            "-" * 70
        )

        print(
            f"Accuracy          : "
            f"{persistence_metrics['accuracy'] * 100:.2f}%"
        )

        print(
            f"Balanced accuracy : "
            f"{persistence_metrics['balanced_accuracy'] * 100:.2f}%"
        )

        print(
            f"Macro F1          : "
            f"{persistence_metrics['macro_f1'] * 100:.2f}%"
        )

        # ====================================================
        # SAVE FOLD RESULT
        # ====================================================

        fold_results.append(
            {
                "fold": config["name"],
                "train_rows": len(train),
                "test_rows": len(test),
                "purged_rows": purged_rows,
                "train_bikes": train[
                    "bike_id"
                ].nunique(),
                "test_bikes": len(test_bikes),
                "bike_overlap": integrity[
                    "bike_overlap"
                ],
                "last_train_timestamp":
                    integrity[
                        "max_train_timestamp"
                    ],
                "last_train_target_timestamp":
                    integrity[
                        "max_train_target"
                    ],
                "test_start": test_start,
                "accuracy":
                    metrics[
                        "accuracy"
                    ],
                "balanced_accuracy":
                    metrics[
                        "balanced_accuracy"
                    ],
                "macro_f1":
                    metrics[
                        "macro_f1"
                    ],
                "critical_recall":
                    metrics[
                        "critical_recall"
                    ],
                "normal_warning_n":
                    nw[
                        "n"
                    ],
                "normal_warning_recall":
                    nw[
                        "recall"
                    ],
                "warning_critical_n":
                    wc[
                        "n"
                    ],
                "warning_critical_recall":
                    wc[
                        "recall"
                    ],
                "persistence_accuracy":
                    persistence_metrics[
                        "accuracy"
                    ],
                "persistence_balanced_accuracy":
                    persistence_metrics[
                        "balanced_accuracy"
                    ],
                "persistence_macro_f1":
                    persistence_metrics[
                        "macro_f1"
                    ],
            }
        )

        all_true.extend(
            y_test.tolist()
        )

        all_pred.extend(
            y_pred.tolist()
        )

        all_persistence.extend(
            persistence_pred.tolist()
        )

        test_copy = test[
            [
                "bike_id",
                "timestamp",
                "target_timestamp_30d",
                "current_risk_class",
                "target_risk_30d",
                "future_transition_30d",
            ]
        ].copy()

        test_copy[
            "prediction"
        ] = y_pred

        test_copy[
            "fold"
        ] = config["name"]

        all_test_frames.append(
            test_copy
        )

    # ========================================================
    # SUMMARY
    # ========================================================

    results_df = pd.DataFrame(
        fold_results
    )

    print(
        "\n"
        +
        "=" * 120
    )

    print(
        "FOLD SUMMARY"
    )

    print(
        "=" * 120
    )

    display_df = results_df.copy()

    percentage_columns = [
        "accuracy",
        "balanced_accuracy",
        "macro_f1",
        "critical_recall",
        "normal_warning_recall",
        "warning_critical_recall",
        "persistence_accuracy",
        "persistence_balanced_accuracy",
        "persistence_macro_f1",
    ]

    for column in percentage_columns:

        display_df[column] = (
            display_df[column]
            *
            100
        )

    print(
        display_df.to_string(
            index=False
        )
    )

    # ========================================================
    # AGGREGATED OOS
    # ========================================================

    all_true = np.asarray(
        all_true
    )

    all_pred = np.asarray(
        all_pred
    )

    all_persistence = np.asarray(
        all_persistence
    )

    combined_test = pd.concat(
        all_test_frames,
        ignore_index=True,
    )

    aggregate_metrics = compute_metrics(
        all_true,
        all_pred,
    )

    persistence_aggregate = compute_metrics(
        all_true,
        all_persistence,
    )

    aggregate_nw = transition_recall(
        combined_test,
        all_pred,
        "NORMAL->WARNING",
        "WARNING",
    )

    aggregate_wc = transition_recall(
        combined_test,
        all_pred,
        "WARNING->CRITICAL",
        "CRITICAL",
    )

    print(
        "\n"
        +
        "=" * 120
    )

    print(
        "AGGREGATED PURGED OUT-OF-SAMPLE RESULT"
    )

    print(
        "=" * 120
    )

    print(
        f"\nTotal predictions       : "
        f"{len(all_true)}"
    )

    print(
        f"NORMAL->WARNING n       : "
        f"{aggregate_nw['n']}"
    )

    print(
        f"WARNING->CRITICAL n     : "
        f"{aggregate_wc['n']}"
    )

    print(
        "\nLOGISTIC V4.2"
    )

    print(
        "-" * 70
    )

    print(
        f"Accuracy                : "
        f"{aggregate_metrics['accuracy'] * 100:.2f}%"
    )

    print(
        f"Balanced accuracy       : "
        f"{aggregate_metrics['balanced_accuracy'] * 100:.2f}%"
    )

    print(
        f"Macro F1                : "
        f"{aggregate_metrics['macro_f1'] * 100:.2f}%"
    )

    print(
        f"Critical recall         : "
        f"{format_percent(aggregate_metrics['critical_recall'])}"
    )

    print(
        f"NORMAL->WARNING recall  : "
        f"{format_percent(aggregate_nw['recall'])}"
    )

    print(
        f"WARNING->CRITICAL recall: "
        f"{format_percent(aggregate_wc['recall'])}"
    )

    print(
        "\nPERSISTENCE"
    )

    print(
        "-" * 70
    )

    print(
        f"Accuracy                : "
        f"{persistence_aggregate['accuracy'] * 100:.2f}%"
    )

    print(
        f"Balanced accuracy       : "
        f"{persistence_aggregate['balanced_accuracy'] * 100:.2f}%"
    )

    print(
        f"Macro F1                : "
        f"{persistence_aggregate['macro_f1'] * 100:.2f}%"
    )

    print(
        f"Critical recall         : "
        f"{format_percent(persistence_aggregate['critical_recall'])}"
    )

    # ========================================================
    # CONFUSION MATRIX
    # ========================================================

    print(
        "\n"
        +
        "=" * 120
    )

    print(
        "AGGREGATED CONFUSION MATRIX"
    )

    print(
        "=" * 120
    )

    cm = confusion_matrix(
        all_true,
        all_pred,
        labels=LABELS,
    )

    cm_df = pd.DataFrame(
        cm,
        index=[
            "TRUE_NORMAL",
            "TRUE_WARNING",
            "TRUE_CRITICAL",
        ],
        columns=[
            "PRED_NORMAL",
            "PRED_WARNING",
            "PRED_CRITICAL",
        ],
    )

    print(
        cm_df
    )

    print(
        "\nAGGREGATED CLASSIFICATION REPORT"
    )

    print(
        "-" * 70
    )

    print(
        classification_report(
            all_true,
            all_pred,
            labels=LABELS,
            zero_division=0,
        )
    )

    # ========================================================
    # FINAL INTEGRITY CHECK
    # ========================================================

    print(
        "\n"
        +
        "=" * 120
    )

    print(
        "FINAL LEAKAGE INTEGRITY"
    )

    print(
        "=" * 120
    )

    total_overlap = (
        results_df[
            "bike_overlap"
        ].sum()
    )

    horizon_valid = (
        pd.to_datetime(
            results_df[
                "last_train_target_timestamp"
            ]
        )
        <
        pd.to_datetime(
            results_df[
                "test_start"
            ]
        )
    ).all()

    print(
        f"Total bike overlap         : "
        f"{total_overlap}"
    )

    print(
        f"All target horizons purged : "
        f"{horizon_valid}"
    )

    if (
        total_overlap == 0
        and
        horizon_valid
    ):

        print(
            "\nFINAL LEAKAGE CHECK : PASSED"
        )

    else:

        raise RuntimeError(
            "FINAL LEAKAGE CHECK FAILED."
        )

    # ========================================================
    # SAVE
    # ========================================================

    os.makedirs(
        os.path.dirname(
            OUTPUT_FILE
        ),
        exist_ok=True,
    )

    results_df.to_csv(
        OUTPUT_FILE,
        index=False,
    )

    print(
        f"\nSaved : {OUTPUT_FILE}"
    )

    print(
        "\n"
        +
        "=" * 120
    )

    print(
        "DONE"
    )

    print(
        "=" * 120
    )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()
