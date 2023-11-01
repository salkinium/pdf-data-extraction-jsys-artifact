# Copyright (c) 2022, Niklas Hauser
#
# This file is part of the modm-data project.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
# -----------------------------------------------------------------------------

import re, sys, json
sys.path.extend([".", "ext/cmsis/svd/python", "ext/modm-devices"])
from pathlib import Path
from deepdiff import DeepDiff
from deepdiff.model import PrettyOrderedSet
from collections import defaultdict
from anytree import RenderTree
from os.path import relpath

from modm_data.cubemx import devices as modm_devices
from modm_data.header2svd.stmicro.tree import _normalize_order
from modm_data.svd.stmicro import *
from modm_data.svd import read_svd
from cmsis_svd.parser import SVDParser


SUBSTITUTIONS = {
    # Peripheral Level
    (r"STM32.*", r"FIREWALL"): "FW",
    (r"STM32.*", r"ADC\d+_COMMON"): "ADC_Common",
    (r"STM32.*", r"HASH_DIGEST"): "HASH",
    (r"STM32.*", r"DSIHOST"): "DSI",
    (r"STM32.*", r"USB_"): "USB",

    # Register Level
    r"sTxMailBox\.(\d+)\.(.*?)R": r"\2\1R",
    r"sFIFOMailBox\.(\d+)\.(.*?)R": r"\2\1R",
    r"sFilterRegister\.(\d+)\.FR(\d)": r"F\1R\2",
    r"AFR.0": "AFRL",
    r"AFR.1": "AFRH",
    r"DFSDM(\d)_": r"FLT\1",
    r"APB(\d)?_": r"APB\1",
    (r":SAI\d:", r"(A|B)(CR\d|FRCR|SR|IM|SLOTR|CLRFR|RB|DR)"): r"\2\1",
    r"^(\d)(RI|RDT|RDL|RDH)R": r"\2\1R",
    r"^CH(\d)(.*)": r"CH\2\1",
    r"CHWDATAR": "CHWDATR",
    r"^CH(.*?)(\d+)R(\d?)": r"CH\1R\3\2",
    r"AWSCD(\d)R": r"AWSCDR\1",
    r"CSR\.(\d+)": r"CSR\1",
    (":HASH:", r"HR\.(\d+)"): r"HR\1",
    (":HASH:", r"HRA(\d+)"): r"HR\1",
    "OSPEEDER": "OSPEEDR",
    (":SAI", r"IMR([AB])"): r"IM\1",
    r"IT_LINE_SR\.(\d+)": r"ITLINE\1",
    (r":DMA\d:", r"S(\d+)(.*)"): r"\2\1",
    (":MDMA", r"C(\d+)(.*)"): r"C\2\1",
    (":DMAMUX", r"C(\d+)(.*)"): r"C\2\1",
    (":LTDC", r"L(\d+)(.*)"): r"\2\1",
    ("HSEM", "."): "",
    ("JPEG", "."): "_",
    ("ETH|Ethernet", "x"): "",
    ("HRTIM", r"TIM[A-F]"): "TIMx",
    ("HRTIM", r"[A-F]R"): "xR",
    ("HRTIM", r"[A-F]CR"): "xCR",
    ("HRTIM", r"[A-F](\d)R"): r"x\1R",
    (":SPI", r"CGFR"): "CFGR",
    (":DMA2D:", r"CLUT\.(\d+)"): r"CLUT\1",
}


SUBSTITUTIONS_INT = {
    # Register Level
    r"EXTICR\.(\d+)": lambda i: f"EXTICR{i+1}",
    r"DIEPTXF\.(\d+)": lambda i: f"DIEPTXF{i+1}",
    r"BTCR\.(\d+)": lambda i: f"B{'CT'[i%2]}R{i//2+1}",
    r"IOGXCR\.(\d+)": lambda i: f"IOG{i+1}CR",
    r"RAM\.(\d+)": lambda i: f"RAM_COM{i//2}",
    r"LUT\.(\d+)": lambda i: f"LUT{i//2}{'LH'[i%2]}",
    r"WPCR\.(\d+)": lambda i: f"WPCR{i+1}",
    r"PCR\.(\d+)": lambda i: f"P{i+1}CR",
    r"SDCR\.(\d+)": lambda i: f"SDCR{i+1}",
    (":RAMECC", r"M(\d)(.*)"): lambda i, s: f"{s}{int(i)+1}",
}


def _subs(context, name):
    for find, replace in SUBSTITUTIONS.items():
        if isinstance(find, tuple):
            if re.search(find[0], context) is None: continue
            find = find[1]
        name = re.sub(find, replace, name)

    for find, replace in SUBSTITUTIONS_INT.items():
        if isinstance(find, tuple):
            if re.search(find[0], context) is None: continue
            find = find[1]
        if match := re.match(find, name):
            groups = match.groups()
            if len(groups) == 1:
                name = replace(int(groups[0]))
            else:
                name = replace(*groups)

    return name


