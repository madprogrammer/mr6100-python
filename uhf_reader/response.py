from typing import Tuple

from uhf_reader.packet import UHFPacket
from uhf_reader.exceptions import InvalidPacketException, InvalidChecksumException, ErrorResponseException

from uhf_reader.constants import RADIO_FREQUENCY_CUSTOM


class UHFResponse(UHFPacket):
    def __init__(self, data: bytes) -> None:
        super().__init__(data)

        if len(data) < 5:
            raise InvalidPacketException("response too short")

        if data[0] != 0x0b:
            raise InvalidPacketException("invalid response header")

        self.addr = data[1]
        self.length = data[2]

        if len(data) != self.length + 3:
            raise InvalidPacketException("response too short")

        self.status = data[3]
        self.payload = data[4:-1]
        self.checksum = data[-1]

        self.validate_response()

    def validate_checksum(self) -> None:
        if self.calculate_checksum(self.data[:-1]) != self.checksum:
            raise InvalidChecksumException()

    def raise_on_status(self) -> None:
        if self.status != 0:
            raise ErrorResponseException(code=self.status)

    def validate_response(self) -> None:
        self.validate_checksum()
        self.raise_on_status()

    def value(self) -> bytes:
        return self.payload


class GetFirmwareVersionResponse(UHFResponse):
    def __init__(self, data: bytes) -> None:
        super().__init__(data)

        self.major = self.payload[0]
        self.minor = self.payload[1]

    def value(self) -> Tuple[int, int]:
        return self.major, self.minor


class GetRadioPowerResponse(UHFResponse):
    def __init__(self, data: bytes) -> None:
        super().__init__(data)

        self.power1 = self.payload[0]
        self.power2 = self.payload[1]
        self.power3 = self.payload[2]
        self.power4 = self.payload[3]

    def value(self) -> Tuple[int, int, int, int]:
        return self.power1, self.power2, self.power3, self.power4


class GetRadioFrequencyResponse(UHFResponse):
    def __init__(self, data: bytes) -> None:
        super().__init__(data)

        self.region = self.payload[1] if self.payload[0] == 0 else RADIO_FREQUENCY_CUSTOM

    def value(self) -> int:
        return self.region


class Gen2SecuredReadResponse(UHFResponse):
    def __init__(self, data: bytes):
        super().__init__(data)

        self.payload = self.payload[1:]
