`timescale 1ns/1ps

module hello_cpu_subsystem_stub #(
    parameter logic [31:0] RESET_PC = 32'h0000_0000,
    parameter logic [31:0] HART_ID  = 32'h0000_0000
) (
    input  logic        clk,
    input  logic        rst_n,

    output logic        m_axil_awvalid,
    input  logic        m_axil_awready,
    output logic [31:0] m_axil_awaddr,
    output logic        m_axil_wvalid,
    input  logic        m_axil_wready,
    output logic [31:0] m_axil_wdata,
    output logic [3:0]  m_axil_wstrb,
    input  logic        m_axil_bvalid,
    output logic        m_axil_bready,
    input  logic [1:0]  m_axil_bresp,
    output logic        m_axil_arvalid,
    input  logic        m_axil_arready,
    output logic [31:0] m_axil_araddr,
    input  logic        m_axil_rvalid,
    output logic        m_axil_rready,
    input  logic [31:0] m_axil_rdata,
    input  logic [1:0]  m_axil_rresp,

    input  logic        timer_irq,
    input  logic        software_irq,
    input  logic        external_irq,

    output logic [31:0] reset_pc,
    output logic [31:0] hart_id,
    output logic        cpu_halted,
    output logic        irq_pending
);
    /* verilator lint_off UNUSEDSIGNAL */
    logic unused_axil_inputs;
    /* verilator lint_on UNUSEDSIGNAL */

    assign unused_axil_inputs = ^{
        clk,
        rst_n,
        m_axil_awready,
        m_axil_wready,
        m_axil_bvalid,
        m_axil_bresp,
        m_axil_arready,
        m_axil_rvalid,
        m_axil_rdata,
        m_axil_rresp
    };

    assign m_axil_awvalid = 1'b0;
    assign m_axil_awaddr  = 32'h0;
    assign m_axil_wvalid  = 1'b0;
    assign m_axil_wdata   = 32'h0;
    assign m_axil_wstrb   = 4'h0;
    assign m_axil_bready  = 1'b1;
    assign m_axil_arvalid = 1'b0;
    assign m_axil_araddr  = 32'h0;
    assign m_axil_rready  = 1'b1;

    assign reset_pc    = RESET_PC;
    assign hart_id     = HART_ID;
    assign cpu_halted  = 1'b1;
    assign irq_pending = timer_irq | software_irq | external_irq;

endmodule
