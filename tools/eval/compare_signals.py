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
from deepdiff.model import PrettyOrderedSet
from collections import defaultdict

import modm_devices.parser
import modm_data.owl.stmicro as owl
import modm_data.cubemx
import modm_data.owl2py.stmicro


SUBSTITUTIONS = {
    r"^WKUP": "SYS_WKUP",
    r"^JTDI": "SYS_JTDI",
    r"NJTRST": "JTRST",
    r"^JTRST": "SYS_JTRST",
    # r"^NRST": "SYS_NRST",
    r"^PVD_IN": "SYS_PVD_IN",
    r"^TAMP_": "SYS_TAMP_",
    r"TAMP_(\d)": r"TAMP\1",
    r"^TRACE": "SYS_TRACE",
    r"TRACECK": "TRACECLK",
    r"SYS_TRACESWO": "SYS_SWO",
    r"^PWR_WKUP": "SYS_WKUP",
    r"^(PWR|VREF)_PVD_": "SYS_PVD_",
    r"SYS_WKUP\d$": "SYS_WKUP",
    r"SYS_V_REF_OUT": "SYS_VREF_OUT",
    r"SYS_VREF_OUT_.*": "SYS_VREF_OUT",
    r"^DEBUG_(SW.*|JT.*|TR.*)": r"SYS_\1",
    r"^JTDO$": "SYS_JTDO",
    r"^JTCK$": "SYS_JTCK",
    r"^JTMS$": "SYS_JTMS",
    r"^SWCLK$": "SYS_SWCLK",
    r"^TRGIO$": "SYS_TRGIO",
    r"^(SWDIO|SWDAT)$": "SYS_SWDIO",
    r"^VREF_OUT$": "SYS_VREF_OUT",
    r"^RTC_TAMP": "SYS_TAMP",

    r"^OSC32_": "RCC_OSC32_",
    r"^OSC_": "RCC_OSC_",
    r"^LSCO": "RCC_LSCO",
    r"^MCO": "RCC_MCO",
    r"MCO_(\d)": r"MCO\1",
    r"^CK_IN": "RCC_CK_IN",
    r"^_CRS": r"CRS",
    r"^(USB_?|OTG_FS_)?CRS_SYNC$": r"RCC_CRS_SYNC",

    r"^IR_?OUT": "IRTIM_OUT",
    r"_SEC$": "",
    r"_NSS$": "_CTS",
    r"^QUADSPI_": "QUADSPI1_",
    r"^SAI_": "SAI1_",
    r"^FDCAN": "CAN",
    r"^FMPI2C": "I2C",
    r"(_V?IN[NMP])\d{1}$": r"\1",
    r"_INN": r"_INM",
    r"^I2SCKIN": "I2S_CKIN",
    r"^(I2S\d+)_SD$": r"\1EXT_SD",
    r"^(I2S\d+)_EXT": r"\1EXT",
    r"_DATIN": "_DATAIN",
    r"_MCK_": "_MCLK_",
    r"_CTS_CTS$": "_CTS",
    r"_RTS_$": "_RTS",
    r"(ADC\d)_(\d)": r"\1_IN\2",
    r"_SMBA$": "_SMBAL",
    r"_BK$": "_BKIN",
    r"_BK(\d+)$": r"_BKIN\1",
    r"_INN": "_INM",
    r"_DBCC": "_DB",
    r"SAI(\d)_PDM_DI(\d)": r"SAI\1_D\2",
    r"SAI(\d)_DI(\d)": r"SAI\1_D\2",
    r"\*": "",
    r"(_FRS[RT]X)\d+": r"\1",
    r"^HDMI_CEC_CEC$": "HDMI_CEC",
    r"^(HDMI)?CEC$": "HDMI_CEC",
    r"^SPI2SCK$": "SPI2_SCK",
    r"XFD(_MODE)?$": "X",
    r"^USB(NOE|DP|DM)": r"USB_\1",

    r"^OTG_": "USB_OTG_",
    r"^USB_FS_": "USB_OTG_FS_",
    r"^ETH_R?MII_": "ETH_",
    r"^DSI_TE": "DSIHOST_TE",
    r"^SPDIF_RX": "SPDIFRX1_IN",
    r"^RTC_OUT_.*": "RTC_OUT",

    # r"UCPD_": "UCPD1_",
    r"^SWPMI_": "SWPMI1_",
    r"^SPDIFRX_": "SPDIFRX1_",
    r"^SDMMC_": "SDMMC1_",
    r"^ADC_": "ADC1_",
    r"^DAC_": r"DAC1_",
    r"^\[(.*?)\]$": r"\1",
    r"^((SEG|COM)\d+)$": r"LTDC_\1",
    r"^LCD_": "LTDC_",
    r"^((A|DA|D|NE|NBL)\d+|NE|NWAIT|NWE|NOE|NADV|CLK)$": r"FMC_\1",
    r"FMC_AD": "FMC_DA",
    r"FMC_DA": "FMC_D",
    r"FMC_SD": r"FMC_",
    r"FSMC_": r"FMC_",
    r"^_USB": r"USB",
    r"^ETH_RCC_CRS_DV": "ETH_CRS_DV",
    r"^I2S\d_CKIN": r"I2S_CKIN",
}

