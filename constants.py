

cid2PackNumber          = b"\x39\x30"       # 0x90
cid2PackAnalogData      = b"\x34\x32"       # 0x42
cid2SoftwareVersion     = b"\x43\x31"       # 0xC1
cid2SerialNumber        = b"\x43\x32"       # 0xC2
cid2PackCapacity        = b"\x41\x36"       # 0xA6
cid2WarnInfo            = b"\x34\x34"       # 0x44


warningStates = {   b'00': "Normal",
                    b'01': "< low limit",
                    b'02': "> up limit",
                    b'F0': "other fault"} # 80H～EFH：user defined

protectState1 = {   1: "Above cell volt protect",
                    2: "Lower cell volt protect",
                    3: "Above total volt protect",
                    4: "Lower total volt protect",
                    5: "Charge current protect",
                    6: "Discharge current protect",
                    7: "Short circuit",
                    8: "undefined"}

protectState2 = {   1: "Above charge temp protect",
                    2: "Above discharge temp protect",
                    3: "Lower charge temp protect",
                    4: "Lower discharge temp protect",
                    5: "Above MOS temp protect",
                    6: "Above Env temp protect",
                    7: "Lower Env temp protect",
                    8: "Fully"}

instructionState = {1: "Current limit indicate ON",
                    2: "CFET indicate ON",
                    3: "DFET indicate ON",
                    4: "Pack indicate ON",
                    5: "Reverse indicate ON",
                    6: "ACin ON",
                    7: "Undefined",
                    8: "Heart indicate ON"}

controlState =     {1: "Buzzer warn function enabled",
                    2: "undefined",
                    3: "undefined",
                    4: "Current limit gear => low gear",
                    5: "Current limit function disabled",
                    6: "LED warn functiuon disabled",
                    7: "Undefined",
                    8: "Undefined"}

faultState =       {1: "Charge MOS fault",
                    2: "Discharge MOS fault",
                    3: "NTC fault (NTC)",
                    4: "Undefined",
                    5: "Cell fault",
                    6: "Sample fault",
                    7: "Undefined",
                    8: "Undefined"}

warnState1 =       {1: "Above cell volt warn",
                    2: "Lower cell volt warn",
                    3: "Above total volt warn",
                    4: "Lower total volt warn",
                    5: "Charge current warn",
                    6: "Discharge current warn",
                    7: "Undefined",
                    8: "Undefined"}

warnState2 =       {1: "Above charge temp warn",
                    2: "Above discharge temp warn",
                    3: "Low charge temp warn",
                    4: "Low discharge temp warn",
                    5: "High env temp warn",
                    6: "Low env temp warn",
                    7: "High MOS temp warn",
                    8: "Low power warn"}

