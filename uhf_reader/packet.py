class UHFPacket:
    def __init__(self, data: bytes) -> None:
        self.data = data

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
