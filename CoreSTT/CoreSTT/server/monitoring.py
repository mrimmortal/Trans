import os
import time
from importlib import import_module


MB = 1024.0 * 1024.0


DIAGNOSTIC_THRESHOLDS = {
    "cpuPercent": {"warn": 75.0, "critical": 90.0},
    "systemMemoryPercent": {"warn": 80.0, "critical": 92.0},
    "cudaMemoryPressure": {"warn": 80.0, "critical": 92.0},
    "cudaFreeMb": {"warnBelow": 1500.0, "criticalBelow": 750.0},
    "queueDelayP95Ms": {
        "realtime": {"warn": 500.0, "critical": 1500.0},
        "final": {"warn": 1000.0, "critical": 3000.0},
    },
    "inferenceDurationP95Ms": {
        "realtime": {"warn": 800.0, "critical": 2000.0},
        "final": {"warn": 3000.0, "critical": 8000.0},
    },
    "totalLatencyP95Ms": {
        "realtime": {"warn": 1500.0, "critical": 3000.0},
        "final": {"warn": 5000.0, "critical": 12000.0},
    },
    "workerBusyRatio": {"warn": 0.75, "critical": 0.90},
    "rejectedJobs": {"warn": 1, "critical": 5},
}


def _round(value, digits=3):
    if value is None:
        return None
    try:
        return round(float(value), digits)
    except (TypeError, ValueError):
        return None


def _bytes_to_mb(value):
    if value is None:
        return None
    try:
        return _round(float(value) / MB, 3)
    except (TypeError, ValueError):
        return None


class ResourceMonitor:
    def __init__(self, settings, psutil_module=None, torch_module=None):
        self.settings = settings
        self._psutil = psutil_module
        self._torch = torch_module
        self._process = None
        self._psutil_loaded = False
        self._torch_loaded = False

    def snapshot(self):
        return {
            "timestamp": time.time(),
            "process": self._process_snapshot(),
            "system": self._system_snapshot(),
            "cuda": self._cuda_snapshot(),
        }

    def _load_psutil(self):
        if self._psutil_loaded:
            return self._psutil
        self._psutil_loaded = True
        if self._psutil is None:
            try:
                self._psutil = import_module("psutil")
            except Exception:
                self._psutil = None
        if self._psutil is not None and self._process is None:
            try:
                self._process = self._psutil.Process()
            except Exception:
                self._process = None
        return self._psutil

    def _load_torch(self):
        if self._torch_loaded:
            return self._torch
        self._torch_loaded = True
        if self._torch is None:
            try:
                self._torch = import_module("torch")
            except Exception:
                self._torch = None
        return self._torch

    def _process_snapshot(self):
        psutil = self._load_psutil()
        if psutil is None or self._process is None:
            return {"available": False, "reason": "psutil_unavailable"}

        process = self._process
        data = {"available": True}
        try:
            data["cpuPercent"] = _round(process.cpu_percent(interval=None), 3)
        except Exception:
            data["cpuPercent"] = None
        try:
            data["rssMb"] = _bytes_to_mb(process.memory_info().rss)
        except Exception:
            data["rssMb"] = None
        try:
            data["threadCount"] = int(process.num_threads())
        except Exception:
            data["threadCount"] = None
        return data

    def _system_snapshot(self):
        psutil = self._load_psutil()
        if psutil is None:
            return {"available": False, "reason": "psutil_unavailable"}

        data = {"available": True}
        try:
            data["cpuPercent"] = _round(psutil.cpu_percent(interval=None), 3)
        except Exception:
            data["cpuPercent"] = None
        try:
            memory = psutil.virtual_memory()
            data["memoryPercent"] = _round(memory.percent, 3)
            data["memoryAvailableMb"] = _bytes_to_mb(memory.available)
        except Exception:
            data["memoryPercent"] = None
            data["memoryAvailableMb"] = None
        try:
            data["loadAverage"] = [_round(value, 3) for value in os.getloadavg()]
        except Exception:
            data["loadAverage"] = None
        return data

    def _cuda_snapshot(self):
        if not getattr(self.settings, "resource_metrics_include_cuda", True):
            return {"available": False, "reason": "cuda_monitoring_disabled"}

        torch = self._load_torch()
        if torch is None or not hasattr(torch, "cuda"):
            return {"available": False, "reason": "torch_unavailable"}

        cuda = torch.cuda
        try:
            available = bool(cuda.is_available())
        except Exception:
            available = False
        if not available:
            return {"available": False, "reason": "cuda_unavailable"}

        device_index = getattr(self.settings, "gpu_device_index", 0)
        if isinstance(device_index, (list, tuple)):
            device_index = device_index[0] if device_index else 0
        data = {"available": True, "deviceIndex": device_index}
        try:
            data["deviceName"] = cuda.get_device_name(device_index)
        except Exception:
            data["deviceName"] = None
        try:
            data["allocatedMb"] = _bytes_to_mb(cuda.memory_allocated(device_index))
        except Exception:
            data["allocatedMb"] = None
        try:
            data["reservedMb"] = _bytes_to_mb(cuda.memory_reserved(device_index))
        except Exception:
            data["reservedMb"] = None
        try:
            data["maxAllocatedMb"] = _bytes_to_mb(cuda.max_memory_allocated(device_index))
        except Exception:
            data["maxAllocatedMb"] = None
        try:
            free_bytes, total_bytes = cuda.mem_get_info(device_index)
            data["freeMb"] = _bytes_to_mb(free_bytes)
            data["totalMb"] = _bytes_to_mb(total_bytes)
        except Exception:
            data["freeMb"] = None
            data["totalMb"] = None
        total_mb = data.get("totalMb")
        free_mb = data.get("freeMb")
        if total_mb and free_mb is not None:
            # Device-wide free memory includes allocations made by CTranslate2,
            # unlike torch's allocated/reserved counters.
            data["memoryPressure"] = _round(
                ((total_mb - free_mb) / total_mb) * 100.0,
                3,
            )
        else:
            data["memoryPressure"] = None
        utilization = getattr(cuda, "utilization", None)
        if callable(utilization):
            try:
                data["utilizationPercent"] = _round(utilization(device_index), 3)
            except Exception:
                data["utilizationPercent"] = None
        else:
            data["utilizationPercent"] = None
        return data


