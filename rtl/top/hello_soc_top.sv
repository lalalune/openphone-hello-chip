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
        .irq(irq_dma)
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
        .irq_vsync(irq_vsync)
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
