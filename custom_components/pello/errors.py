"""Errors raised while talking to a Pello controller."""


class PelloError(Exception):
    """Base error of the Pello client."""


class PelloConnectionError(PelloError):
    """The controller could not be reached or answered with an HTTP error."""


class PelloInvalidHostError(PelloError):
    """The configured host is not a usable host name or address."""


class PelloAuthError(PelloError):
    """The controller rejected the credentials."""


class PelloParseError(PelloError):
    """The controller answered with something that could not be understood."""


class PelloWriteError(PelloError):
    """The controller refused to change a register."""