def diagnose_bottleneck(metrics, thresholds=None):
    thresholds = thresholds or DIAGNOSTIC_THRESHOLDS
    resources = metrics.get("resources") or {}
    scheduler = metrics.get("scheduler") or {}
    sessions = metrics.get("sessions") or {}
    process = resources.get("process") or {}
    system = resources.get("system") or {}
    cuda = resources.get("cuda") or {}
    signals = []

    cpu_percent = _max_number(process.get("cpuPercent"), system.get("cpuPercent"))
    system_memory_percent = _number(system.get("memoryPercent"))
    cuda_available = bool(cuda.get("available"))
    cuda_pressure = _number(cuda.get("memoryPressure"), None) if cuda_available else None
    cuda_free_mb = _number(cuda.get("freeMb"), None) if cuda_available else None
    realtime = _lane_metrics(scheduler, "realtime")
    final = _lane_metrics(scheduler, "final")
    max_busy = _max_worker_busy(scheduler)
    rejected = _rejected_jobs(scheduler)
    max_recording_seconds = _max_recording_seconds(sessions)

    if _gte(cuda_pressure, thresholds["cudaMemoryPressure"]["critical"]):
        signals.append("CUDA memory pressure is critical")
        return _diagnosis("gpu_memory", signals, "Reduce model size, batch size, or concurrent GPU work.")
    if cuda_free_mb is not None and cuda_free_mb < thresholds["cudaFreeMb"]["criticalBelow"]:
        signals.append("CUDA free memory is critically low")
        return _diagnosis("gpu_memory", signals, "Free GPU memory or use a smaller/faster compute configuration.")

    if _gte(cpu_percent, thresholds["cpuPercent"]["critical"]) and _high_inference(final, realtime):
        signals.append("CPU is critical while inference duration is high")
        return _diagnosis("hardware_cpu", signals, "Use a faster CPU, lower beam/model cost, or move inference to CUDA.")

    if final["queueDelayP95Ms"] >= thresholds["queueDelayP95Ms"]["final"]["warn"] and realtime["busy"]:
        signals.append("Final queue delay is elevated while realtime worker is active")
        return _diagnosis("gpu_contention", signals, "Keep the GPU gate enabled or disable realtime transcription.")

    if _queue_high(final, realtime, thresholds) and not _high_inference(final, realtime):
        signals.append("Queue delay is high but inference duration is not")
        return _diagnosis("queue_architecture", signals, "Reduce job creation rate, sessions, or queue contention.")

    if max_recording_seconds >= 20.0 and final["totalLatencyP95Ms"] >= thresholds["totalLatencyP95Ms"]["final"]["warn"]:
        signals.append("Long final audio segments correlate with final latency")
        return _diagnosis("audio_duration", signals, "Shorten utterance segmentation or lower final max duration.")

    if _high_inference(final, realtime) and not _resource_pressure(cpu_percent, system_memory_percent, cuda_pressure, thresholds):
        signals.append("Inference duration is high without clear resource pressure")
        return _diagnosis("model_config", signals, "Benchmark model, beam size, compute type, and batching.")

    if max_busy >= thresholds["workerBusyRatio"]["critical"] or rejected >= thresholds["rejectedJobs"]["critical"]:
        signals.append("Workers are saturated or jobs are being rejected")
        return _diagnosis("session_pressure", signals, "Lower concurrent sessions/speakers or scale inference capacity.")

    if signals:
        return _diagnosis("unknown", signals, "Collect a longer diagnostics export for comparison.")
    return _diagnosis("unknown", ["No clear bottleneck signal"], "Run a representative session and export diagnostics.")


