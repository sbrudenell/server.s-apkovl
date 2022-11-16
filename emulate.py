#!/usr/bin/env python3

import os
import pathlib
import sys
from typing import Iterable, List, NoReturn, Sequence, Union

import requests

ArgType = Union[str, bytes, os.PathLike]


def combine_opts(args: Sequence[ArgType]) -> ArgType:
    def iter_bytes_args() -> Iterable[bytes]:
        for arg in args:
            if isinstance(arg, os.PathLike):
                arg = arg.__fspath__()
            if isinstance(arg, bytes):
                yield arg
            elif isinstance(arg, str):
                yield arg.encode("utf-8")

    return b",".join(arg.replace(b",", b",,") for arg in iter_bytes_args())


def net_args(
    *,
    id: str,
    model: str,
    mode: str,
    mac: str = None,
    net: str = None,
    host: str = None,
    restrict: str = None,
    instance: int = None,
    designation: str = None,
    hostfwd: Sequence[str] = (),
) -> Sequence[ArgType]:
    args: List[ArgType] = []

    assert mode == "user", mode
    netdev_opts = [mode, f"id={id}"]
    if net is not None:
        netdev_opts.append(f"net={net}")
    if host is not None:
        netdev_opts.append(f"host={host}")
    if restrict is not None:
        netdev_opts.append(f"restrict={restrict}")
    for hostfwd_opt in hostfwd:
        netdev_opts.append(f"hostfwd={hostfwd_opt}")
    args.extend(["-netdev", combine_opts(netdev_opts)])

    device_opts = [model, f"id={id}-dev", f"netdev={id}"]
    if mac is not None:
        device_opts.append(f"mac={mac}")
    args.extend(["-device", combine_opts(device_opts)])

    if instance is not None:
       smbios_opts: List[ArgType] = [
           "type=41",
           "kind=ethernet",
           f"pcidev={id}-dev",
           f"instance={instance}",
       ]
       if designation is not None:
           smbios_opts.append(f"designation={designation}")
       args.extend(["-smbios", combine_opts(smbios_opts)])

    return args


def main() -> NoReturn:
    qemu_args: list[ArgType] = ["qemu-system-x86_64"]
    qemu_args.extend(["-enable-kvm"])
    qemu_args.extend(["-machine", "q35"])
    qemu_args.extend(["-cpu", "Skylake-Server-v4"])
    qemu_args.extend(["-m", "4096"])
    qemu_args.extend(["-serial", "vc"])  # ttyS0
    qemu_args.extend(["-serial", "null"])  # ttyS1
    qemu_args.extend(["-serial", "vc"])  # ttyS2

    qemu_args.extend(
        net_args(
            id="eno2",
            mode="user",
            model="rtl8139",  # should be igb
            net="10.11.0.0/21",
            host="10.11.0.1",
            restrict="on",
            mac="AC:1F:6B:22:61:59",
            instance=2,
            designation="Intel Ethernet i210 #2",
        )
    )
    qemu_args.extend(
        net_args(
            id="eno1",
            mode="user",
            model="e1000e",
            net="104.218.233.98/29",
            host="104.218.233.97",
            mac="AC:1F:6B:22:61:58",
            instance=1,
            designation="Intel Ethernet i219 #1",
            hostfwd=("tcp::17463-104.218.233.98:17463", "udp::60000-104.218.233.98:60000"),
        )
    )

    qemu_args.extend(sys.argv[1:])

    print(qemu_args)
    os.execvp(qemu_args[0], qemu_args)


if __name__ == "__main__":
    main()
