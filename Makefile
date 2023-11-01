# Copyright (c) 2022, Niklas Hauser
#
# This file is part of the modm-data project.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
# -----------------------------------------------------------------------------

log/stmicro/%:
	@mkdir -p $@

# ============================= Downloading PDFs ==============================
.PHONY: update-pdfs
update-pdfs:
	@python3 tools/scripts/update_pdfs.py

# ========================== Converting PDF to HTML ===========================
html_output = $(patsubst ext/cache/stmicro-pdf/%.pdf, ext/cache/stmicro-html/%, $1)

ext/cache/stmicro-html/%: ext/cache/stmicro-pdf/%.pdf log/stmicro/pdf/
	@echo "Converting" $< "->" $@ "+" $(patsubst ext/cache/stmicro-html/%, log/stmicro/pdf/%.txt, $@)
	@-python3 tools/scripts/pdf2html.py --document $< --output $@ --html --parallel > \
			$(patsubst ext/cache/stmicro-html/%, log/stmicro/pdf/%.txt, $@) 2>&1


# ============================= Reference Manuals =============================
# Reference manual targets
HTML_RM = $(call html_output, $(sort $(wildcard ext/cache/stmicro-pdf/RM*.pdf)))

HTML_RM_LEN = $(words $(HTML_RM))
HTML_RM_LEN_PART_0  = 0
HTML_RM_LEN_PART_1  = $(shell expr $(HTML_RM_LEN) \* 1 / 10)
HTML_RM_LEN_PART_2  = $(shell expr $(HTML_RM_LEN) \* 2 / 10)
HTML_RM_LEN_PART_3  = $(shell expr $(HTML_RM_LEN) \* 3 / 10)
HTML_RM_LEN_PART_4  = $(shell expr $(HTML_RM_LEN) \* 4 / 10)
HTML_RM_LEN_PART_5  = $(shell expr $(HTML_RM_LEN) \* 5 / 10)
HTML_RM_LEN_PART_6  = $(shell expr $(HTML_RM_LEN) \* 6 / 10)
HTML_RM_LEN_PART_7  = $(shell expr $(HTML_RM_LEN) \* 7 / 10)
HTML_RM_LEN_PART_8  = $(shell expr $(HTML_RM_LEN) \* 8 / 10)
HTML_RM_LEN_PART_9  = $(shell expr $(HTML_RM_LEN) \* 9 / 10)
HTML_RM_LEN_PART_10 = $(HTML_RM_LEN)

HTML_RM_PART_1  = $(wordlist $(shell expr $(HTML_RM_LEN_PART_0) + 1), $(HTML_RM_LEN_PART_1), $(HTML_RM))
HTML_RM_PART_2  = $(wordlist $(shell expr $(HTML_RM_LEN_PART_1) + 1), $(HTML_RM_LEN_PART_2), $(HTML_RM))
HTML_RM_PART_3  = $(wordlist $(shell expr $(HTML_RM_LEN_PART_2) + 1), $(HTML_RM_LEN_PART_3), $(HTML_RM))
HTML_RM_PART_4  = $(wordlist $(shell expr $(HTML_RM_LEN_PART_3) + 1), $(HTML_RM_LEN_PART_4), $(HTML_RM))
HTML_RM_PART_5  = $(wordlist $(shell expr $(HTML_RM_LEN_PART_4) + 1), $(HTML_RM_LEN_PART_5), $(HTML_RM))
HTML_RM_PART_6  = $(wordlist $(shell expr $(HTML_RM_LEN_PART_5) + 1), $(HTML_RM_LEN_PART_6), $(HTML_RM))
HTML_RM_PART_7  = $(wordlist $(shell expr $(HTML_RM_LEN_PART_6) + 1), $(HTML_RM_LEN_PART_7), $(HTML_RM))
HTML_RM_PART_8  = $(wordlist $(shell expr $(HTML_RM_LEN_PART_7) + 1), $(HTML_RM_LEN_PART_8), $(HTML_RM))
HTML_RM_PART_9  = $(wordlist $(shell expr $(HTML_RM_LEN_PART_8) + 1), $(HTML_RM_LEN_PART_9), $(HTML_RM))
HTML_RM_PART_10 = $(wordlist $(shell expr $(HTML_RM_LEN_PART_9) + 1), $(HTML_RM_LEN_PART_10), $(HTML_RM))

