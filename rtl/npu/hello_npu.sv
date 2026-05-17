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
    localparam logic [3:0] OP_DOT8_S4  = 4'h7;
    localparam logic [3:0] OP_GEMM_S8  = 4'h8;

    localparam int unsigned SCRATCH_WORDS = 16;

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
    logic signed [31:0] dot8_s4_sum;

    logic [31:0] scratch [0:SCRATCH_WORDS-1];
    logic [1:0]  gemm_m;
    logic [1:0]  gemm_n;
    logic [2:0]  gemm_k;
    logic [5:0]  gemm_a_base;
    logic [5:0]  gemm_b_base;
    logic [5:0]  gemm_c_base;
    logic [3:0]  gemm_a_stride;
    logic [3:0]  gemm_b_stride;
    logic [3:0]  gemm_c_stride;
    logic [1:0]  gemm_i;
    logic [1:0]  gemm_j;
    logic [2:0]  gemm_l;
    logic signed [31:0] gemm_acc;
    logic [31:0] perf_cycles;
    logic [31:0] perf_macs;
    logic [31:0] perf_errors;
    logic [31:0] perf_ops;
    logic [31:0] perf_unsupported_ops;
    logic [31:0] cmd_param;
    logic [31:0] desc_base;
    logic [2:0]  desc_head;
    logic [2:0]  desc_tail;
    logic        desc_busy;
    logic gemm_busy;

    logic [7:0] gemm_a_addr;
    logic [7:0] gemm_b_addr;
    logic [7:0] gemm_c_addr;
    logic gemm_cfg_ok;
    logic signed [7:0] gemm_a_value;
    logic signed [7:0] gemm_b_value;

    function automatic logic signed [31:0] sx8(input logic [7:0] value);
        sx8 = {{24{value[7]}}, value};
    endfunction

    function automatic logic signed [31:0] sx4(input logic [3:0] value);
        sx4 = {{28{value[3]}}, value};
    endfunction

    function automatic logic signed [31:0] sx16(input logic [15:0] value);
        sx16 = {{16{value[15]}}, value};
    endfunction

    function automatic logic [7:0] scratch_read_byte(input logic [5:0] byte_addr);
        unique case (byte_addr[1:0])
            2'd0: scratch_read_byte = scratch[byte_addr[5:2]][7:0];
            2'd1: scratch_read_byte = scratch[byte_addr[5:2]][15:8];
            2'd2: scratch_read_byte = scratch[byte_addr[5:2]][23:16];
            default: scratch_read_byte = scratch[byte_addr[5:2]][31:24];
        endcase
    endfunction

    task automatic scratch_write_word(input logic [3:0] word_addr, input logic [31:0] value);
        scratch[word_addr] <= value;
    endtask

    task automatic scratch_write_i32(input logic [3:0] word_addr, input logic [31:0] value);
        scratch[word_addr] <= value;
    endtask

    function automatic logic [2:0] opcode_latency(input logic [3:0] op);
        unique case (op)
            OP_MUL_LO:  opcode_latency = 3'd2;
            OP_MAC_S16: opcode_latency = 3'd2;
            OP_DOT4_S8: opcode_latency = 3'd3;
            OP_DOT8_S4: opcode_latency = 3'd3;
            default:    opcode_latency = 3'd1;
        endcase
    endfunction

    function automatic logic opcode_valid(input logic [3:0] op);
        unique case (op)
            OP_ADD, OP_SUB, OP_MUL_LO, OP_MAC_S16, OP_DOT4_S8, OP_MAX_U32, OP_MIN_U32, OP_DOT8_S4, OP_GEMM_S8: opcode_valid = 1'b1;
            default: opcode_valid = 1'b0;
        endcase
    endfunction

    assign irq = status[1];
    assign gemm_a_addr = {2'h0, gemm_a_base} + ({6'h0, gemm_i} * {4'h0, gemm_a_stride}) + {5'h0, gemm_l};
    assign gemm_b_addr = {2'h0, gemm_b_base} + ({5'h0, gemm_l} * {4'h0, gemm_b_stride}) + {6'h0, gemm_j};
    assign gemm_c_addr = {2'h0, gemm_c_base} + ({6'h0, gemm_i} * {4'h0, gemm_c_stride}) + {4'h0, gemm_j, 2'b00};
    assign gemm_cfg_ok = (gemm_m != 2'h0) && (gemm_n != 2'h0) && (gemm_k != 3'h0) &&
                         (gemm_a_addr < 8'd64) && (gemm_b_addr < 8'd64) &&
                         ((gemm_c_addr + 8'd3) < 8'd64) && (gemm_c_addr[1:0] == 2'b00);
    assign gemm_a_value = scratch_read_byte(gemm_a_addr[5:0]);
    assign gemm_b_value = scratch_read_byte(gemm_b_addr[5:0]);

    always_comb begin
        mac_s16_sum = sx16(op_a_q[15:0]) * sx16(op_b_q[15:0]) + $signed(acc_q);
        dot4_s8_sum =
            (sx8(op_a_q[7:0])   * sx8(op_b_q[7:0]))   +
            (sx8(op_a_q[15:8])  * sx8(op_b_q[15:8]))  +
            (sx8(op_a_q[23:16]) * sx8(op_b_q[23:16])) +
            (sx8(op_a_q[31:24]) * sx8(op_b_q[31:24])) +
            $signed(acc_q);
        dot8_s4_sum =
            (sx4(op_a_q[3:0])   * sx4(op_b_q[3:0]))   +
            (sx4(op_a_q[7:4])   * sx4(op_b_q[7:4]))   +
            (sx4(op_a_q[11:8])  * sx4(op_b_q[11:8]))  +
            (sx4(op_a_q[15:12]) * sx4(op_b_q[15:12])) +
            (sx4(op_a_q[19:16]) * sx4(op_b_q[19:16])) +
            (sx4(op_a_q[23:20]) * sx4(op_b_q[23:20])) +
            (sx4(op_a_q[27:24]) * sx4(op_b_q[27:24])) +
            (sx4(op_a_q[31:28]) * sx4(op_b_q[31:28])) +
            $signed(acc_q);

        unique case (opcode_q)
            OP_ADD:     datapath_wide = {32'h0, op_a_q + op_b_q};
            OP_SUB:     datapath_wide = {32'h0, op_a_q - op_b_q};
            OP_MUL_LO:  datapath_wide = {32'h0, op_a_q} * {32'h0, op_b_q};
            OP_MAC_S16: datapath_wide = {{32{mac_s16_sum[31]}}, mac_s16_sum};
            OP_DOT4_S8: datapath_wide = {{32{dot4_s8_sum[31]}}, dot4_s8_sum};
            OP_MAX_U32: datapath_wide = {32'h0, (op_a_q > op_b_q) ? op_a_q : op_b_q};
            OP_MIN_U32: datapath_wide = {32'h0, (op_a_q < op_b_q) ? op_a_q : op_b_q};
            OP_DOT8_S4: datapath_wide = {{32{dot8_s4_sum[31]}}, dot8_s4_sum};
            default:    datapath_wide = 64'h0;
        endcase
    end

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
            gemm_m <= 2'h0;
            gemm_n <= 2'h0;
            gemm_k <= 3'h0;
            gemm_a_base <= 6'h0;
            gemm_b_base <= 6'h0;
            gemm_c_base <= 6'h0;
            gemm_a_stride <= 4'h0;
            gemm_b_stride <= 4'h0;
            gemm_c_stride <= 4'h0;
            gemm_i <= 2'h0;
            gemm_j <= 2'h0;
            gemm_l <= 3'h0;
            gemm_acc <= 32'sh0;
            perf_cycles <= 32'h0;
            perf_macs <= 32'h0;
            perf_errors <= 32'h0;
            perf_ops <= 32'h0;
            perf_unsupported_ops <= 32'h0;
            cmd_param <= 32'h0;
            desc_base <= 32'h0;
            desc_head <= 3'h0;
            desc_tail <= 3'h0;
            desc_busy <= 1'b0;
            gemm_busy <= 1'b0;
            for (int idx = 0; idx < SCRATCH_WORDS; idx++) begin
                scratch[idx] <= 32'h0;
            end
        end else begin
            if (busy_count != 3'h0) begin
                busy_count <= busy_count - 3'h1;
                if (busy_count == 3'h1) begin
                    {result_hi, result} <= datapath_wide;
                    status <= 32'h0000_0002;
                end
            end

            if (gemm_busy) begin
                perf_cycles <= perf_cycles + 32'd1;
                if (!gemm_cfg_ok) begin
                    gemm_busy <= 1'b0;
                    status <= 32'h0000_0006;
                    perf_errors <= perf_errors + 32'd1;
                end else begin
                    perf_macs <= perf_macs + 32'd1;
                    if (gemm_l == gemm_k - 3'd1) begin
                        scratch_write_i32(gemm_c_addr[5:2], gemm_acc + (gemm_a_value * gemm_b_value));
                        gemm_acc <= 32'sh0;
                        gemm_l <= 3'h0;
                        if (gemm_j == gemm_n - 2'd1) begin
                            gemm_j <= 2'h0;
                            if (gemm_i == gemm_m - 2'd1) begin
                                gemm_i <= 2'h0;
                                gemm_busy <= 1'b0;
                                status <= 32'h0000_0002;
                            end else begin
                                gemm_i <= gemm_i + 2'd1;
                            end
                        end else begin
                            gemm_j <= gemm_j + 2'd1;
                        end
                    end else begin
                        gemm_acc <= gemm_acc + (gemm_a_value * gemm_b_value);
                        gemm_l <= gemm_l + 3'd1;
                    end
                end
            end

            if (valid && write) begin
                unique case (addr)
                    6'h00: op_a <= wdata;
                    6'h01: op_b <= wdata;
                    6'h04: opcode <= wdata[3:0];
                    6'h05: acc <= wdata;
                    6'h08: begin
                        gemm_m <= wdata[1:0];
                        gemm_n <= wdata[9:8];
                        gemm_k <= wdata[18:16];
                    end
                    6'h09: begin
                        gemm_a_base <= wdata[5:0];
                        gemm_b_base <= wdata[13:8];
                        gemm_c_base <= wdata[21:16];
                    end
                    6'h0a: begin
                        gemm_a_stride <= wdata[3:0];
                        gemm_b_stride <= wdata[11:8];
                        gemm_c_stride <= wdata[19:16];
                    end
                    6'h0c: cmd_param <= wdata;
                    6'h10: desc_base <= wdata;
                    6'h11: desc_head <= wdata[2:0];
                    6'h17: begin
                        if (wdata[0]) begin
                            perf_cycles <= 32'h0;
                            perf_macs <= 32'h0;
                            perf_errors <= 32'h0;
                            perf_ops <= 32'h0;
                            perf_unsupported_ops <= 32'h0;
                        end
                    end
                    6'h03: begin
                        if (wdata[0] && busy_count == 3'h0 && !gemm_busy) begin
                            if (opcode == OP_GEMM_S8) begin
                                if (gemm_cfg_ok) begin
                                    status <= 32'h0000_0001;
                                    gemm_busy <= 1'b1;
                                    gemm_i <= 2'h0;
                                    gemm_j <= 2'h0;
                                    gemm_l <= 3'h0;
                                    gemm_acc <= 32'sh0;
                                    perf_ops <= perf_ops + 32'd1;
                                end else begin
                                    status <= 32'h0000_0006;
                                    perf_errors <= perf_errors + 32'd1;
                                    perf_unsupported_ops <= perf_unsupported_ops + 32'd1;
                                end
                            end else if (opcode_valid(opcode)) begin
                                status <= 32'h0000_0001;
                                busy_count <= opcode_latency(opcode);
                                op_a_q <= op_a;
                                op_b_q <= op_b;
                                acc_q <= acc;
                                opcode_q <= opcode;
                                perf_ops <= perf_ops + 32'd1;
                            end else begin
                                status <= 32'h0000_0006;
                                perf_errors <= perf_errors + 32'd1;
                                perf_unsupported_ops <= perf_unsupported_ops + 32'd1;
                            end
                        end
                        if (wdata[1]) begin
                            status[1] <= 1'b0;
                            status[2] <= 1'b0;
                        end
                    end
                    default: begin
                        if (addr[5:4] == 2'b10) begin
                            scratch_write_word(addr[3:0], wdata);
                        end
                    end
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
            6'h07: rdata = {24'h0, gemm_busy, opcode_q, busy_count};
            6'h08: rdata = {13'h0, gemm_k, 6'h0, gemm_n, 6'h0, gemm_m};
            6'h09: rdata = {10'h0, gemm_c_base, 2'h0, gemm_b_base, 2'h0, gemm_a_base};
            6'h0a: rdata = {12'h0, gemm_c_stride, 4'h0, gemm_b_stride, 4'h0, gemm_a_stride};
            6'h0b: rdata = perf_unsupported_ops;
            6'h0c: rdata = cmd_param;
            6'h10: rdata = desc_base;
            6'h11: rdata = {29'h0, desc_head};
            6'h12: rdata = {29'h0, desc_tail};
            6'h13: rdata = {29'h0, desc_busy, desc_head == 3'h7, desc_head == desc_tail};
            6'h14: rdata = perf_cycles;
            6'h15: rdata = perf_macs;
            6'h16: rdata = perf_ops;
            6'h17: rdata = perf_errors;
            default: begin
                if (addr[5:4] == 2'b10) begin
                    rdata = scratch[addr[3:0]];
                end else begin
                    rdata = 32'h0;
                end
            end
        endcase
    end
endmodule
