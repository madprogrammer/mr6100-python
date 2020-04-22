import os
import socket
import time

from typing import Tuple, Any

from .request import UHFRequest, GetFirmwareVersionRequest, ResetReaderRequest, SetRadioPowerRequest, \
    GetRadioPowerRequest, SetRadioFrequencyRequest, GetRadioFrequencyRequest, Gen2SecuredReadRequest, \
    Gen2SecuredWriteRequest, Gen2SecuredLockRequest
from .exceptions import NetworkException, InvalidParameterException
from .constants import RADIO_FREQUENCY_EUROPE, USER, EPC, UNLOCK


def deferred_stub():
    return None


try:
    from twisted.internet import defer
    deferred_wrapper = defer.Deferred
except ImportError:
    deferred_wrapper = deferred_stub


class AsyncUHFReader:
    """
    Asynchronous API implementation for Twisted
    """
    def __init__(self, queue) -> None:
        self.queue = queue

    def __put_request(self, request) -> Any:
        request.deferred = deferred_wrapper()
        self.queue.put(request)
        return request.deferred

    def get_fw_version(self):
        return self.__put_request(GetFirmwareVersionRequest())

    def reset_reader(self):
        return self.__put_request(ResetReaderRequest())

    def set_rf_power(self, power1: int = 20, power2: int = 2, power3: int = 32, power4: int = 0):
        return self.__put_request(SetRadioPowerRequest(power1=power1, power2=power2, power3=power3, power4=power4))

    def get_rf_power(self):
        return self.__put_request(GetRadioPowerRequest())

    def set_rf_channel(self, region=RADIO_FREQUENCY_EUROPE):
        return self.__put_request(SetRadioFrequencyRequest(region=region))

    def get_rf_channel(self):
        return self.__put_request(GetRadioFrequencyRequest())

    def gen2_sec_lock(self, password: int = 0, bank: int = USER, level: int = UNLOCK):
        return self.__put_request(Gen2SecuredLockRequest(password=password, bank=bank, level=level))

    def gen2_sec_write(self, data: bytes, password: int = 0, bank: int = USER, addr: int = 0):
        return self.__put_request(Gen2SecuredWriteRequest(data, password=password, bank=bank, addr=addr))

    def gen2_sec_read(self, password: int = 0, bank: int = EPC, addr: int = 0, count: int = 4):
        return self.__put_request(Gen2SecuredReadRequest(password=password, bank=bank, addr=addr, count=count))

    def gen2_sec_write_ex(self, data: bytes, password: int = 0, bank: int = USER):
        if len(data) == 0:
            return
        if len(data) % 2 != 0:
            data += b"\x00"
        chunks = [data[i:i + 2] for i in range(0, len(data), 2)]

        deferred = deferred_wrapper()

        def chunk_write_callback(result):
            request, response = result
            if request.addr < len(chunks) - 1:
                self.gen2_sec_write(chunks[request.addr + 1], password=password, bank=bank, addr=request.addr + 1) \
                    .addCallbacks(chunk_write_callback, chunk_write_error)
            else:
                deferred.callback((request, response))

        def chunk_write_error(failure):
            deferred.errback(failure)

        self.gen2_sec_write(chunks[0], password=password, bank=bank, addr=0) \
            .addCallbacks(chunk_write_callback, chunk_write_error)

        return deferred

    def gen2_sec_read_ex(self, password: int = 0, bank: int = EPC, addr: int = 0, count: int = 16):
        deferred = deferred_wrapper()
        accumulator = b""

        if count == 0:
            deferred.callback(b"")
            return deferred

        if addr < 0:
            raise InvalidParameterException("addr must be positive integer")

        def chunk_read_callback(result):
            nonlocal accumulator

            request, response = result
            accumulator += response.value()

            if request.addr * 2 + 8 < addr + count:
                self.gen2_sec_read(password=password, bank=bank, addr=request.addr + 4) \
                    .addCallbacks(chunk_read_callback, chunk_read_error)
            else:
                deferred.callback(accumulator[addr % 8:addr % 8 + count])

        def chunk_read_error(failure):
            deferred.errback(failure)

        self.gen2_sec_read(password=password, bank=bank, addr=8 * (addr // 8) // 2).addCallbacks(chunk_read_callback,
                                                                                                 chunk_read_error)

        return deferred


class UHFReader:
    """
    Synchronous TCP client implementation
    """
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

    def connect(self) -> None:
        """
        Open connection to the reader
        """
        try:
            self.connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.connection.settimeout(self.timeout)
            self.connection.connect((self.host, self.port))
        except Exception as exc:
            raise NetworkException("failed to connect: " + str(exc))

    def disconnect(self) -> None:
        """
        Close connection to the reader
        """
        try:
            self.connection.close()
        except Exception as exc:
            raise NetworkException("failed to disconnect: " + str(exc))

    def get_response(self) -> bytes:
        """
        Get reader response
        :return: bytes
        :raises: :class:`InvalidChecksumException`, :class:`ErrorResponseException`, :class:`InvalidPacketException`
        """
        data = None

        deadline = time.time() + self.timeout
        while data is None:
            if time.time() >= deadline:
                raise NetworkException("receive timed out")

            try:
                self.connection.settimeout(deadline - time.time())
                data = self.connection.recv(self.buffer_size)
            except Exception as exc:
                raise NetworkException("failed to receive: " + str(exc))

        return data

    def send_request(self, request: UHFRequest) -> None:
        """
        Send request to the reader
        :param request: :class:`UHFRequest`
        """

        try:
            self.connection.sendall(request.data)
        except Exception as exc:
            raise NetworkException("failed to send: " + str(exc))

    def send_request_return_response(self, request) -> Any:
        self.send_request(request)
        return request.parse_response(self.get_response()).value()

    def get_fw_version(self) -> Tuple[int, int]:
        """
        Gets reader firmware version
        :rtype: object
        :return: tuple with major & minor version, e.g. `(6, 3)`
        """
        return self.send_request_return_response(GetFirmwareVersionRequest())

    def reset_reader(self) -> None:
        """
        Reset the reader
        """
        self.send_request(ResetReaderRequest())

    def set_rf_power(self, power1: int = 20, power2: int = 2, power3: int = 32, power4: int = 0) -> None:
        """
        Set RF transmit power in dBm for reader antennas (0-30 dBm). Not all antennas may be present.
        :param power1: Power for the first antenna
        :param power2: Power for the second antenna
        :param power3: Power for the third antenna
        :param power4: Power for the fourth antenna
        """
        self.send_request_return_response(SetRadioPowerRequest(power1=power1, power2=power2,
                                                               power3=power3, power4=power4))

    def get_rf_power(self) -> Tuple[int, int, int, int]:
        """
        Get RF transmit power setting for reader antennas (0-30 dBm). Not all antennas may be present.
        :return: tuple with current RF transmit power for each antenna, e.g. `(20, 2, 30, 0)`
        """
        return self.send_request_return_response(GetRadioPowerRequest())

    def set_rf_channel(self, region: int = RADIO_FREQUENCY_EUROPE) -> None:
        """
        Set RF frequency region to operate
        :param region: `RADIO_FREQUENCY_CHINA`, `RADIO_FREQUENCY_USA` or `RADIO_FREQUENCY_EUROPE`
        """
        self.send_request_return_response(SetRadioFrequencyRequest(region))

    def get_rf_channel(self) -> int:
        """
        Get current RF frequency region setting
        :return: `RADIO_FREQUENCY_CHINA`, `RADIO_FREQUENCY_USA`, `RADIO_FREQUENCY_EUROPE` or `RADIO_FREQUENCY_CUSTOM`
        """
        return self.send_request_return_response(GetRadioFrequencyRequest())

    def __gen2_sec_read(self, password: int = 0, bank: int = EPC, addr: int = 0, count: int = 4) -> bytes:
        return self.send_request_return_response(Gen2SecuredReadRequest(password=password, bank=bank,
                                                                        addr=addr, count=count))

    def __gen2_sec_write(self, data: bytes, password: int = 0, bank: int = USER, addr: int = 0) -> bytes:
        return self.send_request_return_response(Gen2SecuredWriteRequest(data, password=password, bank=bank, addr=addr))

    def gen2_sec_lock(self, password: int = 0, bank: int = USER, level: int = UNLOCK) -> None:
        """
        Lock/unlock given memory bank using specified locking level
        :param password: Access password
        :param bank: Memory bank to lock/unlock (`RESERVED`, `EPC`, `TID`, `USER`)
        :param level: Lock level (`UNLOCK`, `UNLOCK_FOREVER`, `SECURE_LOCK`, `LOCK_FOREVER`)
        """
        self.send_request_return_response(Gen2SecuredLockRequest(password=password, bank=bank, level=level))

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
