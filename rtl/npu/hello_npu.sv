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
    localparam logic [3:0] OP_ADD      = 4'h0;
    localparam logic [3:0] OP_SUB      = 4'h1;
    localparam logic [3:0] OP_MUL_LO   = 4'h2;
    localparam logic [3:0] OP_MAC_S16  = 4'h3;
    localparam logic [3:0] OP_DOT4_S8  = 4'h4;
    localparam logic [3:0] OP_MAX_U32  = 4'h5;
    localparam logic [3:0] OP_MIN_U32  = 4'h6;

    logic [31:0] op_a;
    logic [31:0] op_b;
    logic [31:0] acc;
    logic [3:0]  opcode;
    logic [31:0] result;
    logic [31:0] result_hi;
    logic [31:0] status;
    logic [2:0]  busy_count;
    logic [31:0] op_a_q;
    logic [31:0] op_b_q;
    logic [31:0] acc_q;
    logic [3:0]  opcode_q;
    logic [63:0] datapath_wide;
    logic signed [31:0] mac_s16_sum;
    logic signed [31:0] dot4_s8_sum;

    function automatic logic signed [31:0] sx8(input logic [7:0] value);
        sx8 = {{24{value[7]}}, value};
    endfunction

    function automatic logic signed [31:0] sx16(input logic [15:0] value);
        sx16 = {{16{value[15]}}, value};
    endfunction

    function automatic logic [2:0] opcode_latency(input logic [3:0] op);
        unique case (op)
            OP_MUL_LO:  opcode_latency = 3'd2;
            OP_MAC_S16: opcode_latency = 3'd2;
            OP_DOT4_S8: opcode_latency = 3'd3;
            default:    opcode_latency = 3'd1;
        endcase
    endfunction

    function automatic logic opcode_valid(input logic [3:0] op);
        unique case (op)
            OP_ADD, OP_SUB, OP_MUL_LO, OP_MAC_S16, OP_DOT4_S8, OP_MAX_U32, OP_MIN_U32: opcode_valid = 1'b1;
            default: opcode_valid = 1'b0;
        endcase
    endfunction

    always_comb begin
        mac_s16_sum = sx16(op_a_q[15:0]) * sx16(op_b_q[15:0]) + $signed(acc_q);
        dot4_s8_sum =
            (sx8(op_a_q[7:0])   * sx8(op_b_q[7:0]))   +
            (sx8(op_a_q[15:8])  * sx8(op_b_q[15:8]))  +
            (sx8(op_a_q[23:16]) * sx8(op_b_q[23:16])) +
            (sx8(op_a_q[31:24]) * sx8(op_b_q[31:24])) +
            $signed(acc_q);

        unique case (opcode_q)
            OP_ADD:     datapath_wide = {32'h0, op_a_q + op_b_q};
            OP_SUB:     datapath_wide = {32'h0, op_a_q - op_b_q};
            OP_MUL_LO:  datapath_wide = {32'h0, op_a_q} * {32'h0, op_b_q};
            OP_MAC_S16: datapath_wide = {{32{mac_s16_sum[31]}}, mac_s16_sum};
            OP_DOT4_S8: datapath_wide = {{32{dot4_s8_sum[31]}}, dot4_s8_sum};
            OP_MAX_U32: datapath_wide = {32'h0, (op_a_q > op_b_q) ? op_a_q : op_b_q};
            OP_MIN_U32: datapath_wide = {32'h0, (op_a_q < op_b_q) ? op_a_q : op_b_q};
            default:    datapath_wide = 64'h0;
        endcase
    end

    assign irq = status[1];

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            op_a <= 32'h0;
            op_b <= 32'h0;
            acc <= 32'h0;
            opcode <= OP_ADD;
            result <= 32'h0;
            result_hi <= 32'h0;
            status <= 32'h0;
            busy_count <= 3'h0;
            op_a_q <= 32'h0;
            op_b_q <= 32'h0;
            acc_q <= 32'h0;
            opcode_q <= OP_ADD;
        end else begin
            if (busy_count != 3'h0) begin
                busy_count <= busy_count - 3'h1;
                if (busy_count == 3'h1) begin
                    {result_hi, result} <= datapath_wide;
                    status <= 32'h0000_0002;
                end
            end

            if (valid && write) begin
                unique case (addr)
                    6'h00: op_a <= wdata;
                    6'h01: op_b <= wdata;
                    6'h04: opcode <= wdata[3:0];
                    6'h05: acc <= wdata;
                    6'h03: begin
                        if (wdata[0] && busy_count == 3'h0) begin
                            if (opcode_valid(opcode)) begin
                                status <= 32'h0000_0001;
                                busy_count <= opcode_latency(opcode);
                                op_a_q <= op_a;
                                op_b_q <= op_b;
                                acc_q <= acc;
                                opcode_q <= opcode;
                            end else begin
                                status <= 32'h0000_0006;
                            end
                        end
                        if (wdata[1]) begin
                            status[1] <= 1'b0;
                            status[2] <= 1'b0;
                        end
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
            6'h04: rdata = {28'h0, opcode};
            6'h05: rdata = acc;
            6'h06: rdata = result_hi;
            6'h07: rdata = {24'h0, 1'b0, opcode_q, busy_count};
            default: rdata = 32'h0;
        endcase
    end
endmodule
