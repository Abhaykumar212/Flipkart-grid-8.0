from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.multiclass import OneVsRestClassifier


class ScaledOneVsRest:
    """OvR classifier with a conservative low-confidence ambiguity region."""

    def __init__(self, classifier: OneVsRestClassifier, ambiguity_cutoff: float, class_scales: np.ndarray):
        self.classifier = classifier
        self.ambiguity_cutoff = ambiguity_cutoff
        self.class_scales = class_scales
        self.estimators_ = classifier.estimators_

    def predict_proba(self, frame: pd.DataFrame) -> np.ndarray:
        probability = np.clip(self.classifier.predict_proba(frame), 0, 1)
        scale = 0.349 / max(self.ambiguity_cutoff, 1e-6)
        ambiguous = probability.max(axis=1) <= self.ambiguity_cutoff
        result = probability.copy()
        result[ambiguous] *= scale
        return np.clip(result * self.class_scales, 0, 1)
