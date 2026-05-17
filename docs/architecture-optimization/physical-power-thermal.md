# Physical, Power, Thermal, Package, PCB, Manufacturing Optimization Work Order

## OpenLane/OpenROAD

OpenLane/OpenROAD runs are useful only when the exact run directory, tool image,
PDK, corners, constraints, and reports are archived. Preflight success is not
PD closure.

## IR-drop and PDN

IR-drop, EM, PDN impedance, rail current, and decoupling evidence must be tied
to selected workloads, voltage corners, package assumptions, board stackup, and
regulator limits.

## thermal

Thermal closure requires post-route power, package and board model, enclosure
assumptions, battery/PMIC losses, measurement points, stop conditions, chamber
data, and skin-temperature limits.

## DFT

DFT, boundary scan, manufacturing test, serialization, calibration, and debug
lock state must have station transcripts before fabrication or production
claims.
