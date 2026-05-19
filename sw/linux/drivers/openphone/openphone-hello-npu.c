// SPDX-License-Identifier: GPL-2.0-only
/*
 * OpenPhone hello-NPU character driver.
 *
 * /dev/hello-npu supports:
 *   - read():  ASCII "0x%08x\n" of NPU RESULT
 *   - ioctl(): submit OP_A/OP_B/OPCODE, read back result + perf counters
 *   - mmap():  map the 4 KiB MMIO window (root only) for direct register access
 *
 * Offsets come from hello_platform_contract.h. Base address comes from the
 * DT `reg` of the `openphone,hello-npu` node.
 */

#include <linux/fs.h>
#include <linux/io.h>
#include <linux/miscdevice.h>
#include <linux/mm.h>
#include <linux/module.h>
#include <linux/mutex.h>
#include <linux/of.h>
#include <linux/of_address.h>
#include <linux/platform_device.h>
#include <linux/uaccess.h>

#include "hello_platform_contract.h"
#include "openphone-hello-npu-uapi.h"

struct openphone_hello_npu {
	struct device *dev;
	void __iomem *regs;
	phys_addr_t phys_base;
	resource_size_t size;
	struct miscdevice miscdev;
	struct mutex lock;
};

static inline struct openphone_hello_npu *miscdev_to_npu(struct file *file)
{
	return container_of(file->private_data, struct openphone_hello_npu,
			    miscdev);
}

static ssize_t openphone_hello_npu_read(struct file *file, char __user *buf,
					size_t len, loff_t *ppos)
{
	struct openphone_hello_npu *npu = miscdev_to_npu(file);
	char tmp[16];
	u32 value;
	int n;

	value = readl(npu->regs + HELLO_NPU_RESULT_OFFSET);
	n = scnprintf(tmp, sizeof(tmp), "0x%08x\n", value);
	return simple_read_from_buffer(buf, len, ppos, tmp, n);
}

static long openphone_hello_npu_submit(struct openphone_hello_npu *npu,
				       void __user *argp)
{
	struct openphone_hello_npu_job job;

	if (copy_from_user(&job, argp, sizeof(job)))
		return -EFAULT;

	mutex_lock(&npu->lock);
	writel(job.op_a, npu->regs + HELLO_NPU_OP_A_OFFSET);
	writel(job.op_b, npu->regs + HELLO_NPU_OP_B_OFFSET);
	writel(job.opcode, npu->regs + HELLO_NPU_OPCODE_OFFSET);
	writel(0x1u, npu->regs + HELLO_NPU_CTRL_STATUS_OFFSET);

	job.result = readl(npu->regs + HELLO_NPU_RESULT_OFFSET);
	job.result_hi = readl(npu->regs + HELLO_NPU_RESULT_HI_OFFSET);
	job.ctrl_status = readl(npu->regs + HELLO_NPU_CTRL_STATUS_OFFSET);
	job.perf_cycles = readl(npu->regs + HELLO_NPU_PERF_CYCLES_OFFSET);
	job.perf_macs = readl(npu->regs + HELLO_NPU_PERF_MACS_OFFSET);
	job.perf_errors = readl(npu->regs + HELLO_NPU_PERF_ERRORS_OFFSET);
	mutex_unlock(&npu->lock);

	if (copy_to_user(argp, &job, sizeof(job)))
		return -EFAULT;
	return 0;
}

static long openphone_hello_npu_ioctl(struct file *file, unsigned int cmd,
				      unsigned long arg)
{
	struct openphone_hello_npu *npu = miscdev_to_npu(file);
	void __user *argp = (void __user *)arg;

	switch (cmd) {
	case OPENPHONE_HELLO_NPU_IOC_SUBMIT:
		return openphone_hello_npu_submit(npu, argp);
	case OPENPHONE_HELLO_NPU_IOC_GET_CONTRACT: {
		struct openphone_hello_npu_contract c = {
			.version = HELLO_CONTRACT_VERSION,
			.npu_base = HELLO_NPU_BASE,
			.window_bytes = HELLO_IMPLEMENTED_WINDOW_BYTES,
			.unmapped_read_value = HELLO_UNMAPPED_READ_VALUE,
		};
		return copy_to_user(argp, &c, sizeof(c)) ? -EFAULT : 0;
	}
	default:
		return -ENOTTY;
	}
}

static int openphone_hello_npu_mmap(struct file *file,
				    struct vm_area_struct *vma)
{
	struct openphone_hello_npu *npu = miscdev_to_npu(file);
	unsigned long size = vma->vm_end - vma->vm_start;

	if (!capable(CAP_SYS_RAWIO))
		return -EPERM;
	if (vma->vm_pgoff != 0)
		return -EINVAL;
	if (size > npu->size)
		return -EINVAL;

	vma->vm_page_prot = pgprot_noncached(vma->vm_page_prot);
	return io_remap_pfn_range(vma, vma->vm_start,
				  npu->phys_base >> PAGE_SHIFT,
				  size, vma->vm_page_prot);
}

static const struct file_operations openphone_hello_npu_fops = {
	.owner = THIS_MODULE,
	.read = openphone_hello_npu_read,
	.unlocked_ioctl = openphone_hello_npu_ioctl,
	.compat_ioctl = openphone_hello_npu_ioctl,
	.mmap = openphone_hello_npu_mmap,
	.llseek = no_llseek,
};

static int openphone_hello_npu_probe(struct platform_device *pdev)
{
	struct openphone_hello_npu *npu;
	struct resource *res;

	npu = devm_kzalloc(&pdev->dev, sizeof(*npu), GFP_KERNEL);
	if (!npu)
		return -ENOMEM;

	res = platform_get_resource(pdev, IORESOURCE_MEM, 0);
	if (!res)
		return -EINVAL;

	npu->dev = &pdev->dev;
	npu->phys_base = res->start;
	npu->size = resource_size(res);
	npu->regs = devm_ioremap_resource(&pdev->dev, res);
	if (IS_ERR(npu->regs))
		return PTR_ERR(npu->regs);

	mutex_init(&npu->lock);

	npu->miscdev.minor = MISC_DYNAMIC_MINOR;
	npu->miscdev.name = "hello-npu";
	npu->miscdev.fops = &openphone_hello_npu_fops;
	npu->miscdev.parent = &pdev->dev;
	platform_set_drvdata(pdev, npu);

	dev_info(&pdev->dev,
		 "openphone-hello-npu: phys=0x%llx size=0x%llx contract_v%u\n",
		 (u64)npu->phys_base, (u64)npu->size,
		 HELLO_CONTRACT_VERSION);

	return misc_register(&npu->miscdev);
}

static int openphone_hello_npu_remove(struct platform_device *pdev)
{
	struct openphone_hello_npu *npu = platform_get_drvdata(pdev);

	misc_deregister(&npu->miscdev);
	return 0;
}

static const struct of_device_id openphone_hello_npu_of_match[] = {
	{ .compatible = "openphone,hello-npu" },
	{ }
};
MODULE_DEVICE_TABLE(of, openphone_hello_npu_of_match);

static struct platform_driver openphone_hello_npu_driver = {
	.probe = openphone_hello_npu_probe,
	.remove = openphone_hello_npu_remove,
	.driver = {
		.name = "openphone-hello-npu",
		.of_match_table = openphone_hello_npu_of_match,
	},
};
module_platform_driver(openphone_hello_npu_driver);

MODULE_DESCRIPTION("OpenPhone hello NPU character driver");
MODULE_AUTHOR("OpenPhone hello BSP");
MODULE_LICENSE("GPL");
