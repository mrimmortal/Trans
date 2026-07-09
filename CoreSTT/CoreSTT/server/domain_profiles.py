"""
Loads domain transcription profiles for prompt and hotword biasing.
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Union


Hotwords = Union[str, List[str]]
GLOBAL_PROFILE_NAME = "global"
PROMPT_SEPARATOR = "\n\n"


class DomainProfileError(ValueError):
    """
    Reports invalid domain profile configuration.
    """


@dataclass(frozen=True)
class DomainProfile:
    initial_prompt: Optional[str] = None
    initial_prompt_realtime: Optional[str] = None
    hotwords: Hotwords = None

    def to_dict(self):
        return {
            "initial_prompt": self.initial_prompt,
            "initial_prompt_realtime": self.initial_prompt_realtime,
            "hotwords": self.hotwords,
        }


@dataclass(frozen=True)
class EffectiveDomainProfile(DomainProfile):
    realtime_hotwords: Hotwords = None


class DomainProfiles:
    def __init__(self, profiles: Dict[str, DomainProfile]):
        self._profiles = dict(profiles)

    def names(self):
        return sorted(self._profiles)

    def get(self, name):
        if name is None:
            return None
        return self._profiles.get(str(name))

    def to_dict(self):
        return {
            name: self._profiles[name].to_dict()
            for name in self.names()
        }

    def upsert(self, name, raw_profile):
        profile_name = _profile_name(name)
        if raw_profile is None:
            raw_profile = {}
        if not isinstance(raw_profile, dict):
            raise DomainProfileError(f"domain profile '{profile_name}' must be a JSON object")
        profile = _parse_profile(profile_name, raw_profile)
        self._profiles[profile_name] = profile
        return profile

    def delete(self, name):
        profile_name = _profile_name(name)
        return self._profiles.pop(profile_name, None) is not None


def compose_domain_profile(profiles: DomainProfiles, domain_name=None):
    """
    Builds the effective profile from the reserved global profile and an
    optional selected domain profile.
    """
    global_profile = profiles.get(GLOBAL_PROFILE_NAME)
    domain_profile = profiles.get(domain_name)
    if global_profile is None:
        return domain_profile
    if domain_profile is None:
        return global_profile
    return EffectiveDomainProfile(
        initial_prompt=_compose_prompt(
            global_profile.initial_prompt,
            domain_profile.initial_prompt,
        ),
        initial_prompt_realtime=domain_profile.initial_prompt_realtime,
        hotwords=_compose_hotwords(
            global_profile.hotwords,
            domain_profile.hotwords,
        ),
        realtime_hotwords=domain_profile.hotwords,
    )


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
        name = _profile_name(name)
        if raw_profile is None:
            raw_profile = {}
        if not isinstance(raw_profile, dict):
            raise DomainProfileError(f"domain profile '{name}' must be a JSON object")
        profiles[name] = _parse_profile(name, raw_profile)

    return DomainProfiles(profiles)


def save_domain_profiles(path, profiles: DomainProfiles):
    """
    Persists domain profiles to JSON.
    """
    if not path:
        raise DomainProfileError("domain profiles path is not configured")

    profile_path = Path(path)
    profile_path.parent.mkdir(parents=True, exist_ok=True)
    data = {"profiles": profiles.to_dict()}
    profile_path.write_text(
        json.dumps(data, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _profile_name(name):
    if not isinstance(name, str) or not name.strip():
        raise DomainProfileError("domain profile names must be non-empty strings")
    return name.strip()


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


def _compose_prompt(*prompts):
    parts = [prompt.strip() for prompt in prompts if isinstance(prompt, str) and prompt.strip()]
    return PROMPT_SEPARATOR.join(parts) if parts else None


def _compose_hotwords(*hotword_values):
    merged = []
    seen = set()
    for value in hotword_values:
        for word in _hotword_items(value):
            key = word.casefold()
            if key not in seen:
                seen.add(key)
                merged.append(word)
    return merged or None


def _hotword_items(value):
    if value is None:
        return []
    if isinstance(value, str):
        stripped = value.strip()
        return [stripped] if stripped else []
    return [item.strip() for item in value if item.strip()]
