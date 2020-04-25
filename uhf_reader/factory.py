import logging
import queue

from collections import defaultdict
from twisted.internet.protocol import ReconnectingClientFactory


class UHFReaderClientFactory(ReconnectingClientFactory):
    def __init__(self, timeout=5, **kwargs):
        super().__init__(**kwargs)
        self.timeout = timeout
        self.queues = defaultdict(queue.Queue)
        self.logger = logging.getLogger(__name__)

        # Override default factor & delay
        self.factor = 1.5
        self.maxDelay = 5.0

    def getQueue(self, peer_id):
        return self.queues[peer_id]

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

