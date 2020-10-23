#
# This file is part of FaceDancer
#
""" Functionality for describing USB endpoints. """

from typing      import Iterable
from dataclasses import dataclass

from ..          import logger
from .magic      import AutoInstantiable
from .descriptor import USBDescribable
from .request    import USBRequestHandler, get_request_handler_methods
from .request    import to_this_endpoint, standard_request_handler
from .types      import USBDirection, USBTransferType, USBSynchronizationType
from .types      import USBUsageType, USBStandardRequests


@dataclass
class USBEndpoint(USBDescribable, AutoInstantiable, USBRequestHandler):
    """ Class represenging a USBEndpoint object.

    Field:
        number          -- The endpoint number (without the direction bit) for this endpoint.
        direction       -- A USBDirection constant indicating this endpoint's direction.

        transfer_type   -- A USBTransferType contant indicating the type of communications used.
        max_packet_size -- The maximum packet size for this endpoint.
        interval        -- The polling interval, for an INTERRUPT endpoint.
    """
    DESCRIPTOR_TYPE_NUMBER      = 0x05

    # Core identifiers.
    number               : int
    direction            : USBDirection

    # Endpoint attributes.
    transfer_type        : USBTransferType        = USBTransferType.BULK
    synchronization_type : USBSynchronizationType = USBSynchronizationType.NONE
    usage_type           : USBUsageType           = USBUsageType.DATA

    max_packet_size      : int = 64
    interval             : int = 0

    parent               : USBDescribable = None


    def __post_init__(self):

        # Grab our request handlers.
        self._request_handler_methods = get_request_handler_methods(self)

    #
    # User interface.
    #

    @staticmethod
    def address_for_number(endpoint_number: int, direction: USBDirection) -> int:
        """ Computes the endpoint address for a given number + direction. """
        direction_mask = 0x80 if direction == USBDirection.IN else 0x00
        return endpoint_number | direction_mask


    def get_device(self):
        """ Returns the device associated with the given descriptor. """
        return self.parent.get_device()


    def send(self, data: bytes, *, blocking: bool =False):
        """ Sends data on this endpoint. Valid only for IN endpoints.

        Parameters:
            data     -- The data to be sent.
            blocking -- True if we should block until the backend reports
                        the transmission to be complete.
        """
        self.get_device()._send_in_packets(self.number, data,
            packet_size=self.max_packet_size, blocking=blocking)


    #
    # Event handlers.
    #

    def handle_data_received(self, data: bytes):
        """ Handler for receipt of non-control request data.

        Parameters:
            data   -- The raw bytes received.
        """
        logger.info(f"EP{self.number} received {len(data)} bytes of data; "
                "but has no handler.")


    def handle_data_requested(self):
        """ Handler called when the host requests data on this endpoint."""


    def handle_buffer_empty(self):
        """ Handler called when this endpoint first has an empty buffer. """


    @standard_request_handler(number=USBStandardRequests.CLEAR_FEATURE)
    @to_this_endpoint
    def handle_clear_feature_request(self, request):
        logger.debug(f"received CLEAR_FEATURE request for endpoint {self.number} "
            f"with value {req.value}")
        request.acknowledge()


    #
    # Properties.
    #

    @property
    def address(self):
        """ Fetches the address for the given endpoint. """
        return self.address_for_number(self.number, self.direction)


    def get_address(self):
        """ Method alias for the address property. For backend support. """
        return self.address


    @property
    def attributes(self):
        """ Fetches the attributes for the given endpoint, as a single byte. """
        return (self.transfer_type & 0x03)               | \
               ((self.synchronization_type & 0x03) << 2) | \
               ((self.usage_type & 0x03) << 4)


    def get_descriptor(self) -> bytes:
        """ Get a descriptor string for this endpoint. """
        # FIXME: use construct

        d = bytearray([
                7,          # length of descriptor in bytes
                5,          # descriptor type 5 == endpoint
                self.address,
                self.attributes,
                self.max_packet_size & 0xff,
                (self.max_packet_size >> 8) & 0xff,
                self.interval
        ])

        return d


    #
    # Automatic instantiation helpers.
    #

    def get_identifier(self) -> int:
        return self.address

    def matches_identifier(self, other:int) -> bool:
        # Use only the MSB and the lower nibble; per the USB specification.
        masked_other = 0b10001111
        return self.get_identifier() == masked_other


    #
    # Request handling.
    #

    def _request_handlers(self) -> Iterable[callable]:
        return self._request_handler_methods


    #
    # Pretty-printing.
    #
    def __str__(self):
        direction     = USBDirection(self.direction).name
        transfer_type = USBTransferType(self.transfer_type).name
        is_interrupt  = (self.transfer_type == USBTransferType.INTERRUPT)
        additional    = f" every {self.interval}ms" if is_interrupt else ""

        return f"endpoint {self.number:02x}/{direction}: {transfer_type} transfers{additional}"
