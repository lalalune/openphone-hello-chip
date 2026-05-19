/* SPDX-License-Identifier: GPL-2.0-only WITH Linux-syscall-note */
#ifndef _UAPI_OPENAGENT_E1_NPU_H
#define _UAPI_OPENAGENT_E1_NPU_H

#include <linux/ioctl.h>
#include <linux/types.h>

/*
 * Userspace ABI for /dev/e1-npu. Keep ABI-stable: do not change field
 * order, sizes, or ioctl numbers without bumping the contract version in
 * sw/platform/e1_platform_contract.json.
 */
struct openagent_e1_npu_job {
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

struct openagent_e1_npu_contract {
	__u32 version;
	__u32 npu_base;
	__u32 window_bytes;
	__u32 unmapped_read_value;
};

#define OPENAGENT_E1_NPU_IOC_MAGIC 'N'
#define OPENAGENT_E1_NPU_IOC_SUBMIT \
	_IOWR(OPENAGENT_E1_NPU_IOC_MAGIC, 0x01, struct openagent_e1_npu_job)
#define OPENAGENT_E1_NPU_IOC_GET_CONTRACT \
	_IOR(OPENAGENT_E1_NPU_IOC_MAGIC, 0x02, struct openagent_e1_npu_contract)

#endif /* _UAPI_OPENAGENT_E1_NPU_H */