.PHONY: convert-html-rm-1
convert-html-rm-1: $(HTML_RM_PART_1)
.PHONY: convert-html-rm-2
convert-html-rm-2: $(HTML_RM_PART_2)
.PHONY: convert-html-rm-3
convert-html-rm-3: $(HTML_RM_PART_3)
.PHONY: convert-html-rm-4
convert-html-rm-4: $(HTML_RM_PART_4)
.PHONY: convert-html-rm-5
convert-html-rm-5: $(HTML_RM_PART_5)
.PHONY: convert-html-rm-6
convert-html-rm-6: $(HTML_RM_PART_6)
.PHONY: convert-html-rm-7
convert-html-rm-7: $(HTML_RM_PART_7)
.PHONY: convert-html-rm-8
convert-html-rm-8: $(HTML_RM_PART_8)
.PHONY: convert-html-rm-9
convert-html-rm-9: $(HTML_RM_PART_9)
.PHONY: convert-html-rm-10
convert-html-rm-10: $(HTML_RM_PART_10)

.PHONY: convert-html-rm
convert-html-rm: convert-html-rm-1 convert-html-rm-2 convert-html-rm-3 \
				 convert-html-rm-4 convert-html-rm-5 convert-html-rm-6 \
				 convert-html-rm-7 convert-html-rm-8 convert-html-rm-9 \
				 convert-html-rm-10

.PHONY: clean-html-rm-1
clean-html-rm-1:
	@rm -rf $(HTML_RM_PART_1)
.PHONY: clean-html-rm-2
clean-html-rm-2:
	@rm -rf $(HTML_RM_PART_2)
.PHONY: clean-html-rm-3
clean-html-rm-3:
	@rm -rf $(HTML_RM_PART_3)
.PHONY: clean-html-rm-4
clean-html-rm-4:
	@rm -rf $(HTML_RM_PART_4)
.PHONY: clean-html-rm-5
clean-html-rm-5:
	@rm -rf $(HTML_RM_PART_5)
.PHONY: clean-html-rm-6
clean-html-rm-6:
	@rm -rf $(HTML_RM_PART_6)
.PHONY: clean-html-rm-7
clean-html-rm-7:
	@rm -rf $(HTML_RM_PART_7)
.PHONY: clean-html-rm-8
clean-html-rm-8:
	@rm -rf $(HTML_RM_PART_8)
.PHONY: clean-html-rm-9
clean-html-rm-9:
	@rm -rf $(HTML_RM_PART_9)
.PHONY: clean-html-rm-10
clean-html-rm-10:
	@rm -rf $(HTML_RM_PART_10)

.PHONY: clean-html-rm
clean-html-rm: clean-html-rm-1 clean-html-rm-2 clean-html-rm-3 clean-html-rm-4 \
               clean-html-rm-5 clean-html-rm-6 clean-html-rm-7 clean-html-rm-8 \
               clean-html-rm-9 clean-html-rm-10


# ================================ Datasheets =================================
HTML_DS = $(call html_output, $(sort $(wildcard ext/cache/stmicro-pdf/DS*.pdf)))

HTML_DS_LEN = $(words $(HTML_DS))
HTML_DS_LEN_PART_0 = 0
HTML_DS_LEN_PART_1 = $(shell expr $(HTML_DS_LEN) \* 1 / 4)
HTML_DS_LEN_PART_2 = $(shell expr $(HTML_DS_LEN) \* 2 / 4)
HTML_DS_LEN_PART_3 = $(shell expr $(HTML_DS_LEN) \* 3 / 4)
HTML_DS_LEN_PART_4 = $(HTML_DS_LEN)

HTML_DS_PART_1 = $(wordlist $(shell expr $(HTML_DS_LEN_PART_0) + 1), $(HTML_DS_LEN_PART_1), $(HTML_DS))
HTML_DS_PART_2 = $(wordlist $(shell expr $(HTML_DS_LEN_PART_1) + 1), $(HTML_DS_LEN_PART_2), $(HTML_DS))
HTML_DS_PART_3 = $(wordlist $(shell expr $(HTML_DS_LEN_PART_2) + 1), $(HTML_DS_LEN_PART_3), $(HTML_DS))
HTML_DS_PART_4 = $(wordlist $(shell expr $(HTML_DS_LEN_PART_3) + 1), $(HTML_DS_LEN_PART_4), $(HTML_DS))

