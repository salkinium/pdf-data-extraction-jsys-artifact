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


SUBSTITUTIONS = {
    "USB_WAKEUP": "USBWAKEUP",
    "LPTIMER1": "LPTIM1",
    r"QUAD-SPI": "QUADSPI",
    r"I2CFMP(\d)EVENT": r"FMPI2C\1_EV",
    r"I2CFMP(\d)ERROR": r"FMPI2C\1_ER",

    r"^DMA_CH": "DMA1_CH",
    r"^DMA_STR": "DMA1_STR",
    r"^DMAMUX_OVR": "DMAMUX1_OVR",
    r"DMA(\d)?_CH(.*)": r"DMA\1_Channel\2",
    r"DMA(\d)?_STR(.*)": r"DMA\1_Stream\2",
    r"CSS_LSE": "LSECSS",
    r"FSMC": "FMC",
    r"HRTIM1_": "HRTIM_",
    r"HRTIM_TIM_FLT": "HRTIM_FLT",
    r"TAMPER_STAMP": "TAMP_STAMP",
    r"^TAMPER$": "TAMP_STAMP",
    "EXTI17_RTCALARM": "RTC_ALARM",

    "DACUNDER": "DAC",
    "UCPD1GLOBALINTERRUPT": "UCPD1",
    "WAKEUP_PIN|WKUP": "WKP",
    "SPDIFRX": "SPDIF_RX",
    "EXTI1_0": "EXTI0_1",
    "EXTI3_2": "EXTI2_3",
    "EXTI15_4": "EXTI4_15",
    "EXTI9_5": "EXTI5_9",
    "USART4_USART5": "USART4_5",
    "ADC_COMP": "ADC1_COMP",
    "CANTX": "CAN_TX",
    "CANRXD": "CAN_RX0",
    "CANRXI": "CAN_RX1",
    "CANSCE": "CAN_SCE",
    "PVD_PVM|PDV_PVM": "PVD_AVD",
    "DMA1_CHANNEL4_5_6_7_DMA2_CHANNEL1_2_3_4_5_DMAMUX": "DMA1_CH4_7_DMAMUX1_OVR_DMA1_CH4_7_DMA2_CH1_5_DMAMUX1_OVR_DMA1_CH4_5_DMAMUX1_OVR",
    "DMA2_CHANNEL1_2_DMA_CH2_3": "DMA1_CHANNEL2_3_DMA1_CH2_3_DMA2_CH1_2",
    "DMA2_CHANNEL3_4_5_DMA_CH4_5_6_7": "DMA1_CHANNEL4_5_DMA1_CH4_7_DMA2_CH3_5",
    "I2C2_I2C3": "I2C2_3",
    "SPI2_SPI3": "SPI2_3",
    "USART3_USART4_USART5_USART6": "USART3_4_5_6",
    r"LCD-TFT": "LTDC_ER",
    "DMA2_CHANNEL1_2_DMA_CH2_3": "DMA1_CHANNEL2_3",
    "DMA2_CHANNEL3_4_5_DMA_CH4_5_6_7": "DMA1_CHANNEL4_5",
    "DAC1_DAC2_TIM6_GLB_IT": "TIM6_DAC",
    "TIM_TRG_COM_TIM11": "TIM1_TRG_COM_TIM11",
    "CRYPTO": "AES",
    "LPUART1_USART3_USART4_USART5_USART6": "USART3_4_5_6_LPUART1",
    "LSE_CSS_RTC_SSRU_RTC_STAMP_TAMP": "TAMP_STAMP_LSECSS_SSRU",
    "BUSY_RADIOIRQ": "SUBGHZ_RADIO",
    "UCPD1_UCPD2_USB": "USB_UCPD1_2",
    "HRTIM_MST": "HRTIM_MASTER",
}


def normalize_vector_name(name):
    for find, replace in SUBSTITUTIONS.items():
        name = re.sub(find, replace, name)
    return name.upper()




