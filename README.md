# Automatically Extracting Hardware Descriptions from PDF Technical Documentation

The ever-increasing selection of microcontrollers brings the challenge of
porting embedded software to new devices through much manual work, while code
generators are used only in special cases. Since, in practice, usable data is
limited to machine-readable formats and the substantial amount of technical
documentation is difficult to access due to the print-oriented nature of PDF,
we identify the need for a processor to access the PDFs and extract data with a
high quality to enable more code generation of embedded software.

In this paper, we design and implement a modular processor for extracting
detailed data sets from technical documentation using deterministic table
processing for thousands of microcontrollers: device identifiers, interrupt
tables, package and pinouts, pin functions, and register maps. Our evaluation
of STMicro documentation compares the completeness and correctness of these
data sets against existing machine-readable sources with a weighted average of
96.5% across almost 6 million data points while also finding several issues in
both sources. We show that our tool yields very accurate data with only limited
manual effort and can enable and enhance a significant amount of existing and
new code generation use cases in the embedded software domain that are
currently limited by a lack of machine-readable data sources.

---

The paper is published by the Journal of Systems Research (JSys) and is
[available free of charge here](http://dx.doi.org/10.5070/SR33162446).

```bib
@article{HP23,
  author = {Hauser, Niklas and Pennekamp, Jan},
  title = {{Automatically Extracting Hardware Descriptions from PDF Technical Documentation}},
  journal = {Journal of Systems Research},
  year = {2023},
  volume = {3},
  number = {1},
  publisher = {eScholarship Publishing},
  month = {10},
  doi = {10.5070/SR33162446},
  code = {https://github.com/salkinium/pdf-data-extraction-jsys-artifact},
  code2 = {https://github.com/modm-io/modm-data},
  meta = {},
}
```

Please note that this repository is archived for reproducibility. Any future
development will be done in the [modm-io/modm-data](https://github.com/modm-io/modm-data).
repository.


## Acknowledgement

We thank the JSys reviewers for their remarks that improved our manuscript.
We are grateful to Eduard Vlad for testing the artifacts and improving their
documentation as well as to Roman Matzutt for proof-reading the manuscript.


## Artifact

This repository contains the exact same code that passed the artifact evaluation
by the Journal of Systems Research (JSys).


### Code Artifact

This repository contains the entire code for the tool licensed as MPLv2:

- The conversion pipelines are implemented in the `modm_data` folder and are
  orchestrated by the `tools/scripts` files.
- The HTML patches are in the `patches` folder.
- The evaluation code and data in in the `tools/eval` folder.


### Data Artifact

The input and output data is zipped as a separate file, which we are not allowed
to distribute publicly due to the copyright of the STMicro PDF documentation.
**Please contact [@salkinium](mailto:niklas@salkinium.com) to provide you with a
private copy of the input sources to proceed.**

Please extract or symlink the artifact into the `ext/` folder, so the code
artifact has this structure:

```
jsys-artifact-code
├── ext
│   ├── cache
│   │   ├── stmicro-html
│   │   ├── stmicro-owl
│   │   ├── stmicro-pdf
│   │   └── stmicro-svd
│   ├── cmsis
│   └── modm-devices
├── modm_data
├── patches
└── tools
```

There are two artifact versions:

1. A tiny version of the data that can be used to test all pipelines
   quickly with the individual commands described in each pipeline.
   However, it does not allow for the full evaluation to run.
2. A complete version, containing all input data required to run all pipelines
   completely and perform the evaluation on the output data.


## Installation

This is a **Python 3.11** project making use of these libraries:

- `pypdfium2` for C-bindings to `pdfium`; a pdf manipulation library.
- `anytree` for a tree data structure.
- `owlready2` for working with knowledge graphs via [OWL](https://www.w3.org/OWL/).
- `dashtable` for formatting tables in debug mode.
- `BeautifulSoup4` as a dependency for dashtable, unfortunately.
- `numpy` for working with transformation matrices.
- `lxml` for working with HTML.
- `pillow` for debug renders and image manipulation.
- `patch_ng` for applying unified diff patches.
- `deepdiff` for diffing data structures.
- `CppHeaderParser` for parsing C headers.
- `pygount` for counting source lines, similar to `cloc`.
- `matplotlib` for drawing graphs.
- `jinja2` for templating as part of `modm-devices`.

Install the project dependencies with the following command:

```bash
pip install -r requirements.txt
```

You also need `g++` installed and callable in your path.


## Pipelines

The implemented pipelines are available as Python modules inside `modm_data`
folder. The actually implemented data pipelines have the following structure:

```
              ┌──────┐                 ┌──────────┐
    ┌────────►│CubeMX├─[modm-devices]─►│XML Format├─────────[modm-devices]──────┐
    │         └──────┘                 └──────────┘                             ▼
┌───┴───┐  ┌────────────┐             ┌───────────┐                      ┌───────────┐               ┌─────────┐
│STMicro├─►│PDF Document├─[pdf2html]─►│HTML Folder├───────────[html2py]─►│Python Data│◄─[owlready2]─►│OWL Graph│
└───┬───┘  └────────────┘             └───────────┴──[html2svd]─┐        └─────────┬─┘               └─────────┘
    ├────────────────────────────────────────────────┐          ▼               ▲  │                ┌──────────┐
    │                     ┌────────────┐             │  ┌─────────┐             │  └───────────────►│Evaluation│
    └────────────────────►│CMSIS Header├─[header2svd]┴─►│CMSIS-SVD├─[cmsis-svd]─┘                   └──────────┘
                          └────────────┘                └─────────┘
```

Not all pipelines are implemented directly in this project. For example,
accessing the (7) STM32CubeMX database is already implemented by the
`ext/modm-devices` project, so we just call their Python code directly.
Similarly, parsing the (6) CMSIS-SVD files is already implemented by the
`ext/cmsis/svd` project. Therefore some pipelines just involve calling a single
library function, and are simply part of the evaluation and not callable on
their own. However, all novel pipelines are individually callable as described
here.


### (2) PDF to HTML Pipeline

Conversion from HTML to PDF can be performed either selectively or for the
entirety of PDF files from STMicro. Both ways are presented below.


#### Selective Conversion

Examples of accessing STMicro PDFs with the `tools/scripts/pdf2html.py` script:

```bash
# show the raw AST of the first page
python3 tools/scripts/pdf2html.py --document ext/cache/stmicro-pdf/DS11581-v6.pdf --page 1 --ast

# show the normalized AST of the first 20 pages
python3 tools/scripts/pdf2html.py --document ext/cache/stmicro-pdf/DS11581-v6.pdf --range :20 --tree

# Overlay the graphical debug output on top of the input PDF
python3 tools/scripts/pdf2html.py --document ext/cache/stmicro-pdf/DS11581-v6.pdf --page 1 --pdf --output test.html

# Convert a single PDF page into HTML
python3 tools/scripts/pdf2html.py --document ext/cache/stmicro-pdf/DS11581-v6.pdf --page 1 --html --output test.html

# Convert the whole PDF into a single (!) HTML
python3 tools/scripts/pdf2html.py --document ext/cache/stmicro-pdf/DS11581-v6.pdf --html --output test.html

# Convert the whole PDF into a folder with multiple HTMLs using multiprocessing
python3 tools/scripts/pdf2html.py --document ext/cache/stmicro-pdf/DS11581-v6.pdf --parallel --output DS11581
```

#### Automatic Conversion

We recommend using the Makefile to convert all PDFs. This can take 1-2 hours!
The parallelism depends on the number of CPU cores and amount of RAM. We
recommend using 4-8 jobs at most. The Makefile also redirects the output of
every conversion into the `log/` folder.

```bash
# Conversion of a single datasheet
make ext/cache/stmicro-html/DS11581-v6
# or multiple PDFs
make ext/cache/stmicro-html/DS11581-v6 ext/cache/stmicro-html/RM0432-v9
# Convert all PDFs (Datasheets, Reference Manuals)
make convert-html -j4
# Clean all PDFs
make clean-html
```

Selective conversion of PDFs is also possible:

```bash
# Data Sheets only
make convert-html-ds
# Reference Manuals only
make convert-html-rm
```


### (3) HTML to OWL Pipeline

The resulting knowledge graphs are found in `ext/cache/stmicro-owl`.
Sadly owlready2 does not sort the XML serialization, so the graphs change with
every call, making diffs impractical.
Only takes a few minutes.

```bash
# Convert a single HTML folder to OWL using table processing
python3 tools/scripts/html2owl.py --document ext/cache/stmicro-html/DS11581-v6
# Convert ALL HTML folders using multiprocessing with #CPUs jobs
python3 tools/scripts/html2owl.py --all
```

To perform the steps automatically, you may also use `make`:

```bash
# Generate all owl files
make convert-html-owl
# Remove all generated OWL Graphs
make clean-owl
```


### (4) HTML to SVD Pipeline

The resulting SVD files are found in `ext/cache/stmicro-svd`.
Only takes a few minutes.

```bash
# Convert a single HTML folder to SVD using table processing
python3 tools/scripts/html2svd.py --document ext/cache/stmicro-html/RM0432-v9
# Convert ALL HTML folders using multiprocessing
python3 tools/scripts/html2svd.py --all
```

To perform the steps automatically, you may also use `make`:

```bash
# Conversion using make
make convert-html-svd
# Remove all svd files generated for rms
make clean-html-svd
```


### (5) CMSIS Header to SVD Pipeline

The resulting SVD files are found in `ext/cache/stmicro-svd`.
Only takes a few minutes.

```bash
# Convert a group of devices into SVD files
python3 tools/scripts/header2svd.py --device stm32f030c6t6 --device stm32f030f4p6 --device stm32f030k6t6
# Convert all CMSIS headers into SVD files
python3 tools/scripts/header2svd.py --all
```

To perform the steps automatically, you may also use `make`:

```bash
# Using make
make convert-header-svd
# Remove all svd files
make clean-svd
```



## 5 Evaluation

The evaluation scripts reside in the `tools/eval` folder including their output
as `.txt` files. For some steps the eval is split into two or three steps,
since the actual comparison code is quite slow and the subsequent statistical
computing is done later. The intermediary data is stored as JSON files in the
same folder.

### Requirements

To successfully render the charts, some dependencies are required.
Specifically, a LaTeX distribution like, `texlive` is needed along with
`texlive-science` or at least the `siunitx.sty` style file.

To install the dependencies use the following command:

```bash
# Arch Linux
pacman -S texlive-bin texlive-science
# Ubuntu 22.04 (untested)
apt install texlive-base texlive-science
```

### Automatic evaluation

To perform the automatic evaluation for all the steps described below, execute
the following command:

```bash
make evaluation-all
```


### 5.1 HTML quality

Assessed manually. Click around in the HTML archive to see for yourself.
Also see the `patches/stmicro` folder for an understanding of what needed to be
manually fixed.


### 5.4.1 Device Identifiers

Data for Table 4 is in `tools/eval/output_eval_identifiers.txt`

```bash
# Check if all documents are uniquely identifiable
# Then checks if the identifier are subsets of each other
python3 tools/eval/compare_identifiers.py > tools/eval/output_eval_identifiers.txt
```

Alternatively, you may use the `make` command:

```bash
make evaluation-did
```


### 5.4.2 Interrupt Vector Table

Data is part of the section text from `tools/eval/output_eval_interrupts.txt`

```bash
# Compiles the comparison data (slow)
python3 tools/eval/compare_interrupts.py > tools/eval/output_compare_interrupts.txt
# Computes and formats the comparison data nicely
python3 tools/eval/compare_interrupts.py --eval > tools/eval/output_eval_interrupts.txt
```

Alternatively, you may use the `make` command:

```bash
make evaluation-ivt
```


### 5.4.3 Package and Pinout

This is a lot of data to compare, so this will take like 10mins to compile the
initial comparison. The eval formatting is then faster.
See the `manual_eval_packages.txt` for the data that sources Appendix Table 9 and 10.

```bash
# Compiles the comparison data (very slow!)
python3 tools/eval/compare_packages.py > tools/eval/output_compare_packages.txt
# Computes and formats the comparison data
python3 tools/eval/compare_packages.py --eval > tools/eval/output_eval_packages.txt
```

Alternatively, you may use the `make` command:

```bash
make evaluation-pap
```


### 5.4.4 Pin Functions

Again, lots of data, relatively slow.
Data in text and for Appendix Table 11 and 12.

```bash
# Compiles the comparison data (very slow!)
python3 tools/eval/compare_signals.py > tools/eval/output_compare_signals.txt
# Computes and formats the comparison data
python3 tools/eval/compare_signals.py --eval > tools/eval/output_eval_signals.txt
# Outputs charts
python3 tools/eval/compare_signals.py --charts
```

Alternatively, you may use the `make` command:

```bash
make evaluation-pf
```


### 5.4.5 Register Descriptions

This eval takes 30-40mins due to the sheer mass of data to evaluate.
Data in text, for Table 5, 6, 7, and 13.
Charts for Figure 5, 6, 7, and 8.

```bash
# Compiles the pinout comparison data (very slow!)
python3 tools/eval/compare_svds.py --compare > tools/eval/output_compare_svds.txt
# Computes and formats the comparison data
python3 tools/eval/compare_svds.py --eval > tools/eval/output_eval_svds.txt
# Outputs charts
python3 tools/eval/compare_svds.py --charts
```

Alternatively, you may use the `make` command:

```bash
make evaluation-rd
```


### Appendix

The tables in the appendix have been manually curated from the evaluation data.

Appendix Table 9 and 10 are sourced from the `manual_eval_signals.txt` file,
which contains a filtered and annotated version of the data from the 5.4.3
evaluation resulting in the `output_eval_packages.txt` file.

Appendix Table 11 is sourced from the `output_eval_signals.txt` file created by
the 5.4.4 evaluation.

Appendix Table 12 is a filtered and annotated version of the same
`output_eval_signals.txt` file, resulting in the `manual_eval_signals.txt` file.

Appendix Table 13 is sources from the `output_eval_svd.txt` file created by the
5.4.5 evaluation.
