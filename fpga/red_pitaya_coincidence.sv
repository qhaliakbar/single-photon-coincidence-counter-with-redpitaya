`timescale 1ns / 1ps
/////////////////////////////////



module red_pitaya_coincidence (

    input  logic clk_i,
    input  logic rstn_i,


    // digital inputs

    input logic coin_in_a,
    input logic coin_in_b,


    // system bus

    input  logic [31:0] sys_addr,
    input  logic [31:0] sys_wdata,
    input  logic        sys_wen,
    input  logic        sys_ren,

    output logic [31:0] sys_rdata,
    output logic        sys_err,
    output logic        sys_ack

);



////////////////////////////////////////////////////////////////////////////////
// Registers
////////////////////////////////////////////////////////////////////////////////


logic [31:0] id_reg;


logic [31:0] coincidence_count;

logic [31:0] count_a;
logic [31:0] count_b;



////////////////////////////////////////////////////////////////////////////////
// Fixed coincidence window
////////////////////////////////////////////////////////////////////////////////


// 80 ns @ 125 MHz FPGA clock

localparam logic [31:0] COINCIDENCE_WINDOW = 32'd10;



////////////////////////////////////////////////////////////////////////////////
// Synchronizers
////////////////////////////////////////////////////////////////////////////////


logic coin_a_sync1;
logic coin_a_sync2;

logic coin_b_sync1;
logic coin_b_sync2;



logic coin_a_d;
logic coin_b_d;



////////////////////////////////////////////////////////////////////////////////
// Timestamp counter
////////////////////////////////////////////////////////////////////////////////


logic [31:0] timestamp;


logic [31:0] timestamp_a;
logic [31:0] timestamp_b;



logic [31:0] delta_a;
logic [31:0] delta_b;



////////////////////////////////////////////////////////////////////////////////
// Event flags
////////////////////////////////////////////////////////////////////////////////


logic event_a;
logic event_b;



assign event_a = coin_a_sync2 && !coin_a_d;

assign event_b = coin_b_sync2 && !coin_b_d;



////////////////////////////////////////////////////////////////////////////////
// Timestamp difference
//
// unsigned subtraction automatically handles rollover
//
////////////////////////////////////////////////////////////////////////////////


always_comb begin


    delta_a = timestamp - timestamp_b;

    delta_b = timestamp - timestamp_a;


end




////////////////////////////////////////////////////////////////////////////////
// Main FPGA logic
////////////////////////////////////////////////////////////////////////////////


always_ff @(posedge clk_i) begin


    if(!rstn_i) begin


        id_reg <= 32'h434F494E;


        coincidence_count <= 32'd0;

        count_a <= 32'd0;
        count_b <= 32'd0;


        timestamp <= 32'd0;


        timestamp_a <= 32'd0;
        timestamp_b <= 32'd0;



        coin_a_sync1 <= 1'b0;
        coin_a_sync2 <= 1'b0;


        coin_b_sync1 <= 1'b0;
        coin_b_sync2 <= 1'b0;



        coin_a_d <= 1'b0;
        coin_b_d <= 1'b0;


    end


    else begin



        ////////////////////////////////////////////////////
        // free running timestamp
        ////////////////////////////////////////////////////

        timestamp <= timestamp + 1'b1;



        ////////////////////////////////////////////////////
        // synchronize inputs
        ////////////////////////////////////////////////////

        coin_a_sync1 <= coin_in_a;
        coin_a_sync2 <= coin_a_sync1;


        coin_b_sync1 <= coin_in_b;
        coin_b_sync2 <= coin_b_sync1;



        ////////////////////////////////////////////////////
        // delayed states
        ////////////////////////////////////////////////////

        coin_a_d <= coin_a_sync2;
        coin_b_d <= coin_b_sync2;



        ////////////////////////////////////////////////////
        // Coincidence logic
        ////////////////////////////////////////////////////

        if(event_a && event_b) begin

            // Both edges occurred on the same FPGA clock

            count_a <= count_a + 1'b1;
            count_b <= count_b + 1'b1;

            timestamp_a <= timestamp;
            timestamp_b <= timestamp;

            coincidence_count <= coincidence_count + 1'b1;

        end

        else if(event_a) begin

            count_a <= count_a + 1'b1;

            timestamp_a <= timestamp;

            if((timestamp - timestamp_b) <= COINCIDENCE_WINDOW)

                coincidence_count <= coincidence_count + 1'b1;

        end

        else if(event_b) begin

            count_b <= count_b + 1'b1;

            timestamp_b <= timestamp;

            if((timestamp - timestamp_a) <= COINCIDENCE_WINDOW)

                coincidence_count <= coincidence_count + 1'b1;

        end



    end


end




////////////////////////////////////////////////////////////////////////////////
// Bus acknowledge
////////////////////////////////////////////////////////////////////////////////


always_ff @(posedge clk_i) begin


    if(!rstn_i)

        sys_ack <= 1'b0;


    else

        sys_ack <= sys_wen | sys_ren;


end




////////////////////////////////////////////////////////////////////////////////
// Bus read
////////////////////////////////////////////////////////////////////////////////


always_comb begin


    sys_err = 1'b0;


    case(sys_addr[19:0])


        20'h00050:

            sys_rdata = id_reg;



        20'h00054:

            sys_rdata = coincidence_count;



        20'h0005C:

            sys_rdata = count_a;



        20'h00060:

            sys_rdata = count_b;



        20'h00068:

            sys_rdata = timestamp_a;



        20'h0006C:

            sys_rdata = timestamp_b;



        20'h00070:

            sys_rdata = timestamp;



        default:

            sys_rdata = 32'h00000000;



    endcase


end



endmodule