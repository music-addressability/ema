# csv2np: CSV to Nanopublication

This Python 3 script converts a csv export of the observation database from 
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