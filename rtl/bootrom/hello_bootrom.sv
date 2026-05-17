`timescale 1ns/1ps

module hello_bootrom (
    input  logic [5:0]  addr,
    output logic [31:0] rdata
);
    localparam logic [31:0] MAGIC_OPSO = 32'h4F50_534F;
    localparam logic [31:0] MAGIC_CHIP = 32'h4348_4950;
    localparam logic [31:0] CONTRACT_VERSION = 32'h0000_0001;
    localparam logic [31:0] RESET_SCAFFOLD_HANDOFF = 32'h0000_1000;

    always_comb begin
        unique case (addr)
            6'h00: rdata = MAGIC_OPSO;
            6'h01: rdata = MAGIC_CHIP;
            6'h02: rdata = CONTRACT_VERSION;
            6'h03: rdata = RESET_SCAFFOLD_HANDOFF;
            default: rdata = 32'h0000_0000;
        endcase
    end
endmodule
