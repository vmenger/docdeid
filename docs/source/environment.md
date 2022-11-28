# Developer environment

* This project uses poetry for package management. Install it with ```pip install poetry```
* Set up the environment is easy, just use ```poetry install```
* The makefile contains some useful commands when developing:
  * `make test` runs the tests (including coverage)
  * `make format` formats the package code
  * `make lint` runs the linters (check the output)
  * `make clean` removes build/test artifacts, etc
* And for docs:
  * `make build-docs` builds the docs
  * `make clean-docs` removes docs build

## Releasing
* Readthedocs has a webhook connected to pushes on the main branch. It will trigger and update automatically. 
* Create a [release on github](https://github.com/vmenger/docdeid/releases/new), create a tag with the right version, manually copy paste from the changelog
* Trigger the build pipeline manually to release to PyPi