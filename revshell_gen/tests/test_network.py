from __future__ import annotations

import socket
from collections import namedtuple

import pytest

from revshell_gen import network

FakeAddr = namedtuple("FakeAddr", ["family", "address", "netmask", "broadcast", "ptp"])


def _fake_addr(family: int, address: str) -> FakeAddr:
    return FakeAddr(family=family, address=address, netmask=None, broadcast=None, ptp=None)


@pytest.fixture
def fake_interfaces(monkeypatch):
    fake = {
        "lo": [_fake_addr(socket.AF_INET, "127.0.0.1")],
        "eth0": [
            _fake_addr(socket.AF_INET, "192.168.1.10"),
            _fake_addr(socket.AF_INET6, "fe80::1"),
        ],
        "tun0": [_fake_addr(socket.AF_INET, "10.10.14.5")],
    }
    monkeypatch.setattr(network.psutil, "net_if_addrs", lambda: fake)
    return fake


def test_list_ipv4_addresses_excludes_loopback_by_default(fake_interfaces):
    addresses = network.list_ipv4_addresses()
    ips = [a.ip for a in addresses]
    assert "127.0.0.1" not in ips
    assert "192.168.1.10" in ips
    assert "10.10.14.5" in ips


def test_list_ipv4_addresses_excludes_ipv6(fake_interfaces):
    addresses = network.list_ipv4_addresses()
    assert all(":" not in a.ip for a in addresses)


def test_list_ipv4_addresses_can_include_loopback(fake_interfaces):
    addresses = network.list_ipv4_addresses(include_loopback=True)
    ips = [a.ip for a in addresses]
    assert "127.0.0.1" in ips


def test_interface_address_label_format(fake_interfaces):
    addresses = network.list_ipv4_addresses()
    eth0 = next(a for a in addresses if a.interface == "eth0")
    assert eth0.label == "192.168.1.10 (eth0)"


def test_default_ip_returns_first_non_loopback(fake_interfaces):
    assert network.default_ip() in {"192.168.1.10", "10.10.14.5"}


def test_default_ip_returns_none_when_no_interfaces(monkeypatch):
    monkeypatch.setattr(network.psutil, "net_if_addrs", dict)
    assert network.default_ip() is None
