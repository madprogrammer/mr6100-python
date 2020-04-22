from uhf_reader.packet import UHFPacket
from uhf_reader.response import UHFResponse, GetFirmwareVersionResponse, GetRadioPowerResponse, \
    GetRadioFrequencyResponse, Gen2SecuredReadResponse
from uhf_reader.exceptions import InvalidParameterException

from uhf_reader.constants import GET_FIRMWARE_VERSION, RESET_READER, SET_RADIO_POWER, GET_RADIO_POWER, \
    SET_RADIO_FREQUENCY, GET_RADIO_FREQUENCY, RADIO_FREQUENCY_CHINA, RADIO_FREQUENCY_USA, RADIO_FREQUENCY_EUROPE, \
    GEN2_SECURED_READ, GEN2_SECURED_WRITE, GEN2_SECURED_LOCK
from uhf_reader.constants import EPC, USER, UNLOCK


class UHFRequest(UHFPacket):
    def __init__(self, command: bytes, args: bytes = b"") -> None:
        self.command = command
        self.args = args

        if len(self.command) > 1:
            raise InvalidParameterException("command must be 1 byte long")

        self.deferred = None

        super().__init__(self.build())

    def build(self) -> bytes:
        head = b"\x0A"
        addr = b"\xFF"

        length = (len(self.command) + len(self.args) + 1).to_bytes(1, byteorder="big")

        packet = addr + length + self.command + self.args
        crc = self.calculate_checksum(packet).to_bytes(1, byteorder='big')

        return head + packet + crc

    @staticmethod
    def parse_response(data: bytes) -> UHFResponse:
        return UHFResponse(data)

    @staticmethod
    def _get_password_bank_param(password: int, bank: int, param: int) -> bytes:
        value = (password >> 24 & 0xff).to_bytes(1, byteorder='big')
        value += (password >> 16 & 0xff).to_bytes(1, byteorder='big')
        value += (password >> 8 & 0xff).to_bytes(1, byteorder='big')
        value += (password & 0xff).to_bytes(1, byteorder='big')
        value += bank.to_bytes(1, byteorder='big')
        value += int(param).to_bytes(1, byteorder='big')
        return value


class GetFirmwareVersionRequest(UHFRequest):
    def __init__(self) -> None:
        super().__init__(GET_FIRMWARE_VERSION)

    @staticmethod
    def parse_response(data: bytes) -> GetFirmwareVersionResponse:
        return GetFirmwareVersionResponse(data)


class ResetReaderRequest(UHFRequest):
    def __init__(self) -> None:
        super().__init__(RESET_READER)


class SetRadioPowerRequest(UHFRequest):
    def __init__(self, power1: int = 20, power2: int = 2, power3: int = 32, power4: int = 0) -> None:
        args = power1.to_bytes(1, byteorder='big')
        args += power2.to_bytes(1, byteorder='big')
        args += power3.to_bytes(1, byteorder='big')
        args += power4.to_bytes(1, byteorder='big')

        super().__init__(SET_RADIO_POWER, args)


class GetRadioPowerRequest(UHFRequest):
    def __init__(self) -> None:
        super().__init__(GET_RADIO_POWER)

    @staticmethod
    def parse_response(data: bytes) -> GetRadioPowerResponse:
        return GetRadioPowerResponse(data)


class SetRadioFrequencyRequest(UHFRequest):
    def __init__(self, region: int) -> None:
        if region not in [RADIO_FREQUENCY_CHINA, RADIO_FREQUENCY_USA, RADIO_FREQUENCY_EUROPE]:
            raise InvalidParameterException("invalid radio frequency")

        super().__init__(SET_RADIO_FREQUENCY, b"\x00" + region.to_bytes(1, byteorder='big'))


class GetRadioFrequencyRequest(UHFRequest):
    def __init__(self) -> None:
        super().__init__(GET_RADIO_FREQUENCY)

    @staticmethod
    def parse_response(data: bytes) -> GetRadioFrequencyResponse:
        return GetRadioFrequencyResponse(data)


class Gen2SecuredReadRequest(UHFRequest):
    def __init__(self, password: int = 0, bank: int = EPC, addr: int = 0, count: int = 4) -> None:
        args = self._get_password_bank_param(password, bank, addr)
        args += count.to_bytes(1, byteorder='big')

        self.addr = addr
        self.count = count

        super().__init__(GEN2_SECURED_READ, args)

    @staticmethod
    def parse_response(data: bytes) -> Gen2SecuredReadResponse:
        return Gen2SecuredReadResponse(data)


class Gen2SecuredWriteRequest(UHFRequest):
    def __init__(self, data: bytes, password: int = 0, bank: int = USER, addr: int = 0) -> None:
        if len(data) != 2:
            raise InvalidParameterException("data must be 2 bytes long")

        args = self._get_password_bank_param(password, bank, addr)
        args += data

        self.addr = addr

        super().__init__(GEN2_SECURED_WRITE, args)


class Gen2SecuredLockRequest(UHFRequest):
    def __init__(self, password: int = 0, bank: int = USER, level: int = UNLOCK) -> None:
        args = self._get_password_bank_param(password, bank, level)

        super().__init__(GEN2_SECURED_LOCK, args)