def normalize_signal_name(name, drivers):
    for search, subst in SUBSTITUTIONS.items():
        name = re.sub(search, subst, name)

    if match := re.match(r"(L?P?US?ART\d)_RTS_DE", name):
        return {match.group(1)+"_RTS", match.group(1)+"_DE"}
    if match := re.match(r"(TIM\d)(_CH\d)_ETR", name):
        return {match.group(1)+match.group(2), match.group(1)+"_ETR"}
    if match := re.match(r"(TIM\d_BKIN\d?_COMP|ADC\d_IN[PM])(\d{2})$", name):
        return {n for i in match.group(2) for n in normalize_signal_name(f"{match.group(1)}{i}", drivers)}
    if match := re.match(r"ADC(\d{2,4})_(.*)", name):
        return {n for i in match.group(1) for n in normalize_signal_name(f"ADC{i}_{match.group(2)}", drivers)}

    if name in {"JTMSSWDIO", "SWDIOJTMS", "SWDATJTMS", "JTMS_SWDIO"}: return {"SYS_JTMS", "SYS_SWDIO"}
    if name in {"JTCKSWCLK", "SWCLKJTCK", "JTCK_SWCLK"}: return {"SYS_JTCK", "SYS_SWCLK"}
    if name in {"JTDOTRACESWO", "JTDOSWO"}: return {"SYS_JTDO", "SYS_SWO"}
    if name in {"ETH_TXDETH_RMII_TXD"}: return {"ETH_TXD"}

    return {name.upper()}


def create_diff(xpins, ypins):
    ddiff = DeepDiff(xpins, ypins)
    ddiff = ddiff.to_dict()
    def _rewrite(name, pins):
        if name in ddiff:
            ndiff = defaultdict(set)
            for path in ddiff[name]:
                keys = re.findall(r"\['(.*?)'\]", path)
                if len(keys) == 2:
                    ndiff[f"{keys[0]}-{keys[1]}"].update(pins[keys[0]][keys[1]])
                elif len(keys) == 3:
                    ndiff[f"{keys[0]}-{keys[1]}"].add(keys[2])
            ndiff = {k:v for k,v in ndiff.items() if v}
            if ndiff: ddiff[name] = ndiff
            else: del ddiff[name]
    _rewrite("dictionary_item_added", ypins)
    _rewrite("dictionary_item_removed", xpins)
    _rewrite("set_item_added", ypins)
    _rewrite("set_item_removed", xpins)
    return ddiff


class SetEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (set, PrettyOrderedSet)):
            return list(sorted(obj))
        return json.JSONEncoder.default(self, obj)


def filter_pins(opins, drivers, pins=None):
    fpins = {}
    ignored = set()
    for pin, sigs in opins.items():
        if True if (pins is None) else (pin in pins):
            fpins[pin] = {}
            for af, ss in sigs.items():
                rsignals = {s for rs in ss for s in normalize_signal_name(rs, drivers)}
                signals = {s for s in rsignals if any(s.startswith(d) for d in drivers)}
                ignored.update(rsignals - signals)
                if signals: fpins[pin][af] = signals
    # nopins = {pin:{af:{s for s in ss if True or any(s.startswith(d) for d in drivers)}
    #                for af,ss in sigs.items() if True or len({s for s in ss if any(s.startswith(d) for d in drivers)})}
    #           for pin,sigs in opins.items() if (True if (pins is None) else (pin in pins))}
    return fpins, ignored


