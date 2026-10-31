class ServiceError(Exception):
    """A business-rule failure with a message suitable for the user."""


class PermissionDenied(ServiceError):
    pass
