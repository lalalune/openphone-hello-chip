// SPDX-License-Identifier: MIT
/*
 * User-space smoke source for an external Linux build.
 *
 * This probes the public BSP surface created by openphone,hello-npu,
 * openphone,hello-dma, and openphone,hello-display device tree nodes.
 */

#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>

#define HELLO_DMA_BASE 0x10010000u
#define HELLO_NPU_BASE 0x10020000u
#define HELLO_DISPLAY_BASE 0x10030000u

static int require_path(const char *path)
{
	int fd = open(path, O_RDONLY | O_CLOEXEC);

	if (fd < 0) {
		fprintf(stderr, "%s: %s\n", path, strerror(errno));
		return 1;
	}

	close(fd);
	return 0;
}

int main(void)
{
	int failed = 0;

	printf("HELLO_DMA_BASE=0x%08x\n", HELLO_DMA_BASE);
	printf("HELLO_NPU_BASE=0x%08x\n", HELLO_NPU_BASE);
	printf("HELLO_DISPLAY_BASE=0x%08x\n", HELLO_DISPLAY_BASE);
	failed |= require_path("/dev/hello-npu");
	failed |= require_path("/sys/bus/platform/drivers/openphone-hello-dma");

	return failed;
}
