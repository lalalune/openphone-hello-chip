`timescale 1ns/1ps

module hello_npu (
    input  logic        clk,
    input  logic        rst_n,
    input  logic        valid,
    input  logic        write,
    input  logic [5:0]  addr,
    input  logic [31:0] wdata,
    output logic [31:0] rdata,
    output logic        irq
);
    logic [31:0] op_a;
    logic [31:0] op_b;
    logic [31:0] result;
    logic [31:0] status;
    logic [1:0]  busy_count;

    assign irq = status[1];

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            op_a <= 32'h0;
            op_b <= 32'h0;
            result <= 32'h0;
            status <= 32'h0;
            busy_count <= 2'h0;
        end else begin
            if (busy_count != 2'h0) begin
                busy_count <= busy_count - 2'h1;
                if (busy_count == 2'h1) begin
                    result <= op_a + op_b;
                    status <= 32'h2;
                end
            end

            if (valid && write) begin
                unique case (addr)
                    6'h00: op_a <= wdata;
                    6'h01: op_b <= wdata;
                    6'h03: begin
                        if (wdata[0]) begin
                            status <= 32'h1;
                            busy_count <= 2'h2;
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
            6'h00: rdata = op_a;
            6'h01: rdata = op_b;
            6'h02: rdata = result;
            6'h03: rdata = status;
            default: rdata = 32'h0;
        endcase
    end
endmodule
