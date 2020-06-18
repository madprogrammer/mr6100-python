import queue

from twisted.internet import reactor
from twisted.internet.protocol import Protocol
from twisted.protocols.policies import TimeoutMixin

from uhf_reader.exceptions import RequestTimeoutException


class UHFReaderProtocolBase(Protocol, TimeoutMixin):
    request = None
    peer_id = None
    queue = None

    def dataReceived(self, data):
        try:
            if self.request:
                response = self.request.parse_response(data)
                self.factory.logger.debug("Received response: %s", response.value())

                if self.request.deferred:
                    self.request.deferred.callback((self.request, response))
        except Exception as exc:
            if self.request and self.request.deferred:
                self.request.deferred.errback(exc)
        finally:
            self.setTimeout(None)

        self.checkQueue()

    def connectionMade(self):
        peer = self.transport.getPeer()
        self.peer_id = "{}:{}".format(peer.host, peer.port)
        self.queue = self.factory.getQueue(self.peer_id)
        self.checkQueue()

    def timeoutConnection(self):
        self.timeoutRequest()
        self.transport.abortConnection()

    def timeoutRequest(self):
        if self.request:
            self.factory.logger.error("Request %s timed out", self.request)
            if self.request.deferred:
                self.request.deferred.errback(RequestTimeoutException(self.request))

    def checkQueue(self):
        if not self.queue:
            return

        try:
            item = self.queue.get(block=False)
            self.transport.write(item.build())
            self.factory.logger.debug("Sent request: %s", item)

            if self.factory.timeout:
                self.setTimeout(self.factory.timeout)

            self.request = item
        except queue.Empty:
            reactor.callLater(0.5, self.checkQueue)
