`timescale 1ns/1ps

module hello_display (
    input  logic        clk,
    input  logic        rst_n,
    input  logic        valid,
    input  logic        write,
    input  logic [5:0]  addr,
    input  logic [31:0] wdata,
    output logic [31:0] rdata,
    output logic        irq_vsync
);
    logic [31:0] fb_base;
    logic [15:0] width;
    logic [15:0] height;
    logic [31:0] format;
    logic [7:0]  line_count;
    logic        enable;

    assign irq_vsync = enable && line_count == 8'd0;

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            fb_base <= 32'h0;
            width <= 16'd640;
            height <= 16'd480;
            format <= 32'h3432_5258; // XR24
            line_count <= 8'h0;
            enable <= 1'b0;
        end else begin
            line_count <= line_count + 8'h1;
            if (valid && write) begin
                unique case (addr)
                    6'h00: fb_base <= wdata;
                    6'h01: begin
                        width <= wdata[15:0];
                        height <= wdata[31:16];
                    end
                    6'h02: format <= wdata;
                    6'h03: enable <= wdata[0];
                    default: begin end
                endcase
            end
        end
    end

    always_comb begin
        unique case (addr)
            6'h00: rdata = fb_base;
            6'h01: rdata = {height, width};
            6'h02: rdata = format;
            6'h03: rdata = {31'h0, enable};
            6'h04: rdata = {31'h0, irq_vsync};
            default: rdata = 32'h0;
        endcase
    end
endmodule
