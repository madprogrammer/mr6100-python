import queue

from twisted.internet import reactor
from twisted.internet.protocol import Protocol
from twisted.protocols.policies import TimeoutMixin

from uhf_reader.exceptions import RequestTimeoutException


class UHFReaderProtocolBase(Protocol, TimeoutMixin):
    request = None
    timeout_id = None

    def dataReceived(self, data):
        try:
            if self.request:
                response = self.request.parse_response(data)
                self.factory.logger.debug("Received response: %s", response.value())

                self.setTimeout(None)
                self.resetTimeout()

                if self.request.deferred:
                    self.request.deferred.callback((self.request, response))
        except Exception as exc:
            if self.request and self.request.deferred:
                self.request.deferred.errback(exc)
        finally:
            if self.timeout_id:
                self.timeout_id.cancel()

        self.checkQueue()

    def connectionMade(self):
        self.setTimeout(None)
        self.checkQueue()

    def timeoutConnection(self):
        self.transport.abortConnection()

    def timeoutRequest(self):
        if self.request:
            self.factory.logger.error("Request %s timed out", self.request)
            if self.request.deferred:
                self.request.deferred.errback(RequestTimeoutException(self.request))
        self.checkQueue()

    def checkQueue(self):
        if not self.factory.queue:
            return

        try:
            item = self.factory.queue.get(block=False)
            self.transport.write(item.build())
            self.factory.logger.debug("Sent request: %s", item)

            if self.factory.timeout:
                self.setTimeout(self.factory.timeout)
                self.resetTimeout()
                self.timeout_id = reactor.callLater(self.factory.timeout, self.timeoutRequest)

            self.request = item
        except queue.Empty:
            reactor.callLater(0.5, self.checkQueue)
