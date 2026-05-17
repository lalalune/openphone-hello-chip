// SPDX-License-Identifier: GPL-2.0-only
/*
 * OpenPhone hello-DMA platform driver.
 *
 * Binds the openphone,hello-dma MMIO node and exports sysfs attributes:
 *   /sys/bus/platform/drivers/openphone-hello-dma/<dev>/contract
 *     - Multi-line string carrying every address from the platform contract
 *       so BSP smoke tools can validate without parsing the JSON.
 *   /sys/.../bytes_done, /sys/.../error_count
 *     - Live readback of the corresponding DMA RO counters.
 */

#include <linux/io.h>
#include <linux/module.h>
#include <linux/of.h>
#include <linux/platform_device.h>

#include "hello_platform_contract.h"

struct openphone_hello_dma {
	struct device *dev;
	void __iomem *regs;
};

static ssize_t contract_show(struct device *dev,
			     struct device_attribute *attr, char *buf)
{
	return sysfs_emit(buf,
		"contract_version=%u\n"
		"compatible=openphone,hello-dma\n"
		"HELLO_DMA_BASE=0x%08x\n"
		"HELLO_DMA_SRC_OFFSET=0x%02x\n"
		"HELLO_DMA_DST_OFFSET=0x%02x\n"
		"HELLO_DMA_LEN_OFFSET=0x%02x\n"
		"HELLO_DMA_CTRL_STATUS_OFFSET=0x%02x\n"
		"HELLO_DMA_BYTES_DONE_OFFSET=0x%02x\n"
		"HELLO_DMA_ERROR_COUNT_OFFSET=0x%02x\n",
		HELLO_CONTRACT_VERSION,
		HELLO_DMA_BASE,
		HELLO_DMA_SRC_OFFSET,
		HELLO_DMA_DST_OFFSET,
		HELLO_DMA_LEN_OFFSET,
		HELLO_DMA_CTRL_STATUS_OFFSET,
		HELLO_DMA_BYTES_DONE_OFFSET,
		HELLO_DMA_ERROR_COUNT_OFFSET);
}
static DEVICE_ATTR_RO(contract);

static ssize_t bytes_done_show(struct device *dev,
			       struct device_attribute *attr, char *buf)
{
	struct openphone_hello_dma *dma = dev_get_drvdata(dev);

	return sysfs_emit(buf, "0x%08x\n",
			  readl(dma->regs + HELLO_DMA_BYTES_DONE_OFFSET));
}
static DEVICE_ATTR_RO(bytes_done);

static ssize_t error_count_show(struct device *dev,
				struct device_attribute *attr, char *buf)
{
	struct openphone_hello_dma *dma = dev_get_drvdata(dev);

	return sysfs_emit(buf, "0x%08x\n",
			  readl(dma->regs + HELLO_DMA_ERROR_COUNT_OFFSET));
}
static DEVICE_ATTR_RO(error_count);

static struct attribute *openphone_hello_dma_attrs[] = {
	&dev_attr_contract.attr,
	&dev_attr_bytes_done.attr,
	&dev_attr_error_count.attr,
	NULL,
};
ATTRIBUTE_GROUPS(openphone_hello_dma);

static int openphone_hello_dma_probe(struct platform_device *pdev)
{
	struct openphone_hello_dma *dma;
	struct resource *res;
	int ret;

	dma = devm_kzalloc(&pdev->dev, sizeof(*dma), GFP_KERNEL);
	if (!dma)
		return -ENOMEM;

	res = platform_get_resource(pdev, IORESOURCE_MEM, 0);
	dma->regs = devm_ioremap_resource(&pdev->dev, res);
	if (IS_ERR(dma->regs))
		return PTR_ERR(dma->regs);

	dma->dev = &pdev->dev;
	platform_set_drvdata(pdev, dma);

	ret = sysfs_create_groups(&pdev->dev.kobj, openphone_hello_dma_groups);
	if (ret)
		return ret;

	dev_info(&pdev->dev,
		 "openphone-hello-dma: phys=0x%llx contract_v%u\n",
		 (u64)res->start, HELLO_CONTRACT_VERSION);
	return 0;
}

static int openphone_hello_dma_remove(struct platform_device *pdev)
{
	sysfs_remove_groups(&pdev->dev.kobj, openphone_hello_dma_groups);
	return 0;
}

static const struct of_device_id openphone_hello_dma_of_match[] = {
	{ .compatible = "openphone,hello-dma" },
	{ }
};
MODULE_DEVICE_TABLE(of, openphone_hello_dma_of_match);

static struct platform_driver openphone_hello_dma_driver = {
	.probe = openphone_hello_dma_probe,
	.remove = openphone_hello_dma_remove,
	.driver = {
		.name = "openphone-hello-dma",
		.of_match_table = openphone_hello_dma_of_match,
	},
};
module_platform_driver(openphone_hello_dma_driver);

MODULE_DESCRIPTION("OpenPhone hello DMA contract driver");
MODULE_AUTHOR("OpenPhone hello BSP");
MODULE_LICENSE("GPL");
