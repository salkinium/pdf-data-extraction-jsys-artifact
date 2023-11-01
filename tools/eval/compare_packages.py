# Copyright (c) 2022, Niklas Hauser
#
# This file is part of the modm-data project.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
# -----------------------------------------------------------------------------

import re, sys, json
sys.path.extend([".", "ext/modm-devices"])
from pathlib import Path
from deepdiff import DeepDiff
from collections import defaultdict

import modm_devices.parser
import modm_data.owl.stmicro as owl
import modm_data.cubemx
import modm_data.owl2py.stmicro


def normalize_pin_name(name):
    name = name.replace(" ", "").replace("/", "-")
    name = name.replace("-OSC", "OSC").replace("-BOOT", "BOOT")
    name = name.replace("_USB", "USB").replace("DSIHOST_", "DSI_")
    name = name.replace("VDD50USB", "VDDUSB").replace("VDD33USB", "VDDUSB")
    name = re.sub(r"\(.+?\)", "", name)
    return name


def find_package(package, device):
    packages = list(sorted(owl.Package.instances(), key=lambda p: (-len(p.name), p.name)))
    # print(package, device, packages)
    if package == "EWLCSP49": package = "WLCSP49"
    for ppackage in packages:
        name, *filters = ppackage.name.split("+")
        if not filters and package == name:
            return ppackage

        results = []
        for filt in filters:
            if filt.startswith("STM32"):
                results.append(re.match(filt, device.string, re.IGNORECASE) is not None)
            elif "SMPS" in filt:
                results.append(device.get("variant") in ["p", "q"])
            elif filt in ["S", "N", "E"]:
                results.append(device.get("variant") == filt.lower())
            elif filt == "2" and name == "WLCSP64":
                name = "WLCSP66"
                results.append(True)
            elif filt.isnumeric():
                results.append(True) # Ignore for now

        if all(results) and package == name:
            return ppackage

    if re.match(r"stm32f10[57]", device.string) and package == "LFBGA100": # DS6014-v10
        return find_package("UFBGA100", device)
    if re.match(r"stm32g0[cb]1", device.string) and package == "LQFP80": # DS13560-v3
        return find_package("UFBGA80", device)
    if device.string.startswith("stm32l073") and package == "UFBGA64": # DS10685-v6
        return find_package("TFBGA64", device)

    return None


def compare_packages():
    reports = {}
    seen_devices = set()
    modm_devices = set()
    for did in sorted(modm_data.cubemx.devices(), key=lambda d: d.string):
        sdid = did.string.split("@")[0]
        if sdid in seen_devices: continue
        seen_devices.add(sdid)
        modm_devices.add(did)
    modm_devices = list(sorted(modm_devices, key=lambda d: d.string))

    for ds in modm_data.owl2py.stmicro.owls():
        if ds.startswith("DS"):
        # if ds.startswith("DS11912"):
            print(f"ext/cache/stmicro-html/{ds}", f"ext/cache/stmicro-pdf/{ds}.pdf")
            owl.store.load(ds)
            dids = owl.Device.instances()
            dids = [did for did in modm_devices if any(did.string.startswith(d.name) for d in dids)]
            for did in dids:
                file = modm_data.cubemx.device_file(did)
                pp = file.get_driver("gpio")["package"][0]
                package = pp["name"]
                pins = defaultdict(set)
                for pin in pp["pin"]:
                    if pin["name"] != "NC":
                        pins[pin["position"]].add(normalize_pin_name(pin["name"]))
                pins = {pp: "-".join(sorted(pn)) for pp, pn in pins.items()}
                report_data = {"result": "ok", "package": package, "modm_pins": len(pins), "ds": ds}

                opackage = find_package(package, did)
                if opackage is None:
                    report_data["result"] = "missing"
                    reports[did.string] = report_data
                    print(did, package, owl.Package.instances())
                    continue
                print(did, package, opackage.name)

                opins = defaultdict(set)
                for pin in opackage.hasPin:
                    opos = owl.pinPosition[opackage, owl.hasPin, pin]
                    for pos in opos:
                        opins[pos].add(normalize_pin_name(pin.name))
                opins = {pp: "-".join(sorted(pn)) for pp, pn in opins.items()}
                # print(opins)
                report_data["owl_pins"] = len(opins)

                ddiff = DeepDiff(pins, opins, ignore_order=True)
                if ddiff:
                    report_data.update({"result": "diff", "diff": json.loads(ddiff.to_json())})
                    print(ddiff)
                reports[did.string] = report_data

    return reports