def compare_signals():
    reports = {}
    modm_devices = modm_data.cubemx.devices()

    index = [int(v) for v in sys.argv if v.isnumeric()]
    for ds in modm_data.owl2py.stmicro.owls()[index[0] if index else 0 : index[0] + 1 if index else -1]:
        if ds.startswith("DS"):
        # if ds.startswith("DS6876-v12"):
            print(f"ext/cache/stmicro-html/{ds}", f"ext/cache/stmicro-pdf/{ds}.pdf")
            owl.store.load(ds)
            dids = owl.Device.instances()
            dids = [did for did in modm_devices if any(did.string.startswith(d.name) for d in dids)]
            opins = defaultdict(lambda: defaultdict(set))
            for opin in owl.Pin.instances():
                if (match := re.search(r"P[A-Z]\d{1,2}", opin.name)) is not None:
                    name = match.group(0)
                    for osignal in opin.hasSignal:
                        if "EVENTOUT" in osignal.name:
                            continue
                        if isinstance(osignal, owl.AdditionalFunction):
                            opins[name]["A"].add(osignal.name)
                        else:
                            af = owl.alternateFunction[opin, owl.hasSignal, osignal][0]
                            opins[name][str(af)].add(osignal.name)
                # else:
                #     print(opin.name)
            # print(opins)

            for did in dids:
                # We're not evaluating STM32F1 with their weird AFIO remap groups
                if did.family == "f1": continue
                print(did)
                devfile = modm_data.cubemx.device_file(did)

                gpios = devfile.get_driver("gpio")["gpio"]
                pins = defaultdict(lambda: defaultdict(set))
                for pin in gpios:
                    name = "P" + pin["port"].upper() + pin["pin"]
                    for spin in pin.get("signal", []):
                        signal = spin.get("driver", "").upper() + spin.get("instance", "") + "_" + spin.get("name", "").upper()
                        pins[name][spin.get("af", "A")].add(signal)

                drivers = {"SYS"}
                for driver in devfile.properties["driver"]:
                    name = driver["name"].upper()
                    name = name.replace("FDCAN", "CAN").replace("LCD", "LTDC")
                    name = name.replace("USB_DRD_FS", "USB")
                    if instances := driver.get("instance", []):
                        for instance in instances:
                            drivers.add(name + instance.upper())
                    else:
                        drivers.add(name)
                drivers -= {"DEBUG", "CORE", "TS"}
                if any(d.startswith("I2S") for d in drivers):
                    drivers.add("I2S")

                pins, pignored = filter_pins(pins, drivers)
                npins, npignored = filter_pins(opins, drivers, pins)
                len_pins = sum(sum(len(s) for s in p.values()) for p in pins.values())
                len_npins = sum(sum(len(s) for s in p.values()) for p in npins.values())
                report_data = {"result": "ok", "modm_signals": len_pins, "owl_signals": len_npins, "ds": ds, "drivers": drivers}
                # print(pins)
                # print()
                # print(npins)

                ddiff = create_diff(pins, npins)
                if ddiff:
                    report_data.update({"result": "diff", "diff": ddiff, "modm_ignored": pignored, "owl_ignored": npignored})
                    print("drivers=", "  ".join(sorted(drivers)))
                    print()
                    print("ignored=", "  ".join(sorted(pignored | npignored)))
                    print()
                    print("owl_ignored=", "  ".join(sorted(npignored - pignored)))
                    print("modm_ignored=", "  ".join(sorted(pignored - npignored)))
                    print()
                    print("ddiff=", ddiff)
                    print()
                    print()
                reports[did.string] = report_data
                # return reports

    return reports


