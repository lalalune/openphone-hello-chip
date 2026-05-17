// SPDX-License-Identifier: GPL-2.0-only
/*
 * OpenPhone hello GPIO: minimal gpio-mmio driver.
 *
 * The peripheral_control region exposes a single 32-bit GPIO_OUT register at
 * HELLO_PERIPH_GPIO_OUT_OFFSET. This driver wraps that register with the
 * standard bgpio_init() helper so the kernel sees a real gpiochip with 32
 * output lines. Inputs are not implemented in hardware yet; reads return the
 * last written value.
 */

#include <linux/gpio/driver.h>
#include <linux/io.h>
#include <linux/module.h>
#include <linux/of.h>
#include <linux/platform_device.h>

#include "hello_platform_contract.h"

#define HELLO_GPIO_NGPIO 32

struct openphone_hello_gpio {
	struct gpio_chip gc;
	void __iomem *regs;
};

static int openphone_hello_gpio_probe(struct platform_device *pdev)
{
	struct openphone_hello_gpio *g;
	struct resource *res;
	void __iomem *gpio_out;
	int ret;

	g = devm_kzalloc(&pdev->dev, sizeof(*g), GFP_KERNEL);
	if (!g)
		return -ENOMEM;

	res = platform_get_resource(pdev, IORESOURCE_MEM, 0);
	g->regs = devm_ioremap_resource(&pdev->dev, res);
	if (IS_ERR(g->regs))
		return PTR_ERR(g->regs);

	gpio_out = g->regs + HELLO_PERIPH_GPIO_OUT_OFFSET;

	ret = bgpio_init(&g->gc, &pdev->dev, /* sz = */ 4,
			 /* dat   */ gpio_out,
			 /* set   */ gpio_out,
			 /* clr   */ NULL,
			 /* dirout*/ NULL,
			 /* dirin */ NULL,
			 /* flags */ BGPIOF_READ_OUTPUT_REG_SET);
	if (ret)
		return ret;

	g->gc.label = dev_name(&pdev->dev);
	g->gc.parent = &pdev->dev;
	g->gc.owner = THIS_MODULE;
	g->gc.ngpio = HELLO_GPIO_NGPIO;
	g->gc.base = -1;
	g->gc.of_node = pdev->dev.of_node;

	platform_set_drvdata(pdev, g);
	return devm_gpiochip_add_data(&pdev->dev, &g->gc, g);
}

static const struct of_device_id openphone_hello_gpio_of_match[] = {
	{ .compatible = "openphone,hello-gpio" },
	{ }
};
MODULE_DEVICE_TABLE(of, openphone_hello_gpio_of_match);

static struct platform_driver openphone_hello_gpio_driver = {
	.probe = openphone_hello_gpio_probe,
	.driver = {
		.name = "openphone-hello-gpio",
		.of_match_table = openphone_hello_gpio_of_match,
	},
};
module_platform_driver(openphone_hello_gpio_driver);

MODULE_DESCRIPTION("OpenPhone hello GPIO (gpio-mmio backed)");
MODULE_AUTHOR("OpenPhone hello BSP");
MODULE_LICENSE("GPL");
