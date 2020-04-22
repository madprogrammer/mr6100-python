class InvalidParameterException(Exception):
    pass


class InvalidChecksumException(Exception):
    pass


class InvalidPacketException(Exception):
    pass


class ErrorResponseException(Exception):
    def __init__(self, **kwargs):
        self.code = kwargs.get('code', 0)
        super().__init__(self.__get_message())

    def __get_message(self):
        try:
            return {
                0x00: "No error",
                0x01: "General error",
                0x02: "Parameter setting failed",
                0x03: "Parameter reading failed",
                0x04: "No tag",
                0x05: "Tag reading failed",
                0x06: "Tag writing failed",
                0x07: "Tag locking failed",
                0x08: "Tag erase failed"
            }[self.code]
        except KeyError:
            return "Unknown failure"


class NetworkException(Exception):
    pass


class RequestException(Exception):
    def __init__(self, request):
        self.request = request


class RequestTimeoutException(RequestException):
    pass
