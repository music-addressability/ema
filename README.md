![EMA logo](http://mith.umd.edu/wp-content/uploads/2014/07/header_ema.png) 
# Enhancing Music Notation Addressability (EMA)

This is the GitHub repository for the NEH funded project Enhancing Music Notation Addressability (grant number: HD-51836-14). For more information on the project as a whole, read the [end-of-project white paper](https://securegrants.neh.gov/publicquery/Download.aspx?data=EbwGdSyLkD7zoB3W75cvd%2bXST%2bWypC%2blXFsHQXsXqfJI0drM3OQ%2b3faX2S%2ftHGB3jk8Em52HNbzrN1QYxpAied7tKmRpDL38HbpRGCl421aDODOzEOuNKCNN6eshRCiemwrjR%2fVlC%2bTRfuoCkm3v7w%3d%3d).

The repository collects a number of digital deliverables created during the life of the project.

## Music Addressability API

[Read the Music Addressability API specification here](https://github.com/umd-mith/ema/blob/master/docs/api.md).

This API specification was created to enable granular selections of portions of music notation regardless of the underlying music notation format. In other words, it defines a way of virtually circling, or addressing, machine-readable music notation.

## Open MEI Addressability Service (Omas)

This is a Python implementation of the Music Addressability API for the [Music Encoding Initiative](http://music-encoding.org/) format.

The code and more information are available in the directory [`/Omas`](https://github.com/umd-mith/ema/tree/master/Omas).

[Click here for a live demo of the tool](http://mith.us/ema/omas/).

## Nanopublications

The directory [`/nanopub`](https://github.com/umd-mith/ema/tree/master/nanopub) contains code that was written as part of the project evaluation. EMA partnered with the [*Du Chemin: Lost Voices*](http://digitalduchemin.org) project to convert their relational database of analyses into Linked Open Data objects conformant to the [Nanopublication standard](http://nanopub.org/). References to music notation were remodelled according to the Music Addressability API specification. The resulting data was stored in a public [Nanopublication database](http://digitalduchemin.org/notation/nanopub-server/).

The code contained in `/nanopub` is specific to the Du Chemin data model, though it may serve as a real-world example for other users, particularly the documents in [`/nanopub/examples`](https://github.com/umd-mith/ema/tree/master/nanopub/examples).
