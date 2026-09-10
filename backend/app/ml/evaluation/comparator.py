"""
Experiment comparator — Baseline vs Enhanced, ablation support.
No results are fabricated. All comparisons are over real EvaluationMetrics objects.
"""
from dataclasses import dataclass
from typing import Dict, List, Optional

from app.ml.evaluation.metrics import EvaluationMetrics

ABLATION_CONFIGS: List[str] = [
    "baseline",
    "baseline_context",
    "baseline_adaptive_window",
    "baseline_adaptive_threshold",
    "enhanced_full",
]


@dataclass
class ExperimentComparison:
    experiment_name: str
    configurations: Dict[str, Optional[EvaluationMetrics]]
    winner: Optional[str]
    comparison_notes: str


def compare_experiments(
    experiment_name: str,
    results: Dict[str, Optional[EvaluationMetrics]],
) -> ExperimentComparison:
    """Compare evaluated configurations. Unevaluated ones are clearly labeled."""
    evaluated = {
        k: v for k, v in results.items()
        if v is not None and v.evaluated_on_ground_truth and v.f1 is not None
    }

    if not evaluated:
        return ExperimentComparison(
            experiment_name=experiment_name,
            configurations=results,
            winner=None,
            comparison_notes="No configurations evaluated yet.",
        )

    winner = max(evaluated, key=lambda k: evaluated[k].f1)  # type: ignore
    notes = "\n".join(
        f"{n}: F1={m.f1:.4f} Prec={m.precision:.4f} Recall={m.recall:.4f}"
        for n, m in evaluated.items()
    )
    return ExperimentComparison(
        experiment_name=experiment_name,
        configurations=results,
        winner=winner,
        comparison_notes=notes,
    )


def ablation_summary(
    ablation_results: Dict[str, Optional[EvaluationMetrics]],
) -> Dict[str, Dict]:
    """Summarize ablation study. Unevaluated configs labeled as not_run."""
    out: Dict[str, Dict] = {}
    for cfg in ABLATION_CONFIGS:
        m = ablation_results.get(cfg)
        if m is None:
            out[cfg] = {"status": "not_run"}
        elif not m.evaluated_on_ground_truth:
            out[cfg] = {"status": "not_evaluated", "notes": m.notes}
        else:
            out[cfg] = {"status": "evaluated", **m.to_dict()}
    return out
