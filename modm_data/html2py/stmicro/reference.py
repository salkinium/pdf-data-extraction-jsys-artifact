# Copyright (c) 2022, Niklas Hauser
#
# This file is part of the modm-data project.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
# -----------------------------------------------------------------------------

import re
from functools import cached_property, cache
from collections import defaultdict
import modm_data.html as html
from .identifier import split_device_filter


class ReferenceManual(html.Document):
    def __init__(self, path: str):
        super().__init__(path)

    def __repr__(self) -> str:
        return f"RM({self.fullname})"

    @cached_property
    def devices(self) -> list[str]:
        # Find all occurrences of STM32* strings in the first chapter
        chapter = self.chapter("chapter 0")
        for heading, texts in chapter.heading_texts():
            all_text = ""
            for text in texts:
                all_text += text.text(br=" ")
            # print(heading, all_text)
            # Must also match "STM32L4+" !!!
            rdevices = re.findall(r"STM32[\w/\+]+", all_text)
            if rdevices:
                break

        # Split combo strings into individual devices
        devices = []
        for device in list(set(rdevices)):
            if len(parts := device.split("/")) >= 2:
                base = parts[0]
                devices.append(base)
                base = base[:-len(parts[1])]
                for part in parts[1:]:
                    devices.append(base + part)
            else:
                devices.append(device)

        # Remove non-specific mentions: shortest subset
        return list(sorted(set(devices)))

    @property
    def device_filters(self) -> list[str]:
        # Match STM32L4+ with STM32[SRQP], since STM32L4Axx is STM32L4 (without +)
        return [d.replace("x", ".").replace("+", r"[SRQP]").lower() for d in self.devices]

    def filter_devices(self, devices):
        dids = set()
        for did in devices:
            for device in self.device_filters:
                if re.match(device, did.string):
                    dids.add(did)
                    break
        return list(dids)

    @cached_property
    def vector_tables(self):
        name_replace = {"p": r"\1,", r" +": "", r"\(.*?\)|_IRQn|_$|^-$|[Rr]eserved": "",
                        r"\+|and": ",", r"_(\w+)(LSE|BLE|I2C\d)_": r"_\1,\2_",
                        r"EXTI\[(\d+):(\d+)\]": r"EXTI\1_\2", r"\[(\d+):(\d+)\]": r"\2_\1"}
        capt_replace = {"br": " ", r" +": " ", r"\((Cat\.\d.*?devices)\)": r"\1", r"\(.*?\)": "",
                        r"for +connectivity +line +devices": "for STM32F105/7",
                        r"for +XL\-density +devices": "for STM32F10xxF/G",
                        r"for +other +STM32F10xxx +devices": "for the rest",}

        chapter = next(c for c in self.chapters(r"nvic|interrupt") if "exti" not in c.name)
        tables = chapter.tables(r"vector +table|list +of +vector|NVIC|CPU")
        assert tables

        vtables = {}
        for table in tables:
            caption = table.caption(**capt_replace)
            table_name = "VectorTable"
            if len(tables) > 1:
                # Create the right table filter
                if (core := re.search(r"CPU(\d)|NVIC(\d)", caption)) is not None:
                    table_name += f":Core={core.group(1)}" # Multi-core device
                elif devices := re.findall(r"(STM32[\w/]+)", caption):
                    ndevices = []
                    for device in devices:
                        ndevices.extend(split_device_filter(device))
                    # General device identifier filter
                    devices = "|".join(d.replace("x", ".") for d in sorted(ndevices))
                    table_name += f":Device={devices}"
                elif categories := re.findall(r"Cat\.(\d)", caption):
                    # Size category filter
                    categories = "|".join(categories)
                    table_name += f":Categories={categories}"

            vtable = defaultdict(set)
            for pos, values in table.domains("position").cells("acro").items():
                if pos.isnumeric() and (name := values.match_value("acro")[0].text(**name_replace)):
                    vtable[int(pos)].update(html.listify(name))
            vtables[table_name] = dict(vtable)

        return vtables

    @cache
    def peripheral_maps(self, chapter, assert_table=True):
        off_replace = {r" +": "", "0x000x00": "0x00", "to": "-", "×": "*", r"\(\d+\)": ""}
        dom_replace = {r"Register +size": "Bit position"}
        reg_replace = {
            r" +|\.+": "", r"\(COM(\d)\)": r"_COM\1",
            r"^[Rr]es$||0x[\da-fA-FXx]+|\(.*?\)|-": "",
            r"(?i)reserved|resetvalue.*": "", "enabled": "_EN", "disabled": "_DIS",
            r"(?i)Outputcomparemode": "_Output", "(?i)Inputcapturemode": "_Input", "mode": "",
            r"^TG_FS_": "OTG_FS_", "toRTC": "RTC", "SPI2S_": "SPI_",
            r"andTIM\d+_.*": "", r"x=[\d,]+": ""}
        fld_replace = {
            r"\] +\d+(th|rd|nd|st)": "]", r" +|\.+|\[.*?\]|\[?\d+:\d+\]?|\(.*?\)|-|^[\dXx]+$|%|__|:0\]": "",
            r"Dataregister|Independentdataregister": "DATA",
            r"Framefilterreg0.*": "FRAME_FILTER_REG",
            r"[Rr]es(erved)?|[Rr]egular|x_x(bits)?|NotAvailable|RefertoSection\d+:Comparator": "",
            r"Sampletimebits|Injectedchannelsequence|channelsequence|conversioninregularsequencebits": "",
            r"conversioninsequencebits|conversionininjectedsequencebits|or|first|second|third|fourth": ""}
        bit_replace = {r".*:": ""}
        glo_replace = {r"[Rr]eserved": ""}

        print(chapter._relpath)
        tables = chapter.tables(r"register +map")
        if assert_table: assert tables

        peripheral_data = {}
        for table in tables:
            caption = table.caption()
            if any(n in caption for n in ["DFIFO", "global", "EXTI register map section", "vs swapping option"]):
                continue
            heading = table._heading.text(**{r"((\d+\.)+(\d+)?).*": r"\1"})
            print(table, caption)

            register_data = {}
            for row in table.cell_rows():
                rkey = next(k for k in row.match_keys("register") if not "size" in k)
                register = row[rkey][0].text(**reg_replace).strip()
                if not register: continue
                offset = row.match_value(r"off-?set|addr")[0].text(**off_replace)
                if not offset: continue
                field_data = {}
                for bits in row.match_keys(r"^[\d-]+$|.*?:[\d-]+$"):
                    field = row[bits][0].text(**fld_replace).strip()
                    if not field: continue
                    bits = sorted(html.listify(html.replace(bits, **bit_replace), r"-"))
                    if len(bits) == 2: bits = range(int(bits[0]), int(bits[1]))
                    for bit in bits:
                        bit = int(bit)
                        field_data[bit] = field
                        # print(f"{offset:>10} {register:60} {bit:>2} {field}")
                register_data[register] = (offset, field_data)
            assert register_data
            peripheral_data[caption] = (heading, register_data)

        if peripheral_data and all("HRTIM" in ca for ca in peripheral_data):
            caption, heading = next((c,p) for c, (p, _) in peripheral_data.items())
            all_registers = {k:v for (_, values) in peripheral_data.values() for k,v in values.items()}
            peripheral_data = {caption: (heading, all_registers)}

        instance_offsets = {}
        if tables := chapter.tables(r"ADC +global +register +map"):
            for row in tables[0].cell_rows():
                if ifilter := row.match_value("register")[0].text(**glo_replace):
                    offset = int(row.match_value("offset")[0].text().split("-")[0], 16)
                    for instance in re.findall(r"ADC(\d+)", ifilter):
                        instance_offsets[f"ADC[{instance}]"] = offset

        return peripheral_data, instance_offsets

    @cached_property
    def peripherals(self):
        per_replace = {
            r" +": "", r".*?\(([A-Z]+|DMA2D)\).*?": r"\1",
            r"Reserved|Port|Power|Registers|Reset|\(.*?\)|_REG": "",
            r"(\d)/I2S\d": r"\1", r"/I2S|CANMessageRAM|Cortex-M4|I2S\dext|^GPV$": "",
            r"Ethernet": "ETH", r"Flash": "FLASH", r"(?i).*ETHERNET.*": "ETH",
            r"(?i)Firewall": "FW", r"HDMI-|": "", "SPDIF-RX": "SPDIFRX",
            r"SPI2S2": "SPI2", "Tamper": "TAMP", "TT-FDCAN": "FDCAN",
            r"USBOTG([FH])S": r"USB_OTG_\1S", "LCD-TFT": "LTDC", "DSIHOST": "DSI",
            "TIMER": "TIM", r"^VREF$": "VREFBUF", "DelayBlock": "DLYB",
            "I/O": "M", "I/O": "", "DAC1/2": "DAC12",
            r"[a-z]": ""}
        adr_replace = {r" |\(\d\)": ""}
        sct_replace = {r"-": ""}
        hdr_replace = {r"Peripheral +register +map": "map"}
        bus_replace = {r".*(A\wB\d).*": r"\1", "-": ""}

        # RM0431 has a bug where the peripheral table is in chapter 1
        if "RM0431" in self.name:
            chapters = self.chapters(r"chapter 1 ")
        else:
            chapters = self.chapters(r"memory +and +bus|memory +overview")
        assert chapters
        print(chapters[0]._relpath)

        tables = chapters[0].tables(r"register +boundary")
        assert tables

        peripherals = defaultdict(list)
        for table in tables:
            print(table.caption())
            for row in table.cell_rows(**hdr_replace):
                regmaps = row.match_value("map")
                if regmaps:
                    regmap = regmaps[0].text(**sct_replace).strip()
                    sections = re.findall(r"Section +(\d+\.\d+(\.\d+)?)", regmap)
                    if not sections: continue
                    sections = [s[0] for s in sections]
                else:
                    sections = []
                names = html.listify(row.match_value("peri")[0].text(**per_replace), r"[-\&\+/,]")
                if not names: continue
                address = row.match_value("address")[0].text(**adr_replace)
                address_min = int(address.split("-")[0], 16)
                address_max = int(address.split("-")[1], 16)
                bus = row.match_value("bus")[0].text(**bus_replace).strip()
                peripherals[table.caption()].append( (names, address_min, address_max, bus, sections) )
                print(f"{','.join(names):20} @[{hex(address_min)}, {hex(address_max)}] {bus:4} -> {', '.join(sections)}")

        return peripherals
