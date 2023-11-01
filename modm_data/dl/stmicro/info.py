# Copyright (c) 2022, Niklas Hauser
#
# This file is part of the modm-data project.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
# -----------------------------------------------------------------------------

import json
import logging
from ..store import download_data
from .document import Document
from ...utils import cache_path


_json_short_urls = {
    # Technical docs for STM32 microcontrollers
    "stm32": [
        "microcontrollers-microprocessors/stm32-32-bit-arm-cortex-mcus.cxst-rs-grid.html/CL1734.technical_literature.json",
        "microcontrollers-microprocessors/stm32-32-bit-arm-cortex-mcus/stm32-high-performance-mcus.cxst-rs-grid.html/SC2154.technical_literature.json",
        "microcontrollers-microprocessors/stm32-32-bit-arm-cortex-mcus/stm32-mainstream-mcus.cxst-rs-grid.html/SC2155.technical_literature.json",
        "microcontrollers-microprocessors/stm32-32-bit-arm-cortex-mcus/stm32-ultra-low-power-mcus.cxst-rs-grid.html/SC2157.technical_literature.json",
        "microcontrollers-microprocessors/stm32-32-bit-arm-cortex-mcus/stm32-wireless-mcus.cxst-rs-grid.html/SC2156.technical_literature.json",
    ],
    # Technical docs for STM32 development boards
    "boards": [
        "evaluation-tools/product-evaluation-tools/mcu-mpu-eval-tools/stm32-mcu-mpu-eval-tools/stm32-nucleo-boards.cxst-rs-grid.html/LN1847.technical_literature.json",
        "evaluation-tools/product-evaluation-tools/mcu-mpu-eval-tools/stm32-mcu-mpu-eval-tools/stm32-discovery-kits.cxst-rs-grid.html/LN1848.technical_literature.json",
        # "evaluation-tools/product-evaluation-tools/mcu-mpu-eval-tools/stm32-mcu-mpu-eval-tools/stm32-eval-boards.cxst-rs-grid.html/LN1199.technical_literature.json",
    ],
    # Technical docs for STMicro sensors
    "sensors": [
        "mems-and-sensors/accelerometers.cxst-rs-grid.html/SC444.technical_literature.json",
        "mems-and-sensors/automotive-sensors.cxst-rs-grid.html/SC1946.technical_literature.json",
        "mems-and-sensors/e-compasses.cxst-rs-grid.html/SC1449.technical_literature.json",
        "mems-and-sensors/gyroscopes.cxst-rs-grid.html/SC1288.technical_literature.json",
        "mems-and-sensors/humidity-sensors.cxst-rs-grid.html/SC1718.technical_literature.json",
        "mems-and-sensors/inemo-inertial-modules.cxst-rs-grid.html/SC1448.technical_literature.json",
        "mems-and-sensors/mems-microphones.cxst-rs-grid.html/SC1922.technical_literature.json",
        "mems-and-sensors/pressure-sensors.cxst-rs-grid.html/SC1316.technical_literature.json",
        "mems-and-sensors/temperature-sensors.cxst-rs-grid.html/SC294.technical_literature.json",
    ],
    # Technical docs for STMicro data converters (unused)
    # "converters": [
    #     "data-converters/a-d-d-a-converters.cxst-rs-grid.html/SC47.technical_literature.json",
    #     "data-converters/isolated-adcs.cxst-rs-grid.html/SC2514.technical_literature.json",
    #     "data-converters/metering-ics.cxst-rs-grid.html/SC397.technical_literature.json",
    # ]
}
_json_base_url = "https://www.st.com/content/st_com/en/products/"

json_urls = {key: [_json_base_url + url for url in urls] for key, urls in _json_short_urls.items()}
remote_info_path = "stmicro-pdf/remote.json"
local_info_path = "stmicro-pdf/local.json"
LOGGER = logging.getLogger(__name__)


def load_remote_info(use_cached: bool = False) -> list[dict]:
    info = cache_path(remote_info_path)
    if use_cached and info.exists():
        LOGGER.debug(f"Loading remote info from cache")
        docs = json.loads(info.read_text())
    else:
        LOGGER.info(f"Downloading remote info")
        docs = []
        for urls in json_urls.values():
            for url in urls:
                docs.extend(json.loads(download_data(url))["rows"])
    return docs


def store_remote_info(docs: list[dict]):
    info = cache_path(remote_info_path)
    info.parent.mkdir(parents=True, exist_ok=True)
    info.write_text(json.dumps(sorted(docs, key=lambda d: (d["title"], d["version"])), indent=4, sort_keys=True))


def load_local_info() -> list[dict]:
    info = cache_path(local_info_path)
    if info.exists():
        LOGGER.debug(f"Loading local info from cache")
        return json.loads(info.read_text())
    return []


def store_local_info(docs: list[dict]):
    info = cache_path(local_info_path)
    info.parent.mkdir(parents=True, exist_ok=True)
    info.write_text(json.dumps(sorted(docs, key=lambda d: (d["title"], d["version"])), indent=4, sort_keys=True))


def sync_info(use_cached: bool = False) -> set[Document]:
    remote_docs = set(map(Document, load_remote_info(use_cached)))
    local_docs = set(map(Document, load_local_info()))
    return remote_docs - local_docs
