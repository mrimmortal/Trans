"""
Tests device selection without requiring a physical GPU.
"""

import logging
import os
import unittest
from unittest.mock import patch

from CoreSTT.core.device import resolve_stt_device
from CoreSTT.transcription_engines._model_utils import torch_dtype_from_compute_type


class FakeCuda:
    def __init__(self, available):
        self.available = available

    def is_available(self):
        return self.available

    def get_device_name(self, index):
        return "Test GPU"


class FakeTorch:
    float16 = "float16"
    float32 = "float32"
    bfloat16 = "bfloat16"

    def __init__(self, cuda_available):
        self.cuda = FakeCuda(cuda_available)


class DeviceSelectionTests(unittest.TestCase):
    def setUp(self):
        self.logger = logging.getLogger("corestt.tests.device")

    @patch.dict(os.environ, {}, clear=True)
    def test_auto_selects_cuda_when_available(self):
        with self.assertLogs(self.logger, level="INFO") as logs:
            selected = resolve_stt_device("auto", FakeTorch(True), self.logger)
        self.assertEqual(selected, "cuda")
        output = " ".join(logs.output)
        self.assertIn("AudioToTextRecorder device setting", output)
        self.assertIn("STT processing will run on: CUDA (GPU 0: Test GPU)", output)

    @patch.dict(os.environ, {}, clear=True)
    def test_cuda_request_falls_back_to_cpu(self):
        with self.assertLogs(self.logger, level="WARNING") as logs:
            selected = resolve_stt_device("cuda", FakeTorch(False), self.logger)
        self.assertEqual(selected, "cpu")
        self.assertIn("falling back to CPU", " ".join(logs.output))

    @patch.dict(os.environ, {"STT_DEVICE": "cpu"}, clear=True)
    def test_environment_overrides_constructor_value(self):
        with self.assertLogs(self.logger, level="INFO") as logs:
            selected = resolve_stt_device("cuda", FakeTorch(True), self.logger)
        self.assertEqual(selected, "cpu")
        output = " ".join(logs.output)
        self.assertIn("STT_DEVICE environment variable", output)
        self.assertIn("STT processing will run on: CPU", output)

    def test_cpu_dtype_is_always_float32(self):
        torch_module = FakeTorch(False)
        dtype = torch_dtype_from_compute_type(
            torch_module,
            "float16",
            device="cpu",
        )
        self.assertEqual(dtype, torch_module.float32)


if __name__ == "__main__":
    unittest.main()
