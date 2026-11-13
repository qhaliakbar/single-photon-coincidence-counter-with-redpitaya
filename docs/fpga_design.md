# FPGA design notes

`fpga/red_pitaya_coincidence.sv` is the coincidence-counting module. It counts
rising edges on two inputs (A and B) and the coincidences between them, using a
fixed 80 ns window (10 clock ticks at 125 MHz).

## How the bitstream was built

The bitstream in `bitstream/red_pitaya_top.bit.bin` was generated from this
code:

- Tool: Vivado 2020.1
- Base project: the official Red Pitaya FPGA project
  (<https://github.com/RedPitaya/RedPitaya-FPGA>), project `v0.94`,
  `MODEL=Z10` (STEMlab 125-14, Zynq 7010).
- `red_pitaya_coincidence` is **instantiated in `red_pitaya_top.sv`**, Red
  Pitaya's top-level file. That file is not included in this repository because
  it belongs to Red Pitaya. Only the lines added for this module are shown below.
- The bitstream is only for this board model. Other Red Pitaya models
  (Z20, Gen 2 and so on) would need a rebuild.

Rebuilding requires Vivado and the official Red Pitaya FPGA project. The
build steps are not documented here.

## Lines added to `red_pitaya_top.sv`

```systemverilog
// local signals
logic coin_in_a;
logic coin_in_b;

assign coin_in_a = exp_p_in[0];   // DIO0_P
assign coin_in_b = exp_p_in[1];   // DIO1_P

red_pitaya_coincidence i_coincidence (
    .clk_i      (adc_clk),
    .rstn_i     (adc_rstn),
    .coin_in_a  (coin_in_a),
    .coin_in_b  (coin_in_b),
    .sys_addr   (sys[3].addr),
    .sys_wdata  (sys[3].wdata),
    .sys_wen    (sys[3].wen),
    .sys_ren    (sys[3].ren),
    .sys_rdata  (sys[3].rdata),
    .sys_err    (sys[3].err),
    .sys_ack    (sys[3].ack)
);
```

## Register map

The module sits on system bus region `sys[3]`, base address `0x40300000`.

| Address      | Content                              |
|--------------|--------------------------------------|
| `0x40300050` | ID (`0x434F494E`, ASCII "COIN")      |
| `0x40300054` | Coincidence counter (32-bit)         |
| `0x4030005C` | Channel A event counter (32-bit)     |
| `0x40300060` | Channel B event counter (32-bit)     |
| `0x40300068` | Timestamp of last A event            |
| `0x4030006C` | Timestamp of last B event            |
| `0x40300070` | Free-running timestamp (125 MHz)     |

The acquisition script (`software/coincidence_read_v2.py`) reads the ID and the
three counters.

## License

See `THIRD_PARTY_NOTICES.md` for the Red Pitaya license that applies to the
base project.
