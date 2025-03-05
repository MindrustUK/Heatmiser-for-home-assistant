"""Discovery of Heatmiser Neo Hubs."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
import json
import logging
import socket
import time

_LOGGER = logging.getLogger(__name__)


@dataclass
class NeoHubDetails:
    """NeoHub details."""

    mac_address: str
    ip_address: str


@dataclass
class NeoHubConnectDetails:
    """NeoHub details."""

    mac_address: str
    ip_address: str
    token: str
    version: str
    direct_link_token: str | None


DISCOVERY_PORT = 19790
DISCOVERY_AUTO_CONNECT_PORT = 1979


def create_udp_socket(discovery_port: int) -> socket.socket:
    """Create a udp socket used for communicating with the device."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.bind(("", discovery_port))
    sock.setblocking(False)
    return sock


class HeatmiserDiscovery(asyncio.DatagramProtocol):
    """UDP discovery protocol for Heatmiser Neo Hubs."""

    def __init__(
        self,
        destination: tuple[str, int],
        on_response: Callable[[bytes, tuple[str, int]], None],
    ) -> None:
        """Initialize Heatmiser Discovery."""
        self.transport = None
        self.destination = destination
        self.on_response = on_response

    def datagram_received(self, data: bytes, addr: tuple[str, int]) -> None:
        """Trigger on_response callback with received data."""
        self.on_response(data, addr)

    def error_received(self, exc: Exception | None) -> None:
        """Log any errors received during UDP communication."""
        _LOGGER.error("HeatmiserDiscovery error: %s", exc)


def decode_data(raw_response: bytes) -> NeoHubDetails | None:
    """Decode a Heatmiser discovery response packet."""
    try:
        response = json.loads(raw_response.decode())
        if {"ip", "device_id"} <= response.keys():
            return NeoHubDetails(
                mac_address=response["device_id"], ip_address=response["ip"]
            )
        _LOGGER.warning("Invalid device format: %s", response)
    except json.JSONDecodeError:
        _LOGGER.exception("Failed to decode response")
    return None


def decode_auto_connect_data(
    raw_response: bytes, from_address: tuple[str, int]
) -> NeoHubConnectDetails | None:
    """Decode a Heatmiser connect response packet."""
    try:
        response = json.loads(raw_response.decode())
        if {"MAC", "token", "version"} <= response.keys():
            return NeoHubConnectDetails(
                mac_address=response["MAC"],
                ip_address=from_address[0],
                version=response["version"],
                token=response["token"],
                direct_link_token=response.get("directlinktoken"),
            )
        _LOGGER.warning("Invalid auto connect format: %s", response)
    except json.JSONDecodeError:
        _LOGGER.exception("Failed to decode response")
    return None


