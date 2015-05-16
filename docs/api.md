# Music Addressability API

## Status of this Document

* Version: 1.0.0
* Status: Draft
* Editor: Raffaele Viglianti, University of Maryland
* License: CC-BY 2015

## Description

This API describes a web service that returns a selection from a music notation document. The web service responds to HTTP(S) requests via two URI patterns. An addressing URI can be constructed to indicate to the web service which measures, staves, and beats should be returned, and at what level of completeness. An information URI can be constructed to return metadata about a music notation document that can be used to inform the construction of the selection URI.

## Address a portion of a music notation document

```
GET /{identifier}/{measureRanges}/{stavesToMeasures}/{beatsToMeasures}/{completeness}
```

### Parameters

Name       | Type   | Description
-----------|--------|------------
identifier | string | **Required**. The identifier of the requested music notation document. This may be an URL, ark, URN, filename, or other identifier. Special characters must be URI encoded.
measureRanges | string | **Required**. Comma separated ranges of measures by their index.
stavesToMeasure | string | **Required**. Staff ranges separated by `+` signs and mapped to measure ranges with commas. 
beatsToMeasure | string | **Required**. Beat ranges marked by `@` signs. Mapped to staff ranges by `+`, and mapped to measure ranges with commas.
completeness | string | **Optional**. Specifies how complete the returned selection should be via a closed set of options.

#### BNF grammar of parameters

This is a Backus-Naur Form reference grammar for the parameters. Each parameter is explained in more detail in the following sections.

```
start ::= "start"
startOrEnd ::= "start" | "end"
all ::= "all"
measure ::= integer
measureRanges ::= {measure | startOrEnd | all / ","} | {measure | start, "-", measure | end / ","}
staff ::= integer
staffRange ::= {staff | startOrEnd | all / "+"} | {staff | start, "-", staff | end / "+"}
stavesToMeasures ::= {staffRange / ","}
beat ::= float
beatRange ::= {"@", beat | startOrEnd | all / "+"} | {"@", beat | start, "-", beat | end / "+"}
beatstoMeasures ::= {beatRange / ","}
```
 
selectionParameters ::= measureRanges, "/", stavesToMeasures, "/", beatstoMeasures 

#### Measures

The `measureRanges` parameter expresses any combination of either the index of one measure or a range of indexes of contiguous measures. For example `1` indicates the first measure in the document; `20-25` indicates six measures, starting from the twentieth and ending at the twenty-fifth. 

The keywords `start` and `end` can be used to indicate the first and last measure. For example `10-end` selects all the measures from the tenth to the last measure in the document. The keyword `all` indicates all measures.

Each measure or range of measures is separated by a comma, for example: `1,3-5` selects measures 1, 3, 4, and 5.

#### Staves

The `stavesToMeasures` parameter expresses any combination of either the index of one staff or a range of indexes of contiguous measures. Each range is separated by a `+` sign. For example `1-2` indicates the first two staves; `1+4` indicates the first and fourth stave.

The keywords `start` and `end` can be used to indicate the first and last staff. For example `start-end` selects all the staves. The keyword `all` indicates all staves.

Different staves can be chosen for every selected measure. Commas are used to organize selected staves by measure. For example, given a `measureRanges` parameter of `1,3-4`, staves can be selected independently for each measure with commas: e.g. `1,2-3,1+3` selects the first staff for measure 1, staves 2 and 3 for measure 3 and staves 1 and 3 for measure 4.

#### Beats

The `beatstoMeasures` parameter expresses any combination of either one beat or a ranges of beats. Each beat range is prefixed by an `@` sign. Beat ranges are mapped to staves with a `+` sign and to measures with commas.

The keywords `start` and `end` can be used to indicate the first and last beat in a measure. For example, given a `measureRanges` parameter of `2` an a `beatstoMeasures` parameter of `@start-end`, the selection goes from the first to the last beat in measure 2. The keyword `all` indicates all beats in a measure.

Different beats can be chosen for every selected staff and selected measure. For example, given a `measureRanges` parameter of `1-2`, and a `stavesToMeasures` parameter of `1-2,1`, beats can be selected independently for each staff and measure: e.g. `@1-2+@1-2,@1` selects the first two beats in staves 1 and 2 in measure 1, and beat 1 in staff 1 in measure 2.