def eval_packages(reports):
    total_devices = 0
    correct_devices = 0
    validated_devices = 0
    missing_devices = 0
    wrong_devices = 0

    total_pins = 0
    correct_pins = 0
    validated_pins = 0
    wrong_pins = 0

    valid_devices = {
        # Wrong CubeMX package selection
        "stm32f038e6y6", "stm32f048t6y6", "stm32f058t8y6", "stm32h745xgh6@m4",
        "stm32h745xgh6@m7", "stm32h745xih3@m4", "stm32h745xih3@m7", "stm32h745xih6@m4",
        "stm32h745xih6@m7", "stm32h747xgh6@m4", "stm32h747xgh6@m7", "stm32h747xih6@m4",
        "stm32h747xih6@m7", "stm32h750xbh6", "stm32h755xih3@m4", "stm32h755xih3@m7",
        "stm32h755xih6@m4", "stm32h755xih6@m7", "stm32h757xih6@m4", "stm32h757xih6@m7",
        "stm32h757ziy6@m4", "stm32h757ziy6@m7", "stm32l452rey3p", "stm32l452rey6p",
        "stm32l476qgi3p", "stm32l476qgi6p", "stm32l476qgi7p", "stm32l496qgi3s",
        "stm32l496qgi6s", "stm32l4p5qgi6s", "stm32l4r5aii6p", "stm32l4r5qii6p",
        "stm32l552qei6", "stm32l552vet6", "stm32l552zet3", "stm32l552zet6",
        # Only supply pins issues
        "stm32h742xgh6", "stm32h742xih6", "stm32h747ziy6@m4", "stm32h747ziy6@m7",
        "stm32l071v8i6", "stm32l071vbi6", "stm32l071vzi6", "stm32l072v8i6",
        "stm32l072vbi6", "stm32l072vzi6",
    }

    ignored_devices = {
        "stm32g071.6"
        "stm32g441"
        "stm32g471"
        "stm32l041c4"
        "stm32l485"
        "stm32wb5m"
    }

    for device, report in reports.items():
        if any(re.match(ig, device) for ig in ignored_devices):
            continue
        total_devices += 1

        if report["result"] == "missing":
            missing_devices += 1
            continue

        package = report["package"]
        modm_pins = report["modm_pins"]
        owl_pins = report.get("owl_pins", 0)
        max_pins = max(modm_pins, owl_pins)
        total_pins += max_pins

        if report["result"] == "ok":
            correct_devices += 1
            correct_pins += max_pins
            continue

        removed = set(report["diff"].get("dictionary_item_removed", []))
        added = set(report["diff"].get("dictionary_item_added", []))
        pins = set()

        if package == "UFQFPN32":
            # Thermal pad connected to VSS ground
            pins = {"root['0']"}
        elif package == "UFQFPN48":
            # Thermal pad described in footnote: ext/cache/stmicro-pdf/DS13293-v3.pdf
            # 2. The exposed pad must be connected to the ground plain.
            pins = {"root['49']"}
        elif package == "UFBGA169":
            # All VSS or VSSDSI pins
            pins = {"root['A12']", "root['H11']", "root['J11']", "root['K11']"}
        elif package == "UFBGA176":
            # 5x5 VSS Pads in the center of UFBGA176+25
            pins = {"root['F6']", "root['F7']", "root['F8']", "root['F9']", "root['F10']",
                    "root['G6']", "root['G7']", "root['G8']", "root['G9']", "root['G10']",
                    "root['H6']", "root['H7']", "root['H8']", "root['H9']", "root['H10']",
                    "root['J6']", "root['J7']", "root['J8']", "root['J9']", "root['J10']",
                    "root['K6']", "root['K7']", "root['K8']", "root['K9']", "root['K10']"}
        elif package == "TFBGA240":
            # 5x5 VSS Pads in the center TFBGA240+25
            pins = {"root['G7']", "root['G8']", "root['G9']", "root['G10']", "root['G11']",
                    "root['H7']", "root['H8']", "root['H9']", "root['H10']", "root['H11']",
                    "root['J7']", "root['J8']", "root['J9']", "root['J10']", "root['J11']",
                    "root['K7']", "root['K8']", "root['K9']", "root['K10']", "root['K11']",
                    "root['L7']", "root['L8']", "root['L9']", "root['L10']", "root['L11']"}

        removed -= pins
        added -= pins

        changed = []
        for pos, values in report["diff"].get("values_changed", {}).items():
            premoved, padded = values.values()
            if premoved in padded or padded in premoved:
                continue
            names = [premoved, padded]
            snames = set(names)
            if snames == {"PD0", "OSC_IN"}: continue
            if snames == {"PD1", "OSC_OUT"}: continue
            if snames in [{"VREF", "VDDA"}, {"VREF+", "VDDA"}, {'VLCD', 'VDD'}]: continue
            if snames == {"VDDUSB", "VDDPHYHS"}: continue
            if snames == {'PA11[PA9]-PA8-PB0-PB1', 'PA11[PA9]-PA8-PA9[PA11]-PB0-PB1'}: continue
            if snames == {'PD0OSC_IN', 'OSC_IN-PD0'}: continue
            if snames == {'PD1OSC_IN', 'OSC_IN-PD1'}: continue
            if snames == {'PD0OSC_OUT', 'OSC_OUT-PD0'}: continue
            if snames == {'PD1OSC_OUT', 'OSC_OUT-PD1'}: continue
            if snames in [{'VCAP1', 'VCAP_1'}, {'VCAP2', 'VCAP_2'}, {'VREF+', 'VREF_+'}]: continue
            if snames in [{'VDD12OTGHS', 'V12PHYHS'}, {'REXTPHYHS', 'OTG_HS_REXT'}]: continue
            if snames in [{'AOP1_INN', 'OPAMP1_VINM'}, {'OPAMP2_VINM', 'AOP2_INN'}]: continue
            if snames in [{'VDDCAP', 'VDD_DCAP4'}, {'VDDCAP', 'VDD_DCAP1'}, {'VDDCAP', 'VDD_DCAP3'}, {'VDDCAP', 'VDD_DCAP2'}]: continue
            changed.append((pos, names))

        if removed or added or changed:
            print()
            print(device, f"ext/cache/stmicro-html/{report['ds']}", f"ext/cache/stmicro-pdf/{report['ds']}.pdf")
            print(package, removed, added, changed)
            wrong = len(removed) + len(added) + len(changed)
            wrong_pins += wrong
            correct_pins += max_pins - wrong
            if device in valid_devices:
                validated_devices += 1
                validated_pins += wrong
            wrong_devices += 1
        else:
            correct_devices += 1
            correct_pins += max_pins


    print()
    print(f"total_devices={total_devices} total_pins={total_pins}")
    print(f"correct_devices={correct_devices} correct_pins={correct_pins}")
    print(f"validated_devices={correct_devices + validated_devices} validated_pins={correct_pins + validated_pins}")
    print(f"wrong_devices={wrong_devices} wrong_pins={wrong_pins}")
    print(f"missing_devices={missing_devices}")
    print()
    print(f"correct_devices_pct={correct_devices/total_devices*100:.3f}%")
    print(f"correct_pins_pct={correct_pins/total_pins*100:.3f}%")
    print()
    print(f"validated_devices_pct={(correct_devices + validated_devices)/total_devices*100:.3f}%")
    print(f"validated_pins_pct={(correct_pins + validated_pins)/total_pins*100:.3f}%")


if __name__ == "__main__":
    data_eval = (Path(__file__).parent / "data_eval_packages.json")
    if "--eval" in sys.argv:
        eval_packages(json.loads(data_eval.read_text()))
    else:
        reports = compare_packages()
        data_eval.write_text(json.dumps(reports, sort_keys=True, indent=2))
