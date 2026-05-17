# Software BSP Evidence Capture

This directory is for external command transcripts only. Do not create hand-written
PASS logs. The repo-local gate rejects placeholder, failed, blocked, too-small,
or marker-incomplete files.

List every required artifact, current status, capture command, validation
command, and blocker:

```sh
python3 scripts/check_software_bsp.py status all
```

Generate exact capture commands by supplying the external checkout paths and
runtime command inputs. This prints commands only; it does not create evidence:

```sh
python3 scripts/check_software_bsp.py capture-plan all \
  --buildroot /abs/path/to/buildroot \
  --linux /abs/path/to/linux \
  --opensbi /abs/path/to/opensbi \
  --u-boot /abs/path/to/u-boot \
  --aosp /abs/path/to/aosp \
  --target-host root@TARGET \
  --opensbi-handoff-cmd '/exact/OpenSBI/fw_dynamic/boot/command' \
  --uboot-build-cmd '/exact/U-Boot/build/command' \
  --uboot-boot-cmd '/exact/OpenSBI/to/U-Boot/boot/command'
```

Run the fail-closed evidence gate after importing real external logs:

```sh
python3 scripts/check_software_bsp.py all --require-evidence
```

The legacy manifest-oriented view is still available as:

```sh
python3 scripts/check_software_bsp.py all --evidence-plan
```

## Buildroot

```sh
sw/buildroot/scripts/capture-buildroot-evidence.sh /path/to/buildroot defconfig
sw/buildroot/scripts/capture-buildroot-evidence.sh /path/to/buildroot image-manifest
HELLO_SMOKE_CMD='ssh root@TARGET /usr/bin/hello-mmio-smoke' \
  sw/buildroot/scripts/capture-buildroot-evidence.sh /path/to/buildroot smoke
python3 scripts/check_software_bsp.py buildroot --require-evidence
```

## Linux

```sh
sw/linux/scripts/capture-linux-bsp-evidence.sh /path/to/linux kernel-build
sw/linux/scripts/capture-linux-bsp-evidence.sh /path/to/linux dtb-check
HELLO_SMOKE_CMD='ssh root@TARGET /tmp/hello-mmio-smoke' \
  sw/linux/scripts/capture-linux-bsp-evidence.sh /path/to/linux smoke
python3 scripts/check_software_bsp.py linux --require-evidence
```

## OpenSBI

```sh
OPENPHONE_OPENSBI_CMD='make PLATFORM=generic FW_DYNAMIC=y' \
  sw/opensbi/capture-opensbi-evidence.sh /path/to/opensbi build
OPENPHONE_OPENSBI_HANDOFF_CMD='/path/to/qemu-or-renode boot command' \
  sw/opensbi/capture-opensbi-evidence.sh /path/to/opensbi handoff
python3 scripts/check_software_bsp.py opensbi --require-evidence
```

## U-Boot

```sh
OPENPHONE_UBOOT_CMD='make openphone_defconfig && make' \
  sw/u-boot/capture-u-boot-evidence.sh /path/to/u-boot build
OPENPHONE_UBOOT_BOOT_CMD='/path/to/qemu-or-renode boot command' \
  sw/u-boot/capture-u-boot-evidence.sh /path/to/u-boot boot-chain
python3 scripts/check_software_bsp.py u-boot --require-evidence
```

## AOSP

```sh
sw/aosp-device/capture-aosp-evidence.sh /path/to/aosp lunch
sw/aosp-device/capture-aosp-evidence.sh /path/to/aosp vendorimage
sw/aosp-device/capture-aosp-evidence.sh /path/to/aosp checkvintf
sw/aosp-device/capture-aosp-evidence.sh /path/to/aosp cuttlefish-boot
sw/aosp-device/capture-aosp-evidence.sh /path/to/aosp cts-subset
sw/aosp-device/capture-aosp-evidence.sh /path/to/aosp vts-subset
python3 scripts/check_software_bsp.py aosp --require-evidence
```

The Cuttlefish, CTS, and VTS logs are bounded virtual-device evidence only.
They do not prove hello_soc hardware boot, CDD compliance, GMS certification,
or full Android compatibility.
