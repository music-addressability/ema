#!/usr/bin/env python
# coding=UTF-8

import csv
import os
import os.path
import urllib.parse
import argparse
import logging
from uuid import uuid4
from datetime import datetime, timedelta
from rdflib import ConjunctiveGraph, Namespace, URIRef, Literal
from rdflib.plugin import register, Serializer
from rdflib.namespace import RDF, RDFS, FOAF, XSD
from trustyuri.rdf import RdfTransformer

# Tell rdflib verbose logger to be quiet unless stricly necessary.
logging.getLogger("rdflib").setLevel(logging.ERROR)


parser = argparse.ArgumentParser(description='Convert a digitalduchemin.org \
observation CSV export to a nanopublication graph.')
parser.add_argument('csv_path', metavar='CSV', type=str, nargs='?',
                    help='path to the CSV file')
parser.add_argument('out_dir', metavar='output', type=str, nargs='?',
                    help='path to an output directory')
parser.add_argument('--jsonld', '-j', dest='format', action='store_const',
                    const="jsonld",
                    help='serialize as JSON-LD')
parser.add_argument('--nquads', '-n', dest='format', action='store_const',
                    const="nquads",
                    help='serialize as N-Quads')
parser.add_argument('--trix', '-t', dest='format', action='store_const',
                    const="trix",
                    help='serialize as TriX (default)')

args = parser.parse_args()

csv_path = args.csv_path
out_dir = args.out_dir
os.makedirs(out_dir, exist_ok=True)
csv_headers = []

DDC = Namespace('http://digitalduchemin.org/')
NP = Namespace('http://www.nanopub.org/nschema#')
PROV = Namespace('http://www.w3.org/ns/prov#')
OA = Namespace("http://www.w3.org/ns/oa#")
DCTYPES = Namespace("http://purl.org/dc/dcmitype/")
CNT = Namespace("http://www.w3.org/2011/content#")

CONTEXT = {
    "ddc": DDC,
    "np": NP,
    "prov": PROV,
    "oa": OA,
    "dctypes": DCTYPES,
    "foaf": FOAF,
    "cnt": CNT
}


