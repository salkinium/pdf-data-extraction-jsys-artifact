# Copyright (c) 2022, Niklas Hauser
#
# This file is part of the modm-data project.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
# -----------------------------------------------------------------------------

import re, sys, json, subprocess
sys.path.extend([".", "ext/modm-devices"])
from pathlib import Path
from deepdiff import DeepDiff
from deepdiff.model import PrettyOrderedSet
from collections import defaultdict

import modm_devices.parser
import modm_data.cubemx
import modm_data.owl2py.stmicro
from pygount import SourceAnalysis, ProjectSummary


def repopath(path):
    return Path(__file__).parents[2] / path

def data_patches():
    patches = list(repopath("patches").glob("*/*.patch"))
    lines = 0
    for patch in patches:
        for line in patch.read_text().splitlines():
            if re.match(r"[+-][^+-].*", line) is not None:
                lines += 1
    return {"Patches": len(patches), "PatchLines": lines}

def data_pdfs():
    pdftotal = list(repopath("../../../Desktop/stmicro-pdf").glob("*.pdf"))
    rms = [pdf for pdf in pdftotal if pdf.stem.startswith("RM")]
    dss = [pdf for pdf in pdftotal if pdf.stem.startswith("DS")]
    ess = [pdf for pdf in pdftotal if pdf.stem.startswith("ES")]
    ums = [pdf for pdf in pdftotal if pdf.stem.startswith("UM")]
    pdfs = rms + dss# + ess + ums
    def _page_count(types):
        cmd = f'mdls -name kMDItemFSName -name kMDItemNumberOfPages {types} | '
        cmd += 'grep NumberOfPages | cut -d" " -f3 | paste -s -d+ - | bc'
        result = subprocess.run(cmd, shell=True, cwd=repopath("../../../Desktop/stmicro-pdf"), stdout=subprocess.PIPE)
        return int(result.stdout.decode("ascii").splitlines()[0])

    prms = _page_count("RM*.pdf")
    pdss = _page_count("DS*.pdf")
    pess = _page_count("ES*.pdf")
    pums = _page_count("UM*.pdf")
    ptotal = prms + pdss# + pess + pums

    return {"PdfCountTotal": len(pdftotal), "PdfCount": len(pdfs),
            "PdfCountRM": len(rms), "PdfCountDS": len(dss),
            "PdfCountES": len(ess), "PdfCountUM": len(ums),
            "PdfPageCount": ptotal,
            "PdfPageCountRM": prms, "PdfPageCountDS": pdss,
            "PdfPageCountES": pess, "PdfPageCountUM": pums,
            "PdfPageCountPctRM": round(prms/ptotal*100), "PdfPageCountPctDS": round(pdss/ptotal*100),
            "PdfPageCountPctES": round(pess/ptotal*100), "PdfPageCountPctUM": round(pums/ptotal*100)}

def data_headers():
    headers = list(repopath("ext/cmsis/stm32-header").glob("**/stm32*.h"))
    return {"StmHeaderCount": len(headers)}

def data_svds():
    cm_svds = list(repopath("ext/cmsis/svd/data/STMicro").glob("*.svd"))
    hd_svds = list(repopath("ext/cache/stmicro-svd").glob("header_*.svd"))
    rm_svds = list(repopath("ext/cache/stmicro-svd").glob("rm_*.svd"))
    return {"SvdCmsisCount": len(cm_svds), "SvdHeaderCount": len(hd_svds), "SvdRmCount": len(rm_svds)}

def data_cubemx():
    ignored = {"stm32g071.6", "stm32g441", "stm32g471", "stm32l041c4", "stm32l485"}
    devices = {d.string.split("@")[0] for d in modm_data.cubemx.devices()}
    ignored = {d for d in devices if any(re.match(p, d) for p in ignored)}
    # Simple devices without Pin, Size or Temperature keys
    devices_simple = {d[:9] + d[11:12] + d[13:] for d in devices}
    xmls = list(repopath("ext/modm-devices/tools/generator/raw-device-data/stm32-devices/mcu").glob("STM32*.xml"))
    return {"CubeDevCountTotal": len(devices),
            "CubeDevCount": len(devices - ignored),
            "CubeDevCountSimple": len(devices_simple),
            "CubeXmlCount": len(xmls)}

def data_owls():
    devices = modm_data.owl2py.stmicro.owl_devices()
    owls = modm_data.owl2py.stmicro.owls()
    ods = [o for o in owls if o.startswith("DS")]
    orm = [o for o in owls if o.startswith("RM")]
    return {"OwlDevCount": len(devices), "OwlCountDS": len(ods), "OwlCountRM": len(orm)}

def _code_size(*paths):
    dl_code = ProjectSummary()
    for path in paths:
        basepath = path.split("*")[0].rsplit("/", 1)[0] + "/"
        query = path.replace(basepath, "")
        if not query: query = "**/*.py"
        # print(basepath, query)
        for source_file in repopath(basepath).glob(query):
            source_analysis = SourceAnalysis.from_file(source_file, "pygount", encoding="utf-8")
            # print(source_file, source_analysis.code_count)
            dl_code.add(source_analysis)
    return sum(s.code_count for s in dl_code.language_to_language_summary_map.values())

def data_code():
    sizes = {"CodeSizeDlTechDoc": _code_size("modm_data/dl/"),
             "CodeSizePdfToHtml": _code_size("modm_data/pdf*/**/*.py", "modm_data/utils/"),
             "CodeSizeHtmlToOwl": _code_size("modm_data/html2py/**/*.py", "modm_data/html/**/*.py", "modm_data/*owl*/**/*.py"),
             "CodeSizeHtmlToSvd": _code_size("modm_data/html2svd/**/*.py"),
             "CodeSizeCube": _code_size("modm_data/cubemx/", "ext/modm-devices/tools/generator/dfg/input/xm*.py",
                                        "ext/modm-devices/tools/generator/dfg/stm32/stm_device*.py",
                                        "ext/modm-devices/tools/generator/dfg/stm32/stm_dmamux*.py"),
             "CodeSizeCmsisHeader": _code_size("ext/cmsis/stm32-header/updat*.py",
                                               "modm_data/header2svd/**/*.py"),
             "CodeSizeCmsisSvd": _code_size("ext/cmsis/svd/python/cmsis_svd/*.py"),
             "CodeSizeEval": _code_size("tools/eval/compare*.py"),
             "CodeSizeDlMachine": _code_size("ext/modm-devices/tools/generator/raw-data-extractor/*stm32.py",
                                             "ext/cmsis/stm32-header/update.py"),
             }
    sizes["CodeSizeTechDoc"] = sizes["CodeSizeDlTechDoc"] + sizes["CodeSizePdfToHtml"] + sizes["CodeSizeHtmlToOwl"] + sizes["CodeSizeHtmlToSvd"]
    sizes["CodeSizeMachineReadable"] = sizes["CodeSizeDlMachine"] + sizes["CodeSizeCube"] + sizes["CodeSizeCmsisHeader"] + sizes["CodeSizeCmsisSvd"]
    sizes["CodeSizeTechVsMachine"] = round(sizes["CodeSizeTechDoc"] / sizes["CodeSizeMachineReadable"], 1)
    return sizes


if __name__ == "__main__":
    data = {}
    data.update(data_patches())
    data.update(data_pdfs())
    data.update(data_headers())
    data.update(data_svds())
    data.update(data_cubemx())
    data.update(data_owls())
    data.update(data_code())
    print(json.dumps(data, sort_keys=True, indent=2))
