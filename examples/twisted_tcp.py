import logging
import binascii
import uhf_reader

from twisted.internet import reactor

UHF_HOST = "172.16.50.20"
UHF_PORT = 100

FORMAT = ('%(asctime)-15s %(threadName)-15s'
          ' %(levelname)-8s %(module)-15s:%(lineno)-8s %(message)s')

logging.basicConfig(format=FORMAT)
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

reader_queue = None
reader = None

def sendTestRequest():
    deferred = reader.gen2_sec_read_ex(bank=uhf_reader.USER, addr=3, count=16)
    deferred.addCallbacks(lambda result: print(binascii.hexlify(result)),
                          lambda err: print(err))


class UHFReaderProtocol(uhf_reader.protocol.UHFReaderProtocolBase):
    def connectionMade(self):
        super().connectionMade()
        logger.info("Connection established")
        reactor.callLater(5, sendTestRequest)


if __name__ == '__main__':
    factory = uhf_reader.factory.UHFReaderClientFactory.forProtocol(UHFReaderProtocol)
    reader_queue = factory.getQueue("{}:{}".format(UHF_HOST, UHF_PORT))
    reader = uhf_reader.AsyncUHFReader(queue=reader_queue)

    reactor.connectTCP(UHF_HOST, UHF_PORT, factory)
    reactor.run()
