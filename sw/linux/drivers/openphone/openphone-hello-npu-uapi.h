/* SPDX-License-Identifier: GPL-2.0-only WITH Linux-syscall-note */
#ifndef _UAPI_OPENPHONE_HELLO_NPU_H
#define _UAPI_OPENPHONE_HELLO_NPU_H

#include <linux/ioctl.h>
#include <linux/types.h>

/*
 * Userspace ABI for /dev/hello-npu. Keep ABI-stable: do not change field
 * order, sizes, or ioctl numbers without bumping the contract version in
 * sw/platform/hello_platform_contract.json.
 */
struct openphone_hello_npu_job {
	__u32 op_a;
	__u32 op_b;
	__u32 opcode;
	__u32 result;
	__u32 result_hi;
	__u32 ctrl_status;
	__u32 perf_cycles;
	__u32 perf_macs;
	__u32 perf_errors;
	__u32 _reserved;
};

struct openphone_hello_npu_contract {
	__u32 version;
	__u32 npu_base;
	__u32 window_bytes;
	__u32 unmapped_read_value;
};

#define OPENPHONE_HELLO_NPU_IOC_MAGIC 'N'
#define OPENPHONE_HELLO_NPU_IOC_SUBMIT \
	_IOWR(OPENPHONE_HELLO_NPU_IOC_MAGIC, 0x01, struct openphone_hello_npu_job)
#define OPENPHONE_HELLO_NPU_IOC_GET_CONTRACT \
	_IOR(OPENPHONE_HELLO_NPU_IOC_MAGIC, 0x02, struct openphone_hello_npu_contract)

#endif /* _UAPI_OPENPHONE_HELLO_NPU_H */