def _diagnosis(kind, signals, recommendation):
    return {
        "likelyBottleneck": kind,
        "signals": signals,
        "recommendedAction": recommendation,
    }


def _number(value, default=0.0):
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _max_number(*values):
    present = [_number(value, None) for value in values]
    present = [value for value in present if value is not None]
    return max(present) if present else 0.0


def _gte(value, threshold):
    return value is not None and float(value) >= float(threshold)


def _lane_metrics(scheduler, lane):
    workers = scheduler.get("workers") or {}
    worker = workers.get(lane) or {}
    if lane == "final":
        worker = workers.get("main") or worker
    return {
        "queueDelayP95Ms": _number((worker.get("queueDelay") or {}).get("p95Ms")),
        "inferenceDurationP95Ms": _number((worker.get("inferenceDuration") or {}).get("p95Ms")),
        "totalLatencyP95Ms": _number((worker.get("totalLatency") or {}).get("p95Ms")),
        "busyRatio": _number(worker.get("busyRatio")),
        "busy": _number(worker.get("busyRatio")) > 0.05,
    }


def _high_inference(final, realtime):
    return (
        final["inferenceDurationP95Ms"] >= DIAGNOSTIC_THRESHOLDS["inferenceDurationP95Ms"]["final"]["warn"]
        or realtime["inferenceDurationP95Ms"] >= DIAGNOSTIC_THRESHOLDS["inferenceDurationP95Ms"]["realtime"]["warn"]
    )


def _queue_high(final, realtime, thresholds):
    return (
        final["queueDelayP95Ms"] >= thresholds["queueDelayP95Ms"]["final"]["warn"]
        or realtime["queueDelayP95Ms"] >= thresholds["queueDelayP95Ms"]["realtime"]["warn"]
    )


def _resource_pressure(cpu_percent, system_memory_percent, cuda_pressure, thresholds):
    return (
        _gte(cpu_percent, thresholds["cpuPercent"]["warn"])
        or _gte(system_memory_percent, thresholds["systemMemoryPercent"]["warn"])
        or _gte(cuda_pressure, thresholds["cudaMemoryPressure"]["warn"])
    )


def _max_worker_busy(scheduler):
    workers = scheduler.get("workers") or {}
    if not workers:
        return 0.0
    return max(_number((worker or {}).get("busyRatio")) for worker in workers.values())


def _rejected_jobs(scheduler):
    queues = scheduler.get("queues") or {}
    total = 0
    for queue in queues.values():
        total += int(_number((queue or {}).get("rejectedJobs")))
    return total


def _max_recording_seconds(sessions):
    if not sessions:
        return 0.0
    return max(_number((session or {}).get("recordingSeconds")) for session in sessions.values())