def _contains_eachother(values):
    for name in values:
        new_set = {n for n in values if name not in n} | {name}
        if len(new_set) == 1:
            return True
    return False


def _compare_values(addr, names, print_diff=True):
    set_names = {v.name for v in names.values()}
    if len(set_names) == 1: return None
    if _contains_eachother(set_names): return None

    parents = {v.parent.name for v in names.values()}
    context = f":{':'.join(sorted(parents))}:"
    subs_names = {name: _subs(context, name) for name in set_names}
    set_names = set(subs_names.values())
    if _contains_eachother(set_names): return None

    diffs = defaultdict(set)
    for s,n in names.items():
        diffs[subs_names[n.name]].add(s)
    diffs = dict(diffs)

    if print_diff: print(hex(addr), context, diffs)
    return (addr, parents, diffs)


def _compare_sources(rm_map, cm_map, hd_map):
    # print(RenderTree(cm_map, maxlevel=2))
    # print(RenderTree(rm_map, maxlevel=2))
    # print(RenderTree(hd_map, maxlevel=2))

    report = defaultdict(list)

    # Compare peripherals and their register structures
    peripheral_addr = defaultdict(dict)
    register_addr = defaultdict(dict)
    bit_addr = defaultdict(dict)
    def _percmp(dmap, key):
        for dper in dmap.children:
            for addr in range(dper.address, dper.address+4):
                peripheral_addr[addr][key] = dper
                report[f"number_peripherals_{key}"].append(addr)
            for dreg in dper.children:
                for addr in dreg.addresses:
                    register_addr[addr][key] = dreg
                    report[f"number_registers_{key}"].append(addr)
                for dbit in dreg.children:
                    for addr in dbit.bit_addresses:
                        bit_addr[addr][key] = dbit
                        report[f"number_bits_{key}"].append(addr)
        report[f"number_peripherals_{key}"] = len(set(report[f"number_peripherals_{key}"]))
        report[f"number_registers_{key}"] = len(set(report[f"number_registers_{key}"]))
        report[f"number_bits_{key}"] = len(set(report[f"number_bits_{key}"]))
    _percmp(rm_map, "rm")
    _percmp(cm_map, "cm")
    _percmp(hd_map, "hd")
    report["number_peripherals"] = len(peripheral_addr)
    report["number_registers"] = len(register_addr)
    report["number_bits"] = len(bit_addr)

    for addr, pers in peripheral_addr.items():
        if diff := _compare_values(addr, pers):
            report["peripherals"].append(diff)
        elif len(pers) == 3:
            report["identical_peripherals"].append(addr)
        if len(pers) >= 2:
            report["intersection_peripherals"].append(addr)

        # per_reg_addr = defaultdict(lambda: defaultdict(set))
        # for key, dper in pers.items():
        #     for dreg in dper.children:
        #         per_reg_addr[dreg.offset][key] = dreg
        # for offs in sorted(per_reg_addr):
        #     regs = per_reg_addr[offs]
        #     if diff := _compare_values(offs, regs):
        #         report["peripheral_registers"].append(diff)

    for addr, regs in register_addr.items():
        if diff := _compare_values(addr, regs):
            report["registers"].append(diff)
        elif len(regs) == 3:
            report["identical_registers"].append(addr)
        if len(regs) >= 2:
            report["intersection_registers"].append(addr)
        # reg_bit_addr = defaultdict(lambda: defaultdict(set))
        # for key, dreg in regs.items():
        #     for dbit in dreg.children:
        #         reg_bit_addr[dbit.position][key] = dbit
        # for offs in sorted(reg_bit_addr):
        #     bits = reg_bit_addr[offs]
        #     if diff := _compare_values(offs, bits, print_diff=False):
        #         report["register_bits"].append(diff)

    for addr, bits in bit_addr.items():
        if diff := _compare_values(addr, bits, print_diff=False):
            report["bits"].append(diff)
        elif len(bits) == 3:
            report["identical_bits"].append(addr)
        if len(bits) >= 2:
            report["intersection_bits"].append(addr)

    report["identical_peripherals"] = len(report["identical_peripherals"])
    report["identical_registers"] = len(report["identical_registers"])
    report["identical_bits"] = len(report["identical_bits"])

    report["intersection_peripherals"] = len(report["intersection_peripherals"])
    report["intersection_registers"] = len(report["intersection_registers"])
    report["intersection_bits"] = len(report["intersection_bits"])

    return dict(report)


class SetEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (set, PrettyOrderedSet)):
            return list(sorted(obj))
        return json.JSONEncoder.default(self, obj)


