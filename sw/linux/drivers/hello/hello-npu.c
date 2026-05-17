// SPDX-License-Identifier: GPL-2.0-only
/*
 * Minimal OpenPhone hello NPU Linux driver source.
 *
 * Import this file into an external Linux tree before building. The checked-in
 * repository only owns the platform contract and BSP source scaffold.
 */

#include <linux/fs.h>
#include <linux/io.h>
#include <linux/miscdevice.h>
#include <linux/module.h>
#include <linux/of.h>
#include <linux/of_address.h>
#include <linux/platform_device.h>

#include "hello_platform_contract.h"

struct hello_npu {
	void __iomem *regs;
	struct miscdevice miscdev;
};

static ssize_t hello_npu_read(struct file *file, char __user *buf, size_t len, loff_t *ppos)
{
	struct hello_npu *npu = container_of(file->private_data, struct hello_npu, miscdev);
	u32 value = readl(npu->regs + HELLO_NPU_RESULT_OFFSET);
	char tmp[16];
	int n = scnprintf(tmp, sizeof(tmp), "0x%08x\n", value);

	return simple_read_from_buffer(buf, len, ppos, tmp, n);
}

static const struct file_operations hello_npu_fops = {
	.owner = THIS_MODULE,
	.read = hello_npu_read,
	.llseek = no_llseek,
};

static int hello_npu_probe(struct platform_device *pdev)
{
	struct hello_npu *npu;
	struct resource *res;

	npu = devm_kzalloc(&pdev->dev, sizeof(*npu), GFP_KERNEL);
	if (!npu)
		return -ENOMEM;

	res = platform_get_resource(pdev, IORESOURCE_MEM, 0);
	npu->regs = devm_ioremap_resource(&pdev->dev, res);
	if (IS_ERR(npu->regs))
		return PTR_ERR(npu->regs);

	npu->miscdev.minor = MISC_DYNAMIC_MINOR;
	npu->miscdev.name = "hello-npu";
	npu->miscdev.fops = &hello_npu_fops;
	npu->miscdev.parent = &pdev->dev;
	platform_set_drvdata(pdev, npu);

	return misc_register(&npu->miscdev);
}

static int hello_npu_remove(struct platform_device *pdev)
{
	struct hello_npu *npu = platform_get_drvdata(pdev);

	misc_deregister(&npu->miscdev);
	return 0;
}

static const struct of_device_id hello_npu_of_match[] = {
	{ .compatible = "openphone,hello-npu" },
	{ }
};
MODULE_DEVICE_TABLE(of, hello_npu_of_match);

static struct platform_driver hello_npu_driver = {
	.probe = hello_npu_probe,
	.remove = hello_npu_remove,
	.driver = {
		.name = "openphone-hello-npu",
		.of_match_table = hello_npu_of_match,
	},
};
module_platform_driver(hello_npu_driver);

MODULE_DESCRIPTION("OpenPhone hello NPU contract driver");
MODULE_LICENSE("GPL");
