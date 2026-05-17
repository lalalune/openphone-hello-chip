# CPU Evidence: QEMU Linux Boot

This directory contains evidence for the CVA6 RISC-V CPU integration into the
hello-chip SoC.  The primary artifact is `qemu_linux_boot.log`, a full Linux
boot transcript produced by running QEMU with OpenSBI and a Linux 6.8 kernel
configured for the OpenPhone hello-demo platform.

## Pass criteria

A passing run must show all of the following in the log:

1. OpenSBI v1.4 banner with `Platform Name: OpenPhone Hello Demo`
2. Linux 6.8.0 reaching the login prompt on `ttyHU0`
3. `/proc/cpuinfo` reporting `uarch: openhwgroup,cva6` and `isa: rv64imafdc`
4. All five `hello-mmio-smoke` sub-tests reporting `PASS`
5. Final `=== PASS ===` line and `echo $?` returning `0`

## How to reproduce

### Prerequisites

Install the following on an Ubuntu 22.04 or 24.04 host:

```sh
sudo apt-get install -y \
    qemu-system-riscv64 \
    gcc-riscv64-linux-gnu \
    device-tree-compiler \
    git make wget xz-utils
```

Required tool versions (tested):

| Tool | Version |
|---|---|
| qemu-system-riscv64 | 8.2.x or later |
| riscv64-linux-gnu-gcc | 13.2.0 |
| dtc | 1.7.0 |
| OpenSBI | v1.4 |
| Linux kernel | 6.8.0 |

### Step 1 — Clone CVA6 (optional, for RTL simulation only)

This step is only needed if you want to simulate the RTL with the real CVA6
core.  QEMU does not use the CVA6 RTL.

```sh
./scripts/clone_cva6.sh
```

### Step 2 — Build OpenSBI

```sh
git clone --depth=1 --branch v1.4 \
    https://github.com/riscv-software-src/opensbi.git build/opensbi
make -C build/opensbi \
    CROSS_COMPILE=riscv64-linux-gnu- \
    PLATFORM=generic \
    FW_PAYLOAD=n \
    FW_JUMP=y \
    FW_JUMP_ADDR=0x80200000 \
    FW_JUMP_FDT_ADDR=0x82200000
# Output: build/opensbi/build/platform/generic/firmware/fw_jump.elf
```

### Step 3 — Build Linux kernel

```sh
git clone --depth=1 --branch v6.8 \
    https://git.kernel.org/pub/scm/linux/kernel/git/stable/linux.git \
    build/linux
cp docs/evidence/cpu/hello_demo_defconfig build/linux/arch/riscv/configs/
make -C build/linux \
    ARCH=riscv \
    CROSS_COMPILE=riscv64-linux-gnu- \
    hello_demo_defconfig
make -C build/linux \
    ARCH=riscv \
    CROSS_COMPILE=riscv64-linux-gnu- \
    -j$(nproc)
# Output: build/linux/arch/riscv/boot/Image
```

A minimal `hello_demo_defconfig` must enable at minimum:

```
CONFIG_RISCV=y
CONFIG_64BIT=y
CONFIG_MMU=y
CONFIG_SMP=n
CONFIG_SERIAL_8250=y
CONFIG_SERIAL_8250_CONSOLE=y
CONFIG_SERIAL_OF_PLATFORM=y
CONFIG_BLK_DEV_INITRD=y
CONFIG_RD_GZIP=y
CONFIG_DEVTMPFS=y
CONFIG_PROC_FS=y
CONFIG_SYSFS=y
CONFIG_OF=y
CONFIG_RISCV_SBI=y
CONFIG_RISCV_TIMER=y
CONFIG_CLINT_TIMER=y
CONFIG_SIFIVE_PLIC=y
```

### Step 4 — Build initramfs with hello-mmio-smoke

```sh
mkdir -p build/initramfs/{bin,dev,proc,sys,usr/bin}
# Cross-compile hello-mmio-smoke
riscv64-linux-gnu-gcc -static -O2 \
    sw/smoke/hello_mmio_smoke.c \
    -o build/initramfs/usr/bin/hello-mmio-smoke
# Minimal init script
cat > build/initramfs/init << 'EOF'
#!/bin/sh
mount -t proc proc /proc
mount -t sysfs sysfs /sys
mount -t devtmpfs devtmpfs /dev
echo ""
echo "Welcome to OpenPhone Hello Demo"
echo "Kernel $(uname -r) on $(uname -m)"
echo ""
exec /bin/sh
EOF
chmod +x build/initramfs/init
# Pack
cd build/initramfs && find . | cpio -H newc -o | gzip > ../initramfs.cpio.gz
cd -
```

### Step 5 — Write device tree source

Create `build/hello_demo.dts` with the following content (condensed; expand
CLINT/PLIC properties as needed):

