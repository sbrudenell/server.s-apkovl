#!/usr/bin/env python3

import argparse
import os
import pathlib
import subprocess
from typing import Iterable, List, NoReturn, Sequence, Union

import requests

ArgType = Union[str, bytes, os.PathLike]


def call(args: Sequence[ArgType]) -> int:
    print(args)
    return subprocess.check_call(args)


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

    # if instance is not None:
    #    smbios_opts: List[ArgType] = [
    #        "type=41",
    #        "kind=ethernet",
    #        f"pcidev={id}-dev",
    #        f"instance={instance}",
    #    ]
    #    if designation is not None:
    #        smbios_opts.append(f"designation={designation}")
    #    args.extend(["-smbios", combine_opts(smbios_opts)])

    return args


DIR = pathlib.Path(__file__).parent


def main() -> NoReturn:
    parser = argparse.ArgumentParser()
    parser.add_argument("--netboot", action="store_true")
    parser.add_argument(
        "--ipxe",
        type=pathlib.Path,
        default=DIR / "ipxe/ipxe/src/bin-x86_64-efi/ipxe.efi",
    )
    parser.add_argument("--ipxe-cfg", type=pathlib.Path, default=DIR / "ipxe.cfg")
    parser.add_argument(
        "--bios", type=pathlib.Path, default=pathlib.Path("/usr/share/ovmf/OVMF.fd")
    )

    args = parser.parse_args()

    qemu_args: list[ArgType] = ["qemu-system-x86_64"]
    qemu_args.extend(["-enable-kvm"])
    qemu_args.extend(["-machine", "q35"])
    qemu_args.extend(["-cpu", "Skylake-Server-v4"])
    qemu_args.extend(["-m", "4096"])
    qemu_args.extend(["-serial", "vc"])  # ttyS0
    qemu_args.extend(["-serial", "null"])  # ttyS1
    qemu_args.extend(["-serial", "vc"])  # ttyS2
    qemu_args.extend(["-bios", args.bios])

    qemu_args.extend(
        net_args(
            id="eno2",
            mode="user",
            model="e1000e",  # should be igb
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
            hostfwd=("tcp::17463-:17463",),
        )
    )

    if args.netboot:
        netboot_path = pathlib.Path("netboot.iso")
        netboot_img = requests.get("https://boot.netboot.xyz/ipxe/netboot.xyz.iso")
        netboot_path.write_bytes(netboot_img.content)
        qemu_args.extend(["-cdrom", netboot_path])
    else:
        ipxe_path = args.ipxe.resolve(strict=True)
        ipxe_cfg_path = args.ipxe_cfg.resolve(strict=True)
        esp_path = pathlib.Path("uefi.img")
        esp_size = 64 * 1024 * 1024
        with esp_path.open(mode="wb") as fp:
            zero4k = b"\0" * 4096
            for _ in range(esp_size // len(zero4k)):
                fp.write(zero4k)
        call(["mkfs.vfat", esp_path, "-F", "32"])
        call(["mmd", "-i", esp_path, "::/EFI"])
        call(["mmd", "-i", esp_path, "::/EFI/BOOT"])
        call(["mcopy", "-i", esp_path, ipxe_path, "::/EFI/BOOT/BOOTX64.EFI"])
        call(["mcopy", "-i", esp_path, ipxe_cfg_path, "::/EFI/BOOT/IPXE.CFG"])
        qemu_args.extend(["-drive", combine_opts([f"file={esp_path}", "format=raw"])])

    print(qemu_args)
    os.execvp(qemu_args[0], qemu_args)


if __name__ == "__main__":
    main()