class Nanopub(object):
    def __init__(self, data, given_id=None):
        """ Create a nanopublication graph """
        self.data = data

        if not given_id:
            given_id = str(uuid4())

        np = DDC.term("np" + given_id) 
        np_ns = Namespace(np)

        g = self.g = ConjunctiveGraph('default', URIRef(np_ns.head))

        assertion = self.assertion = URIRef(np_ns.assertion)
        provenance = self.provenance = URIRef(np_ns.provenance)
        pubinfo = self.pubInfo = URIRef(np_ns.pubinfo)

        # Pubinfo
        ema = "Enhanching Music Notation Addressability Project"
        g.add((np, PROV.wasAttributedTo, Literal(ema), pubinfo))

        # Provenance
        date = data[csv_headers.index("timestamp")]
        try:
            creation_date = datetime.strptime(date, "%d/%m/%Y %H:%M:%S")
        except ValueError:
            creation_date = datetime.strptime(date, "%b %d, %Y %I:%M %p")
            creation_date = creation_date + timedelta(seconds=0)

        creation_date = creation_date.strftime('%Y-%m-%dT%H:%M:%S-05:00')
        timestamp = Literal(creation_date, datatype=XSD.dateTime)
        g.add((assertion, PROV.generatedAtTime, timestamp, provenance))

        analyst = Literal(data[csv_headers.index("analyst")])
        g.add((assertion, PROV.wasAttributedTo, analyst, provenance))

        # Assertion (OA)
        observation = URIRef(np_ns.observation)
        g.add((observation, RDF.type, OA.Annotation, assertion))
        g.add((observation, OA.annotatedBy, analyst, assertion))

        # OA tags for analytical statements
        columns = [
            csv_headers.index("cadence_final_tone"),
            csv_headers.index("cadence_kind"),
            csv_headers.index("cadence_alter"),
            csv_headers.index("cadence_role_cantz"),
            csv_headers.index("cadence_role_tenz"),
            csv_headers.index("voices_53_lo"),
            csv_headers.index("voices_53_up"),
            csv_headers.index("voices_p3_lo"),
            csv_headers.index("voices_p3_up"),
            csv_headers.index("voices_p6_lo"),
            csv_headers.index("voices_p6_up"),
            csv_headers.index("other_formulas"),
            csv_headers.index("other_pres_type"),
            csv_headers.index("voice_role_up1_nim"),
            csv_headers.index("voice_role_lo1_nim"),
            csv_headers.index("voice_role_up2_nim"),
            csv_headers.index("voice_role_lo2_nim"),
            csv_headers.index("voice_role_dux1"),
            csv_headers.index("voice_role_com1"),
            csv_headers.index("voice_role_dux2"),
            csv_headers.index("voice_role_com2"),
            csv_headers.index("voice_role_above"),
            csv_headers.index("voice_role_below"),
            csv_headers.index("voice_role_fifth"),
            csv_headers.index("voice_role_fourth"),
            csv_headers.index("voice_role_un_oct"),
            csv_headers.index("other_contrapuntal"),
            csv_headers.index("text_treatment"),
            csv_headers.index("repeat_exact_varied"),
            csv_headers.index("repeat_kind"),
            csv_headers.index("earlier_phrase"),
            ]

        forbidden_values = ["none", "nocadence", ""]

        for l in columns:
            value = data[l].strip()
            if value.lower() not in forbidden_values:
                label = csv_headers[l].strip()
                uri = np_ns+label
                self.addAssertionTag(label, value, observation, uri)

        # OA body for free text comment
        comment = data[csv_headers.index("comment")].strip()
        if comment.lower() not in forbidden_values:
            body = URIRef(np_ns.comment)

            g.add((observation, OA.motivatedBy, OA.commenting, assertion))

            g.add((body, RDF.type, DCTYPES.Text, assertion))
            g.add((body, RDF.type, CNT.ContentAsText, assertion))
            g.add((body, CNT.chars, Literal(comment), assertion))

            g.add((observation, OA.hasBody, body, assertion))

        # OA target
        target = URIRef(self.buildEMAurl())
        g.add((observation, OA.hasTarget, target, assertion))

        # NP main graph

        g.add((np, RDF.type, NP.Nanopublication))
        g.add((np, NP.hasAssertion, assertion))
        g.add((np, NP.hasProvenance, provenance))
        g.add((np, NP.hasPublicationInfo, pubinfo))

        self.g = RdfTransformer.transform(g, np)

    def addAssertionTag(self, label, value, observation, uri):
        tag = URIRef(uri)

        self.g.add((observation, OA.motivatedBy, OA.tagging, self.assertion))
        self.g.add((observation, OA.motivatedBy, OA.identifying,
                    self.assertion))

        self.g.add((tag, RDF.type, OA.Tag, self.assertion))
        self.g.add((tag, RDFS.label, Literal(label), self.assertion))
        self.g.add((tag, RDF.value, Literal(value), self.assertion))
        self.g.add((observation, OA.motivatedBy, OA.identifying,
                    self.assertion))

        self.g.add((observation, OA.hasBody, tag, self.assertion))

    def buildEMAurl(self):
        d = self.data
        start_m = d[csv_headers.index("start_measure")]
        final_m = d[csv_headers.index("stop_measure")]
        measures = "{0}-{1}".format(start_m, final_m)
        staves = []

        staff_data = [
            csv_headers.index("cadence_role_cantz"),
            csv_headers.index("cadence_role_tenz"),
            csv_headers.index("voices_53_lo"),
            csv_headers.index("voices_53_up"),
            csv_headers.index("voices_p3_lo"),
            csv_headers.index("voices_p3_up"),
            csv_headers.index("voices_p6_lo"),
            csv_headers.index("voices_p6_up"),
            csv_headers.index("voice_role_up1_nim"),
            csv_headers.index("voice_role_lo1_nim"),
            csv_headers.index("voice_role_up2_nim"),
            csv_headers.index("voice_role_lo2_nim"),
            csv_headers.index("voice_role_dux1"),
            csv_headers.index("voice_role_com1"),
            csv_headers.index("voice_role_dux2"),
            csv_headers.index("voice_role_com2"),
            csv_headers.index("voice_role_above"),
            csv_headers.index("voice_role_below"),
            csv_headers.index("voice_role_fifth"),
            csv_headers.index("voice_role_fourth"),
            csv_headers.index("voice_role_un_oct")]

        for s in staff_data:
            r_id = self.roleToIndex(d[s])
            if r_id and r_id not in staves:
                staves.append(r_id)

        # remove duplicate values
        staves = list(set(staves))
        staves_str = ",".join(str(x) for x in staves)

        if not staves_str:
            staves_str = "all"

        dc_id = d[csv_headers.index("composition_number")][:6].upper()
        dcfile = "http://digitalduchemin.org/mei/{0}.xml".format(dc_id)
        dcfile = urllib.parse.quote(dcfile, "")

        return "http://ema.mith.org/{0}/{1}/{2}/@all".format(dcfile,
                                                             measures,
                                                             staves_str)

    def roleToIndex(self, r):
        r = r.lower()
        roles = [None, "s", "ct", "t", "b"]
        if r in roles:
            return roles.index(r)
        else:
            return None

    def jsonld(self, indent=2):
        return self.g.serialize(format='json-ld',
                                indent=indent, context=CONTEXT)

    def nquads(self):
        return self.g.serialize(format='nquads')

    def trix(self, indent=2):
        return self.g.serialize(format='trix')

def write_np(s, npid, formt):
    filename = filename = "np{0}.{1}".format(npid, formt)
    with open(os.path.join(out_dir, filename), 'wb') as f:
        f.write(s)

with open(csv_path) as csvfile:
    creader = csv.reader(csvfile)
    for i, analysis in enumerate(creader):
        if i == 0:
            csv_headers = analysis
        else:
            npid = analysis[csv_headers.index("id")]
            n = Nanopub(analysis, npid)
            if args.format == "trix":
                s = n.trix()
            if args.format == "nquads":
                s = n.trix()
            elif args.format == "jsonld":
                s = n.jsonld()
            else:
                s = n.trix()

            write_np(s, npid, args.format)

register('json-ld', Serializer, 'rdflib_jsonld.serializer', 'JsonLDSerializer')
