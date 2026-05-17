`timescale 1ns/1ps

module hello_dma (
    input  logic        clk,
    input  logic        rst_n,
    input  logic        valid,
    input  logic        write,
    input  logic [5:0]  addr,
    input  logic [31:0] wdata,
    output logic [31:0] rdata,
    output logic        irq
);
    logic [31:0] src;
    logic [31:0] dst;
    logic [31:0] len;
    logic [31:0] status;
    logic [2:0]  busy_count;

    assign irq = status[1];

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            src <= 32'h0;
            dst <= 32'h0;
            len <= 32'h0;
            status <= 32'h0;
            busy_count <= 3'h0;
        end else begin
            if (busy_count != 3'h0) begin
                busy_count <= busy_count - 3'h1;
                status[0] <= 1'b1;
                if (busy_count == 3'h1) begin
                    status[0] <= 1'b0;
                    status[1] <= 1'b1;
                end
            end

            if (valid && write) begin
                unique case (addr)
                    6'h00: src <= wdata;
                    6'h01: dst <= wdata;
                    6'h02: len <= wdata;
                    6'h03: begin
                        if (wdata[0]) begin
                            busy_count <= 3'h4;
                            status <= 32'h1;
                        end
                        if (wdata[1]) status[1] <= 1'b0;
                    end
                    default: begin end
                endcase
            end
        end
    end

    always_comb begin
        unique case (addr)
            6'h00: rdata = src;
            6'h01: rdata = dst;
            6'h02: rdata = len;
            6'h03: rdata = status;
            default: rdata = 32'h0;
        endcase
    end
endmodule
