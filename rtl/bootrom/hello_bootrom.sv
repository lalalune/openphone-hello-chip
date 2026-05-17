`timescale 1ns/1ps

module hello_bootrom (
    input  logic [5:0]  addr,
    output logic [31:0] rdata
);
    always_comb begin
        unique case (addr)
            6'h00: rdata = 32'h4F50_534F; // OPSO
            6'h01: rdata = 32'h4348_4950; // CHIP
            6'h02: rdata = 32'h0000_0001; // contract version
            6'h03: rdata = 32'h0000_1000; // boot vector placeholder
            default: rdata = 32'h0000_0000;
        endcase
    end
endmodule
