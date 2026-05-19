// SPDX-License-Identifier: BSD-2-Clause
/*
 * OpenSBI platform glue for the openagent e1_chip_cpu_variant.
 *
 * Single source of truth: sw/platform/e1_platform_contract.json
 *                         (section: e1_chip_cpu_variant)
 *
 *   UART (ns16550a) @ 0x10001000, IRQ 1, clock 50 MHz, baud 115200
 *   PLIC             @ 0x0C000000, 32 sources, 2 contexts (M + S, hart 0)
 *   CLINT            @ 0x02000000, timebase 10 MHz
 *   DRAM             @ 0x80000000, 256 MiB
 *
 * Reference: opensbi/platform/generic and opensbi/platform/template.
 * Copy this directory into <opensbi>/platform/openagent/ and build with:
 *   make PLATFORM=openagent FW_PAYLOAD_PATH=<path/to/Image>
 */

#include <sbi/riscv_asm.h>
#include <sbi/riscv_encoding.h>
#include <sbi/riscv_io.h>
#include <sbi/sbi_const.h>
#include <sbi/sbi_hart.h>
#include <sbi/sbi_platform.h>
#include <sbi_utils/fdt/fdt_helper.h>
#include <sbi_utils/ipi/aclint_mswi.h>
#include <sbi_utils/irqchip/plic.h>
#include <sbi_utils/serial/uart8250.h>
#include <sbi_utils/timer/aclint_mtimer.h>

/* --- Addresses from e1_platform_contract.json :: e1_chip_cpu_variant --- */
#define OPENAGENT_UART_ADDR        0x10001000UL
#define OPENAGENT_UART_FREQ        50000000U
#define OPENAGENT_UART_BAUD        115200U
#define OPENAGENT_UART_REG_SHIFT   0
#define OPENAGENT_UART_REG_WIDTH   1
#define OPENAGENT_UART_IRQ         1

#define OPENAGENT_PLIC_ADDR        0x0C000000UL
#define OPENAGENT_PLIC_NUM_SOURCES 32
#define OPENAGENT_PLIC_NUM_CONTEXTS 2

#define OPENAGENT_CLINT_ADDR       0x02000000UL
#define OPENAGENT_CLINT_SIZE       0x00010000UL
#define OPENAGENT_ACLINT_MTIMER_FREQ 10000000U

#define OPENAGENT_HART_COUNT       1
#define OPENAGENT_HART_STACK_SIZE  SBI_PLATFORM_DEFAULT_HART_STACK_SIZE

static struct plic_data plic = {
	.addr = OPENAGENT_PLIC_ADDR,
	.num_src = OPENAGENT_PLIC_NUM_SOURCES,
};

static struct aclint_mtimer_data mtimer = {
	.mtime_freq = OPENAGENT_ACLINT_MTIMER_FREQ,
	.mtime_addr = OPENAGENT_CLINT_ADDR + CLINT_MTIMER_OFFSET + ACLINT_DEFAULT_MTIME_OFFSET,
	.mtime_size = ACLINT_DEFAULT_MTIME_SIZE,
	.mtimecmp_addr = OPENAGENT_CLINT_ADDR + CLINT_MTIMER_OFFSET + ACLINT_DEFAULT_MTIMECMP_OFFSET,
	.mtimecmp_size = ACLINT_DEFAULT_MTIMECMP_SIZE,
	.first_hartid = 0,
	.hart_count = OPENAGENT_HART_COUNT,
	.has_64bit_mmio = TRUE,
};

static struct aclint_mswi_data mswi = {
	.addr = OPENAGENT_CLINT_ADDR + CLINT_MSWI_OFFSET,
	.size = ACLINT_MSWI_SIZE,
	.first_hartid = 0,
	.hart_count = OPENAGENT_HART_COUNT,
};

static int openagent_early_init(bool cold_boot)
{
	return 0;
}

static int openagent_final_init(bool cold_boot)
{
	return 0;
}

static int openagent_console_init(void)
{
	return uart8250_init(OPENAGENT_UART_ADDR,
			     OPENAGENT_UART_FREQ,
			     OPENAGENT_UART_BAUD,
			     OPENAGENT_UART_REG_SHIFT,
			     OPENAGENT_UART_REG_WIDTH,
			     0);
}

static int openagent_irqchip_init(bool cold_boot)
{
	int ret;

	if (cold_boot) {
		ret = plic_cold_irqchip_init(&plic);
		if (ret)
			return ret;
	}
	/* hart 0: M-mode context 0, S-mode context 1 */
	return plic_warm_irqchip_init(&plic, 0, 1);
}

static int openagent_ipi_init(bool cold_boot)
{
	int ret;

	if (cold_boot) {
		ret = aclint_mswi_cold_init(&mswi);
		if (ret)
			return ret;
	}
	return aclint_mswi_warm_init();
}

static int openagent_timer_init(bool cold_boot)
{
	int ret;

	if (cold_boot) {
		ret = aclint_mtimer_cold_init(&mtimer, NULL);
		if (ret)
			return ret;
	}
	return aclint_mtimer_warm_init();
}

const struct sbi_platform_operations platform_ops = {
	.early_init        = openagent_early_init,
	.final_init        = openagent_final_init,
	.console_init      = openagent_console_init,
	.irqchip_init      = openagent_irqchip_init,
	.ipi_init          = openagent_ipi_init,
	.timer_init        = openagent_timer_init,
};

const struct sbi_platform platform = {
	.opensbi_version   = OPENSBI_VERSION,
	.platform_version  = SBI_PLATFORM_VERSION(0x0, 0x01),
	.name              = "openagent-e1-cpu-variant",
	.features          = SBI_PLATFORM_DEFAULT_FEATURES,
	.hart_count        = OPENAGENT_HART_COUNT,
	.hart_stack_size   = OPENAGENT_HART_STACK_SIZE,
	.platform_ops_addr = (unsigned long)&platform_ops,
};
