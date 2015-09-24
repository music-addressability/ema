# CSV to Nanopublication

The Python 3 script `csv2np` converts a csv export of the observation database from 
[digitalduchemin.org](http://digitalduchemin.org) to a nanopublication datamodel. **It will only work with that export.**

Each observation is converted to a jsonld file containing a Nanopublication graph.

The assertion of the Nanopublication is expressed as an Open Annotation targeting a portion of
a music document. The target resource URI is expressed according to the 
[Enhancing Music Notation Addressability API](https://github.com/umd-mith/ema/blob/master/docs/api.md).

## Installation and Usage

Install requirements using pip

```
pip install -r requirements.txt
```

Then run the script by providing the input CSV file and the output directory for the jsonld files.

```
python csv2np.py PATH_TO_CSV PATH_TO_OUTPUT_DIR
```

The default output is Trig, but other foramats can be output as well. Run `python csv2np.py --help` for more info.

## POSTing Trig nanopubs to a Nanopublication server

The script `np2srv` is a simple program for POSTing the Trig output of `csv2np` to a Nanopublication server on the web.

```
python np2srv.py PATH_TO_OUTPUT_DIR URL_TO_SERVER
```