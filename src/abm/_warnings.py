"""Centralized suppression for noisy third-party warnings.

Imported early by packages to ensure filters are active before other imports.
"""

from __future__ import annotations

import warnings

# Suppress torch CUDA pynvml deprecation warning emitted during torch.cuda init
# Message typically: "The pynvml package is deprecated. Please install nvidia-ml-py instead."
warnings.filterwarnings(
    "ignore",
    category=FutureWarning,
    message=r"The pynvml package is deprecated.*",
)
# Also target the emitting module to be safe
warnings.filterwarnings(
    "ignore",
    category=FutureWarning,
    module=r"torch\.cuda.*",
)
