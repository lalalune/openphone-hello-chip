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
    logic dma_m_awready;
    logic [31:0] dma_m_awaddr;
    logic dma_m_wvalid;
    logic dma_m_wready;
    logic [31:0] dma_m_wdata;
    logic [3:0] dma_m_wstrb;
    logic dma_m_bvalid;
    logic dma_m_bready;
    logic [1:0] dma_m_bresp;
    logic dma_m_arvalid;
    logic dma_m_arready;
    logic [31:0] dma_m_araddr;
    logic dma_m_rvalid;
    logic dma_m_rready;
    logic [31:0] dma_m_rdata;
    logic [1:0] dma_m_rresp;
    logic display_scan_hsync;
    logic display_scan_vsync;
    logic display_scan_active;
    logic [15:0] display_scan_x;
    logic [15:0] display_scan_y;
    logic [31:0] display_scan_fb_addr;
    logic [23:0] display_scan_rgb;
    logic display_fb_read_valid;
    logic [31:0] display_fb_read_addr;
    logic [31:0] display_fb_read_data;
    logic        display_fb_read_ready;

    logic bootrom_sel;
    logic dma_sel;
    logic npu_sel;
    logic display_sel;
    logic periph_sel;
    logic dram_sel;
    logic word_aligned;
    logic implemented_window;
    logic [31:0] dram_mem [0:1023];

    wire [9:0]  mmio_dram_word = mmio_addr[11:2];
    wire [9:0]  dma_wr_word = dma_m_awaddr[11:2];
    wire [9:0]  dma_rd_word = dma_m_araddr[11:2];
    wire [9:0]  display_rd_word = display_fb_read_addr[11:2];
    wire        dma_wr_fire = dma_m_awvalid && dma_m_awready && dma_m_wvalid && dma_m_wready;
    wire        dma_rd_fire = dma_m_arvalid && dma_m_arready;
    wire        dma_wr_ok = (dma_m_awaddr[31:12] == 20'h8000_0) && (dma_m_awaddr[1:0] == 2'b00);
    wire        dma_rd_ok = (dma_m_araddr[31:12] == 20'h8000_0) && (dma_m_araddr[1:0] == 2'b00);
    wire        display_rd_ok = display_fb_read_valid &&
                                (display_fb_read_addr[31:12] == 20'h8000_0) &&
                                (display_fb_read_addr[1:0] == 2'b00);

    assign word_aligned       = mmio_addr[1:0] == 2'b00;
    assign implemented_window = mmio_addr[11:8] == 4'h0 && word_aligned;
    assign bootrom_sel = implemented_window && mmio_addr[31:12] == 20'h0000_0;
    assign periph_sel  = implemented_window && mmio_addr[31:12] == 20'h1000_0;
    assign dma_sel     = implemented_window && mmio_addr[31:12] == 20'h1001_0;
    assign npu_sel     = implemented_window && mmio_addr[31:12] == 20'h1002_0;
    assign display_sel = implemented_window && mmio_addr[31:12] == 20'h1003_0;
    assign dram_sel    = word_aligned && mmio_addr[31:12] == 20'h8000_0;

    /* verilator lint_off UNUSEDSIGNAL */
    logic unused_display_scanout;
    assign unused_display_scanout = ^{
        display_scan_hsync,
        display_scan_vsync,
        display_scan_active,
        display_scan_x,
        display_scan_y,
        display_scan_fb_addr,
        display_scan_rgb
    };
    /* verilator lint_on UNUSEDSIGNAL */

    assign dma_m_awready = !dma_m_bvalid;
    assign dma_m_wready  = !dma_m_bvalid;
    assign dma_m_arready = !dma_m_rvalid;
    assign display_fb_read_ready = display_rd_ok;
    assign display_fb_read_data  = display_rd_ok ? dram_mem[display_rd_word] : 32'hDEAD_BEEF;

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            dma_m_bvalid <= 1'b0;
            dma_m_bresp  <= 2'b00;
            dma_m_rvalid <= 1'b0;
            dma_m_rdata  <= 32'h0;
            dma_m_rresp  <= 2'b00;
        end else begin
            if (dma_m_bvalid && dma_m_bready) begin
                dma_m_bvalid <= 1'b0;
            end

            if (dma_m_rvalid && dma_m_rready) begin
                dma_m_rvalid <= 1'b0;
            end

            if (mmio_valid && mmio_write && dram_sel) begin
                dram_mem[mmio_dram_word] <= mmio_wdata;
            end

            if (dma_wr_fire) begin
                if (dma_wr_ok) begin
                    if (dma_m_wstrb[0]) dram_mem[dma_wr_word][7:0]   <= dma_m_wdata[7:0];
                    if (dma_m_wstrb[1]) dram_mem[dma_wr_word][15:8]  <= dma_m_wdata[15:8];
                    if (dma_m_wstrb[2]) dram_mem[dma_wr_word][23:16] <= dma_m_wdata[23:16];
                    if (dma_m_wstrb[3]) dram_mem[dma_wr_word][31:24] <= dma_m_wdata[31:24];
                    dma_m_bresp <= 2'b00;
                end else begin
                    dma_m_bresp <= 2'b10;
                end
                dma_m_bvalid <= 1'b1;
            end

            if (dma_rd_fire) begin
                if (dma_rd_ok) begin
                    dma_m_rdata <= dram_mem[dma_rd_word];
                    dma_m_rresp <= 2'b00;
                end else begin
                    dma_m_rdata <= 32'hDEAD_BEEF;
                    dma_m_rresp <= 2'b10;
                end
                dma_m_rvalid <= 1'b1;
            end
        end
    end

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
        .m_axil_awready(dma_m_awready),
        .m_axil_awaddr(dma_m_awaddr),
        .m_axil_wvalid(dma_m_wvalid),
        .m_axil_wready(dma_m_wready),
        .m_axil_wdata(dma_m_wdata),
        .m_axil_wstrb(dma_m_wstrb),
        .m_axil_bvalid(dma_m_bvalid),
        .m_axil_bready(dma_m_bready),
        .m_axil_bresp(dma_m_bresp),
        .m_axil_arvalid(dma_m_arvalid),
        .m_axil_arready(dma_m_arready),
        .m_axil_araddr(dma_m_araddr),
        .m_axil_rvalid(dma_m_rvalid),
        .m_axil_rready(dma_m_rready),
        .m_axil_rdata(dma_m_rdata),
        .m_axil_rresp(dma_m_rresp)
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
        .fb_read_data(display_fb_read_data),
        .fb_read_ready(display_fb_read_ready)
    );

    always_comb begin
        mmio_ready = mmio_valid;
        unique case (1'b1)
            bootrom_sel:  mmio_rdata = bootrom_rdata;
            periph_sel:   mmio_rdata = periph_rdata;
            dma_sel:      mmio_rdata = dma_rdata;
            npu_sel:      mmio_rdata = npu_rdata;
            display_sel:  mmio_rdata = display_rdata;
            dram_sel:     mmio_rdata = dram_mem[mmio_dram_word];
            default:      mmio_rdata = 32'hDEAD_BEEF;
        endcase
    end

endmodule
