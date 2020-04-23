import logging

from twisted.internet.protocol import ReconnectingClientFactory


class UHFReaderClientFactory(ReconnectingClientFactory):
    def __init__(self, timeout=5, queue=None, **kwargs):
        super().__init__(**kwargs)
        self.timeout = timeout
        self.queue = queue
        self.logger = logging.getLogger(__name__)

        # Override default factor & delay
        self.factor = 1.5
        self.maxDelay = 5.0

    def startedConnecting(self, connector):
        self.logger.info("Started to connect to UHF reader")

    def buildProtocol(self, addr):
        self.logger.info("Connected to UHF reader")
        self.resetDelay()
        return super(UHFReaderClientFactory, self).buildProtocol(addr)

    def clientConnectionLost(self, connector, reason):
        self.logger.error("Lost connection to UHF reader. Reason: " + str(reason))
        super(UHFReaderClientFactory, self).clientConnectionLost(connector, reason)

    def clientConnectionFailed(self, connector, reason):
        self.logger.error("Connection to UHF reader failed. Reason: " + str(reason))
        super(UHFReaderClientFactory, self).clientConnectionFailed(connector, reason)

