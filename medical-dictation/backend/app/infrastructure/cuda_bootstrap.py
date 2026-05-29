"""Windows CUDA DLL path bootstrap for Faster-Whisper runtime."""

import glob
import logging
import os
import sys

logger = logging.getLogger(__name__)


def configure_windows_cuda_paths() -> None:
    """Add bundled NVIDIA DLL directories to PATH on Windows, falling back to CPU."""
    if sys.platform != "win32":
        return

    try:
        site_packages_dirs = [p for p in sys.path if "site-packages" in p.lower()]
        if not site_packages_dirs:
            raise ImportError("site-packages not found in sys.path")

        site_packages = site_packages_dirs[0]
        nvidia_base = os.path.join(site_packages, "nvidia")
        if not os.path.exists(nvidia_base):
            raise ImportError(f"nvidia directory not found at {nvidia_base}")

        cuda_paths: list[str] = []
        for subdir in ["cublas", "cudnn"]:
            base_dir = os.path.join(nvidia_base, subdir)
            if not os.path.exists(base_dir):
                continue

            for root, _dirs, files in os.walk(base_dir):
                dll_files = [f for f in files if f.endswith(".dll")]
                if dll_files and root not in cuda_paths:
                    cuda_paths.append(root)

        if not cuda_paths:
            raise ImportError("No CUDA DLL directories found")

        path_addition = os.pathsep.join(cuda_paths)
        os.environ["PATH"] = path_addition + os.pathsep + os.environ.get("PATH", "")
        logger.info("Added %s CUDA path(s) to system PATH", len(cuda_paths))
        for path in cuda_paths:
            dll_count = len(glob.glob(os.path.join(path, "*.dll")))
            logger.debug(
                "CUDA path: %s/bin (%s DLLs)",
                os.path.basename(os.path.dirname(path)),
                dll_count,
            )

    except Exception as exc:
        logger.warning("CUDA setup failed, falling back to CPU mode: %s", exc)
        os.environ["DEVICE"] = "cpu"
        os.environ["COMPUTE_TYPE"] = "int8"
