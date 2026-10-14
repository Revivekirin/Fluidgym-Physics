"""Explicit error types so unsupported requests fail loudly instead of degrading silently."""


class FluidGymPhysicsError(Exception):
    pass


class UpstreamIntegrityError(FluidGymPhysicsError):
    pass


class UnsupportedEnvironmentError(FluidGymPhysicsError):
    pass


class UnsupportedParameterError(FluidGymPhysicsError):
    pass


class MissingInitialDomainError(FluidGymPhysicsError):
    pass


class CudaUnavailableError(FluidGymPhysicsError):
    pass