def compare_svds():
    reports = {}
    ignored_devices = [
        "stm32g071.6",
        "stm32g441",
        "stm32g471",
        "stm32l041c4",
        "stm32l485",
        "stm32wb5m",
        "stm32u5",
        "stm32l5",
    ]
    all_devices = set(d for d in modm_devices() if not any(re.match(u, d.string) for u in ignored_devices))
    print("Total devices", len(all_devices))
    reports["number_devices_total"] = len(modm_devices())
    reports["number_devices"] = len(all_devices)
    hd_files, cm_files, rm_files = svd_file_devices()
    device_files = defaultdict(list)

    hd_devices = set()
    for file, devices in hd_files.items():
        hd_devices.update(devices)
        # print(file)
        # print(devices)

    print("Header files device coverage")
    hd_missing = all_devices - hd_devices
    print(len(hd_missing), hd_missing)
    reports["number_hd_missing"] = len(hd_missing)
    hd_missing = list(sorted((d for d in hd_missing if d.family not in ["wl", "wb"]),
                             key=lambda d: d.string))
    print(len(hd_missing), hd_missing)
    reports["number_hd_missing_clean"] = len(hd_missing)
    print()


    cm_devices = set()
    for file, devices in cm_files.items():
        cm_devices.update(devices)
        # print(file)
        # print(devices)

    print("CMSIS SVD files device coverage")
    cm_missing = all_devices - cm_devices
    print(len(cm_missing), list(sorted(cm_missing, key=lambda d: d.string)))
    reports["number_cm_missing"] = len(cm_missing)
    print()

    rm_devices = set()
    for file, devices in rm_files.items():
        rm_devices.update(devices)
        # print(file)
        # print(devices)

    print("Reference Manual files device coverage")
    rm_missing = all_devices - rm_devices
    print(len(rm_missing), rm_missing)
    print()
    reports["number_rm_missing"] = len(rm_missing)
    reports["devices"] = {}

    result_cache = {}
    for device, files in svd_device_files().items():
        result_cache_key = (files.get("rm"), files.get("cm"), files.get("hd"))
        if None in result_cache_key:
            reports["devices"][device.string] = "Missing"
            print(device, "MISSING!!!")
            continue
        print(device, relpath(result_cache_key[0]),
              relpath(result_cache_key[1]), relpath(result_cache_key[2]))
        if result_cache_key not in result_cache:
            rm_map = read_svd(files["rm"])
            cm_map = _normalize_order(read_svd(files["cm"]))
            hd_map = read_svd(files["hd"])
            report = _compare_sources(rm_map, cm_map, hd_map)
            result_cache[result_cache_key] = (device, report)
            report["rm_file"] = str(files["rm"])
            report["cm_file"] = str(files["cm"])
            report["hd_file"] = str(files["hd"])
            reports["devices"][device.string] = report
        else:
            other_device, report = result_cache[result_cache_key]
            reports["devices"][device.string] = other_device.string



    return reports


def eval_devices():
    ignored_devices = [
        "stm32g071.6",
        "stm32g441",
        "stm32g471",
        "stm32l041c4",
        "stm32l485",
        "stm32wb.m",
        "stm32wl.m",
        "stm32u5",
        "stm32l5",
        "stm32c0",
        "stm32h5",
        "stm32f1",
    ]

    all_devices = set(d for d in modm_devices() if not any(re.match(u, d.string) for u in ignored_devices))
    print("number_devices_total", len(all_devices))
    all_devices_str = set(d.string.split("@")[0] for d in all_devices)
    print("Total devices", len(all_devices_str))

    hd_files, cm_files, rm_files = svd_file_devices()
    device_files = defaultdict(list)

    hd_devices = set()
    for file, devices in hd_files.items():
        hd_devices.update(devices)
        # print(file)
        # print(devices)

    print("Header files device coverage")
    hd_missing = all_devices - hd_devices
    hd_missing_str = set(d.string.split("@")[0] for d in hd_missing)
    print(len(hd_missing), hd_missing)
    print("number_hd_missing", len(hd_missing))
    print("number_hd_missing_str", len(hd_missing_str))

    hd_missing_clean = list(sorted((d for d in hd_missing if d.family not in ["wl", "wb"]),
                             key=lambda d: d.string))
    print(len(hd_missing_clean), hd_missing_clean)
    print("number_hd_missing_clean", len(hd_missing_clean))
    print()


    cm_devices = set()
    for file, devices in cm_files.items():
        cm_devices.update(devices)
        # print(file)
        # print(devices)

    print("CMSIS SVD files device coverage")
    cm_missing = all_devices - cm_devices
    cm_missing_str = set(d.string.split("@")[0] for d in cm_missing)
    print(len(cm_missing), list(sorted(cm_missing, key=lambda d: d.string)))
    print("number_cm_missing", len(cm_missing))
    print("number_cm_missing_str", len(cm_missing_str))
    print()

    rm_devices = set()
    for file, devices in rm_files.items():
        rm_devices.update(devices)
        # print(file)
        # print(devices)

    print("Reference Manual files device coverage")
    rm_missing = all_devices - rm_devices
    print(len(rm_missing), rm_missing)
    print()
    print("number_rm_missing", len(rm_missing))

    compared = all_devices - rm_missing - cm_missing - hd_missing
    compared_str = set(d.string.split("@")[0] for d in compared)
    print("number_compared", len(compared))
    print("number_compared_str", len(compared_str))
    # exit(1)



