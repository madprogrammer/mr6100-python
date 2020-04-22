import logging

from twisted.internet.protocol import ReconnectingClientFactory


class UHFReaderClientFactory(ReconnectingClientFactory):
    def __init__(self, timeout=5, queue=None, **kwargs):
        self.timeout = timeout
        self.queue = queue
        self.logger = logging.getLogger(__name__)

    def startedConnecting(self, connector):
        self.logger.info("Started to connect")

    def buildProtocol(self, addr):
        self.logger.info("Connected")
        self.resetDelay()
        return super(UHFReaderClientFactory, self).buildProtocol(addr)

    def clientConnectionLost(self, connector, reason):
        self.logger.error("Lost connection. Reason: " + str(reason))

    def clientConnectionFailed(self, connector, reason):
        self.logger.error("Connect failed. Reason: " + str(reason))
