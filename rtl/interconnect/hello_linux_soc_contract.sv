`timescale 1ns/1ps

module hello_linux_soc_contract #(
    parameter int unsigned NUM_IRQ_SOURCES = 4
) (
    input  logic        clk,
    input  logic        rst_n,

    input  logic        cpu_awvalid,
    output logic        cpu_awready,
    input  logic [31:0] cpu_awaddr,
    input  logic        cpu_wvalid,
    output logic        cpu_wready,
    input  logic [31:0] cpu_wdata,
    input  logic [3:0]  cpu_wstrb,
    output logic        cpu_bvalid,
    input  logic        cpu_bready,
    output logic [1:0]  cpu_bresp,

    input  logic        cpu_arvalid,
    output logic        cpu_arready,
    input  logic [31:0] cpu_araddr,
    output logic        cpu_rvalid,
    input  logic        cpu_rready,
    output logic [31:0] cpu_rdata,
    output logic [1:0]  cpu_rresp,

    input  logic [NUM_IRQ_SOURCES-1:0] irq_sources,
    output logic                       cpu_external_irq,
    output logic [31:0]                irq_pending
);
    logic        dram_awvalid;
    logic        dram_awready;
    logic [31:0] dram_awaddr;
    logic        dram_wvalid;
    logic        dram_wready;
    logic [31:0] dram_wdata;
    logic [3:0]  dram_wstrb;
    logic        dram_bvalid;
    logic        dram_bready;
    logic [1:0]  dram_bresp;
    logic        dram_arvalid;
    logic        dram_arready;
    logic [31:0] dram_araddr;
    logic        dram_rvalid;
    logic        dram_rready;
    logic [31:0] dram_rdata;
    logic [1:0]  dram_rresp;

    logic        intc_awvalid;
    logic        intc_awready;
    logic [31:0] intc_awaddr;
    logic        intc_wvalid;
    logic        intc_wready;
    logic [31:0] intc_wdata;
    logic [3:0]  intc_wstrb;
    logic        intc_bvalid;
    logic        intc_bready;
    logic [1:0]  intc_bresp;
    logic        intc_arvalid;
    logic        intc_arready;
    logic [31:0] intc_araddr;
    logic        intc_rvalid;
    logic        intc_rready;
    logic [31:0] intc_rdata;
    logic [1:0]  intc_rresp;

    hello_axi_lite_interconnect u_interconnect (
        .clk(clk),
        .rst_n(rst_n),
        .m_axil_awvalid(cpu_awvalid),
        .m_axil_awready(cpu_awready),
        .m_axil_awaddr(cpu_awaddr),
        .m_axil_wvalid(cpu_wvalid),
        .m_axil_wready(cpu_wready),
        .m_axil_wdata(cpu_wdata),
        .m_axil_wstrb(cpu_wstrb),
        .m_axil_bvalid(cpu_bvalid),
        .m_axil_bready(cpu_bready),
        .m_axil_bresp(cpu_bresp),
        .m_axil_arvalid(cpu_arvalid),
        .m_axil_arready(cpu_arready),
        .m_axil_araddr(cpu_araddr),
        .m_axil_rvalid(cpu_rvalid),
        .m_axil_rready(cpu_rready),
        .m_axil_rdata(cpu_rdata),
        .m_axil_rresp(cpu_rresp),
        .dram_awvalid(dram_awvalid),
        .dram_awready(dram_awready),
        .dram_awaddr(dram_awaddr),
        .dram_wvalid(dram_wvalid),
        .dram_wready(dram_wready),
        .dram_wdata(dram_wdata),
        .dram_wstrb(dram_wstrb),
        .dram_bvalid(dram_bvalid),
        .dram_bready(dram_bready),
        .dram_bresp(dram_bresp),
        .dram_arvalid(dram_arvalid),
        .dram_arready(dram_arready),
        .dram_araddr(dram_araddr),
        .dram_rvalid(dram_rvalid),
        .dram_rready(dram_rready),
        .dram_rdata(dram_rdata),
        .dram_rresp(dram_rresp),
        .intc_awvalid(intc_awvalid),
        .intc_awready(intc_awready),
        .intc_awaddr(intc_awaddr),
        .intc_wvalid(intc_wvalid),
        .intc_wready(intc_wready),
        .intc_wdata(intc_wdata),
        .intc_wstrb(intc_wstrb),
        .intc_bvalid(intc_bvalid),
        .intc_bready(intc_bready),
        .intc_bresp(intc_bresp),
        .intc_arvalid(intc_arvalid),
        .intc_arready(intc_arready),
        .intc_araddr(intc_araddr),
        .intc_rvalid(intc_rvalid),
        .intc_rready(intc_rready),
        .intc_rdata(intc_rdata),
        .intc_rresp(intc_rresp)
    );

    hello_axi_lite_dram u_dram (
        .clk(clk),
        .rst_n(rst_n),
        .s_axil_awvalid(dram_awvalid),
        .s_axil_awready(dram_awready),
        .s_axil_awaddr(dram_awaddr),
        .s_axil_wvalid(dram_wvalid),
        .s_axil_wready(dram_wready),
        .s_axil_wdata(dram_wdata),
        .s_axil_wstrb(dram_wstrb),
        .s_axil_bvalid(dram_bvalid),
        .s_axil_bready(dram_bready),
        .s_axil_bresp(dram_bresp),
        .s_axil_arvalid(dram_arvalid),
        .s_axil_arready(dram_arready),
        .s_axil_araddr(dram_araddr),
        .s_axil_rvalid(dram_rvalid),
        .s_axil_rready(dram_rready),
        .s_axil_rdata(dram_rdata),
        .s_axil_rresp(dram_rresp)
    );

    hello_interrupt_controller #(
        .NUM_SOURCES(NUM_IRQ_SOURCES)
    ) u_interrupt_controller (
        .clk(clk),
        .rst_n(rst_n),
        .irq_sources(irq_sources),
        .cpu_external_irq(cpu_external_irq),
        .pending_status(irq_pending),
        .s_axil_awvalid(intc_awvalid),
        .s_axil_awready(intc_awready),
        .s_axil_awaddr(intc_awaddr),
        .s_axil_wvalid(intc_wvalid),
        .s_axil_wready(intc_wready),
        .s_axil_wdata(intc_wdata),
        .s_axil_wstrb(intc_wstrb),
        .s_axil_bvalid(intc_bvalid),
        .s_axil_bready(intc_bready),
        .s_axil_bresp(intc_bresp),
        .s_axil_arvalid(intc_arvalid),
        .s_axil_arready(intc_arready),
        .s_axil_araddr(intc_araddr),
        .s_axil_rvalid(intc_rvalid),
        .s_axil_rready(intc_rready),
        .s_axil_rdata(intc_rdata),
        .s_axil_rresp(intc_rresp)
    );

endmodule