#### Completeness

The `completeness` parameter specifies how complete the returned selection should be. By default, the selection returned by the web service must be valid against the original music document format (e.g. a valid MEI file). Some of the `completeness` values are used to override this behavior. The table below lists the values accepted. 

Name  | Description
------|-------------
raw   | The web service only returns the music notation selected, without requiring validation.
signature | The web service returns a full signature for each staff. This already happens when the returned selection is valid, but it does not require to include further context to be valid if used together with `raw`.
nospace | The web service must not fill unselected beats from the beginning of the measure with non-notational beats, such as space or invisible rests.
cut | The web service must cut the duration of music notation elements beginning within a measure range but ending outside of the range (spanning events such as slurs may be kept intact in between non-contiguous *beat* ranges).

Multiple values can be listed separated by commas. For example `raw,cut`.

#### Complexity of expressions

The parameters described above are able to deal with complex selections and expressions can get long and complicated. Most selections, however, are likely to be simpler and contiguous. 

For example this is the expression for selecting the first three measures: `1-3/all/@all`

Notice how `stavesToMeasures` and `beatstoMeasures` are only expressed once: *selections that apply to all selected measures and all selected staves only need to be expressed once*.

Another example: `1-3/all,all,1+3/@all`. This expression selects all of the content for measures 1 and 2 and only the content of the first and third staves in measure 3.

The more particular the selection, the more specific the expression.

### Response

The web service must return a portion of a music notation document corresponding to the selection addressed via the URI. By default, the web service must follow these rules:

**The selection returned must be valid against the original music document format (e.g. a valid MEI file)**

This often means that a time and key signature must be provided. Since the selection may address any part of the document, the provided signature must reflect the current context, not the one at the beginning of the piece.

**Partial selections in measures should be filled**

When a measure is only partially selected, the rest of the measure should be filled with non-notational beats. Some music representations may have a dedicated class, for example MEI may use `<mei:space>`; others may use invisible rests as an alternative. 

While space before the selection must be filled, space following the selection may be left unexpressed if the music document format allows it. For example, give a document with a 4/4 time signature and the following selection: `file/1/1/@2-3/`, the space left by beat 1 must be filled, but the space left by beat 4 does not have to be filled unless that is required for validity.

This behavior can be overridden by specifying `nospace` as a `completeness` value.

**Partially selected music notation should be returned in full**

When music notation elements begin within the range of a selection but end outside of the range, they must be returned with their full duration. For example, give a document with a 4/4 time signature and the following selection: `file/1/1/@2-3/`, where a half note sits at the third beat, the note should be returned in full (that is as a half note, not as a quarter note).

This behavior can be overridden by specifying `cut` as a `completeness` value. In this case, the half note in the example must be returned as a quarter note.

#### Example response

```
Status: 200 OK 
Content-Type: // depending on format of origin, usually "application/xml"
```
```
// returned selection document
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
identifier | string | **Required**. The identifier of the requested music notation document. This may be an URL, ark, URN, filename, or other identifier. Special characters must be URI encoded.

### Response

#### Fields

Name | Type | Description
-----|------|------------
measures | integer | The number of all measures in the files. Repeated measures must not be counted.
measure_labels | array of strings | an array of measure labels to facilitate human readable selection. For example there can be two measures with label "1", but with different indexes. The array index of each label corresponds to the absolute measure number. 
staves | object | This object contains all changes in staves and the measure at which the change happens. The measure number is the key and value is an array of staff labels. For example `{"0":["Soprano", "Alto", "Tenor", "Bass"]}` indicates that there are 4 staves at measure 1, and their labels. The absence of other items indicates that there is no change of stave numbers throughout the piece.
beats | object | This object contains all changes in number of beats and the measure at which the change happens. The measure number is the key and the number of beats is the value. For example `{"0": {"count": 4, "unit": 4} }` indicates that there are 4 beats, each lasting a quarter (quaver) at measure 1. The absence of other items indicates that there is no change of beat numbers throughout the piece.
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
  "staves": {"0" : ["Soprano", "Alto", "Tenor", "Bass"] },
  "beats" : {"0" : {"count": 6, "unit": 8} }
  },
  "completeness" : ["raw", "signature", "nospace", "cut"]
}
```
