FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential ca-certificates curl git make cmake ninja-build python3 python3-dev python3-pip python3-venv \
    verilator yosys iverilog gtkwave qemu-system-misc gcc-riscv64-unknown-elf z3 \
    && rm -rf /var/lib/apt/lists/*

RUN python3 -m venv /opt/openphone-venv
ENV PATH="/opt/openphone-venv/bin:${PATH}"
COPY requirements.txt /tmp/requirements.txt
RUN pip install --upgrade pip && pip install -r /tmp/requirements.txt

WORKDIR /work
