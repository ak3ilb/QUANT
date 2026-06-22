import numpy as np


class PageHinkleyDetector:
  """Concept drift detector for trade win/loss streams."""

  def __init__(self, delta: float = 0.005, threshold: float = 5.0, window: int = 15):
    self.delta = delta
    self.threshold = threshold
    self.window = max(5, int(window))
    self.reset()

  def reset(self):
    self.recent: list[float] = []
    self.baseline = 0.5
    self.cumsum = 0.0
    self.min_cumsum = 0.0
    self.n = 0
    self.drift_detected = False
    self.drift_count = 0

  def update(self, value: float) -> bool:
    """Feed a bounded outcome (1=win, 0=loss). Returns True on new drift."""
    value = float(value)
    self.n += 1
    self.recent.append(value)
    if len(self.recent) > self.window:
      self.recent.pop(0)

    if len(self.recent) >= self.window:
      rolling = float(np.mean(self.recent))
      if self.n <= self.window:
        self.baseline = rolling
      self.cumsum += rolling - self.baseline - self.delta
      self.min_cumsum = min(self.min_cumsum, self.cumsum)

      if (self.cumsum - self.min_cumsum) > self.threshold or rolling < (self.baseline - 0.25):
        self.drift_detected = True
        self.drift_count += 1
        self.cumsum = 0.0
        self.min_cumsum = 0.0
        self.baseline = rolling
        return True

    return False

  def is_active(self) -> bool:
    return self.drift_detected

  def clear(self):
    self.drift_detected = False

  def severity(self) -> str:
    if self.drift_count >= 3:
      return "severe"
    if self.drift_detected:
      return "moderate"
    return "none"

  def size_multiplier(self) -> float:
    sev = self.severity()
    if sev == "severe":
      return 0.0
    if sev == "moderate":
      return 0.35
    return 1.0

  def to_dict(self) -> dict:
    return {
      "drift_active": self.drift_detected,
      "drift_events": self.drift_count,
      "severity": self.severity(),
      "size_multiplier": self.size_multiplier(),
      "observations": self.n,
      "baseline_win_rate": self.baseline,
      "recent_win_rate": float(np.mean(self.recent)) if self.recent else 0.5,
    }

  @classmethod
  def from_dict(cls, data: dict) -> "PageHinkleyDetector":
    det = cls()
    det.cumsum = float(data.get("cumsum", 0.0))
    det.min_cumsum = float(data.get("min_cumsum", 0.0))
    det.n = int(data.get("n", 0))
    det.baseline = float(data.get("baseline", 0.5))
    det.drift_detected = bool(data.get("drift_detected", False))
    det.drift_count = int(data.get("drift_count", 0))
    det.recent = list(data.get("recent", []))
    return det

  def as_dict(self) -> dict:
    return {
      "cumsum": self.cumsum,
      "min_cumsum": self.min_cumsum,
      "n": self.n,
      "baseline": self.baseline,
      "drift_detected": self.drift_detected,
      "drift_count": self.drift_count,
      "recent": self.recent[-self.window :],
    }
