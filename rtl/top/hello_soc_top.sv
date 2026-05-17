`timescale 1ns/1ps

module hello_soc_top (
    input  logic        clk,
    input  logic        rst_n,
    input  logic        mmio_valid,
    input  logic        mmio_write,
    input  logic [31:0] mmio_addr,
    input  logic [31:0] mmio_wdata,
    output logic [31:0] mmio_rdata,
    output logic        mmio_ready,
    output logic        irq_timer,
    output logic        irq_dma,
    output logic        irq_npu,
    output logic        irq_vsync,
    output logic [7:0]  gpio_out
);

    logic [31:0] bootrom_rdata;
    logic [31:0] dma_rdata;
    logic [31:0] npu_rdata;
    logic [31:0] display_rdata;
    logic [31:0] periph_rdata;
    logic dma_m_awvalid;
    logic [31:0] dma_m_awaddr;
    logic dma_m_wvalid;
    logic [31:0] dma_m_wdata;
    logic [3:0] dma_m_wstrb;
    logic dma_m_bready;
    logic dma_m_arvalid;
    logic [31:0] dma_m_araddr;
    logic dma_m_rready;
    logic display_scan_hsync;
    logic display_scan_vsync;
    logic display_scan_active;
    logic [15:0] display_scan_x;
    logic [15:0] display_scan_y;
    logic [31:0] display_scan_fb_addr;
    logic [23:0] display_scan_rgb;
    logic display_fb_read_valid;
    logic [31:0] display_fb_read_addr;

    logic bootrom_sel;
    logic dma_sel;
    logic npu_sel;
    logic display_sel;
    logic periph_sel;
    logic word_aligned;
    logic implemented_window;

    assign word_aligned       = mmio_addr[1:0] == 2'b00;
    assign implemented_window = mmio_addr[11:8] == 4'h0 && word_aligned;
    assign bootrom_sel = implemented_window && mmio_addr[31:12] == 20'h0000_0;
    assign periph_sel  = implemented_window && mmio_addr[31:12] == 20'h1000_0;
    assign dma_sel     = implemented_window && mmio_addr[31:12] == 20'h1001_0;
    assign npu_sel     = implemented_window && mmio_addr[31:12] == 20'h1002_0;
    assign display_sel = implemented_window && mmio_addr[31:12] == 20'h1003_0;

    /* verilator lint_off UNUSEDSIGNAL */
    logic unused_display_scanout;
    assign unused_display_scanout = ^{
        display_scan_hsync,
        display_scan_vsync,
        display_scan_active,
        display_scan_x,
        display_scan_y,
        display_scan_fb_addr,
        display_scan_rgb,
        display_fb_read_valid,
        display_fb_read_addr
    };
    /* verilator lint_on UNUSEDSIGNAL */

    /* verilator lint_off UNUSEDSIGNAL */
    logic unused_dma_write_payload;
    assign unused_dma_write_payload = ^{
        dma_m_awvalid,
        dma_m_awaddr,
        dma_m_wvalid,
        dma_m_wdata,
        dma_m_wstrb,
        dma_m_arvalid
    };
    /* verilator lint_on UNUSEDSIGNAL */

    hello_bootrom u_bootrom (
        .addr(mmio_addr[7:2]),
        .rdata(bootrom_rdata)
    );

    hello_peripherals u_peripherals (
        .clk(clk),
        .rst_n(rst_n),
        .valid(mmio_valid && periph_sel),
        .write(mmio_write),
        .addr(mmio_addr[7:2]),
        .wdata(mmio_wdata),
        .rdata(periph_rdata),
        .irq_timer(irq_timer),
        .gpio_out(gpio_out)
    );

    hello_dma u_dma (
        .clk(clk),
        .rst_n(rst_n),
        .valid(mmio_valid && dma_sel),
        .write(mmio_write),
        .addr(mmio_addr[7:2]),
        .wdata(mmio_wdata),
        .rdata(dma_rdata),
        .irq(irq_dma),
        .m_axil_awvalid(dma_m_awvalid),
        .m_axil_awready(1'b1),
        .m_axil_awaddr(dma_m_awaddr),
        .m_axil_wvalid(dma_m_wvalid),
        .m_axil_wready(1'b1),
        .m_axil_wdata(dma_m_wdata),
        .m_axil_wstrb(dma_m_wstrb),
        .m_axil_bvalid(dma_m_bready),
        .m_axil_bready(dma_m_bready),
        .m_axil_bresp(2'b00),
        .m_axil_arvalid(dma_m_arvalid),
        .m_axil_arready(1'b1),
        .m_axil_araddr(dma_m_araddr),
        .m_axil_rvalid(dma_m_rready),
        .m_axil_rready(dma_m_rready),
        .m_axil_rdata(dma_m_araddr ^ 32'hA5A5_0000),
        .m_axil_rresp(2'b00)
    );

    hello_npu u_npu (
        .clk(clk),
        .rst_n(rst_n),
        .valid(mmio_valid && npu_sel),
        .write(mmio_write),
        .addr(mmio_addr[7:2]),
        .wdata(mmio_wdata),
        .rdata(npu_rdata),
        .irq(irq_npu)
    );

    hello_display u_display (
        .clk(clk),
        .rst_n(rst_n),
        .valid(mmio_valid && display_sel),
        .write(mmio_write),
        .addr(mmio_addr[7:2]),
        .wdata(mmio_wdata),
        .rdata(display_rdata),
        .irq_vsync(irq_vsync),
        .scan_hsync(display_scan_hsync),
        .scan_vsync(display_scan_vsync),
        .scan_active(display_scan_active),
        .scan_x(display_scan_x),
        .scan_y(display_scan_y),
        .scan_fb_addr(display_scan_fb_addr),
        .scan_rgb(display_scan_rgb),
        .fb_read_valid(display_fb_read_valid),
        .fb_read_addr(display_fb_read_addr),
        .fb_read_data(32'h0),
        .fb_read_ready(1'b1)
    );

    always_comb begin
        mmio_ready = mmio_valid;
        unique case (1'b1)
            bootrom_sel:  mmio_rdata = bootrom_rdata;
            periph_sel:   mmio_rdata = periph_rdata;
            dma_sel:      mmio_rdata = dma_rdata;
            npu_sel:      mmio_rdata = npu_rdata;
            display_sel:  mmio_rdata = display_rdata;
            default:      mmio_rdata = 32'hDEAD_BEEF;
        endcase
    end

endmodule
