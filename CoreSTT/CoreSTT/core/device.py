"""
Selects and reports the STT model execution device.
"""

import os


VALID_STT_DEVICES = {"auto", "cuda", "cpu"}


def resolve_stt_device(configured_device, torch_module, logger):
    """
    Resolves STT_DEVICE/configuration to an available cpu or cuda device.
    """

    environment_device = os.environ.get("STT_DEVICE")
    if environment_device is not None:
        requested = environment_device
        request_source = "STT_DEVICE environment variable"
    else:
        requested = configured_device or "auto"
        request_source = "AudioToTextRecorder device setting"

    requested = str(requested).strip().lower()
    logger.info("STT device request: %s (source: %s)", requested, request_source)

    if requested not in VALID_STT_DEVICES:
        logger.warning(
            "Invalid STT device '%s'; expected auto, cuda, or cpu. Using auto.",
            requested,
        )
        requested = "auto"

    cuda_available = bool(torch_module.cuda.is_available())
    logger.info("PyTorch CUDA available: %s", cuda_available)

    if requested == "cuda" and not cuda_available:
        logger.warning("CUDA was requested but is unavailable; falling back to CPU.")

    selected = "cuda" if cuda_available and requested in ("auto", "cuda") else "cpu"

    if selected == "cuda":
        try:
            logger.info(
                "STT processing will run on: CUDA (GPU 0: %s)",
                torch_module.cuda.get_device_name(0),
            )
        except Exception as exc:
            logger.warning("CUDA is available, but the GPU name could not be read: %s", exc)
            logger.info("STT processing will run on: CUDA (GPU 0)")
    else:
        logger.info("STT processing will run on: CPU")

    return selected
