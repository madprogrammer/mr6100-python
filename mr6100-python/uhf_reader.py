import socket
import time
import os

from typing import Dict, Tuple, Any

# Reader defined commands
RESET_READER = b"\x21"
GET_FIRMWARE_VERSION = b"\x22"

SET_RF_POWER = b"\x25"
GET_RF_POWER = b"\x26"
SET_RF_FREQUENCY = b"\x27"
GET_RF_FREQUENCY = b"\x28"

GEN2_SECURED_READ = b"\x88"
GEN2_SECURED_WRITE = b"\x89"
GEN2_SECURED_LOCK = b"\x8A"

# RF frequency settings
RF_FREQUENCY_CHINA = 0
RF_FREQUENCY_USA = 1
RF_FREQUENCY_EUROPE = 2
RF_FREQUENCY_CUSTOM = 3

# Memory Bank IDs
RESERVED = 0
EPC = 1
TID = 2
USER = 3

# Lock levels
UNLOCK = 0
UNLOCK_FOREVER = 1
SECURE_LOCK = 2
LOCK_FOREVER = 3


class InvalidParameterException(Exception):
    pass


class InvalidChecksumException(Exception):
    pass


class ErrorResponseException(Exception):
    def __init__(self, *args, **kwargs):
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


class UHDReader:
    buffer_size = 8192
    connection = None
    timeout = 5.0
    host = None
    port = 100

    def __init__(self, *args, **kwargs):
        if len(kwargs):
            self.timeout = kwargs.get('timeout', self.timeout)
            self.host = kwargs.get('host', self.host)
            self.port = kwargs.get('port', self.port)

    def connect(self):
        """
        Open connection to the reader
        :return: :class:`socket.socket`
        """
        self.connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connection.settimeout(self.timeout)
        self.connection.connect((self.host, self.port))

        return self.connection

    def disconnect(self) -> None:
        """
        Close connection to the reader
        """
        self.connection.close()

    def get_response(self) -> Dict[str, Any]:
        """
        Get reader response as `dict`, validate checksum and status byte
        :return: `dict` with reader response
        :raises: :class:`InvalidChecksumException`, :class:`ErrorResponseException`
        """
        data = None

        deadline = time.time() + self.timeout
        while data is None:
            if time.time() >= deadline:
                raise Exception()

            self.connection.settimeout(deadline - time.time())
            data = self.connection.recv(self.buffer_size)

        if self.calculate_checksum(data[:-1]) != data[-1]:
            raise InvalidChecksumException()

        response = {
            'addr': data[1],
            'len': data[2],
            'status': data[3],
            'data': data[4:-1],
            'chksum': data[-1]
        }

        if response['status'] != 0:
            raise ErrorResponseException(code=response['status'])

        return response

    def send_command(self, cmd: bytes, data: bytes = b"") -> None:
        """
        Send command to the reader
        :param cmd: Operation code, e.g. `GET_FIRMWARE_VERSION`
        :param data: Command payload, if needed
        """
        head = b"\x0A"
        addr = b"\xFF"
        length = (len(cmd) + len(data) + 1).to_bytes(1, byteorder="big")

        packet = addr + length + cmd + data
        crc = self.calculate_checksum(packet).to_bytes(1, byteorder='big')

        request = head + packet + crc
        self.connection.sendall(request)

    @staticmethod
    def calculate_checksum(packet: bytes) -> int:
        """
        Calculate checksum for the packet
        :param packet: Binary string to calculate the checksum forr
        :rtype: int
        :return: Checksum value
        """
        checksum = 0

        for x in packet:
            checksum = checksum + x
            if checksum > 255:
                checksum = checksum.to_bytes(2, byteorder='big')[1]

        checksum = ((~checksum) + 1) & 0xff

        if checksum > 255:
            checksum = checksum.to_bytes(2, byteorder='big')[1]

        return checksum

    def get_fw_version(self) -> Tuple[int, int]:
        """
        Gets reader firmware version
        :rtype: object
        :return: tuple with major & minor version, e.g. `(6, 3)`
        """
        self.send_command(GET_FIRMWARE_VERSION)
        response = self.get_response()['data']
        return response[0], response[1]

    def reset_reader(self) -> None:
        """
        Reset the reader
        """
        self.send_command(RESET_READER)

    def set_rf_power(self, power1: int = 20, power2: int = 2, power3: int = 32, power4: int = 0) -> None:
        """
        Set RF transmit power in dBm for reader antennas (0-30 dBm). Not all antennas may be present.
        :param power1: Power for the first antenna
        :param power2: Power for the second antenna
        :param power3: Power for the third antenna
        :param power4: Power for the fourth antenna
        """
        data = power1.to_bytes(1, byteorder='big')
        data += power2.to_bytes(1, byteorder='big')
        data += power3.to_bytes(1, byteorder='big')
        data += power4.to_bytes(1, byteorder='big')

        self.send_command(SET_RF_POWER, data)
        self.get_response()

    def get_rf_power(self) -> Tuple[int, int, int, int]:
        """
        Get RF transmit power setting for reader antennas (0-30 dBm). Not all antennas may be present.
        :return: tuple with current RF transmit power for each antenna, e.g. `(20, 2, 30, 0)`
        """
        self.send_command(GET_RF_POWER)
        response = self.get_response()['data']
        return response[0], response[1], response[2], response[3]

    def set_rf_frequency(self, region: int = RF_FREQUENCY_EUROPE) -> None:
        """
        Set RF frequency region to operate
        :param region: `RF_FREQUENCY_CHINA`, `RF_FREQUENCY_USA` or `RF_FREQUENCY_EUROPE`
        """
        self.send_command(SET_RF_FREQUENCY, b"\x00" + region.to_bytes(1, byteorder='big'))
        self.get_response()

    def get_rf_frequency(self) -> int:
        """
        Get current RF frequency region setting
        :return: `RF_FREQUENCY_CHINA`, `RF_FREQUENCY_USA`, `RF_FREQUENCY_EUROPE` or `RF_FREQUENCY_CUSTOM`
        """
        self.send_command(GET_RF_FREQUENCY)
        response = self.get_response()['data']
        if response[0] == 0:
            return response[1]
        return RF_FREQUENCY_CUSTOM

    @staticmethod
    def __get_password_bank_param(password: int, bank: int, param: int) -> bytes:
        value = (password >> 24 & 0xff).to_bytes(1, byteorder='big')
        value += (password >> 16 & 0xff).to_bytes(1, byteorder='big')
        value += (password >> 8 & 0xff).to_bytes(1, byteorder='big')
        value += (password & 0xff).to_bytes(1, byteorder='big')
        value += bank.to_bytes(1, byteorder='big')
        value += int(param).to_bytes(1, byteorder='big')
        return value

    def __gen2_sec_read(self, password: int = 0, bank: int = EPC, addr: int = 0, count: int = 4) -> bytes:
        value = self.__get_password_bank_param(password, bank, addr)
        value += count.to_bytes(1, byteorder='big')

        self.send_command(GEN2_SECURED_READ, value)
        response = self.get_response()['data'][1:]

        return response

    def __gen2_sec_write(self, data: bytes, password: int = 0, bank: int = USER, addr: int = 0) -> None:
        if len(data) != 2:
            raise InvalidParameterException("Data must be 2 bytes long")

        value = self.__get_password_bank_param(password, bank, addr)
        value += data

        self.send_command(GEN2_SECURED_WRITE, value)
        self.get_response()

    def gen2_sec_lock(self, password: int = 0, bank: int = USER, level: int = UNLOCK) -> None:
        """
        Lock/unlock given memory bank using specified locking level
        :param password: Access password
        :param bank: Memory bank to lock/unlock (`RESERVED`, `EPC`, `TID`, `USER`)
        :param level: Lock level (`UNLOCK`, `UNLOCK_FOREVER`, `SECURE_LOCK`, `LOCK_FOREVER`)
        """
        value = self.__get_password_bank_param(password, bank, level)

        self.send_command(GEN2_SECURED_LOCK, value)
        self.get_response()

    def gen2_sec_write(self, data: bytes, password: int = 0, bank: int = USER) -> None:
        """
        Write data to given memory bank
        :param data: Data to write
        :param password: Access password
        :param bank: Memory bank to write into (`RESERVED`, `EPC`, `TID`, `USER`)
        """
        if len(data) == 0:
            return
        if len(data) % 2 != 0:
            data += b"\x00"
        chunks = [data[i:i + 2] for i in range(0, len(data), 2)]
        for idx, chunk in enumerate(chunks):
            self.__gen2_sec_write(chunk, password=password, bank=bank, addr=idx)

    def gen2_sec_read(self, password: int = 0, bank: int = EPC, addr: int = 0, count: int = 16) -> bytes:
        """
        Read data from given memory bank
        :param password: Access password
        :param bank: Memory bank to read from (`RESERVED`, `EPC`, `TID`, `USER`)
        :param addr: Start byte offset
        :param count: Count of bytes to read
        :return: Bytes read from the specified memory bank
        """
        result = b""

        if count == 0:
            return result

        if addr < 0:
            raise InvalidParameterException("addr must be positive integer")

        # Read minimal number of 8-byte blocks containing requested data
        for i in range(8 * (addr // 8), addr + count, 8):
            result += self.__gen2_sec_read(password=password, bank=bank, addr=i // 2)

        # Slice requested chunk from the possibly larger read chunk
        return result[addr % 8:addr % 8 + count]

    def write_epc(self, password: int = 0, data: bytes = b"") -> None:
        """
        Write specified or random data to EPC bits 96-128 to make EPC unique
        :param password: Access password
        :param data: Data to write (bytes of length 4)
        """
        if len(data) != 4:
            raise InvalidParameterException("data must be exactly 4 bytes long if specified")
        if len(data) == 0:
            data = os.urandom(4)
        self.__gen2_sec_write(data[0:2], password=password, bank=EPC, addr=6)
        self.__gen2_sec_write(data[2:4], password=password, bank=EPC, addr=7)
