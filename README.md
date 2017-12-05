# tb_explorer

Minimalist webapp to visualize your tracebacks. You can :
- upload your tracebacks (using joblib.dump) to it
- view the list of uploaded tracebacks
- explore local variables in a python shell

## Installation

```
$ pip install tb-explorer
```

## Usage

```
$ tb-explorer -h
Traceback explorer

Usage:
  app.py [--storage STORAGE] [--port PORT]
  app.py -h | --help

Optional arguments:
  -h, --help         Show this help message and exit
  --port PORT        TCP port number [default: 5000]
  --storage STORAGE  Path of the data storing folder [default: ./store]
```

## Screenshots

Screenshot of the python shell page :

![https://lut.im/IVGwY2017U/GDOI1dh7HBbweP26.png](https://lut.im/IVGwY2017U/GDOI1dh7HBbweP26.png)
