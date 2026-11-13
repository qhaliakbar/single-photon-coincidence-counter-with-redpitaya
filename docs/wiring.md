# Wiring and safety

## Connections

The two detector signals go to the **E1 extension connector** of the Red Pitaya
STEMlab 125-14.

| Signal    | Red Pitaya pin                           | E1 connector pin |
|-----------|------------------------------------------|------------------|
| Channel A | DIO0_P (also the external trigger input) | 3                |
| Channel B | DIO1_P                                   | 5                |
| Ground    | GND                                      | 25 or 26         |

Connect the detector grounds to a GND pin of the same connector.
DIO0_P doubles as the Red Pitaya's external trigger input. This does not
affect the coincidence counter.

## Warning: 3.3 V logic only

All digital I/O pins are **LVCMOS 3.3 V**. According to Red Pitaya's
documentation, the absolute maximum input voltage is **3.3 V + 0.55 V**
(minimum -0.40 V). Anything higher can permanently damage the board.

- Many single-photon detector modules output **5 V TTL** pulses. Check the
  output level of your detector before connecting it, and use a level shifter
  or voltage divider if needed.
- Never connect a signal that can exceed these limits, even briefly.
- These pins have no built-in overvoltage protection.

## Signal requirements

- The design counts **rising edges**.
- The FPGA samples at 125 MHz (8 ns). Pulses shorter than one clock period
  (8 ns) may be missed.
- Each input passes through a two-stage synchroniser, so a pulse takes a few
  clock cycles to be registered. Both channels have the same delay.

## Where to find the official pinout

Red Pitaya publishes the full pinout and electrical specifications on its
website. These links open Red Pitaya's pages; the picture is hosted by Red
Pitaya and is not stored in this repository. Check them for the latest
information.

- STEMlab 125-14 hardware page (pinout tables, electrical limits):
  <https://redpitaya.readthedocs.io/en/latest/developerGuide/hardware/ORIG_GEN/125-14/top.html#top-125-14>
- Pinout picture:
  <https://redpitaya.readthedocs.io/en/latest/_images/Red_Pitaya_pinout.jpg>