.PHONY: convert-html-ds-1
convert-html-ds-1: $(HTML_DS_PART_1)
.PHONY: convert-html-ds-2
convert-html-ds-2: $(HTML_DS_PART_2)
.PHONY: convert-html-ds-3
convert-html-ds-3: $(HTML_DS_PART_3)
.PHONY: convert-html-ds-4
convert-html-ds-4: $(HTML_DS_PART_4)
.PHONY: convert-html-ds
convert-html-ds: convert-html-ds-1 convert-html-ds-2 convert-html-ds-3 convert-html-ds-4

.PHONY: clean-html-ds-1
clean-html-ds-1:
	@rm -rf $(HTML_DS_PART_1)
.PHONY: clean-html-ds-2
clean-html-ds-2:
	@rm -rf $(HTML_DS_PART_2)
.PHONY: clean-html-ds-3
clean-html-ds-3:
	@rm -rf $(HTML_DS_PART_3)
.PHONY: clean-html-ds-4
clean-html-ds-4:
	@rm -rf $(HTML_DS_PART_4)

.PHONY: clean-html-ds
clean-html-ds: clean-html-ds-1 clean-html-ds-2 clean-html-ds-3 clean-html-ds-4


# =============================== Errata Sheets ===============================
HTML_ES = $(call html_output, $(sort $(wildcard ext/cache/stmicro-pdf/ES*.pdf)))

.PHONY: convert-html-es
convert-html-es: $(HTML_ES)

.PHONY: clean-html-es
clean-html-es:
	@rm -rf $(HTML_ES)


# =============================== User Manuals ================================
HTML_UM = $(call html_output, $(sort $(wildcard ext/cache/stmicro-pdf/UM*.pdf)))

HTML_UM_LEN = $(words $(HTML_UM))
HTML_UM_LEN_PART_0 = 0
HTML_UM_LEN_PART_1 = $(shell expr $(HTML_UM_LEN) \* 1 / 4)
HTML_UM_LEN_PART_2 = $(shell expr $(HTML_UM_LEN) \* 2 / 4)
HTML_UM_LEN_PART_3 = $(shell expr $(HTML_UM_LEN) \* 3 / 4)
HTML_UM_LEN_PART_4 = $(HTML_UM_LEN)

HTML_UM_PART_1 = $(wordlist $(shell expr $(HTML_UM_LEN_PART_0) + 1), $(HTML_UM_LEN_PART_1), $(HTML_UM))
HTML_UM_PART_2 = $(wordlist $(shell expr $(HTML_UM_LEN_PART_1) + 1), $(HTML_UM_LEN_PART_2), $(HTML_UM))
HTML_UM_PART_3 = $(wordlist $(shell expr $(HTML_UM_LEN_PART_2) + 1), $(HTML_UM_LEN_PART_3), $(HTML_UM))
HTML_UM_PART_4 = $(wordlist $(shell expr $(HTML_UM_LEN_PART_3) + 1), $(HTML_UM_LEN_PART_4), $(HTML_UM))

.PHONY: convert-html-um-1
convert-html-um-1: $(HTML_UM_PART_1)
.PHONY: convert-html-um-2
convert-html-um-2: $(HTML_UM_PART_2)
.PHONY: convert-html-um-3
convert-html-um-3: $(HTML_UM_PART_3)
.PHONY: convert-html-um-4
convert-html-um-4: $(HTML_UM_PART_4)
.PHONY: convert-html-um
convert-html-um: convert-html-um-1 convert-html-um-2 convert-html-um-3 convert-html-um-4

.PHONY: clean-html-um-1
clean-html-um-1:
	@rm -rf $(HTML_UM_PART_1)
.PHONY: clean-html-um-2
clean-html-um-2:
	@rm -rf $(HTML_UM_PART_2)
.PHONY: clean-html-um-3
clean-html-um-3:
	@rm -rf $(HTML_UM_PART_3)
.PHONY: clean-html-um-4
clean-html-um-4:
	@rm -rf $(HTML_UM_PART_4)

.PHONY: clean-html-um
clean-html-um: clean-html-um-1 clean-html-um-2 clean-html-um-3 clean-html-um-4

# ==================================== All ====================================

