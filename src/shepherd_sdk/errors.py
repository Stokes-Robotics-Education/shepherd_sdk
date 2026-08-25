class ShepherdError(Exception):
    """Base SDK error."""


class ShepherdConnectionError(ShepherdError):
    """The Shep service could not be reached."""


class ShepherdResponseError(ShepherdError):
    def __init__(self, message: str, status: int = 0) -> None:
        super().__init__(message)
        self.status = status

