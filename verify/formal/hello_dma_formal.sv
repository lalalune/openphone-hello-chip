`timescale 1ns/1ps

module hello_dma_formal(input logic clk);
    logic rst_n = 1'b0;
    (* anyseq *) logic valid;
    (* anyseq *) logic write;
    (* anyseq *) logic [5:0] addr;
    (* anyseq *) logic [31:0] wdata;
    logic [31:0] rdata;
    logic irq;

    hello_dma dut (
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
        assume(addr < 6'h0c);

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

        if (rst_n && addr == 6'h0b) begin
            assert(rdata[5:2] == 4'h0);
            assert(rdata[31:10] == 22'h0);
        end
    end
endmodule
