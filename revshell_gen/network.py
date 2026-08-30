"""Enumerate local network interfaces so the user can pick an attacker IP
without having to type `ip a` / `ifconfig` / `ipconfig` in another terminal.
"""

from __future__ import annotations

import socket
from dataclasses import dataclass

import psutil


@dataclass(frozen=True, order=True)
class InterfaceAddress:
    """A single (interface name, IPv4 address) pair."""

    interface: str
    ip: str

    @property
    def is_loopback(self) -> bool:
        return self.ip.startswith("127.")

    @property
    def label(self) -> str:
        """Human friendly label used in the TUI select / CLI table."""
        return f"{self.ip} ({self.interface})"


def list_ipv4_addresses(include_loopback: bool = False) -> list[InterfaceAddress]:
    """Return every IPv4 address bound to a local network interface.

    Uses ``psutil.net_if_addrs`` so it works the same way on Linux, macOS
    and Windows, without shelling out to ``ip``/``ifconfig``/``ipconfig``.
    """
    results: list[InterfaceAddress] = []

    for interface, addresses in psutil.net_if_addrs().items():
        for addr in addresses:
            if addr.family != socket.AF_INET:
                continue

            candidate = InterfaceAddress(interface=interface, ip=addr.address)

            if candidate.is_loopback and not include_loopback:
                continue

            results.append(candidate)

    # Stable, predictable ordering: real interfaces before loopback,
    # then alphabetically by interface name.
    return sorted(results, key=lambda a: (a.is_loopback, a.interface, a.ip))


def default_ip() -> str | None:
    """Best-effort guess of the "main" outbound IP (first non-loopback one)."""
    addresses = list_ipv4_addresses(include_loopback=False)
    return addresses[0].ip if addresses else None
