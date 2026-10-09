"""Evaluation helpers that keep experimental results from being described as product accuracy."""


def evaluation_record(*, dataset: str, metrics: dict, protocol: str) -> dict:
    return {
        "dataset": dataset,
        "protocol": protocol,
        "metrics": metrics,
        "claim_accuracy": False,
        "status": "experimental",
    }