def eval_signals(reports):
    total_devices = len(reports)
    correct_devices = 0
    quasi_devices = {}
    wrong_devices = 0

    total_signals = 0
    correct_signals = 0
    quasi_signals = 0
    wrong_signals = 0
    signals_per_family = defaultdict(int)
    wrong_signals_per_family = defaultdict(int)

    total_wrong_signals_added = []
    total_wrong_signals_removed = []
    mixed_af_signals = defaultdict(list)

    for device, report in reports.items():
        print(device)
        owl_signals = report.get("owl_signals", 0)
        if report["result"] == "missing":
            wrong_devices += 1
            continue

        modm_signals = report["modm_signals"]
        max_signals = max(modm_signals, owl_signals)
        total_signals += max_signals
        signals_per_family[device[:7]] += max_signals

        if report["result"] == "ok":
            correct_devices += 1
            correct_signals += max_signals
            continue

        def _filter(name):
            signals = defaultdict(set)
            def _values(part):
                for key, values in report["diff"].get(part + "_item_" + name, {}).items():
                    # values = [v for v in values if not re.search(r"US?ART\d+_DE|TIM\d+_(ETR|BKIN)", v)]
                    # values = [v for v in values if not re.search(r"SYS_SW|SYS_JT|SYS_TR|SYS_WK", v)]
                    # values = [v for v in values if not re.search(r"COMP.*?INP", v)]
                    if values: signals[key].update(values)
            _values("dictionary")
            _values("set")
            return dict(signals)

        added = _filter("added") # FROM PDF
        added_values = [v for values in added.values() for v in values]
        total_wrong_signals_added += added_values

        removed = _filter("removed") # FROM CUBEMX
        removed_values = [v for values in removed.values() for v in values]
        total_wrong_signals_removed += removed_values

        af_map = defaultdict(set)
        def _af_map(values):
            for key, signals in values.items():
                pin, af = key.split("-")
                for signal in signals:
                    af_map[pin + "-" + signal].add(af)
        _af_map(added)
        _af_map(removed)
        af_map = {k:v for k,v in af_map.items() if len(v) >= 2}
        for k, v in af_map.items():
            mixed_af_signals[k].append("-".join(sorted(v)))

        wrong = len(removed_values) + len(added_values)
        wrong_signals_per_family[device[:7]] += wrong
        if wrong == 0:
            correct_devices += 1
            correct_signals += max_signals
        else:
            if af_map: print(af_map)
            # print("removed", removed)
            # print("added", added)
            wrong_signals += wrong
            quasi_signals += max(max_signals - wrong, 0)
            quasi_devices[device] = wrong

    print()
    print(f"total_devices={total_devices} total_signals={total_signals}")
    print(f"correct_devices={correct_devices} correct_signals={correct_signals}")
    print(f"quasi_signals={correct_signals+quasi_signals} wrong_signals={wrong_signals}")
    print()
    print(f"quasi_signals_pct={(correct_signals+quasi_signals)/total_signals*100:.2f}%")
    print()
    signals_per_family_list = [(-c, f) for f, c in signals_per_family.items()]
    for count, family in sorted(signals_per_family_list):
        print(f"{family} {-count} {-count/total_signals*100:.1f}")
    print()
    wrong_signals_per_family_list = [(-c, f) for f, c in wrong_signals_per_family.items()]
    for count, family in sorted(wrong_signals_per_family_list):
        print(f"{family} {-count}/{signals_per_family[family]} {-count/wrong_signals*100:.1f} {-count/signals_per_family[family]*100:.5f}")
    print()

    mixed_af_signals_simple = defaultdict(list)
    mixed_af_signals_simple = defaultdict(list)
    for k,v in mixed_af_signals.items():
        mixed_af_signals_simple["".join(c for c in k.split("-")[1] if not c.isnumeric())].extend(v)
    # print(f"mixed_af_signals={dict(mixed_af_signals)}\n\nmixed_af_signals_simple={dict(mixed_af_signals_simple)}")
    # print()

    mixed_af_count = []
    for k,signals in mixed_af_signals.items():
        count = defaultdict(int)
        for signal in signals:
            count[signal] += 1
        count = list(sorted((c, s) for s,c in count.items()))
        mixed_af_count.append((k, count))
    mixed_af_count.sort(key=lambda sig: -sum(c[0] for c in sig[1]))
    print(f"mixed_af_count={mixed_af_count}")
    print()

    mixed_af_count_simple = []
    for k,signals in mixed_af_signals_simple.items():
        count = defaultdict(int)
        for signal in signals:
            count[signal] += 1
        count = [(-c, k, s) for s,c in count.items()]
        mixed_af_count_simple.extend(count)
    mixed_af_count_simple.sort()
    print(f"mixed_af_count_simple={mixed_af_count_simple}")
    print()

    # FROM PDF
    print("Found in PDF but not in CubeMX")
    count = defaultdict(int)
    for signal in total_wrong_signals_added:
        count[signal] += 1
    count = list(sorted((-c, s) for s,c in count.items() if c >= 100))
    print(count)
    print()

    count = defaultdict(int)
    for signal in total_wrong_signals_added:
        count["".join(c for c in signal if not c.isnumeric())] += 1
    count = list(sorted((-c, s) for s,c in count.items() if c >= 100))
    print(count)
    print()

    # FROM CUBEMX
    print("Found in CubeMX but not in PDF")
    count = defaultdict(int)
    for signal in total_wrong_signals_removed:
        count[signal] += 1
    count = list(sorted((-c, s) for s,c in count.items() if c >= 100))
    print(count)
    print()

    count = defaultdict(int)
    for signal in total_wrong_signals_removed:
        count["".join(c for c in signal if not c.isnumeric())] += 1
    count = list(sorted((-c, s) for s,c in count.items() if c >= 100))
    print(count)
    print()

    # BOTH
    print("Both")
    count = defaultdict(int)
    for signal in (total_wrong_signals_removed + total_wrong_signals_added):
        count[signal] += 1
    count = list(sorted((-c, s) for s,c in count.items() if c >= 100))
    print(count)
    print()

    count = defaultdict(int)
    for signal in (total_wrong_signals_removed + total_wrong_signals_added):
        count["".join(c for c in signal if not c.isnumeric())] += 1
    count = list(sorted((-c, s) for s,c in count.items() if c >= 100))
    print(count)
    print()

    # import matplotlib.pyplot as plt
    # _ = plt.hist(quasi_devices.values(), bins='auto')
    # plt.show()

    wrong_signals_per_family = defaultdict(list)
    for device, wrong in quasi_devices.items():
        wrong_signals_per_family[device[:7]].append(wrong)

    chart_data = {
        "signals": quasi_devices,
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
    })
    data = chart_data["signals"]
    scale = 8.2
    figsize = (1, 0.225)

    plt.figure(figsize=(figsize[0]*scale, figsize[1]*scale))
    plt.hist(data.values(), bins=range(120), color="black")


    # plt.yscale('log', nonposy='clip')
    ax = plt.gca()
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.set_ylabel("Number of Devices")
    ax.set_xlabel("Number of Pin Function Conflicts")

    ax.annotate("STM32H7\nSTM32L1\nSTM32L4",
                xy=(97.5, 35), xytext=(97.5, 50), #xycoords='axes fraction',
                fontsize=9, ha='center', va='bottom',
                arrowprops=dict(arrowstyle='-[, widthB=6.4, lengthB=0.75', lw=1))

    ax.margins(y=0, x=0)
    x0, x1, y0, y1 = plt.axis()
    plt.axis((0, x1, y0, y1*1.01))
    # ax.set_yscale("log")

    figname = "evaluation_pin_function_distribution"
    fmt = dict(bbox_inches='tight', pad_inches=0.01, transparent=True)
    # plt.savefig(f"../../master/thesis/Thesis/figures/{figname}.pgf", **fmt)
    plt.savefig(f"{figname}.png", **fmt)


if __name__ == "__main__":
    data_eval = (Path(__file__).parent / "data_eval_signals.json")
    chars_eval = (Path(__file__).parent / "data_charts_signals.json")
    if "--charts" in sys.argv:
        charts = render_charts(json.loads(chars_eval.read_text()))
    elif "--eval" in sys.argv:
        chart_data = eval_signals(json.loads(data_eval.read_text()))
        chars_eval.write_text(json.dumps(chart_data, sort_keys=True, indent=2, cls=SetEncoder))
    else:
        reports = compare_signals()
        data_eval.write_text(json.dumps(reports, sort_keys=True, indent=2, cls=SetEncoder))
