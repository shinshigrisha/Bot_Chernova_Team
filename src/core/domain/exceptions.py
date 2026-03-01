"""Domain exceptions."""


class DomainError(Exception):
    """Base domain error."""


class AssetAlreadyAssignedError(DomainError):
    """Asset already has an active assignment."""