class AIOHeatmiserDiscovery:
    """Asynchronous scanner for Heatmiser Neo Hubs."""

    BROADCAST_FREQUENCY = 3
    DISCOVER_MESSAGE = b"hubseek"
    BROADCAST_ADDRESS = "<broadcast>"

    def __init__(self) -> None:
        """Initialize the AIOHeatmiserDiscovery scanner."""
        self.found_devices: list[NeoHubDetails] = []

    def _destination_from_address(self, address: str | None) -> tuple[str, int]:
        if address is None:
            address = self.BROADCAST_ADDRESS
        return (address, DISCOVERY_PORT)

    def _process_response(
        self,
        data: bytes | None,
        from_address: tuple[str, int],
        response_list: dict[tuple[str, int], NeoHubDetails],
        specific_address: bool = False,
    ) -> bool:
        """Process a response.

        Returns True if processing should stop
        """
        if data is None or data == self.DISCOVER_MESSAGE:
            return False
        try:
            response_list[from_address] = decode_data(data)
        except Exception:
            _LOGGER.exception("Failed to decode response from %s", from_address)
            return False
        return specific_address

    async def _async_run_scan(
        self,
        transport: asyncio.DatagramTransport,
        destination: tuple[str, int],
        timeout: int,
        found_all_future: asyncio.Future[bool],
    ) -> None:
        """Send the scans."""
        _LOGGER.debug("discover: %s => %s", destination, self.DISCOVER_MESSAGE)
        transport.sendto(self.DISCOVER_MESSAGE, destination)
        quit_time = time.monotonic() + timeout
        remain_time = float(timeout)
        while True:
            time_out = min(remain_time, timeout / self.BROADCAST_FREQUENCY)
            if time_out <= 0:
                return
            try:
                await asyncio.wait_for(
                    asyncio.shield(found_all_future), timeout=time_out
                )
            except TimeoutError:
                if time.monotonic() >= quit_time:
                    return
                # No response, send broadcast again in cast it got lost
                _LOGGER.debug("discover: %s => %s", destination, self.DISCOVER_MESSAGE)
                transport.sendto(self.DISCOVER_MESSAGE, destination)
            else:
                return  # found_all
            remain_time = quit_time - time.monotonic()

    async def async_scan(
        self,
        timeout: int = 10,
        address: str | None = None,
        targetted_address: bool = True,
    ) -> list[NeoHubDetails]:
        """Discover NeoHub devices."""
        _LOGGER.debug("Starting NeoHub discovery with timeout %ds", timeout)

        sock = create_udp_socket(DISCOVERY_PORT)
        destination = self._destination_from_address(address)
        found_all_future: asyncio.Future[bool] = asyncio.Future()
        response_list: dict[tuple[str, int], NeoHubDetails] = {}

        def _on_response(data: bytes, addr: tuple[str, int]) -> None:
            _LOGGER.debug("discover: %s <= %s", addr, data)
            if self._process_response(data, addr, response_list, targetted_address):
                found_all_future.set_result(True)

        transport, _ = await asyncio.get_running_loop().create_datagram_endpoint(
            lambda: HeatmiserDiscovery(
                destination=destination,
                on_response=_on_response,
            ),
            sock=sock,
        )
        try:
            await self._async_run_scan(
                transport,
                destination,
                timeout,
                found_all_future,
            )
        finally:
            transport.close()

        self.found_devices = list(response_list.values())
        _LOGGER.debug(
            "Discovered %d NeoHub devices: %s",
            len(self.found_devices),
            self.found_devices,
        )
        return self.found_devices


class AIOHeatmiserAutoConnect:
    """Asynchronous listener for Heatmiser Neo Hubs connect."""

    def __init__(self) -> None:
        """Initialize the AIOHeatmiserDiscovery scanner."""
        self.found_device: NeoHubConnectDetails | None = None

    def _process_response(
        self, data: bytes | None, from_address: tuple[str, int]
    ) -> NeoHubDetails | None:
        """Process a response.

        Returns True if processing should stop
        """
        if data is None:
            return None
        try:
            return decode_auto_connect_data(data, from_address)
        except Exception:
            _LOGGER.exception("Failed to decode response from %s", from_address)
            return None

    async def _async_run_scan(
        self,
        timeout: int,
        found_future: asyncio.Future[bool],
    ) -> None:
        try:
            await asyncio.wait_for(asyncio.shield(found_future), timeout=timeout)
        except TimeoutError:
            return

    async def async_scan(self, timeout: int = 120) -> NeoHubConnectDetails:
        """Discover NeoHub devices."""
        _LOGGER.debug(
            "Starting NeoHub Auto Connect discovery with timeout %ds", timeout
        )

        sock = create_udp_socket(DISCOVERY_AUTO_CONNECT_PORT)
        found_future: asyncio.Future[bool] = asyncio.Future()

        def _on_response(data: bytes, addr: tuple[str, int]) -> None:
            _LOGGER.debug("discover auto connect: %s <= %s", addr, data)
            self.found_device = self._process_response(data, addr)
            if self.found_device:
                found_future.set_result(True)

        transport, _ = await asyncio.get_running_loop().create_datagram_endpoint(
            lambda: HeatmiserDiscovery(
                destination=None,
                on_response=_on_response,
            ),
            sock=sock,
        )
        try:
            await self._async_run_scan(
                timeout,
                found_future,
            )
        finally:
            transport.close()

        _LOGGER.debug(
            "Received connect button press: %s",
            self.found_device,
        )
        return self.found_device
