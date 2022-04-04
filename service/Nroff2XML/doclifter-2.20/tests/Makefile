# Regression tests for doclifter
TESTDIRPARENT=/tmp
UTILBINDIR=..

TESTLOADS := $(shell ls *.man | sed '/.man/s///')

default:
	@./setpython python2
	@make -e --quiet regress
	@./setpython python3
	@make -e --quiet regress
	@./setpython python
	@echo "No output (other than testfile stem names) is good news."

rebuild:
	@for file in $(TESTLOADS); do \
	    echo "Remaking $${file}.chk"; \
	    $(UTILBINDIR)/doclifter <$${file}.man >$${file}.chk 2>&1; \
	done
regress:
	@for file in $(TESTLOADS); do \
	    echo $${file}; \
	    if $(UTILBINDIR)/doclifter <$${file}.man >$(TESTDIRPARENT)/regress$$; \
	    then diff -u $${file}.chk $(TESTDIRPARENT)/regress$$; \
	        if [ $$? -ne 0 ]; then echo "*** Output differs"; exit 1; fi \
	    else echo "*** Nonzero return status on $${file}!"; exit 1; fi \
	done
	@rm -f $(TESTDIRPARENT)/regress
