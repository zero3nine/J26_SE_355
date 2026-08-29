from dataclasses import dataclass

from .metrics import ClassificationMetrics, calculate_metrics


@dataclass(frozen=True)
class ThresholdResult:
    threshold: float
    metrics: ClassificationMetrics


def calibrate_threshold(
    predictions_by_threshold: dict[
        float,
        set[tuple[str, str]],
    ],
    ground_truth: set[tuple[str, str]],
) -> list[ThresholdResult]:
    results = []

    for threshold, predictions in sorted(
        predictions_by_threshold.items()
    ):
        metrics = calculate_metrics(
            predicted=predictions,
            ground_truth=ground_truth,
        )

        results.append(
            ThresholdResult(
                threshold=threshold,
                metrics=metrics,
            )
        )

    return results


def select_best_threshold(
    results: list[ThresholdResult],
) -> ThresholdResult:
    if not results:
        raise ValueError(
            "At least one threshold result is required."
        )

    return max(
        results,
        key=lambda result: (
            result.metrics.f1,
            result.metrics.precision,
        ),
    )