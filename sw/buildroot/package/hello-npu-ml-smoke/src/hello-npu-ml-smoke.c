// SPDX-License-Identifier: GPL-2.0-only
/*
 * hello-npu-ml-smoke: target-side /dev/hello-npu smoke for Buildroot.
 *
 * This proves only that the built rootfs can execute a tiny userspace program
 * against the Linux hello-NPU ioctl ABI. It is not NNAPI, Android, model, or
 * performance evidence.
 */

#include <errno.h>
#include <fcntl.h>
#include <linux/ioctl.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <sys/ioctl.h>
#include <unistd.h>

struct openphone_hello_npu_job {
	uint32_t op_a;
	uint32_t op_b;
	uint32_t opcode;
	uint32_t result;
	uint32_t result_hi;
	uint32_t ctrl_status;
	uint32_t perf_cycles;
	uint32_t perf_macs;
	uint32_t perf_errors;
	uint32_t reserved;
};

struct openphone_hello_npu_contract {
	uint32_t version;
	uint32_t npu_base;
	uint32_t window_bytes;
	uint32_t unmapped_read_value;
};

#define OPENPHONE_HELLO_NPU_IOC_MAGIC 'N'
#define OPENPHONE_HELLO_NPU_IOC_SUBMIT \
	_IOWR(OPENPHONE_HELLO_NPU_IOC_MAGIC, 0x01, struct openphone_hello_npu_job)
#define OPENPHONE_HELLO_NPU_IOC_GET_CONTRACT \
	_IOR(OPENPHONE_HELLO_NPU_IOC_MAGIC, 0x02, struct openphone_hello_npu_contract)

#define HELLO_NPU_OPCODE_GEMM_S8 8u

int main(int argc, char **argv)
{
	const char *device = "/dev/hello-npu";
	struct openphone_hello_npu_contract contract = {0};
	struct openphone_hello_npu_job job = {
		.op_a = 0,
		.op_b = 0,
		.opcode = HELLO_NPU_OPCODE_GEMM_S8,
	};
	int fd;

	if (argc == 3 && strcmp(argv[1], "--device") == 0)
		device = argv[2];
	else if (argc != 1) {
		fprintf(stderr, "usage: %s [--device /dev/hello-npu]\n", argv[0]);
		return 2;
	}

	fd = open(device, O_RDWR | O_CLOEXEC);
	if (fd < 0) {
		fprintf(stderr, "hello-npu-ml-smoke: FAIL open %s: %s\n",
			device, strerror(errno));
		return 2;
	}

	if (ioctl(fd, OPENPHONE_HELLO_NPU_IOC_GET_CONTRACT, &contract) != 0) {
		fprintf(stderr, "hello-npu-ml-smoke: FAIL get-contract: %s\n",
			strerror(errno));
		close(fd);
		return 3;
	}

	if (ioctl(fd, OPENPHONE_HELLO_NPU_IOC_SUBMIT, &job) != 0) {
		fprintf(stderr, "hello-npu-ml-smoke: FAIL submit GEMM_S8: %s\n",
			strerror(errno));
		close(fd);
		return 4;
	}

	close(fd);

	if (job.perf_errors != 0) {
		fprintf(stderr,
			"hello-npu-ml-smoke: FAIL workload=gemm_s8_int8_2x2x3 errors=%u\n",
			job.perf_errors);
		return 5;
	}

	printf("hello-npu-ml-smoke: PASS workload=gemm_s8_int8_2x2x3 "
	       "device=%s contract_version=%u npu_base=0x%08x result=0x%08x "
	       "cycles=%u macs=%u errors=%u "
	       "claim_boundary=driver_ioctl_gemm_only_not_nnapi_or_hardware_benchmark\n",
	       device, contract.version, contract.npu_base, job.result,
	       job.perf_cycles, job.perf_macs, job.perf_errors);
	return 0;
}
