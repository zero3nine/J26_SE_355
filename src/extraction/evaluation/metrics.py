from dataclasses import dataclass


@dataclass(frozen=True)
class ClassificationMetrics:
    true_positives: int
    false_positives: int
    false_negatives: int
    precision: float
    recall: float
    f1: float


def calculate_metrics(
    predicted: set[tuple[str, str]],
    ground_truth: set[tuple[str, str]],
) -> ClassificationMetrics:
    true_positives = len(
        predicted & ground_truth
    )

    false_positives = len(
        predicted - ground_truth
    )

    false_negatives = len(
        ground_truth - predicted
    )

    precision = (
        true_positives
        / (true_positives + false_positives)
        if true_positives + false_positives
        else 0.0
    )

    recall = (
        true_positives
        / (true_positives + false_negatives)
        if true_positives + false_negatives
        else 0.0
    )

    f1 = (
        2 * precision * recall
        / (precision + recall)
        if precision + recall
        else 0.0
    )

    return ClassificationMetrics(
        true_positives=true_positives,
        false_positives=false_positives,
        false_negatives=false_negatives,
        precision=precision,
        recall=recall,
        f1=f1,
    )