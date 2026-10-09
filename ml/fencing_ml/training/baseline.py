"""Mechanics for a classical baseline classifier.

The function refuses to train unless the caller explicitly acknowledges that the
dataset license allows local experimentation. The returned model is always
experimental and must not be registered as a production fencing recognizer.
"""

from __future__ import annotations


def train_baseline(features, labels, *, acknowledge_license: bool, synthetic: bool = False):
    if not synthetic and not acknowledge_license:
        raise RuntimeError(
            "Refusing to train. Confirm the dataset license allows this use, "
            "or pass synthetic=True only for pipeline tests on generated data."
        )
    try:
        import numpy as np
        from sklearn.linear_model import LogisticRegression
        from sklearn.model_selection import train_test_split
        from sklearn.pipeline import Pipeline
        from sklearn.preprocessing import StandardScaler
    except ImportError as exc:
        raise RuntimeError("numpy and scikit-learn are required to train the baseline") from exc
    array = np.asarray(features, dtype="float64")
    target = np.asarray(labels)
    if len(array) < 8:
        raise RuntimeError("Need at least 8 rows to build a train/test split")
    if len(set(target.tolist())) < 2:
        raise RuntimeError("Need at least two classes")
    train_x, test_x, train_y, test_y = train_test_split(array, target, test_size=0.25, random_state=7, stratify=target)
    model = Pipeline(
        [
            ("scale", StandardScaler()),
            ("clf", LogisticRegression(max_iter=500)),
        ]
    )
    model.fit(train_x, train_y)
    predicted = model.predict(test_x)
    accuracy = float((predicted == test_y).mean())
    return {
        "status": "experimental",
        "synthetic": synthetic,
        "claim_accuracy": False,
        "holdout_accuracy": accuracy,
        "holdout_size": int(len(test_y)),
        "classes": sorted(set(target.tolist())),
        "note": "Holdout accuracy is a pipeline check. It is not a fencing recognition claim.",
        "model": model,
    }
