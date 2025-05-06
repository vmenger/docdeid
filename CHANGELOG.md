# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## 1.0.1 (2025-05-06)

### Changed
* updated dependencies

## 1.0.0 (2023-12-20)

### Added 
* some internal speedups for `SingleTokenLooupAnnotator`, `MultiTokenLookupAnnotator` and `LookupTrie`
* caching for sorting annotations, which helps with speed
* the `pre_match_words` attribute for `RegexpAnnotator`
* the option to provide a `LookupTrie` to a `MultiTokenAnnotator` directly
* a method for getting all words or, for looking up tokens with specific text values in a `TokenList`, with options for `matching_pipeline`
* automated build/publish on merge to main

### Changed
* sorting `Annotation` and `AnnotationSet` now requires sort key to be provided as a `tuple`, and callbacks as a `frozendict`
* renamed `docdeid.tokenize` to `docdeid.tokenizer`
* renamed `docdeid.process.doc` to `docdeid.process.doc_processor`
* renamed `docdeid.process.annotation_set` to `docdeid.process.annotation_processor`
* `Annotation` and `Token` now only include `int`/`str` fields when serializing
* formatting and linting settings
* moved the logic for linking tokens to `TokenList` rather than `Tokenizer`
* use `casefold()` instead of `lower()` for lowercasing

### Fixed
* a bug with overlapping annotations in `MultiTokenLookupAnnotator`

### Removed
* automated coverage reporting

## 0.1.10 (2023-11-28) 

### Added
* `RegexpAannotator` accepts regexp strings in addition to compiled regexp patterns

### Changed
* consisent use of `args` and `kwargs` in `Annotator` class tree
* `RegexpAnnotator` now offers function to validate matches, implementable by subclassing

## 0.1.9 (2023-10-20)

### Changed
* made the `priority` attribute of an `Annotation` non-Optional
* multi token lookup now sets the `start_token` and `end_token` fields of an `Annotation`

### Fixed
* a bug with determnistic sort, when `Optional` fields were set


## 0.1.8 (2023-08-01)

### Added
* an additional `priority` attribute for `Annotation`, giving an extra option for sorting

## 0.1.7 (2023-07-26)

### Changed
* upgraded dependencies

## 0.1.6 (2023-03-28)

### Changed
* upgraded dependencies, including a `markdown-it-py` which had a vulnerability

## 0.1.5 (2023-02-15)

### Changed
* upgraded dependencies, including `certifi` which had a vulnerability

## 0.1.4 (2022-11-29)

### Changed
* renamed `processors_enabled` and `processors_disabled` to `enabled` and `disabled`, respectively

## 0.1.3 (2022-11-28)

### Added
* Include `py.typed` in packaging

## 0.1.2 (2022-11-28)

### Added
* a `py.typed` file, indicating PEP 561 compliance

### Changed
* minor type hint updates
* minor doc updates

## 0.1.1 (2022-11-18)

### Added
* Support for disabling specific processors with the `processors_disabled` keyword. 

## 0.1.0 (2022-11-18)

### Added
* Initial version