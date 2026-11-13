#!/usr/bin/env python3

import time
import csv
import argparse
import subprocess


##################################################
# FPGA register map
##################################################

REG_ID          = "0x40300050"
REG_COINC       = "0x40300054"
REG_COUNT_A     = "0x4030005C"
REG_COUNT_B     = "0x40300060"


COUNTER_MAX = 2**32



##################################################
# Arguments
##################################################

parser = argparse.ArgumentParser()


parser.add_argument(
    "--time",
    type=float,
    default=60
)


parser.add_argument(
    "--file",
    default="coincidence_data.csv"
)


args = parser.parse_args()



##################################################
# FPGA read
##################################################

def monitor(address):

    result = subprocess.check_output(
        [
            "/opt/redpitaya/bin/monitor",
            address
        ]
    )

    value = int(
        result.decode().strip(),
        16
    )

    return value & 0xffffffff



##################################################
# Counter difference with rollover protection
##################################################

def counter_difference(new, old):

    if new >= old:

        return new-old

    else:

        # 32-bit rollover

        return (
            COUNTER_MAX-old
        ) + new



##################################################
# FPGA check
##################################################

fpga_id = monitor(REG_ID)

print(
    "FPGA_ID",
    hex(fpga_id),
    flush=True
)



##################################################
# Initial values
##################################################

previous_coin = monitor(REG_COINC)

previous_a = monitor(REG_COUNT_A)

previous_b = monitor(REG_COUNT_B)


previous_time=time.time()

start=previous_time


data=[]



print(
    "TIME,COINC_RATE,A_RATE,B_RATE",
    flush=True
)



##################################################
# Acquisition
##################################################

while True:


    read_time=time.time()


    elapsed=read_time-start


    if elapsed >= args.time:

        break



    coin=monitor(REG_COINC)

    count_a=monitor(REG_COUNT_A)

    count_b=monitor(REG_COUNT_B)



    dt=read_time-previous_time



    if dt <= 0:

        continue



    ##################################################
    # Differences
    ##################################################

    dcoin = counter_difference(
        coin,
        previous_coin
    )


    da = counter_difference(
        count_a,
        previous_a
    )


    db = counter_difference(
        count_b,
        previous_b
    )



    ##################################################
    # Rates
    ##################################################

    rate_coin=dcoin/dt

    rate_a=da/dt

    rate_b=db/dt



    row=[

        elapsed,
        rate_coin,
        rate_a,
        rate_b

    ]

    data.append(row)



    ##################################################
    # Send to GUI
    ##################################################

    print(
        f"{elapsed:.3f},"
        f"{rate_coin:.3f},"
        f"{rate_a:.3f},"
        f"{rate_b:.3f}",
        flush=True
    )



    previous_coin=coin

    previous_a=count_a

    previous_b=count_b

    previous_time=read_time



    time.sleep(0.25)




##################################################
# Save
##################################################

with open(
    args.file,
    "w",
    newline=""
) as f:


    writer=csv.writer(f)


    writer.writerow(
        [
            "Time_s",
            "Coincidence_rate_Hz",
            "Singles_A_rate_Hz",
            "Singles_B_rate_Hz"
        ]
    )


    writer.writerows(data)



print(
    "FINISHED",
    flush=True
)


print(
    "FILE:",
    args.file,
    flush=True
)
