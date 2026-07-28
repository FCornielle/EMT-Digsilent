"""Project-specific exceptions."""


class PFEMTError(RuntimeError):
    """Base exception for controlled workflow failures."""


class ConfigurationError(PFEMTError):
    """Raised when study configuration is incomplete or inconsistent."""


class PowerFactoryUnavailable(PFEMTError):
    """Raised when the PowerFactory Python API cannot be loaded or connected."""


class PowerFactoryExecutionError(PFEMTError):
    """Raised when a PowerFactory command reports a non-zero return code."""


class ResultFormatError(PFEMTError):
    """Raised when an exported result does not match the declared channel map."""

