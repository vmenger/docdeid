# docdeid

[![tests](https://github.com/vmenger/docdeid/actions/workflows/test.yml/badge.svg?branch=main)](https://github.com/vmenger/docdeid/actions/workflows/test.yml)
[![coverage](https://coveralls.io/repos/github/vmenger/docdeid/badge.svg?branch=main)](https://coveralls.io/github/vmenger/docdeid?branch=main)
[![build](https://github.com/vmenger/docdeid/actions/workflows/build.yml/badge.svg?branch=main)](https://github.com/vmenger/docdeid/actions/workflows/build.yml)
[![Documentation Status](https://readthedocs.org/projects/docdeid/badge/?version=latest)](https://docdeid.readthedocs.io/en/latest/?badge=latest)
![pypy version](https://img.shields.io/pypi/v/docdeid)
![python versions](https://img.shields.io/pypi/pyversions/docdeid)
![license](https://img.shields.io/github/license/vmenger/docdeid)
[![black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

[Installation](#installation) - [Getting started](#getting-started) - [Features](#features) - [Documentation](#documentation) - [Development and contributiong](#development-and-contributing) - [Authors](#authors)  

<!-- start include in docs -->

Create your own document de-identifier using `docdeid`, a simple framework independent of language or domain.

> Note that `docdeid` is still on version 0.x.x, and breaking changes might occur. If you plan to do extensive work involving `docdeid`, feel free to get in touch to coordinate. 

## Installation

Grab the latest version from PyPi:

```bash
pip install docdeid
```

## Getting started

```python
from docdeid import DocDeid
from docdeid.tokenize import WordBoundaryTokenizer
from docdeid.process SingleTokenLookupAnnotator, RegexpAnnotator, SimpleRedactor

deidentifier = DocDeid()

deidentifier.tokenizers["default"] = WordBoundaryTokenizer()

deidentifier.processors.add_processor(
    "name_lookup",
    SingleTokenLookupAnnotator(lookup_values=["John", "Mary"], tag="name"),
)

deidentifier.processors.add_processor(
    "name_regexp",
    RegexpAnnotator(regexp_pattern=re.compile(r"[A-Z]\w+"), tag="name"),
)

deidentifier.processors.add_processor(
    "redactor", 
    SimpleRedactor()
)

text = "John loves Mary, but Mary loves William."
doc = deidentifier.deidentify(text)
```

Find the relevant info in the `Document` object:

```python
print(doc.annotations)

AnnotationSet({
    Annotation(text='John', start_char=0, end_char=4, tag='name', length=4),
    Annotation(text='Mary', start_char=11, end_char=15, tag='name', length=4),
    Annotation(text='Mary', start_char=21, end_char=25, tag='name', length=4), 
    Annotation(text='William', start_char=32, end_char=39, tag='name', length=7)
})
```

```python
print(doc.deidentified_text)

'[NAME-1] loves [NAME-2], but [NAME-2] loves [NAME-3].'
```

## Features

Additionally, `docdeid` features: 

- Ability to create your own `Annotator`, `AnnotationProcessor`, `Redactor` and `Tokenizer` components
- Some basic re-usable components included (e.g. regexp, token lookup, token patterns)
- Callable from one interface (`DocDeid.deidenitfy()`)
- String processing and filtering
- Fast lookup based on sets or tries
- Anything you add! PRs welcome.

For a more in-depth tutorial, see: [docs/tutorial](https://docdeid.readthedocs.io/en/latest/tutorial.html)

<!-- end include in docs -->

## Documentation

For full documentation and API, see: [https://docdeid.readthedocs.io/en/latest/](https://docdeid.readthedocs.io/en/latest/)

## Development and contributing

For setting up dev environment, see: [docs/environment](https://docdeid.readthedocs.io/en/latest/environment.html)

For contributing, see: [docs/contributing](https://docdeid.readthedocs.io/en/latest/contributing.html).

## Authors
Vincent Menger - *Author, maintainer*
