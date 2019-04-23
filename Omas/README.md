# Omas
## Open MEI Addressability Service

This web service implements the Music Addressability API.

## Run

The easiest way to run your own instance of Omas is with Docker. For example
this will start up an instance listening on http://0.0.0.0:5000

    docker run -p 0.0.0.0:5000:5000 umdmith/omas

## Build

Most requirements for Omas can be installed with pip:

```pip install -r requirements.txt```

The pymei library, however, needs to be installed manually. Clone the [libmei](https://github.com/DDMAL/libmei)
project and follow [these instructions](https://github.com/DDMAL/libmei/wiki/Installing-the-Python-bindings)
to install the Python bindings.

## Run the test server

Omas comes with a test server provided by Flask. To run it on port 5000 type:

```python api.py```
