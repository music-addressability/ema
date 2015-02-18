
class OmasException(Exception):
    def __init__(self, message):
        self.message = message

class CannotReadMEIException(OmasException):
    pass

class CannotWriteMEIException(OmasException):
    pass

class UnknownMEIReadException(OmasException):
    pass

class BadApiRequest(OmasException):
    pass

class CannotAccessRemoteMEIException(OmasException):
    pass
