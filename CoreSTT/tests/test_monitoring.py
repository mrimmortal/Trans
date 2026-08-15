import unittest
from types import SimpleNamespace

from CoreSTT.server.monitoring import ResourceMonitor, diagnose_bottleneck
from CoreSTT.server.settings import ServerSettings


class FakeProcess:
    def cpu_percent(self, interval=None):
        return 12.5

    def memory_info(self):
        return SimpleNamespace(rss=256 * 1024 * 1024)

    def num_threads(self):
        return 8


class FakePsutil:
    def Process(self):
        return FakeProcess()

    def cpu_percent(self, interval=None):
        return 42.0

    def virtual_memory(self):
        return SimpleNamespace(percent=66.0, available=4096 * 1024 * 1024)


class FakeCuda:
    def is_available(self):
        return True

    def get_device_name(self, _device):
        return "Fake GPU"

    def memory_allocated(self, _device):
        return 1024 * 1024 * 1024

    def memory_reserved(self, _device):
        return 1024 * 1024 * 1024

    def max_memory_allocated(self, _device):
        return 3072 * 1024 * 1024

    def mem_get_info(self, _device):
        return (6144 * 1024 * 1024, 8192 * 1024 * 1024)

    def utilization(self, _device):
        return 72


class MonitoringTest(unittest.TestCase):
    def test_resource_monitor_collects_process_system_and_cuda_metrics(self):
        monitor = ResourceMonitor(
            ServerSettings(),
            psutil_module=FakePsutil(),
            torch_module=SimpleNamespace(cuda=FakeCuda()),
        )

        snapshot = monitor.snapshot()

        self.assertTrue(snapshot["process"]["available"])
        self.assertEqual(snapshot["process"]["cpuPercent"], 12.5)
        self.assertEqual(snapshot["process"]["rssMb"], 256.0)
        self.assertEqual(snapshot["process"]["threadCount"], 8)
        self.assertTrue(snapshot["system"]["available"])
        self.assertEqual(snapshot["system"]["cpuPercent"], 42.0)
        self.assertEqual(snapshot["system"]["memoryPercent"], 66.0)
        self.assertTrue(snapshot["cuda"]["available"])
        self.assertEqual(snapshot["cuda"]["deviceName"], "Fake GPU")
        self.assertEqual(snapshot["cuda"]["allocatedMb"], 1024.0)
        self.assertEqual(snapshot["cuda"]["reservedMb"], 1024.0)
        self.assertEqual(snapshot["cuda"]["freeMb"], 6144.0)
        self.assertEqual(snapshot["cuda"]["totalMb"], 8192.0)
        self.assertEqual(snapshot["cuda"]["memoryPressure"], 25.0)
        self.assertEqual(snapshot["cuda"]["utilizationPercent"], 72.0)

    def test_resource_monitor_falls_back_when_dependencies_are_unavailable(self):
        monitor = ResourceMonitor(
            ServerSettings(resource_metrics_include_cuda=False),
            psutil_module=None,
            torch_module=None,
        )
        monitor._psutil_loaded = True
        monitor._torch_loaded = True

        snapshot = monitor.snapshot()

        self.assertFalse(snapshot["process"]["available"])
        self.assertEqual(snapshot["process"]["reason"], "psutil_unavailable")
        self.assertFalse(snapshot["system"]["available"])
        self.assertFalse(snapshot["cuda"]["available"])
        self.assertEqual(snapshot["cuda"]["reason"], "cuda_monitoring_disabled")

    def test_diagnose_bottleneck_detects_gpu_memory(self):
        metrics = {
            "resources": {
                "process": {"cpuPercent": 10},
                "system": {"cpuPercent": 10, "memoryPercent": 40},
                "cuda": {"available": True, "memoryPressure": 95, "freeMb": 6000},
            },
            "scheduler": {"workers": {}, "queues": {}},
            "sessions": {},
        }

        diagnosis = diagnose_bottleneck(metrics)

        self.assertEqual(diagnosis["likelyBottleneck"], "gpu_memory")

    def test_diagnose_bottleneck_detects_queue_architecture(self):
        metrics = {
            "resources": {
                "process": {"cpuPercent": 10},
                "system": {"cpuPercent": 10, "memoryPercent": 40},
                "cuda": {"available": True, "memoryPressure": 20, "freeMb": 6000},
            },
            "scheduler": {
                "workers": {
                    "main": {
                        "queueDelay": {"p95Ms": 2500},
                        "inferenceDuration": {"p95Ms": 100},
                        "totalLatency": {"p95Ms": 2600},
                        "busyRatio": 0.1,
                    }
                },
                "queues": {},
            },
            "sessions": {},
        }

        diagnosis = diagnose_bottleneck(metrics)

        self.assertEqual(diagnosis["likelyBottleneck"], "queue_architecture")

    def test_diagnose_bottleneck_ignores_unavailable_cuda_memory(self):
        metrics = {
            "resources": {
                "process": {"available": False, "reason": "psutil_unavailable"},
                "system": {"available": False, "reason": "psutil_unavailable"},
                "cuda": {"available": False, "reason": "cuda_unavailable"},
            },
            "scheduler": {"workers": {}, "queues": {}},
            "sessions": {},
        }

        diagnosis = diagnose_bottleneck(metrics)

        self.assertEqual(diagnosis["likelyBottleneck"], "unknown")
        self.assertNotIn("CUDA", " ".join(diagnosis["signals"]))


if __name__ == "__main__":
    unittest.main()
