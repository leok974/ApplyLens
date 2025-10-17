"""Active learning subsystem for continuous improvement.

Modules:
- feeds: Load labeled examples from approvals, feedback, gold sets
- heur_trainer: Train heuristic thresholds from labeled data
- weights: Compute judge reliability weights
- sampler: Uncertainty sampling for human review
- bundles: Version and apply configuration bundles
"""

__all__ = ["feeds", "heur_trainer", "weights", "sampler", "bundles"]
