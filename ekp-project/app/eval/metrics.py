from typing import List, Dict

def calculate_recall(retrieved: List[str], relevant: List[str]) -> float:
    """Calculate Recall metric."""
    if not relevant:
        return 0.0
    return len(set(retrieved) & set(relevant)) / len(relevant)

def calculate_precision(retrieved: List[str], relevant: List[str]) -> float:
    """Calculate Precision metric."""
    if not retrieved:
        return 0.0
    return len(set(retrieved) & set(relevant)) / len(retrieved)

def calculate_f1_score(precision: float, recall: float) -> float:
    """Calculate F1 Score metric."""
    if precision + recall == 0:
        return 0.0
    return 2 * (precision * recall) / (precision + recall)

def log_metrics(metrics: Dict[str, float]) -> None:
    """Log evaluation metrics."""
    for metric, value in metrics.items():
        print(f"{metric}: {value:.4f}")

def evaluate_retrieval(retrieved: List[str], relevant: List[str]) -> None:
    """Evaluate retrieval performance."""
    recall = calculate_recall(retrieved, relevant)
    precision = calculate_precision(retrieved, relevant)
    f1 = calculate_f1_score(precision, recall)

    metrics = {
        "Recall": recall,
        "Precision": precision,
        "F1 Score": f1
    }
    
    log_metrics(metrics)