# Music Addressability API

## Status of this Document

* Version: 0.1
* Status: Draft
* Editor: Raffaele Viglianti, University of Maryland
* License: CC-BY 2014

## Description

This API describes a web service that returns a selection from a music notation document. The web service responds to HTTP(S) requests via two URI patterns. An addressing URI can be constructed to indicate to the web service which staff, beat, measure, and level of completeness should be returned. An information URI can be constructed to return metadata about a music notation document that can be used to inform the construction of the selection URI.

## Address a portion of a music notation document

```
GET /{identifier}/{measures}/{staves}/{beats}/{completeness}
```

### Parameters

Name       | Type   | Description
-----------|--------|------------
identifier | string | **Required**. The identifier of the requested music notation document. This may be an ark, URN, filename, or other identifier. Special characters must be URI encoded.
measures | string | **Required**. Range of measures by their index. Must be contiguous.
staves | string | **Required**. Selection of staves. Does not have to be contiguous.
beats | string | **Required**. Selection of beats within measure range.
completeness | string | **Optional**. Specifies how complete the returned selection should be via a closed set of options.

#### Measures

The `measures` parameter expresses either the index of one measure or a range of indexes of contiguous measures. For example `1` indicates the first measure in the document; `20-25` indicates five measures, starting from the twentieth and ending at the twenty-fifth. 

The keywords `start` and `end` can be used to indicate the first and last measure. For example `10-end` selects all the measures from the tenth to the last measure in the document.

#### Staves

The `staves` parameter can be expressed either as a range, or as a comma-separated list of stave indexes. For example `1-2` indicates the first two staves; `1,4` indicates the first and fourth stave.

The keywords `start` and `end` can be used to indicate the first and last staff. For example `start-end` selects all the staves.

Staves can also be addressed via their label by introducing the prefix `lbs:`. For example, given a choral with four staves labelled Soprano, Alto, Tenor, and Bass, the following string selects the first two staves:
`lbs:Soprano,Alto`.

#### Beats

The `beats` parameter expresses a ranges of beats. This must be a range, even when only one beat is selected. The first and second parts of the range are in the context, respectively, of the first and and last measures expressed in the `measures` parameter. For example, given a `measures` parameter of `1-2` an a `beats` parameter of `1-1`, the selection goes from the first beat in measure 1 to the first beat in measure 2. 

When only one measure is expressed, it constitutes both the first and last measure of the selection. For example, given a `measures` parameter of `2` an a `beats` parameter of `1-4`, the selection goes from the first to the fourth beat in measure 2.

The keywords `start` and `end` can be used to indicate the first and last beat in a measure. For example, given a `measures` parameter of `2` an a `beats` parameter of `start-end`, the selection goes from the first to the last beat in measure 2.

#### Completeness

The `completeness` parameter specifies how complete the returned selection should be. By default, the selection returned by the web service must be valid against the original music document format (e.g. a valid MEI file). Some of the `completeness` values are used to override this behaviour. The table below lists the values accepted. 

Name  | Description
------|-------------
raw   | The web service only returns the music notation selected, without requiring validation.
signature | The web service returns a full signature for each staff. This already happens when the returned selection is valid, but it does not require to include further context to be valid if used together with `raw`.
nospace | The web service must not fill unselected beats from the beginning of the measure with non-notational beats, such as space or invisible rests.
cut | The web service must cut the duration of music notation elements beginning within range but ending outside of the range.

Multiple values can be listed separated by commas. For example `raw,cut`.

### Response

The web service must return a portion of a music notation document corresponding to the selection addressed via the URI. By default, the web service must follow these rules:

**The selection returned must be valid against the original music document format (e.g. a valid MEI file)**

This often means that a time and key signature must be provided. Since the selection may address any part of the document, the provided signature must reflect the current context, not the one at the beginning of the piece.

**Partial selections in measures should be filled**

When a measure is only partially selected, the rest of the measure should be filled with non-notational beats. Some music representations may have a dedicated class, for example MEI may use `<mei:space>`; others may use invisible rests as an alternative. 

While space before the selection must be filled, space following the selection may be left unexpressed if the music document format allows it. For example, give a document with a 4/4 time signature and the following selection: `file/1/1/2-3/`, the space left by beat 1 must be filled, but the space left by beat 4 does not have to be filled unless that is required for validity.

This behavior can be overridden by specifying `nospace` as a `completeness` value.

**Partially selected music notation should be returned in full**

When music notation elements begin within the range of a selection but end outside of the range, they must be returned with their full duration. For example, give a document with a 4/4 time signature and the following selection: `file/1/1/2-3/`, where a half note sits at the third beat, the note should be returned in full (that is as a half note, not as a quarter note).

This behavior can be overridden by specifying `cut` as a `completeness` value. In this case, the half note in the example must be returned as a quarter note.

#### Example response

To be completed.

```
Status: 200 OK 
Content-Type: application/xml
```
```xml
<mei/>
```
&nbsp;

```
Status: 500 Internal Error 
Content-Type: application/json
```
```
{"message" : "Error in processing selection. Possible causes..."}
```

&nbsp;

```
Status: 501 Not implemented
Content-Type: application/json
```
```
{"message" : "Completeness option 'nospace' not implemented."}
```

## Request information on music notation document

```
GET /{identifier}/info.json 
```

### Parameters

Name       | Type   | Description
-----------|--------|------------
identifier | string | **Required**. The identifier of the requested music notation document. This may be an ark, URN, filename, or other identifier. Special characters must be URI encoded.

### Response

#### Fields

Name | Type | Description
-----|------|------------
measures | integer | The number of all measures in the files. Repeated measures must not be counted.
measure_labels | array of strings | an array of measure labels to facilitate human readable selection. For example there can be two measures with label "1", but with different indexes. The array index of each label corresponds to the absolute measure number. 
staves | object | This object contains all changes in staves and the measure at which the change happens. The measure number is the key and value is an array of staff labels. For example `{"1":["Soprano", "Alto", "Tenor", "Bass"]}` indicates that there are 4 staves at measure 1, and their labels. The absence of other items indicates that there is no change of stave numbers throughout the piece.
beats | object | This object contains all changes in number of beats and the measure at which the change happens. The measure number is the key and the number of beats is the value. For example `{"1":4}` indicates that there are 4 beats at measure 1. The absence of other items indicates that there is no change of beat numbers throughout the piece.
operations | array of strings | List of supported operations corresponding to the parameter `completeness` of the selection URI.

#### Example response

```
Status: 200 OK 
Content-Type: application/json
```
```json
{ 
  "measures": 4, 
  "measure_labels": ["1","2","3","4"],
  "staves": {"1" : ["Soprano", "Alto", "Tenor", "Bass"]},
  "beats" : {"1" : 4},
  "completeness" : ["raw", "signature", "nospace", "cut"]
}
```