def eval_svds(reports):
    number_devices_total = reports["number_devices_total"]
    number_devices = reports["number_devices"]
    print(f"Total Devices = {number_devices} / {number_devices_total} ({number_devices/number_devices_total*100:.1f}%)")

    number_hd_missing = reports["number_hd_missing"]
    number_hd_missing_clean = reports["number_hd_missing_clean"]
    print(f"Missing from Header = {number_hd_missing} (-WL|B = {number_hd_missing_clean})")

    number_cm_missing = reports["number_cm_missing"]
    print(f"Missing from CMSIS-SVD = {number_cm_missing}")

    number_rm_missing = reports["number_rm_missing"]
    print(f"Missing from Reference Manuals = {number_rm_missing}")

    devices = reports["devices"]
    str_devices = [v for v in reports["devices"].values() if isinstance(v, str)]
    missing_devices = [v for v in str_devices if "Missing" in v]
    print(f"Total compared devices = {len(devices)}")
    print(f"Total compared devices delegated = {len(str_devices)}")
    print(f"Total compared devices missing = {len(missing_devices)}")

    comparisons = {k:v for k,v in reports["devices"].items() if not isinstance(v, str)}
    print(f"Unique comparisons = {len(comparisons)}")


    aggr_number_peripherals = []
    aggr_number_registers = []
    aggr_number_bits = []

    aggr_number_peripherals_cm = {}
    aggr_number_peripherals_hd = {}
    aggr_number_peripherals_rm = {}

    aggr_number_registers_cm = {}
    aggr_number_registers_hd = {}
    aggr_number_registers_rm = {}

    aggr_number_bits_cm = {}
    aggr_number_bits_hd = {}
    aggr_number_bits_rm = {}

    aggr_identical_peripherals = []
    aggr_identical_registers = []
    aggr_identical_bits = []

    aggr_intersection_peripherals = []
    aggr_intersection_registers = []
    aggr_intersection_bits = []

    diff_number_peripherals = {}
    diff_number_registers = {}
    diff_number_bits = {}

    sources_peripherals = defaultdict(list)
    sources_registers = defaultdict(list)
    sources_bits = defaultdict(list)

    issues_peripherals = defaultdict(list)
    names_peripherals = defaultdict(list)
    names_registers = defaultdict(list)

    for device, report in comparisons.items():
        # print()
        # print(device.upper())
        number_peripherals = report["number_peripherals"]
        number_registers = report["number_registers"]
        number_bits = report["number_bits"]
        # print(f"Peripherals = {number_peripherals}, Registers = {number_registers}, Bits = {number_bits}")
        aggr_number_peripherals.append(number_peripherals)
        aggr_number_registers.append(number_registers)
        aggr_number_bits.append(number_bits)

        aggr_number_peripherals_cm[device] = report["number_peripherals_cm"]
        aggr_number_peripherals_hd[device] = report["number_peripherals_hd"]
        aggr_number_peripherals_rm[device] = report["number_peripherals_rm"]

        # print(f"Registers by Source: cm={number_registers_cm}, hd={number_registers_hd}, rm={number_registers_rm}")
        aggr_number_registers_cm[device] = report["number_registers_cm"]
        aggr_number_registers_hd[device] = report["number_registers_hd"]
        aggr_number_registers_rm[device] = report["number_registers_rm"]

        # print(f"Registers by Source: cm={number_bits_cm}, hd={number_bits_hd}, rm={number_bits_rm}")
        aggr_number_bits_cm[device] = report["number_bits_cm"]
        aggr_number_bits_hd[device] = report["number_bits_hd"]
        aggr_number_bits_rm[device] = report["number_bits_rm"]

        identical_peripherals = report["identical_peripherals"]
        identical_registers = report["identical_registers"]
        identical_bits = report["identical_bits"]
        # print(f"Identical Peripherals = {identical_peripherals}, Registers = {identical_registers}, Bits = {identical_bits}")
        aggr_identical_peripherals.append(identical_peripherals)
        aggr_identical_registers.append(identical_registers)
        aggr_identical_bits.append(identical_bits)

        aggr_intersection_peripherals.append(report["intersection_peripherals"])
        aggr_intersection_registers.append(report["intersection_registers"])
        aggr_intersection_bits.append(report["intersection_bits"])

        peripherals = report.get("peripherals", {})
        peripheral_registers = report.get("peripheral_registers", {})
        registers = report.get("registers", {})
        bits = report.get("bits", {})

        # print(f"Diffs: Peripherals = {len(peripherals)}, Peripheral Registers = {len(peripheral_registers)}")
        # print(f"Diffs: Registers = {len(registers)}, Bits = {len(bits)}")

        diff_number_peripherals[device] = len(peripherals)
        diff_number_registers[device] = len(registers)
        diff_number_bits[device] = len(bits)

        for (addr, devices, names) in peripherals:
            sources_peripherals[device].append(["+".join(sorted(n)) for n in names.values()])

        for (addr, peripherals, names) in registers:
            issues_peripherals[device].extend(peripherals)
            names_peripherals[device].append(("+".join(sorted(peripherals)), "+".join(sorted(names))))
            sources_registers[device].append(["+".join(sorted(n)) for n in names.values()])

        for (addr, registers, names) in bits:
            sources_bits[device].append(["+".join(sorted(n)) for n in names.values()])
            names_registers[device].append(("+".join(sorted(registers)), "+".join(sorted(names))))

    print()
    print()
    print(f"Peripherals = {sum(aggr_number_peripherals)} [{min(aggr_number_peripherals)}, {max(aggr_number_peripherals)}]")
    print(f"Registers = {sum(aggr_number_registers)} [{min(aggr_number_registers)}, {max(aggr_number_registers)}]")
    print(f"Bits = {sum(aggr_number_bits)} [{min(aggr_number_bits)}, {max(aggr_number_bits)}]")
    print()
    print(f"Peripherals by Source: "
          f"cm={sum(aggr_number_peripherals_cm.values())}, "
          f"hd={sum(aggr_number_peripherals_hd.values())}, "
          f"rm={sum(aggr_number_peripherals_rm.values())}")
    print(f"Peripherals by Source: "
          f"cm={sum(aggr_number_peripherals_cm.values())/sum(aggr_number_peripherals)*100:.1f}%, "
          f"hd={sum(aggr_number_peripherals_hd.values())/sum(aggr_number_peripherals)*100:.1f}%, "
          f"rm={sum(aggr_number_peripherals_rm.values())/sum(aggr_number_peripherals)*100:.1f}%")
    print()
    print(f"Registers by Source: "
          f"cm={sum(aggr_number_registers_cm.values())}, "
          f"hd={sum(aggr_number_registers_hd.values())}, "
          f"rm={sum(aggr_number_registers_rm.values())}")
    print(f"Registers by Source: "
          f"cm={sum(aggr_number_registers_cm.values())/sum(aggr_number_registers)*100:.1f}%, "
          f"hd={sum(aggr_number_registers_hd.values())/sum(aggr_number_registers)*100:.1f}%, "
          f"rm={sum(aggr_number_registers_rm.values())/sum(aggr_number_registers)*100:.1f}%")
    print()
    print(f"bits by Source: "
          f"cm={sum(aggr_number_bits_cm.values())}, "
          f"hd={sum(aggr_number_bits_hd.values())}, "
          f"rm={sum(aggr_number_bits_rm.values())}")
    print(f"bits by Source: "
          f"cm={sum(aggr_number_bits_cm.values())/sum(aggr_number_bits)*100:.1f}%, "
          f"hd={sum(aggr_number_bits_hd.values())/sum(aggr_number_bits)*100:.1f}%, "
          f"rm={sum(aggr_number_bits_rm.values())/sum(aggr_number_bits)*100:.1f}%")

    print()
    print(f"Identical Peripherals = {sum(aggr_identical_peripherals)}/{sum(aggr_number_peripherals)} "
          f"{sum(aggr_identical_peripherals)/sum(aggr_number_peripherals)*100:.1f}%")
    print(f"Identical Registers = {sum(aggr_identical_registers)}/{sum(aggr_number_registers)} "
          f"{sum(aggr_identical_registers)/sum(aggr_number_registers)*100:.1f}%")
    print(f"Identical Bits = {sum(aggr_identical_bits)}/{sum(aggr_number_bits)} "
          f"{sum(aggr_identical_bits)/sum(aggr_number_bits)*100:.1f}%")
    print()
    print(f"Intersection Peripherals = {sum(aggr_intersection_peripherals)}/{sum(aggr_number_peripherals)} "
          f"{sum(aggr_intersection_peripherals)/sum(aggr_number_peripherals)*100:.1f}%")
    print(f"Intersection Registers = {sum(aggr_intersection_registers)}/{sum(aggr_number_registers)} "
          f"{sum(aggr_intersection_registers)/sum(aggr_number_registers)*100:.1f}%")
    print(f"Intersection Bits = {sum(aggr_intersection_bits)}/{sum(aggr_number_bits)} "
          f"{sum(aggr_intersection_bits)/sum(aggr_number_bits)*100:.1f}%")
    print()

    print()
    print(f"Error Peripherals = {sum(diff_number_peripherals.values())}/{sum(aggr_number_peripherals)} "
          f"{100-sum(diff_number_peripherals.values())/sum(aggr_number_peripherals)*100:.1f}%")
    print(f"Error Registers = {sum(diff_number_registers.values())}/{sum(aggr_number_registers)} "
          f"{100-sum(diff_number_registers.values())/sum(aggr_number_registers)*100:.1f}%")
    print(f"Error Bits = {sum(diff_number_bits.values())}/{sum(aggr_number_bits)} "
          f"{100-sum(diff_number_bits.values())/sum(aggr_number_bits)*100:.1f}%")
    print()

    print()
    print(f"Error Overlap Peripherals = {sum(diff_number_peripherals.values())}/{sum(aggr_intersection_peripherals)} "
          f"{100-sum(diff_number_peripherals.values())/sum(aggr_intersection_peripherals)*100:.1f}%")
    print(f"Error Overlap Registers = {sum(diff_number_registers.values())}/{sum(aggr_intersection_registers)} "
          f"{100-sum(diff_number_registers.values())/sum(aggr_intersection_registers)*100:.1f}%")
    print(f"Error Overlap Bits = {sum(diff_number_bits.values())}/{sum(aggr_intersection_bits)} "
          f"{100-sum(diff_number_bits.values())/sum(aggr_intersection_bits)*100:.1f}%")
    print()

    def _eval_source_counts(data_sources, overlaps):
        all_sources = [s for source in data_sources.values() for s in source]
        count_total = len(all_sources)
        overlap = sum(overlaps)

        count_cmrm = 0
        count_cmhd = 0
        count_hdrm = 0

        for source in all_sources:
            count_cmrm += source.count("cm+rm")
            count_cmhd += source.count("cm+hd")
            count_hdrm += source.count("hd+rm")

        count_diffs = count_hdrm + count_cmhd + count_cmrm

        print(f"all={count_diffs}/{count_total} = {count_diffs/count_total*100:.1f}% -> {(overlap - count_total + count_diffs)/overlap*100:.1f}")
        print(f"hd+rm={count_hdrm} {count_hdrm/count_diffs*100:.1f}%")
        print(f"cm+hd={count_cmhd} {count_cmhd/count_diffs*100:.1f}%")
        print(f"cm+rm={count_cmrm} {count_cmrm/count_diffs*100:.1f}%")
        print()

        counts = {}
        for device, sources in data_sources.items():
            count_majority = 0
            count_total = 0

            for source in sources:
                count_total += len(source)
                count_majority += source.count("cm+rm")
                count_majority += source.count("cm+hd")
                count_majority += source.count("hd+rm")

            counts[device] = {
                "total": count_total,
                "majority": count_majority,
            }
        return counts


    print("Majority Voting Performance for Peripherals")
    _eval_source_counts(sources_peripherals, aggr_intersection_peripherals)

    print("Majority Voting Performance for Registers")
    majority_registers = _eval_source_counts(sources_registers, aggr_intersection_registers)

    print("Majority Voting Performance for Bit Fields")
    majority_bits = _eval_source_counts(sources_bits, aggr_intersection_bits)

    print("Ordered Peripherals with the most Register conflicts")

    count_issues_peripherals = defaultdict(list)
    all_periperals = []
    for device, peripherals in issues_peripherals.items():
        all_periperals.extend(peripherals)
        fname = device[:7]
        if re.match("stm32l4[srqp]", device): fname = "stm32l4+"
        count_issues_peripherals[fname].extend(peripherals)
    for family, peripherals in count_issues_peripherals.items():
        total = len(peripherals)
        pcount = defaultdict(int)
        for per in peripherals:
            pname = "".join(c.upper() for c in per if not c.isnumeric()).split("_")[0]
            pcount[pname] += 1
        pcount = list(sorted((-c/total, s) for s,c in pcount.items()))
        print(f"{family.upper()} {total/len(all_periperals)*100:.1f}%")
        for (c, p) in pcount[:10]:
            print(f"{int(round(-c*100))}%: {p}")

    count_issues_peripherals = defaultdict(int)
    for peripheral in all_periperals:
        pname = "".join(c.upper() for c in peripheral if not c.isnumeric()).split("_")[0]
        count_issues_peripherals[pname] += 1
    pcount = list(sorted((-c/len(all_periperals), s) for s,c in count_issues_peripherals.items()))
    print("Total peripheral count")
    for (c, p) in pcount[:30]:
        print(f"{int(round(-c*100))}%: {p}")
    print()

    # count_names_registers = defaultdict(list)
    # all_periperals = []
    # for device, peripherals in names_peripherals.items():
    #     all_periperals.extend(peripherals)
    #     fname = device[:7]
    #     if re.match("stm32l4[srqp]", device): fname = "stm32l4+"
    #     count_names_registers[fname].extend(peripherals)
    # count_registers = defaultdict(int)
    # for family, names in count_names_registers.items():
    #     count_registers[names] += 1
    # rcount = list(sorted((-c/len(all_periperals), s) for s,c in count_registers.items() if c >= 10))
    # print("Most common Register conflicts")
    # for (c, p) in rcount[:30]:
    #     print(f"{int(round(-c*100))}%: {p}")
    # print()

    bit_conflicts_l4p = []
    for device, conflicts in names_registers.items():
        # if re.match("stm32l4[srqp]", device):
        if re.match("stm32h7", device):
            for (registers, bits) in conflicts:
                bit_conflicts_l4p.append(bits)
    bit_percent_l4p = defaultdict(int)
    for bit in bit_conflicts_l4p:
        bit_percent_l4p[bit] += 1
    bcount = list(sorted((-c/len(bit_conflicts_l4p), s) for s,c in bit_percent_l4p.items() if c >= 10))
    print("STM32H7 bit conflicts")
    for (c, p) in bcount[:30]:
        print(f"{int(round(-c*100))}%: {p}")

    # print("Most common Peripheral::Register conflicts")
    # count_names_peripherals = defaultdict(int)
    # for peripherals, names in names_peripherals:
    #     count_names_peripherals[f"{peripherals}::{names}"] += 1
    # count = list(sorted((-c, s) for s,c in count_names_peripherals.items() if c >= 10))
    # print(count)

    chart_data = {
        "peripherals": {
            "hd": aggr_number_peripherals_hd,
            "rm": aggr_number_peripherals_rm,
            "cm": aggr_number_peripherals_cm,
        },
        "registers": {
            "hd": aggr_number_registers_hd,
            "rm": aggr_number_registers_rm,
            "cm": aggr_number_registers_cm,
        },
        "bits": {
            "hd": aggr_number_bits_hd,
            "rm": aggr_number_bits_rm,
            "cm": aggr_number_bits_cm,
        },
        "collisions": {
            "peripherals": diff_number_peripherals,
            "registers": diff_number_registers,
            "bits": diff_number_bits,
        },
        "majority": {
            "registers": majority_registers,
            "bits": majority_bits,
        }
    }

    return chart_data


