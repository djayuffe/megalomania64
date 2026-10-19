.PHONY: all test preview package run clean
all:
	python3 tools/build.py
test:
	python3 tools/build.py --test
preview:
	python3 tools/build.py --preview
package:
	python3 tools/build.py --test --preview --package
run:
	sh tools/run_vice.sh
clean:
	rm -f dist/*.zip dist/*.sha256
