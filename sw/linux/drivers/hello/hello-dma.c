// SPDX-License-Identifier: GPL-2.0-only
/*
 * Minimal OpenPhone hello DMA Linux driver source.
 *
 * The register layout mirrors sw/platform/hello_platform_contract.json and is
 * intended for an external Linux tree integration.
 */

#include <linux/io.h>
#include <linux/module.h>
#include <linux/of.h>
#include <linux/platform_device.h>

#define HELLO_DMA_BASE 0x10010000u
#define HELLO_DMA_SRC_OFFSET 0x00u
#define HELLO_DMA_DST_OFFSET 0x04u
#define HELLO_DMA_LEN_OFFSET 0x08u
#define HELLO_DMA_CTRL_STATUS_OFFSET 0x0cu

struct hello_dma {
	void __iomem *regs;
};

static ssize_t contract_show(struct device *dev, struct device_attribute *attr, char *buf)
{
	return sysfs_emit(buf, "HELLO_DMA_BASE=0x%08x compatible=openphone,hello-dma\n",
			 HELLO_DMA_BASE);
}
static DEVICE_ATTR_RO(contract);

static int hello_dma_probe(struct platform_device *pdev)
{
	struct hello_dma *dma;
	struct resource *res;

	dma = devm_kzalloc(&pdev->dev, sizeof(*dma), GFP_KERNEL);
	if (!dma)
		return -ENOMEM;

	res = platform_get_resource(pdev, IORESOURCE_MEM, 0);
	dma->regs = devm_ioremap_resource(&pdev->dev, res);
	if (IS_ERR(dma->regs))
		return PTR_ERR(dma->regs);

	platform_set_drvdata(pdev, dma);
	return device_create_file(&pdev->dev, &dev_attr_contract);
}

static int hello_dma_remove(struct platform_device *pdev)
{
	device_remove_file(&pdev->dev, &dev_attr_contract);
	return 0;
}

static const struct of_device_id hello_dma_of_match[] = {
	{ .compatible = "openphone,hello-dma" },
	{ }
};
MODULE_DEVICE_TABLE(of, hello_dma_of_match);

static struct platform_driver hello_dma_driver = {
	.probe = hello_dma_probe,
	.remove = hello_dma_remove,
	.driver = {
		.name = "openphone-hello-dma",
		.of_match_table = hello_dma_of_match,
	},
};
module_platform_driver(hello_dma_driver);

MODULE_DESCRIPTION("OpenPhone hello DMA contract driver");
MODULE_LICENSE("GPL");
