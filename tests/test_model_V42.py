import joblib
import numpy as np
import pandas as pd


MODEL_FILE = (
    "models/logistic_temporal_V42.joblib"
)


def load_artifact():

    return joblib.load(
        MODEL_FILE
    )


def test_model_artifact_structure():

    artifact = load_artifact()

    assert isinstance(
        artifact,
        dict,
    )

    expected_keys = {
        "model",
        "features",
        "target",
        "model_version",
        "prediction_horizon_days",
    }

    assert expected_keys.issubset(
        artifact.keys()
    )


def test_model_version():

    artifact = load_artifact()

    assert (
        artifact["model_version"]
        ==
        "V4.2"
    )

    assert (
        artifact[
            "prediction_horizon_days"
        ]
        ==
        30
    )


def test_feature_count():

    artifact = load_artifact()

    assert len(
        artifact["features"]
    ) == 57


def test_model_classes():

    artifact = load_artifact()

    model = artifact[
        "model"
    ]

    classifier = model.named_steps[
        "classifier"
    ]

    classes = set(
        classifier.classes_
    )

    assert classes == {
        "NORMAL",
        "WARNING",
        "CRITICAL",
    }


def test_probability_sum():

    artifact = load_artifact()

    model = artifact[
        "model"
    ]

    features = artifact[
        "features"
    ]

    #
    # Artificial input only to verify
    # technical model behavior.
    #

    X = pd.DataFrame(
        np.zeros(
            (
                1,
                len(features),
            )
        ),
        columns=features,
    )

    probabilities = (
        model.predict_proba(
            X
        )[0]
    )

    assert np.isclose(
        probabilities.sum(),
        1.0,
        atol=1e-6,
    )

    assert np.all(
        probabilities >= 0
    )

    assert np.all(
        probabilities <= 1
    )