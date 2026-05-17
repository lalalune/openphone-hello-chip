`timescale 1ns/1ps

module hello_axi_lite_interconnect (
    input  logic        clk,
    input  logic        rst_n,

    input  logic        m_axil_awvalid,
    output logic        m_axil_awready,
    input  logic [31:0] m_axil_awaddr,
    input  logic        m_axil_wvalid,
    output logic        m_axil_wready,
    input  logic [31:0] m_axil_wdata,
    input  logic [3:0]  m_axil_wstrb,
    output logic        m_axil_bvalid,
    input  logic        m_axil_bready,
    output logic [1:0]  m_axil_bresp,

    input  logic        m_axil_arvalid,
    output logic        m_axil_arready,
    input  logic [31:0] m_axil_araddr,
    output logic        m_axil_rvalid,
    input  logic        m_axil_rready,
    output logic [31:0] m_axil_rdata,
    output logic [1:0]  m_axil_rresp,

    output logic        dram_awvalid,
    input  logic        dram_awready,
    output logic [31:0] dram_awaddr,
    output logic        dram_wvalid,
    input  logic        dram_wready,
    output logic [31:0] dram_wdata,
    output logic [3:0]  dram_wstrb,
    input  logic        dram_bvalid,
    output logic        dram_bready,
    input  logic [1:0]  dram_bresp,
    output logic        dram_arvalid,
    input  logic        dram_arready,
    output logic [31:0] dram_araddr,
    input  logic        dram_rvalid,
    output logic        dram_rready,
    input  logic [31:0] dram_rdata,
    input  logic [1:0]  dram_rresp,

    output logic        intc_awvalid,
    input  logic        intc_awready,
    output logic [31:0] intc_awaddr,
    output logic        intc_wvalid,
    input  logic        intc_wready,
    output logic [31:0] intc_wdata,
    output logic [3:0]  intc_wstrb,
    input  logic        intc_bvalid,
    output logic        intc_bready,
    input  logic [1:0]  intc_bresp,
    output logic        intc_arvalid,
    input  logic        intc_arready,
    output logic [31:0] intc_araddr,
    input  logic        intc_rvalid,
    output logic        intc_rready,
    input  logic [31:0] intc_rdata,
    input  logic [1:0]  intc_rresp
);
    localparam logic [1:0] SEL_NONE = 2'h0;
    localparam logic [1:0] SEL_DRAM = 2'h1;
    localparam logic [1:0] SEL_INTC = 2'h2;
    localparam logic [1:0] SEL_ERR  = 2'h3;

    logic [1:0] wr_sel_q;
    logic [1:0] rd_sel_q;
    logic       wr_pending;
    logic       rd_pending;
    logic       wr_err_valid;
    logic       rd_err_valid;
    logic       wr_addr_valid;
    logic       wr_data_valid;
    logic [31:0] wr_addr_q;
    logic [31:0] wr_data_q;
    logic [3:0]  wr_strb_q;

    wire aw_dram_sel = wr_addr_q[31:28] == 4'h8;
    wire ar_dram_sel = m_axil_araddr[31:28] == 4'h8;
    wire aw_intc_sel = wr_addr_q[31:12] == 20'h0C00_0;
    wire ar_intc_sel = m_axil_araddr[31:12] == 20'h0C00_0;

    wire wr_has_addr_data = wr_addr_valid && wr_data_valid && !wr_pending;
    wire rd_has_addr      = m_axil_arvalid && !rd_pending;
    wire wr_decode_error  = wr_has_addr_data && !aw_dram_sel && !aw_intc_sel;

    assign dram_awaddr = wr_addr_q - 32'h8000_0000;
    assign dram_wdata  = wr_data_q;
    assign dram_wstrb  = wr_strb_q;
    assign dram_araddr = m_axil_araddr - 32'h8000_0000;
    assign intc_awaddr = wr_addr_q - 32'h0C00_0000;
    assign intc_wdata  = wr_data_q;
    assign intc_wstrb  = wr_strb_q;
    assign intc_araddr = m_axil_araddr - 32'h0C00_0000;

    assign dram_awvalid = wr_has_addr_data && aw_dram_sel;
    assign dram_wvalid  = wr_has_addr_data && aw_dram_sel;
    assign intc_awvalid = wr_has_addr_data && aw_intc_sel;
    assign intc_wvalid  = wr_has_addr_data && aw_intc_sel;

    assign dram_arvalid = rd_has_addr && ar_dram_sel;
    assign intc_arvalid = rd_has_addr && ar_intc_sel;

    assign m_axil_awready = !wr_addr_valid && !wr_pending;
    assign m_axil_wready  = !wr_data_valid && !wr_pending;

    assign m_axil_arready = rd_has_addr &&
                            ((ar_dram_sel && dram_arready) ||
                             (ar_intc_sel && intc_arready) ||
                             (!ar_dram_sel && !ar_intc_sel));

    assign dram_bready = wr_sel_q == SEL_DRAM && m_axil_bready;
    assign intc_bready = wr_sel_q == SEL_INTC && m_axil_bready;
    assign dram_rready = rd_sel_q == SEL_DRAM && m_axil_rready;
    assign intc_rready = rd_sel_q == SEL_INTC && m_axil_rready;

    always_comb begin
        unique case (wr_sel_q)
            SEL_DRAM: begin
                m_axil_bvalid = dram_bvalid;
                m_axil_bresp  = dram_bresp;
            end
            SEL_INTC: begin
                m_axil_bvalid = intc_bvalid;
                m_axil_bresp  = intc_bresp;
            end
            SEL_ERR: begin
                m_axil_bvalid = wr_err_valid;
                m_axil_bresp  = 2'b11;
            end
            default: begin
                m_axil_bvalid = 1'b0;
                m_axil_bresp  = 2'b00;
            end
        endcase
    end

    always_comb begin
        unique case (rd_sel_q)
            SEL_DRAM: begin
                m_axil_rvalid = dram_rvalid;
                m_axil_rdata  = dram_rdata;
                m_axil_rresp  = dram_rresp;
            end
            SEL_INTC: begin
                m_axil_rvalid = intc_rvalid;
                m_axil_rdata  = intc_rdata;
                m_axil_rresp  = intc_rresp;
            end
            SEL_ERR: begin
                m_axil_rvalid = rd_err_valid;
                m_axil_rdata  = 32'hDEAD_BEEF;
                m_axil_rresp  = 2'b11;
            end
            default: begin
                m_axil_rvalid = 1'b0;
                m_axil_rdata  = 32'h0;
                m_axil_rresp  = 2'b00;
            end
        endcase
    end

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            wr_sel_q     <= SEL_NONE;
            rd_sel_q     <= SEL_NONE;
            wr_pending   <= 1'b0;
            rd_pending   <= 1'b0;
            wr_err_valid <= 1'b0;
            rd_err_valid <= 1'b0;
            wr_addr_valid <= 1'b0;
            wr_data_valid <= 1'b0;
            wr_addr_q     <= 32'h0;
            wr_data_q     <= 32'h0;
            wr_strb_q     <= 4'h0;
        end else begin
            if (m_axil_awready && m_axil_awvalid) begin
                wr_addr_valid <= 1'b1;
                wr_addr_q     <= m_axil_awaddr;
            end

            if (m_axil_wready && m_axil_wvalid) begin
                wr_data_valid <= 1'b1;
                wr_data_q     <= m_axil_wdata;
                wr_strb_q     <= m_axil_wstrb;
            end

            if (wr_has_addr_data &&
                ((aw_dram_sel && dram_awready && dram_wready) ||
                 (aw_intc_sel && intc_awready && intc_wready) ||
                 wr_decode_error)) begin
                wr_pending <= 1'b1;
                wr_addr_valid <= 1'b0;
                wr_data_valid <= 1'b0;
                if (aw_dram_sel) begin
                    wr_sel_q <= SEL_DRAM;
                end else if (aw_intc_sel) begin
                    wr_sel_q <= SEL_INTC;
                end else begin
                    wr_sel_q     <= SEL_ERR;
                    wr_err_valid <= 1'b1;
                end
            end

            if (m_axil_bvalid && m_axil_bready) begin
                wr_pending   <= 1'b0;
                wr_sel_q     <= SEL_NONE;
                wr_err_valid <= 1'b0;
            end

            if (m_axil_arready && m_axil_arvalid) begin
                rd_pending <= 1'b1;
                if (ar_dram_sel) begin
                    rd_sel_q <= SEL_DRAM;
                end else if (ar_intc_sel) begin
                    rd_sel_q <= SEL_INTC;
                end else begin
                    rd_sel_q     <= SEL_ERR;
                    rd_err_valid <= 1'b1;
                end
            end

            if (m_axil_rvalid && m_axil_rready) begin
                rd_pending   <= 1'b0;
                rd_sel_q     <= SEL_NONE;
                rd_err_valid <= 1'b0;
            end
        end
    end

endmodule
