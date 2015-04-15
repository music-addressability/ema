# Omas
## Open MEI Addressability Service

This web service implements the Music Addressability API.

## Setup

Most requirements for Omas can be installed with pip:

```pip install -r requirements.txt```

The pymei library, however, needs to be installed manually. Clone the [libmei](https://github.com/DDMAL/libmei)
project and follow [these instructions](https://github.com/DDMAL/libmei/wiki/Installing-the-Python-bindings)
to install the Python bindings.

## Run the test server

Omas comes with a test server provided by Flask. To run it on port 5000 type:

```python api.py```