.PHONY: clean-html
clean-html:
	@rm -rf $(wildcard ext/cache/stmicro-html/*-v*)

.PHONY: convert-html
convert-html: convert-html-ds convert-html-rm



# ========================== Converting HTML to OWL ===========================
owl_output = $(patsubst ext/cache/stmicro-html/%, ext/cache/stmicro-owl/%.owl, $1)

ext/cache/stmicro-owl/%.owl: ext/cache/stmicro-html/% log/stmicro/owl/
	@echo "Converting" $< "->" $@ "+" $(patsubst ext/cache/stmicro-owl/%.owl, log/stmicro/owl/%.txt, $@)
	@-python3 tools/scripts/html2owl.py --document $< > \
			$(patsubst ext/cache/stmicro-owl/%.owl, log/stmicro/owl/%.txt, $@) 2>&1


.PHONY: convert-html-owl
convert-html-owl:
	@echo "Converting all HTML Files to OWL Graphs."
	@-python3 tools/scripts/html2owl.py --all

.PHONY: clean-owl
clean-owl:
	@rm -f $(wildcard ext/cache/stmicro-owl/*.owl)


# ========================== Converting HTML to SVD ===========================
.PHONY: convert-html-svd-%
convert-html-svd-%: log/stmicro/svd/
	@-python3 tools/scripts/html2svd.py $(patsubst convert-html-svd-%, %, $@) > \
			$(patsubst convert-html-svd-%, log/stmicro/svd/html_%.txt, $@) 2>&1

.PHONY: convert-html-svd
convert-html-svd:
	@echo "Converting all HTML Files to SVD."
	@-python3 tools/scripts/html2svd.py --all

.PHONY: clean-html-svd
clean-html-svd:
	@rm -f $(wildcard ext/cache/stmicro-svd/rm_*.svd)


# ========================= Converting Header to SVD ==========================
.PHONY: convert-header-svd-%
convert-header-svd-%: log/stmicro/svd/
	@-python3 tools/scripts/header2svd.py $(patsubst convert-header-svd-%, %, $@) > \
			$(patsubst convert-header-svd-%, log/stmicro/svd/header_%.txt, $@) 2>&1

.PHONY: convert-header-svd
convert-header-svd:
	@-python3 tools/scripts/header2svd.py \
		--all stm32f0 --all stm32f1 --all stm32f2 \
		--all stm32f3 --all stm32f4 --all stm32f7 \
		--all stm32g0 --all stm32g4 --all stm32h7 \
		--all stm32l0 --all stm32l1 --all stm32l4
	# We are ignoring L5 U5 WB WL due to ARMv8-M S/NS aliasing and issues in headers


.PHONY: clean-svd
clean-svd:
	@rm -f $(wildcard ext/cache/stmicro-svd/*.svd)


# ========================= Evaluation Script ==========================


.PHONY: evaluation-did
evaluation-did:
	@echo "Running evaluation for device identifiers"
	@-python3 tools/eval/compare_identifiers.py > tools/eval/output_eval_identifiers.txt


.PHONY: evaluation-ivt
evaluation-ivt:
	@echo "Running evaluation for interrupt vector tables"
	@-python3 tools/eval/compare_interrupts.py > tools/eval/output_compare_interrupts.txt
	@-python3 tools/eval/compare_interrupts.py --eval > tools/eval/output_eval_interrupts.txt

.PHONY: evaluation-pap
evaluation-pap:
	@echo "Running evaluation for package and pinout"
	@-python3 tools/eval/compare_packages.py > tools/eval/output_compare_packages.txt
	@-python3 tools/eval/compare_packages.py --eval > tools/eval/output_eval_packages.txt


.PHONY: evaluation-pf
evaluation-pf:
	@echo "Running evaluation for pin functions"
	@-python3 tools/eval/compare_signals.py > tools/eval/output_compare_signals.txt
	@-python3 tools/eval/compare_signals.py --eval > tools/eval/output_eval_signals.txt
	@-python3 tools/eval/compare_signals.py --charts


.PHONY: evaluation-rd
evaluation-rd:
	@echo "Running evaluation for register descriptions"
	@-python3 tools/eval/compare_svds.py --compare > tools/eval/output_compare_svds.txt
	@-python3 tools/eval/compare_svds.py --eval > tools/eval/output_eval_svds.txt
	@-python3 tools/eval/compare_svds.py --charts


.PHONY: evaluation-all
evaluation-all: evaluation-did evaluation-ivt evaluation-pap evaluation-pf evaluation-rd
	@echo "Running all evaluation scripts."