w_byte = {
0: {1: {"type": "AS", "msg": "V DIF alarm"},
    2: {"type": "PS", "msg": "OVV PROT 10, No more lifting"},
    3: {"type": "PS", "msg": "Under V PROT 10, No more lifting"},
    4: {"type": "AS", "msg": "TEMP DIF alarm"},
    5: {"type": "FS", "msg": "Cell fail"},
    6: {"type": "FS", "msg": "Blown fuse"},
    7: {"type": "FS", "msg": "Voltage diff protected"},
    8: {"type": "FS", "msg": "SYS sleep"}
    },
1: {1: {"type": "PS", "msg": "Cell over V PROT"},
    2: {"type": "PS", "msg": "Cell under V PROT"},
    3: {"type": "PS", "msg": "TOT over V PROT"},
    4: {"type": "PS", "msg": "TOT under V PROT"},
    5: {"type": "AS", "msg": "Cell high V alarm"},
    6: {"type": "AS", "msg": "Cell low V alarm"},
    7: {"type": "AS", "msg": "Pack high V alarm"},
    8: {"type": "AS", "msg": "Pack low V alarm"}
    },
2: {1: {"type": "PS", "msg": "OC 10, No more lifting"},
    2: {"type": "PS", "msg": "RVS connection"},
    3: {"type": "N/A", "msg": "N/A"},
    4: {"type": "INFO", "msg": "Current limit"},
    5: {"type": "N/A", "msg": "N/A"},
    6: {"type": "N/A", "msg": "N/A"},
    7: {"type": "N/A", "msg": "N/A"},
    8: {"type": "N/A", "msg": "N/A"}
    },
3: {1: {"type": "INFO", "msg": "Charging"},
    2: {"type": "INFO", "msg": "Discharging"},
    3: {"type": "PS", "msg": "Charge Over C PROT"},
    4: {"type": "PS", "msg": "Short circuit PROT"},
    5: {"type": "PS", "msg": "DISCH over C 1 PROT"},
    6: {"type": "PS", "msg": "DISCH over C 2 PROT"},
    7: {"type": "PS", "msg": "Charge current alarm"},
    8: {"type": "PS", "msg": "DISCH current alarm"}
    },
4: {1: {"type": "AS", "msg": "Charge High TEMP alarm"},
    2: {"type": "AS", "msg": "Charge Low TEMP alarm"},
    3: {"type": "AS", "msg": "DISCH High TEMP alarm"},
    4: {"type": "AS", "msg": "DISCH Low TEMP alarm"},
    5: {"type": "AS", "msg": "ENV High TEMP alarm"},
    6: {"type": "AS", "msg": "ENV Low TEMP alarm"},
    7: {"type": "AS", "msg": "Power High TEMP_alarm"},
    8: {"type": "AS", "msg": "Power Low TEMP_alarm"}
    },
5: {1: {"type": "PS", "msg": "Charge High TEMP PROT"},
    2: {"type": "PS", "msg": "Charge Low TEMP PROT"},
    3: {"type": "PS", "msg": "DISCH High TEMP PROT"},
    4: {"type": "PS", "msg": "DISCH Low TEMP PROT"},
    5: {"type": "PS", "msg": "ENV High TEMP PROT"},
    6: {"type": "PS", "msg": "ENV Low TEMP PROT"},
    7: {"type": "PS", "msg": "MOS High TEMP PROT"},
    8: {"type": "PS", "msg": "Power Low TEMP PROT"}
    },
6: {1: {"type": "PS", "msg": "MOS High TEMP PROT"},
    2: {"type": "FS", "msg": "Heating film fail"},
    3: {"type": "FS", "msg": "Limit board fail"},
    4: {"type": "FS", "msg": "Sampling fail"},
    5: {"type": "FS", "msg": "Cell fail"},
    6: {"type": "FS", "msg": "NTC fail"},
    7: {"type": "FS", "msg": "Charge MOS fail"},
    8: {"type": "FS", "msg": "DISCH MOS fail"}
    },
7: {1: {"type": "N/A", "msg": "N/A"},
    2: {"type": "AS", "msg": "CHG_FET fail alarm"},
    3: {"type": "AS", "msg": "Extern SD fail alarm"},
    4: {"type": "AS", "msg": "SPI fail alarm"},
    5: {"type": "AS", "msg": "E2P fail alarm"},
    6: {"type": "AS", "msg": "LED alarm"},
    7: {"type": "AS", "msg": "Buzzer alarm"},
    8: {"type": "AS", "msg": "Low BAT alarm"}
    },
8: {1: {"type": "N/A", "msg": "N/A"},
    2: {"type": "N/A", "msg": "N/A"},
    3: {"type": "N/A", "msg": "N/A"},
    4: {"type": "AS", "msg": "LED alarm status"},
    5: {"type": "N/A", "msg": "N/A"},
    6: {"type": "FS", "msg": "AFE chip fail"},
    7: {"type": "AS", "msg": "AFE alarm pin fail"},
    8: {"type": "PS", "msg": "Low BAT PROT"}
    },
9: {1: {"type": "INFO", "msg": "Charge MOS"},
    2: {"type": "INFO", "msg": "DISCH MOS"},
    3: {"type": "FS", "msg": "Charge FET fail"},
    4: {"type": "FS", "msg": "DISCH FET fail"},
    5: {"type": "N/A", "msg": "N/A"},
    6: {"type": "N/A", "msg": "N/A"},
    7: {"type": "INFO", "msg": "Heating"},
    8: {"type": "N/A", "msg": "N/A"}
    },
31: {1: {"type": "FS", "msg": "crystal oscillator fail"},
    2: {"type": "FS", "msg": "EEP fail"},
    3: {"type": "N/A", "msg": "N/A"},
    4: {"type": "N/A", "msg": "N/A"},
    5: {"type": "N/A", "msg": "N/A"},
    6: {"type": "N/A", "msg": "N/A"},
    7: {"type": "N/A", "msg": "N/A"},
    8: {"type": "N/A", "msg": "N/A"}
     },
32: {1: {"type": "PS", "msg": "Battery Locked"},
    2: {"type": "PS", "msg": "Anti Theft Locked"},
    3: {"type": "PS", "msg": "Battery Locked"},
    4: {"type": "N/A", "msg": "N/A"},
    5: {"type": "N/A", "msg": "N/A"},
    6: {"type": "N/A", "msg": "N/A"},
    7: {"type": "N/A", "msg": "N/A"},
    8: {"type": "N/A", "msg": "N/A"}
    }
}
