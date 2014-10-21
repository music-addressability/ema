# Music Addressability API

## Status of this Document

* Version: 0.1
* Editor: Raffaele Viglianti, University of Maryland
* Lincense: CC-BY 2014

## Description

This API describes a web service that returns a selection from a music notation document. The web service responds to HTTP(S) requests via two URI patterns. A selection URI can be constructed to indicate to the web service which staff, beat, measure, and lvel of completeness should be returned. An information URI can be constructed to return metadata about a music notation document that can be used to inform the construction of the selection URI.

## Request information on music notation document

```
GET /{identifier}/info.json 
```

### Parameters

Name       | Type   | Description
-----------|--------|------------
identifier | string | **Required**. The identifier of the requested music notation document. This may be an ark, URN, filename, or other identifier. Special characters must be URI encoded.

## Response

```
Status: 200 OK 
Content-Type: application/json
```
```json
{ 
  "sections" : 1,
  "measures": 37, 
  "measure_labels": ["1","2","3","4","5","6","7","8","9","10","11","12","13","14","15","16","17","18","19","20","21","22","23","24","25","26","27","28","29","30","31","32","33","34","35","36","37"],
  "staves": {
    1 : 4 // at measure 1 there are 4 staves
    // 10 : 3 add changes by their starting measure
  },
  "beats" : {
    1 : 4 // at measure 1 there are 4 beats
  },
  "total_beats" : 148
}
```