def find_table(did):
    if did.get("core"): return None
    interrupts = owl.InterruptTable.instances()
    for table in interrupts:
        name, *filters = table.name.split(":")
        if not filters: return table

        results = []
        for filt in filters:
            if filt.startswith("Device="):
                if re.match(filt[7:], did.string, re.IGNORECASE):
                    return table
            elif filt.startswith("Core="):
                return None
            elif filt.startswith("Categories="):
                return None

    return None


def compare_interrupts():
    reports = {}
    modm_devices = list(sorted(modm_data.cubemx.devices(), key=lambda d: d.string))

    for rm in modm_data.owl2py.stmicro.owls():
        if rm.startswith("RM"):
            print(f"ext/cache/stmicro-html/{rm}", f"ext/cache/stmicro-pdf/{rm}.pdf")
            owl.store.load(rm)
            filters = owl.DeviceFilter.instances()
            dids = [did for did in modm_devices if any(re.match(f.name, did.string) for f in filters)]
            for did in dids:
                print(did)
                file = modm_data.cubemx.device_file(did)
                vectors = {int(v["position"]): v["name"] for v in file.get_driver("core")["vector"]}

                otable = find_table(did)
                if otable is None:
                    print("TABLE NOT FOUND!!!")
                    reports[did.string] = "missing"
                    continue

                ovectors = defaultdict(list)
                for ovector in otable.hasInterruptVector:
                    opos = owl.vectorPosition[otable, owl.hasInterruptVector, ovector]
                    for pos in opos:
                        ovectors[pos].append(ovector.name)
                ovectors = {p:"_".join(sorted(v)) for p,v in ovectors.items()}

                # print(vectors)
                # print(ovectors)

                # print(opins)
                report_data = {
                    "modm_vectors": len(vectors),
                    "owl_vectors": len(ovectors),
                    "diffs": {}
                }

                for position, name in vectors.items():
                    oname = ovectors.get(position)
                    if oname is None:
                        print(position, "missing", name)
                        report_data["diffs"][position] = "missing"
                        continue
                    name = normalize_vector_name(name)
                    oname = normalize_vector_name(oname)

                    if name in oname or oname in name:
                        continue

                    names = set(name.split("_"))
                    onames = set(oname.split("_"))

                    if (all(name in onames for name in names) or
                        all(name in names for name in onames)):
                        continue

                    diff = [name, oname]
                    print(position, diff, names, onames)
                    report_data["diffs"][position] = diff

                reports[did.string] = report_data

    return reports


