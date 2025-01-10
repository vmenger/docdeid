format:
	python -m black .
	python -m isort .
	python -m docformatter .

lint:
	{ python -m flake8 .; fret=$$?; }; \
		{ python -m pylint docdeid/; pret=$$?; }; \
		{ python -m mypy docdeid/; mret=$$?; }; \
		echo "flake8: $$fret, pylint: $$pret, mypy: $$mret"; \
	  [ $$fret,$$pret,$$mret = "0,0,0" ]

build-docs:
	sphinx-apidoc --module-first --force --templatedir=docs/templates -o docs/source/api docdeid
	sphinx-build docs/source docs/_build/html -c docs/

clean:
	rm -rf .coverage
	rm -rf htmlcov
	rm -rf coverage.lcov
	rm -rf .pytest_cache
	rm -rf .mypy_cache
	rm -rf dist
	rm -rf docs/_build
	rm -rf docs/source/api

.PHONY: format lint clean
