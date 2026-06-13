import datetime
import threading
import time

from .settings import ServerSettings


class SegmentState:
    def __init__(self):
        self._lock = threading.Lock()
        self._segment_id = 1
        self._has_realtime = False

    def realtime(self):
        with self._lock:
            self._has_realtime = True
            return self._segment_id

    def final(self):
        with self._lock:
            segment_id = self._segment_id
            self._segment_id += 1
            self._has_realtime = False
            return segment_id

    def current(self):
        with self._lock:
            return self._segment_id

    def reset(self):
        with self._lock:
            self._segment_id += 1
            self._has_realtime = False
            return self._segment_id


def timestamp_iso(timestamp):
    return (
        datetime.datetime.fromtimestamp(timestamp, datetime.timezone.utc)
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z")
    )


def segment_text_fields(segment):
    fields = {}
    for key in (
        "durationSeconds",
        "endReason",
        "preRecordingBuffer",
        "recordingEndedAt",
        "recordingEndedAtIso",
        "recordingStartedAt",
        "recordingStartedAtIso",
        "wakeWord",
    ):
        if key in segment:
            fields[key] = segment[key]
    return fields


class SegmentTimelineTracker:
    def __init__(self, settings: ServerSettings):
        self.settings = settings
        self._lock = threading.Lock()
        self._segments = {}
        self._current_segment_id = None
        self._wakeword_wait_started_at = None
        self._pending_wakeword_detected_at = None
        self._last_wakeword_timeout_at = None

    def reset(self):
        with self._lock:
            self._segments.clear()
            self._current_segment_id = None
            self._wakeword_wait_started_at = None
            self._pending_wakeword_detected_at = None
            self._last_wakeword_timeout_at = None

    def mark_wakeword_wait_started(self, timestamp=None):
        timestamp = time.time() if timestamp is None else float(timestamp)
        with self._lock:
            self._wakeword_wait_started_at = timestamp
            self._pending_wakeword_detected_at = None
            return {
                "wakeWord": self._wakeword_payload(
                    wait_started_at=timestamp,
                    state="waiting_for_wake_word",
                )
            }

    def mark_wakeword_wait_ended(self, timestamp=None):
        timestamp = time.time() if timestamp is None else float(timestamp)
        with self._lock:
            wait_started_at = self._wakeword_wait_started_at
            self._wakeword_wait_started_at = None
            return {
                "wakeWord": self._wakeword_payload(
                    wait_started_at=wait_started_at,
                    wait_ended_at=timestamp,
                    state="wake_word_wait_ended",
                )
            }

    def mark_wakeword_detected(self, timestamp=None):
        timestamp = time.time() if timestamp is None else float(timestamp)
        with self._lock:
            self._pending_wakeword_detected_at = timestamp
            return {
                "wakeWord": self._wakeword_payload(
                    wait_started_at=self._wakeword_wait_started_at,
                    detected_at=timestamp,
                    state="wake_word_detected_waiting_for_voice",
                )
            }

    def mark_wakeword_timeout(self, timestamp=None):
        timestamp = time.time() if timestamp is None else float(timestamp)
        with self._lock:
            self._last_wakeword_timeout_at = timestamp
            self._pending_wakeword_detected_at = None
            return {
                "wakeWord": self._wakeword_payload(
                    wait_started_at=self._wakeword_wait_started_at,
                    timeout_at=timestamp,
                    state="wake_word_timeout",
                )
            }

    def mark_recording_started(self, segment_id, actual_preroll_seconds=None, timestamp=None):
        timestamp = time.time() if timestamp is None else float(timestamp)
        configured_preroll = max(0.0, float(self.settings.pre_recording_buffer_duration))
        included_preroll = (
            max(0.0, float(actual_preroll_seconds))
            if actual_preroll_seconds is not None
            else configured_preroll
        )
        prebuffer = {
            "configuredSeconds": configured_preroll,
            "includedSeconds": included_preroll,
            "startTimestamp": timestamp - included_preroll,
            "startTimestampIso": timestamp_iso(timestamp - included_preroll),
            "endTimestamp": timestamp,
            "endTimestampIso": timestamp_iso(timestamp),
            "exact": actual_preroll_seconds is not None,
        }
        with self._lock:
            segment = self._segment_locked(segment_id)
            segment.update({
                "segmentId": segment_id,
                "recordingStartedAt": timestamp,
                "recordingStartedAtIso": timestamp_iso(timestamp),
                "recordingEndedAt": None,
                "recordingEndedAtIso": None,
                "durationSeconds": None,
                "endReason": None,
                "preRecordingBuffer": prebuffer,
            })
            if self._pending_wakeword_detected_at is not None:
                segment["wakeWord"] = self._wakeword_payload(
                    wait_started_at=self._wakeword_wait_started_at,
                    detected_at=self._pending_wakeword_detected_at,
                    state="recording",
                )
            self._current_segment_id = segment_id
            return self._copy_segment_locked(segment_id)

    def mark_recording_ended(
        self,
        reason,
        segment_id=None,
        actual_duration_seconds=None,
        timestamp=None,
    ):
        timestamp = time.time() if timestamp is None else float(timestamp)
        with self._lock:
            if segment_id is None:
                segment_id = self._current_segment_id
            if segment_id is None:
                return None
            segment = self._segment_locked(segment_id)
            started_at = segment.get("recordingStartedAt")
            duration = actual_duration_seconds
            if duration is None and started_at is not None:
                duration = max(0.0, timestamp - float(started_at))
            segment.update({
                "recordingEndedAt": timestamp,
                "recordingEndedAtIso": timestamp_iso(timestamp),
                "durationSeconds": duration,
                "endReason": reason,
            })
            self._current_segment_id = None
            self._pending_wakeword_detected_at = None
            return self._copy_segment_locked(segment_id)

    def snapshot(self, segment_id=None):
        with self._lock:
            if segment_id is None:
                segment_id = self._current_segment_id
            if segment_id is None:
                return None
            return self._copy_segment_locked(segment_id)

    def _segment_locked(self, segment_id):
        return self._segments.setdefault(segment_id, {"segmentId": segment_id})

    def _copy_segment_locked(self, segment_id):
        segment = self._segments.get(segment_id)
        if segment is None:
            return None
        payload = {}
        for key, value in segment.items():
            if value is None:
                continue
            if isinstance(value, dict):
                payload[key] = dict(value)
            else:
                payload[key] = value
        return payload

    def _wakeword_payload(
        self,
        *,
        wait_started_at=None,
        wait_ended_at=None,
        detected_at=None,
        timeout_at=None,
        state=None,
    ):
        payload = {
            "enabled": self.settings.wake_word_enabled(),
            "backend": self.settings.wakeword_backend,
            "wakeWords": self.settings.wake_words,
            "state": state,
        }
        timestamps = {
            "waitStartedAt": wait_started_at,
            "waitEndedAt": wait_ended_at,
            "detectedAt": detected_at,
            "timeoutAt": timeout_at,
        }
        for key, value in timestamps.items():
            if value is None:
                continue
            payload[key] = value
            payload[f"{key}Iso"] = timestamp_iso(value)
        return payload
