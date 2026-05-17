# Base image pinned by digest for reproducibility.
# TODO(toolchain-ci): refresh digest with
#   docker manifest inspect --verbose ubuntu:24.04 | jq -r '.Descriptor.digest // .manifests[0].digest'
# and replace the placeholder below. Until then we tag-pin to ubuntu:24.04 and
# record the expected digest in docs/toolchain/reproducibility.md.
ARG UBUNTU_DIGEST=sha256:TODO_PIN_UBUNTU_24_04_DIGEST
FROM ubuntu:24.04@${UBUNTU_DIGEST}

ENV DEBIAN_FRONTEND=noninteractive

# Capture an apt manifest archive so the exact resolved package set for this
# image build is reproducible from a single artifact. The archive is consumed
# by scripts/record_tool_versions.sh and docs/toolchain/reproducibility.md.
RUN set -eux; \
    mkdir -p /var/log/apt-manifest; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
        build-essential ca-certificates curl git make cmake ninja-build \
        python3 python3-dev python3-pip python3-venv \
        verilator yosys iverilog gtkwave qemu-system-misc \
        gcc-riscv64-unknown-elf z3; \
    dpkg-query -W -f='${Package}\t${Version}\t${Architecture}\n' \
        > /var/log/apt-manifest/installed-packages.tsv; \
    apt-cache policy > /var/log/apt-manifest/apt-policy.txt 2>&1 || true; \
    cp /etc/apt/sources.list /var/log/apt-manifest/sources.list 2>/dev/null || true; \
    if [ -d /etc/apt/sources.list.d ]; then \
        tar -C /etc/apt -cf /var/log/apt-manifest/sources.list.d.tar sources.list.d 2>/dev/null || true; \
    fi; \
    rm -rf /var/lib/apt/lists/*

RUN python3 -m venv /opt/openphone-venv
ENV PATH="/opt/openphone-venv/bin:${PATH}"
COPY requirements.txt /tmp/requirements.txt
RUN pip install --upgrade pip && pip install -r /tmp/requirements.txt

WORKDIR /work