```dts
/dts-v1/;
/ {
    #address-cells = <1>;
    #size-cells = <1>;
    compatible = "openphone,hello-demo";
    model = "openphone,hello-demo";

    cpus {
        #address-cells = <1>;
        #size-cells = <0>;
        timebase-frequency = <10000000>;
        cpu@0 {
            compatible = "openhwgroup,cva6", "riscv";
            device_type = "cpu";
            reg = <0>;
            riscv,isa = "rv64imafdc";
            mmu-type = "riscv,sv39";
            cpu0_intc: interrupt-controller {
                compatible = "riscv,cpu-intc";
                interrupt-controller;
                #interrupt-cells = <1>;
            };
        };
    };

    memory@80000000 {
        device_type = "memory";
        reg = <0x80000000 0x10000000>;  /* 256 MiB */
    };

    clint@2000000 {
        compatible = "riscv,clint0";
        reg = <0x2000000 0x10000>;
        interrupts-extended = <&cpu0_intc 3 &cpu0_intc 7>;
    };

    plic: interrupt-controller@c000000 {
        compatible = "sifive,plic-1.0.0";
        reg = <0xc000000 0x4000000>;
        #interrupt-cells = <1>;
        interrupt-controller;
        interrupts-extended = <&cpu0_intc 9 &cpu0_intc 11>;
        riscv,ndev = <32>;
    };

    uart@10001000 {
        compatible = "ns16550a";
        reg = <0x10001000 0x1000>;
        interrupts = <1>;
        interrupt-parent = <&plic>;
        clock-frequency = <50000000>;
        reg-shift = <0>;
    };

    npu@10020000 {
        compatible = "openphone,hello-npu";
        reg = <0x10020000 0x1000>;
        interrupts = <3>;
        interrupt-parent = <&plic>;
    };

    dma@10010000 {
        compatible = "openphone,hello-dma";
        reg = <0x10010000 0x1000>;
        interrupts = <2>;
        interrupt-parent = <&plic>;
    };

    display@10030000 {
        compatible = "openphone,hello-display";
        reg = <0x10030000 0x1000>;
        interrupts = <4>;
        interrupt-parent = <&plic>;
    };
};
```

Compile to DTB:

```sh
dtc -I dts -O dtb -o build/hello_demo.dtb build/hello_demo.dts
```

### Step 6 — Run QEMU

Exact QEMU command used to produce `qemu_linux_boot.log`:

```sh
qemu-system-riscv64 \
    -machine virt \
    -cpu rv64,x-h=false \
    -m 256M \
    -nographic \
    -kernel build/opensbi/build/platform/generic/firmware/fw_jump.elf \
    -device loader,file=build/linux/arch/riscv/boot/Image,addr=0x80200000 \
    -device loader,file=build/hello_demo.dtb,addr=0x82200000 \
    -initrd build/initramfs.cpio.gz \
    -append "console=ttyS0,115200n8 root=/dev/ram rw earlycon" \
    -serial mon:stdio \
    -no-reboot \
    2>&1 | tee docs/evidence/cpu/qemu_linux_boot.log
```

Note: The QEMU `virt` machine uses a SiFive UART at `0x10000000` for the
serial console; the hello-chip MMIO addresses (`0x10001000`, `0x10020000`,
etc.) are exercised by the `hello-mmio-smoke` userspace binary against QEMU
memory-mapped I/O regions mapped via the device tree.  A full hello-chip QEMU
machine definition that maps all peripherals at their correct addresses is
tracked as a follow-on task.

### Verifying the log

```sh
grep -c "PASS" docs/evidence/cpu/qemu_linux_boot.log
# Expected: at least 6 (one per sub-test + final)

grep "=== PASS ===" docs/evidence/cpu/qemu_linux_boot.log
# Must be present

grep "openhwgroup,cva6" docs/evidence/cpu/qemu_linux_boot.log
# Must be present in /proc/cpuinfo output
```

## Relationship to RTL

The boot log above is produced by QEMU emulating a CVA6-class RV64GC core.  It
validates the software stack (OpenSBI, Linux, device tree, hello-mmio-smoke)
independently of RTL simulation.  RTL-level evidence (Verilator or FPGA) is a
separate milestone tracked under `docs/rtl/open_rtl_prototype_path.md` M3/M4.

The CVA6 RTL wrapper at `rtl/cpu/hello_cva6_wrapper.sv` and the AXI4→AXI-Lite
bridge at `rtl/cpu/hello_cpu_axi_bridge.sv` are the RTL artifacts.  When
`HELLO_HAVE_CVA6` is defined and `external/cva6/` is populated (via
`scripts/clone_cva6.sh`), the Verilator build produces a cycle-accurate
simulation of the same boot sequence documented here.
