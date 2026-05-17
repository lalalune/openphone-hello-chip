`timescale 1ns/1ps

module hello_npu_formal(input logic clk);
    logic rst_n = 1'b0;
    (* anyseq *) logic valid;
    (* anyseq *) logic write;
    (* anyseq *) logic [5:0] addr;
    (* anyseq *) logic [31:0] wdata;
    logic [31:0] rdata;
    logic irq;
    logic [3:0] opcode_shadow = 4'h0;

    hello_npu dut (
        .clk(clk),
        .rst_n(rst_n),
        .valid(valid),
        .write(write),
        .addr(addr),
        .wdata(wdata),
        .rdata(rdata),
        .irq(irq)
    );

    initial rst_n = 1'b0;

    always_ff @(posedge clk) begin
        rst_n <= 1'b1;
        assume(addr < 6'h08);

        if (!$past(rst_n)) begin
            assert(!irq);
        end

        if (rst_n && addr == 6'h03) begin
            assert(irq == rdata[1]);
            assert(!(rdata[0] && rdata[1]));
            assert(!(rdata[0] && rdata[2]));
            if (rdata[2]) begin
                assert(rdata[1]);
                assert(irq);
            end
        end

        if (rst_n && irq && addr == 6'h03) begin
            assert(rdata[1]);
        end

        if (rst_n && addr == 6'h04) begin
            assert(rdata == {28'h0, opcode_shadow});
        end

        if (rst_n && addr == 6'h07) begin
            assert(rdata[31:7] == 25'h0);
        end

        if (rst_n && valid && write && addr == 6'h04) begin
            opcode_shadow <= wdata[3:0];
        end
    end
endmodule
