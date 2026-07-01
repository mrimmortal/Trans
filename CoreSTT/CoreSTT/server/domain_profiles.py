"""
Loads domain transcription profiles for prompt and hotword biasing.
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Union


Hotwords = Union[str, List[str]]


class DomainProfileError(ValueError):
    """
    Reports invalid domain profile configuration.
    """


@dataclass(frozen=True)
class DomainProfile:
    initial_prompt: Optional[str] = None
    initial_prompt_realtime: Optional[str] = None
    hotwords: Hotwords = None


class DomainProfiles:
    def __init__(self, profiles: Dict[str, DomainProfile]):
        self._profiles = dict(profiles)

    def names(self):
        return sorted(self._profiles)

    def get(self, name):
        if name is None:
            return None
        return self._profiles.get(str(name))


def load_domain_profiles(path):
    """
    Loads domain profiles from JSON. Missing files mean no profiles configured.
    """
    if not path:
        return DomainProfiles({})

    profile_path = Path(path)
    if not profile_path.exists():
        return DomainProfiles({})

    try:
        data = json.loads(profile_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise DomainProfileError(f"domain profiles JSON is invalid: {exc.msg}") from exc

    if not isinstance(data, dict) or not isinstance(data.get("profiles"), dict):
        raise DomainProfileError("domain profiles file must contain a JSON object field 'profiles'")

    profiles = {}
    for name, raw_profile in data["profiles"].items():
        if not isinstance(name, str) or not name.strip():
            raise DomainProfileError("domain profile names must be non-empty strings")
        if raw_profile is None:
            raw_profile = {}
        if not isinstance(raw_profile, dict):
            raise DomainProfileError(f"domain profile '{name}' must be a JSON object")
        profiles[name] = _parse_profile(name, raw_profile)

    return DomainProfiles(profiles)


def _parse_profile(name, raw_profile):
    initial_prompt = _optional_string(raw_profile, "initial_prompt", name)
    initial_prompt_realtime = _optional_string(raw_profile, "initial_prompt_realtime", name)
    hotwords = _hotwords(raw_profile.get("hotwords"), name)
    return DomainProfile(
        initial_prompt=initial_prompt,
        initial_prompt_realtime=initial_prompt_realtime,
        hotwords=hotwords,
    )


def _optional_string(raw_profile, field, name):
    value = raw_profile.get(field)
    if value is not None and not isinstance(value, str):
        raise DomainProfileError(f"domain profile '{name}' field '{field}' must be a string or null")
    return value


def _hotwords(value, name):
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return value
    raise DomainProfileError(
        f"domain profile '{name}' field 'hotwords' must be a string or list of strings"
    )
