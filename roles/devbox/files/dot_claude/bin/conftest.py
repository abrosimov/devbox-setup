from __future__ import annotations

from hypothesis import settings

settings.register_profile("dev", max_examples=100, deadline=2000)
settings.register_profile("ci", max_examples=500, deadline=5000)
settings.load_profile("dev")
