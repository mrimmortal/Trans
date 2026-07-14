import argparse

from .settings import BASE_TUNING_DEFAULTS, TUNING_PROFILES, ServerSettings

try:
    from protocol import normalize_engine_name, parse_json_object
except ImportError:
    from ...protocol import normalize_engine_name, parse_json_object


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="CoreSTT FastAPI browser streaming server")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8010)
    parser.add_argument(
        "--profile",
        "--tuning-profile",
        dest="tuning_profile",
        choices=sorted(TUNING_PROFILES),
        default="custom",
        help="Named tuning profile. Parakeet profiles tune cadence/batching/VAD timing, not Whisper beam search.",
    )
    parser.add_argument("--model", default="small.en")
    parser.add_argument("--realtime-model", default="tiny.en")
    parser.add_argument("--language", default="en")
    parser.add_argument("--engine", "--transcription-engine", dest="transcription_engine", default="faster_whisper")
    parser.add_argument("--realtime-engine", "--realtime-transcription-engine", dest="realtime_transcription_engine")
    parser.add_argument("--engine-options", dest="transcription_engine_options")
    parser.add_argument("--realtime-engine-options", dest="realtime_transcription_engine_options")
    parser.add_argument("--domain-profiles-path", default="domain_profiles.json")
    parser.add_argument("--default-domain")
    parser.add_argument("--download-root")
    parser.add_argument("--compute-type", default="default")
    parser.add_argument("--cpu-threads", type=int)
    parser.add_argument("--num-workers", type=int, default=1)
    parser.add_argument(
        "--single-gpu-inference-gate",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--gpu-device-index", type=int, default=0)
    parser.add_argument("--beam-size", type=int)
    parser.add_argument("--beam-size-realtime", type=int)
    parser.add_argument("--batch-size", type=int)
    parser.add_argument("--realtime-batch-size", type=int)
    parser.add_argument("--no-vad-filter", action="store_true")
    parser.add_argument(
        "--vad-filter-final",
        action=argparse.BooleanOptionalAction,
        default=None,
    )
    parser.add_argument(
        "--vad-filter-realtime",
        action=argparse.BooleanOptionalAction,
        default=None,
    )
    parser.add_argument("--normalize-audio", action="store_true")
    parser.add_argument("--realtime-callback", choices=("update", "stabilized"), default="update")
    parser.add_argument("--min-length-of-recording", type=float)
    parser.add_argument("--min-gap-between-recordings", type=float, default=0.0)
    parser.add_argument("--post-speech-silence-duration", type=float)
    parser.add_argument("--silero-sensitivity", type=float, default=0.05)
    parser.add_argument("--webrtc-sensitivity", type=int, default=3)
    parser.add_argument("--realtime-processing-pause", type=float)
    parser.add_argument("--realtime-use-syllable-boundaries", action="store_true")
    parser.add_argument("--realtime-boundary-detector-sensitivity", type=float, default=0.6)
    parser.add_argument("--realtime-boundary-followup-delays", default="0.05,0.2")
    parser.add_argument("--early-transcription-on-silence", type=float)
    parser.add_argument("--initial-prompt")
    parser.add_argument("--initial-prompt-realtime")
    parser.add_argument("--wakeword-backend", default="")
    parser.add_argument("--openwakeword-model-paths")
    parser.add_argument("--openwakeword-inference-framework", default="onnx")
    parser.add_argument("--wake-words", default="")
    parser.add_argument("--wake-words-sensitivity", type=float, default=0.5)
    parser.add_argument("--wake-word-activation-delay", type=float, default=0.0)
    parser.add_argument("--wake-word-timeout", type=float, default=5.0)
    parser.add_argument("--wake-word-buffer-duration", type=float, default=0.1)
    parser.add_argument("--wake-word-followup-window", type=float, default=0.0)
    parser.add_argument("--use-main-model-for-realtime", action="store_true")
    parser.add_argument("--use-recorder-backed-realtime-session", action="store_true")
    parser.add_argument("--audio-queue-size", type=int, default=128)
    parser.add_argument("--max-audio-packet-bytes", type=int, default=512 * 1024)
    parser.add_argument("--max-sessions", type=int, default=4)
    parser.add_argument("--max-active-speakers", type=int, default=4)
    parser.add_argument("--max-audio-queue-seconds-per-session", type=float, default=30.0)
    parser.add_argument("--pre-recording-buffer-duration", type=float, default=0.75)
    parser.add_argument("--max-realtime-queue-age-ms", type=int, default=1500)
    parser.add_argument("--max-final-queue-depth-per-session", type=int, default=8)
    parser.add_argument("--max-global-inference-queue-depth", type=int, default=64)
    parser.add_argument("--realtime-degradation-threshold-ms", type=int, default=1500)
    parser.add_argument("--realtime-min-audio-seconds", type=float, default=0.8)
    parser.add_argument("--realtime-max-audio-seconds", type=float, default=5.0)
    parser.add_argument("--vad-energy-threshold", type=float, default=250.0)
    parser.add_argument("--no-model-warmup", action="store_true")
    parser.add_argument("--log-level", default="INFO")
    return parser.parse_args(argv)


def _tuning_defaults(profile):
    defaults = dict(BASE_TUNING_DEFAULTS)
    defaults.update(TUNING_PROFILES[profile]["settings"])
    return defaults


def _value_or_default(args, defaults, name):
    value = getattr(args, name)
    return defaults[name] if value is None else value


def parse_float_tuple(value, flag_name):
    if value is None:
        return ()
    if isinstance(value, (tuple, list)):
        return tuple(float(item) for item in value)

    parts = [part.strip() for part in str(value).split(",")]
    try:
        return tuple(float(part) for part in parts if part)
    except ValueError as exc:
        raise SystemExit(f"{flag_name} must be a comma-separated list of numbers") from exc


def settings_from_args(args):
    if args.model != "small.en":
        raise SystemExit("--model is fixed to small.en for final transcription")
    if args.realtime_model != "tiny.en":
        raise SystemExit("--realtime-model is fixed to tiny.en for realtime transcription")
    if args.use_main_model_for_realtime:
        raise SystemExit(
            "--use-main-model-for-realtime is incompatible with the fixed final/realtime model roles"
        )

    tuning_profile = args.tuning_profile
    defaults = _tuning_defaults(tuning_profile)
    vad_filter_final = True if args.vad_filter_final is None else args.vad_filter_final
    vad_filter_realtime = (
        False if args.vad_filter_realtime is None else args.vad_filter_realtime
    )
    if args.no_vad_filter:
        vad_filter_final = False
        vad_filter_realtime = False
    return ServerSettings(
        host=args.host,
        port=args.port,
        tuning_profile=tuning_profile,
        tuning_description=TUNING_PROFILES[tuning_profile]["description"],
        model=args.model,
        realtime_model=args.realtime_model,
        language=args.language,
        transcription_engine=normalize_engine_name(args.transcription_engine),
        realtime_transcription_engine=normalize_engine_name(args.realtime_transcription_engine),
        transcription_engine_options=parse_json_object(args.transcription_engine_options, "--engine-options"),
        realtime_transcription_engine_options=parse_json_object(
            args.realtime_transcription_engine_options,
            "--realtime-engine-options",
        ),
        domain_profiles_path=args.domain_profiles_path,
        default_domain=args.default_domain,
        download_root=args.download_root,
        compute_type=args.compute_type,
        cpu_threads=args.cpu_threads,
        num_workers=args.num_workers,
        single_gpu_inference_gate=args.single_gpu_inference_gate,
        device=args.device,
        gpu_device_index=args.gpu_device_index,
        beam_size=_value_or_default(args, defaults, "beam_size"),
        beam_size_realtime=_value_or_default(args, defaults, "beam_size_realtime"),
        batch_size=_value_or_default(args, defaults, "batch_size"),
        realtime_batch_size=_value_or_default(args, defaults, "realtime_batch_size"),
        vad_filter_final=vad_filter_final,
        vad_filter_realtime=vad_filter_realtime,
        normalize_audio=args.normalize_audio,
        realtime_callback=args.realtime_callback,
        min_length_of_recording=_value_or_default(args, defaults, "min_length_of_recording"),
        min_gap_between_recordings=args.min_gap_between_recordings,
        post_speech_silence_duration=_value_or_default(args, defaults, "post_speech_silence_duration"),
        silero_sensitivity=args.silero_sensitivity,
        webrtc_sensitivity=args.webrtc_sensitivity,
        realtime_processing_pause=_value_or_default(args, defaults, "realtime_processing_pause"),
        realtime_transcription_use_syllable_boundaries=args.realtime_use_syllable_boundaries,
        realtime_boundary_detector_sensitivity=args.realtime_boundary_detector_sensitivity,
        realtime_boundary_followup_delays=parse_float_tuple(
            args.realtime_boundary_followup_delays,
            "--realtime-boundary-followup-delays",
        ),
        early_transcription_on_silence=_value_or_default(args, defaults, "early_transcription_on_silence"),
        initial_prompt=args.initial_prompt,
        initial_prompt_realtime=args.initial_prompt_realtime,
        wakeword_backend=(
            args.wakeword_backend
            or ("pvporcupine" if args.wake_words else "")
        ),
        openwakeword_model_paths=args.openwakeword_model_paths,
        openwakeword_inference_framework=args.openwakeword_inference_framework,
        wake_words=args.wake_words,
        wake_words_sensitivity=args.wake_words_sensitivity,
        wake_word_activation_delay=args.wake_word_activation_delay,
        wake_word_timeout=args.wake_word_timeout,
        wake_word_buffer_duration=args.wake_word_buffer_duration,
        wake_word_followup_window=args.wake_word_followup_window,
        use_main_model_for_realtime=args.use_main_model_for_realtime,
        use_recorder_backed_realtime_session=args.use_recorder_backed_realtime_session,
        audio_queue_size=args.audio_queue_size,
        max_audio_packet_bytes=args.max_audio_packet_bytes,
        max_sessions=args.max_sessions,
        max_active_speakers=args.max_active_speakers,
        max_audio_queue_seconds_per_session=args.max_audio_queue_seconds_per_session,
        pre_recording_buffer_duration=args.pre_recording_buffer_duration,
        max_realtime_queue_age_ms=args.max_realtime_queue_age_ms,
        max_final_queue_depth_per_session=args.max_final_queue_depth_per_session,
        max_global_inference_queue_depth=args.max_global_inference_queue_depth,
        realtime_degradation_threshold_ms=args.realtime_degradation_threshold_ms,
        realtime_min_audio_seconds=args.realtime_min_audio_seconds,
        realtime_max_audio_seconds=args.realtime_max_audio_seconds,
        vad_energy_threshold=args.vad_energy_threshold,
        model_warmup=not args.no_model_warmup,
        log_level=args.log_level.upper(),
    )
