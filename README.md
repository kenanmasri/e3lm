<img src="https://i.ibb.co/gVczmTW/3LM.png" height="64" width="64" style="vertical-align: middle;"/> &nbsp;&nbsp; <span style="color: orange; font-size: 32px; vertical-align: middle;">3LM</span>

<img src="https://img.shields.io/github/license/kenanmasri/3lm" /> <img src="https://img.shields.io/github/repo-size/kenanmasri/3lm" /> <img src="https://img.shields.io/pypi/v/e3lm" /> 

Have fun while learning!

---

## So what is this exactly?

3LM is a structure language parsed in Python.

It is used for defining hierarchial objects, intended mainly to help write structured content fast and with ease.
Whether you are a scientist, a programmer or an educator, 3LM can be useful for you.

3LM is intended to be a language of use for an educational platform.

---

## Installation

> NOTE: Installation does not work right now.. Since the package is not published to PyPI.

### Installation from Github
```bash
$ pip install git+https://github.com/kenanmasri/3lm.git#egg=e3lm
```

### Installation through PyPI
Creating a virtual environment is very preferrable.

```bash
$ python -m venv venv
$ python -m pip install e3lm
```

## Configuration
```env
# Environment variables and their default values.

E3LM_TEMP_DIRECTORY="tmp"
```

## Usage

Basic example:

```bash
# Interpret example.3lm file.
$ e3lm example.3lm

# Interpret demo code1 and generate graphviz dot file and view graph image.
$ e3lm -d code1 -p dot view

# Benchmarking 20 times the demo code0 for 6 measurements.
$ e3lm -d code0 -b 6 20
```

More options:

```bash
$ e3lm --version
$ e3lm --help
```

---

## Additional resources

Refer to the [Wiki](https://github.com/kenanmasri/3lm/wiki) to learn the language.

---

## TODO:

 - [ ] Examination questions auto-extraction from 3lm files. (Could be a plugin.)
 - [ ] Rewrite included out-of-the-box example codes and error codes.
 - [ ] Add more tests.
 - [x] Benchmarking.
 - [x] Contrib plugins.
 - [ ] Make publish ready documentation.
 - [ ] Publish to PyPI.

More possibilities... See [e3lm.todo](https://github.com/e3lm/e3lm/blob/master/e3lm.todo)

---
