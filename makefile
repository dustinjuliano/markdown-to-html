.PHONY: test
test:
	python3 -m unittest discover -s test

serve:
	python3 -m http.server 8000 --directory /Users/theta/dev/markdown-to-html/test/mock_output
