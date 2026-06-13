import collections
import threading


class RunningStats:
    def __init__(self):
        self._lock = threading.Lock()
        self._count = 0
        self._total = 0.0
        self._max = 0.0
        self._recent = collections.deque(maxlen=256)

    def record(self, value):
        value = float(value)
        with self._lock:
            self._count += 1
            self._total += value
            self._max = max(self._max, value)
            self._recent.append(value)

    def snapshot_ms(self):
        with self._lock:
            recent = sorted(self._recent)
            count = self._count
            total = self._total
            max_value = self._max

        def percentile(fraction):
            if not recent:
                return 0.0
            index = min(len(recent) - 1, int(round((len(recent) - 1) * fraction)))
            return recent[index] * 1000.0

        return {
            "count": count,
            "avgMs": (total / count * 1000.0) if count else 0.0,
            "maxMs": max_value * 1000.0,
            "p50Ms": percentile(0.50),
            "p95Ms": percentile(0.95),
        }