def eval_interrupts(reports):
    total_devices = 0
    missing_devices = 0
    correct_devices = 0

    total_vectors = 0
    missing_vectors = 0
    wrong_vectors = 0

    ignored = {"stm32g071.6", "stm32g441", "stm32g471", "stm32l041c4", "stm32l485", "stm32wb", "stm32l1"}

    for device, report in reports.items():
        if "@" in device:
            continue
        if any(re.match(p, device) for p in ignored):
            continue
        total_devices += 1
        if isinstance(report, str) and report == "missing":
            missing_devices += 1
            print(device, "MISSING")
            continue

        # print(device)

        total_vectors += report["modm_vectors"]

        diffs = report["diffs"]
        if not diffs:
            correct_devices += 1
            continue
        for position, diff in diffs.items():
            if diff == "missing":
                missing_vectors += 1
                continue
            if set(diff) == {"LPTIMER1", "LPTIM1"}: continue
            if set(diff) == {"SUBGHZ_RADIO", "BUSY_RADIOIRQ"}: continue
            if set(diff) == {"HRTIM_MASTER", "HRTIM_MST"}: continue
            if set(diff) == {"HSEM1", "HSEM0"}: continue
            if set(diff) == {"DMA1_CH4_7_DMAMUX1_OVR", "DMA1_CHANNEL4_5_6_7_DMA2_CHANNEL1_2_3_4_5_DMAMUX"}: continue
            if set(diff) == {"DMA1_CH4_7_DMA2_CH1_5_DMAMUX1_OVR", "DMA1_CHANNEL4_5_6_7_DMA2_CHANNEL1_2_3_4_5_DMAMUX"}: continue
            if set(diff) == {"DMA1_CH4_5_DMAMUX1_OVR", "DMA1_CHANNEL4_5_6_7_DMA2_CHANNEL1_2_3_4_5_DMAMUX"}: continue
            if set(diff) == {"USART3_4_LPUART1", "LPUART1_USART3_USART4_5_USART6"}: continue
            if set(diff) == {"USART3_4_5_6_LPUART1", "LPUART1_USART3_USART4_5_USART6"}: continue
            if set(diff) == {"OTG_FS_WKP", "OTG_FSWKP"}: continue
            if set(diff) == {"FMPI2C1_EV", "I2CFMP1EVENT"}: continue
            if set(diff) == {"FMPI2C1_ER", "I2CFMP1ERROR"}: continue
            if set(diff) == {"RTC_ALARM", "EXTI17_RTCALARM"}: continue
            if set(diff) == {"QUADSPI", "QUAD-SPI"}: continue
            if set(diff) == {"USBWAKEUP_RMP", "USB_WAKEUP_RMP"}: continue
            if set(diff) == {"RTC_ALARM", "RTCALARM"}: continue
            if set(diff) == {"DMA1_CHANNEL4_5_6_7", "DMA2_CHANNEL3_4_5_DMA_CH4_5_6_7"}: continue
            if set(diff) == {"DMA1_CHANNEL2_3", "DMA2_CHANNEL1_2_DMA_CH2_3"}: continue
            if set(diff) == {"FMPI2C1_ER", "FMPI2C1ERROR"}: continue
            if set(diff) == {"DMA1_CHANNEL2_3", "DMA2_CHANNEL1_2_DMA_CH2_3"}: continue
            if set(diff) == {"SPDIF_RX", "SPDIF-RX"}: continue
            if set(diff) == {"DMA1_CH2_3_DMA2_CH1_2", "DMA2_CHANNEL1_2_DMA_CH2_3"}: continue
            if set(diff) == {"DMA1_CH4_7_DMA2_CH3_5", "DMA2_CHANNEL3_4_5_DMA_CH4_5_6_7"}: continue
            if set(diff) == {"DMA1_CH1", "DMA1_CHANNEL1"}: continue
            if set(diff) == {"USART3_4_5_6", "USART3_USART4_5_USART6"}: continue
            print(position, diff)
            wrong_vectors += 1


    correct_vectors = total_vectors - missing_vectors - wrong_vectors
    wrong_devices = total_devices - missing_devices - correct_devices
    table_devices = total_devices - missing_devices
    print()
    print(f"correct_devices={correct_devices}/{total_devices} = {correct_devices/total_devices*100:.1f}%")
    print(f"table_devices={table_devices}/{total_devices} = {table_devices/total_devices*100:.1f}%")
    print(f"missing_devices={missing_devices}/{total_devices} = {missing_devices/total_devices*100:.1f}%")
    print(f"wrong_devices={wrong_devices}/{total_devices} = {wrong_devices/total_devices*100:.1f}%")
    print()
    print(f"correct_vectors={correct_vectors}/{total_vectors} = {correct_vectors/total_vectors*100:.1f}%")
    print(f"missing_vectors={missing_vectors}/{total_vectors} = {missing_vectors/total_vectors*100:.1f}%")
    print(f"wrong_vectors={wrong_vectors}/{total_vectors} = {wrong_vectors/total_vectors*100:.1f}%")


if __name__ == "__main__":
    data_eval = (Path(__file__).parent / "data_eval_interrupts.json")
    if "--eval" in sys.argv:
        eval_interrupts(json.loads(data_eval.read_text()))
    else:
        reports = compare_interrupts()
        data_eval.write_text(json.dumps(reports, sort_keys=True, indent=2))
