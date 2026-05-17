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
    localparam logic [1:0] DMA_IDLE  = 2'd0;
    localparam logic [1:0] DMA_READ  = 2'd1;
    localparam logic [1:0] DMA_WRITE = 2'd2;
    localparam logic [1:0] DMA_DONE  = 2'd3;

    logic [31:0] src;
    logic [31:0] dst;
    logic [31:0] len;
    logic [31:0] status;
    logic [31:0] cfg;
    logic [31:0] bytes_done;
    logic [31:0] beats_issued;
    logic [31:0] cur_src;
    logic [31:0] cur_dst;
    logic [31:0] remaining;
    logic [31:0] last_src;
    logic [31:0] last_dst;
    logic [3:0]  last_wstrb;
    logic [1:0]  state;

    wire clear_req = valid && write && addr == 6'h03 && wdata[1];
    wire unsupported_align = (src[1:0] != 2'b00) || (dst[1:0] != 2'b00);

    assign irq = status[1];

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            src <= 32'h0;
            dst <= 32'h0;
            len <= 32'h0;
            status <= 32'h0;
            cfg <= 32'h0000_0004;
            bytes_done <= 32'h0;
            beats_issued <= 32'h0;
            cur_src <= 32'h0;
            cur_dst <= 32'h0;
            remaining <= 32'h0;
            last_src <= 32'h0;
            last_dst <= 32'h0;
            last_wstrb <= 4'h0;
            state <= DMA_IDLE;
        end else begin
            status[3] <= 1'b0;
            status[4] <= 1'b0;

            if (clear_req) begin
                status[1] <= 1'b0;
                status[2] <= 1'b0;
            end

            if (status[0]) begin
                unique case (state)
                    DMA_READ: begin
                        last_src <= cur_src;
                        status[3] <= 1'b1;
                        state <= DMA_WRITE;
                    end
                    DMA_WRITE: begin
                        last_dst <= cur_dst;
                        last_wstrb <= (remaining >= 32'd4) ? 4'hF : ((4'h1 << remaining[1:0]) - 4'h1);
                        status[4] <= 1'b1;
                        beats_issued <= beats_issued + 32'd1;
                        if (remaining <= 32'd4) begin
                            bytes_done <= bytes_done + remaining;
                            remaining <= 32'h0;
                            state <= DMA_DONE;
                        end else begin
                            bytes_done <= bytes_done + 32'd4;
                            remaining <= remaining - 32'd4;
                            cur_src <= cur_src + 32'd4;
                            cur_dst <= cur_dst + 32'd4;
                            state <= DMA_READ;
                        end
                    end
                    DMA_DONE: begin
                        status[0] <= 1'b0;
                        status[1] <= 1'b1;
                        state <= DMA_IDLE;
                    end
                    default: begin
                        state <= DMA_IDLE;
                        status[0] <= 1'b0;
                    end
                endcase
            end

            if (valid && write) begin
                unique case (addr)
                    6'h00: src <= wdata;
                    6'h01: dst <= wdata;
                    6'h02: len <= wdata;
                    6'h04: cfg <= wdata;
                    6'h03: begin
                        if (wdata[0] && !status[0]) begin
                            bytes_done <= 32'h0;
                            beats_issued <= 32'h0;
                            cur_src <= src;
                            cur_dst <= dst;
                            last_src <= src;
                            last_dst <= dst;
                            remaining <= len;
                            last_wstrb <= 4'h0;
                            if (unsupported_align) begin
                                status <= 32'h0000_0006;
                                state <= DMA_IDLE;
                            end else if (len == 32'h0) begin
                                status <= 32'h0000_0002;
                                state <= DMA_IDLE;
                            end else begin
                                status <= 32'h0000_0001;
                                state <= DMA_READ;
                            end
                        end
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
            6'h04: rdata = cfg;
            6'h05: rdata = bytes_done;
            6'h06: rdata = beats_issued;
            6'h07: rdata = cur_src;
            6'h08: rdata = cur_dst;
            6'h09: rdata = last_src;
            6'h0a: rdata = last_dst;
            6'h0b: rdata = {22'h0, last_wstrb, 4'h0, state};
            default: rdata = 32'h0;
        endcase
    end
endmodule
