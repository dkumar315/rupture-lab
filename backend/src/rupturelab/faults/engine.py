import random
from threading import Lock

from rupturelab.faults.models import FaultProfile


class FaultEngine:
    def __init__(self, seed: int | None = None) -> None:
        self._lock = Lock()
        self._profile = FaultProfile()
        self._random = random.Random(seed)

    def current(self) -> FaultProfile:
        with self._lock:
            return self._profile.model_copy(deep=True)

    def configure(self, profile: FaultProfile) -> FaultProfile:
        with self._lock:
            self._profile = profile.model_copy(deep=True)
            return self._profile.model_copy(deep=True)

    def reset(self) -> None:
        with self._lock:
            self._profile = FaultProfile()

    def match(
        self,
        method: str,
        path: str,
    ) -> FaultProfile | None:
        with self._lock:
            profile = self._profile.model_copy(deep=True)

            if not profile.enabled:
                return None

            if method not in profile.methods:
                return None

            if not path.startswith(profile.path_prefix):
                return None

            if self._random.random() >= profile.probability:
                return None

            return profile