def render_charts(chart_data):
    import matplotlib
    import matplotlib.pyplot as plt
    from matplotlib.ticker import FuncFormatter

    matplotlib.use("pgf")
    matplotlib.rcParams.update({
        "pgf.texsystem": "pdflatex",
        'font.family': 'serif',
        'text.usetex': True,
        'pgf.rcfonts': False,
        # "pgf.preamble": r"\usepackage[binary-units]{siunitx}"
    })
    def _n(dev):
        cpu = ""
        if "@" in dev:
            dev, cpu = dev.split("@")
            cpu = "@" + cpu
        dev = dev[5:-2] + cpu
        return dev.upper()

    for chart in range(5):
        figsize = (1, 0.25)
        scale = 8.1
        legendloc = (0.02, 0.6)
        hd_plot, rm_plot, cm_plot, diff_plot, maj_plot = None, None, None, None, None
        if chart == 0:
            hd_plot = list(zip(*sorted((_n(k),v) for k,v in chart_data["peripherals"]["hd"].items())))
            rm_plot = list(zip(*sorted((_n(k),v) for k,v in chart_data["peripherals"]["rm"].items())))
            cm_plot = list(zip(*sorted((_n(k),v) for k,v in chart_data["peripherals"]["cm"].items())))
            figname = "evaluation_mmio_count_peripherals"
            # yformatter = FuncFormatter(lambda y, _: r"\SI{"+str(int(y))+r"}{\byte}")
            yformatter = FuncFormatter(lambda y, _: f"{int(y)} B")
        elif chart == 1:
            hd_plot = list(zip(*sorted((_n(k),v) for k,v in chart_data["registers"]["hd"].items())))
            rm_plot = list(zip(*sorted((_n(k),v) for k,v in chart_data["registers"]["rm"].items())))
            cm_plot = list(zip(*sorted((_n(k),v) for k,v in chart_data["registers"]["cm"].items())))
            figname = "evaluation_mmio_count_registers"
            # yformatter = FuncFormatter(lambda y, _: r"\SI{"+str(int(y/1000))+r"}{\kilo\byte}")
            yformatter = FuncFormatter(lambda y, _: f"{int(y/1000)} kB")
        elif chart == 2:
            hd_plot = list(zip(*sorted((_n(k),v) for k,v in chart_data["bits"]["hd"].items())))
            rm_plot = list(zip(*sorted((_n(k),v) for k,v in chart_data["bits"]["rm"].items())))
            cm_plot = list(zip(*sorted((_n(k),v) for k,v in chart_data["bits"]["cm"].items())))
            figname = "evaluation_mmio_count_bits"
            # yformatter = FuncFormatter(lambda y, _: r"\SI{"+str(int(y/1000))+r"}{\kilo\bit}")
            yformatter = FuncFormatter(lambda y, _: f"{int(y/1000)} kb")
        elif chart == 3:
            col_registers = chart_data["collisions"]["registers"]
            maj_registers = chart_data["majority"]["registers"]
            diff_plot = list(zip(*sorted((_n(k),v/sum(col_registers.values())) for k,v in col_registers.items())))
            maj_plot = list(zip(*sorted((_n(k),v["majority"]/sum(col_registers.values())) for k,v in maj_registers.items())))
            hd_plot = diff_plot
            figsize = (1, 0.2)
            figname = "evaluation_mmio_relative_error_registers"
            yformatter = FuncFormatter(lambda y, _: f"{int(y*100)}%")
        elif chart == 4:
            col_bits = chart_data["collisions"]["bits"]
            maj_bits = chart_data["majority"]["bits"]
            diff_plot = list(zip(*sorted((_n(k),v/sum(col_bits.values())) for k,v in col_bits.items())))
            maj_plot = list(zip(*sorted((_n(k),v["majority"]/sum(col_bits.values())) for k,v in maj_bits.items())))
            hd_plot = diff_plot
            figsize = (1, 0.2)
            figname = "evaluation_mmio_relative_error_bits"
            yformatter = FuncFormatter(lambda y, _: f"{int(y*100)}%")

        if diff_plot:
            ymax = max([max(diff_plot[1]), max(maj_plot[1])])
        else:
            ymax = max([max(hd_plot[1]), max(rm_plot[1]), max(cm_plot[1])])
        text_pos = ymax * -0.02 / figsize[1]
        xlabel_pos = ymax * -0.055 / figsize[1]

        plt.clf()
        plt.figure(figsize=(figsize[0]*scale, figsize[1]*scale))
        if diff_plot:
            plt.fill_between(*diff_plot, color="white", step="pre", alpha=0.2)
            pass
        else:
            plt.fill_between(*hd_plot, color="lightgray", step="pre", edgecolor='black', label="CMSIS Header")
        # plt.xlabel("STM32 devices")
        # plt.ylabel("Number of Registers")
        # plt.xticks(range(len(hd_plot[0])), [v[5:7] for v in hd_plot[0]], rotation=90)
        plt.xticks([], rotation=90, size=5)

        current = hd_plot[0][0][:2]
        last_value = 0
        last_index = 0
        for ii, (name, value) in enumerate(zip(*hd_plot)):
            fname = name[:2]
            if re.match(r"L4[SRQP]", name, re.IGNORECASE):
                fname = "L4\\texttt{+}"
            if fname != current or ii+1 == len(hd_plot[0]):
                if ii+1 == len(hd_plot[0]): ii += 1
                plt.text((last_index + ii-1)/2, text_pos, current,
                         dict(size=10), ha='center', va='center')
            if fname != current:
                plt.plot([ii-1, ii-1], [0, max(last_value, value)], 'k-', lw=1)
                current = fname
                last_index = ii-1
            last_value = value

        if diff_plot:
            plt.fill_between(*maj_plot, color="darkgray", step="pre", label="Using Majority Voting")
            plt.step(*diff_plot, "k-", lw=1, label="Relative Conflict Rate")
        else:
            plt.step(*cm_plot, "r-", label="CMSIS-SVD", alpha=1, lw=1)
            plt.step(*rm_plot, "b-", label="Reference Manual", alpha=1, lw=1)

        plt.legend(loc=legendloc, frameon=False)
        # plt.autoscale(enable=True, tight=True)
        ax = plt.gca()
        ax.spines['top'].set_visible(False)
        ax.yaxis.set_major_formatter(yformatter)
        plt.text(len(hd_plot[1])/2, xlabel_pos,
                 "Unique Three-way Comparison Sorted by Device Identifier and Grouped by Family",
                 dict(size=10), ha='center', va='center')
        if "relative" in figname:
            ax.set_ylabel("Conflict Rate [%]")
        elif "bits" in figname:
            ax.set_ylabel("Memory Map Size [Bit]")
        else:
            ax.set_ylabel("Memory Map Size [Byte]")
        ax.margins(y=0, x=0)
        x0, x1, y0, y1 = plt.axis()
        plt.axis((x0, x1, y0, y1*1.01))
        # ax.spines['right'].set_visible(False)
        # ax.spines['bottom'].set_visible(False)
        # ax.spines['left'].set_visible(False)

        fmt = dict(bbox_inches='tight', pad_inches=0.01, transparent=True)
        # plt.savefig(f"../../master/thesis/Thesis/figures/{figname}.pgf", **fmt)
        plt.savefig(f"{figname}.png", **fmt)


if __name__ == "__main__":
    data_eval = (Path(__file__).parent / "data_eval_svds.json")
    chars_eval = (Path(__file__).parent / "data_charts_svds.json")
    if "--charts" in sys.argv:
        charts = render_charts(json.loads(chars_eval.read_text()))
    elif "--eval" in sys.argv:
        eval_devices()
        chart_data = eval_svds(json.loads(data_eval.read_text()))
        chars_eval.write_text(json.dumps(chart_data, sort_keys=True, indent=2, cls=SetEncoder))
    elif "--compare" in sys.argv:
        reports = compare_svds()
        data_eval.write_text(json.dumps(reports, sort_keys=True, indent=2, cls=SetEncoder))

