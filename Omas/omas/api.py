# coding=UTF-8
from flask import jsonify, send_from_directory
from flask.ext.restful import reqparse, abort, Api, Resource
from omas import omas

from pymei import XmlImport, XmlExport
from meiinfo import MusDocInfo
from meislicer import MeiSlicer

from urlparse import urlparse
from urllib import unquote
import requests

from werkzeug.routing import BaseConverter, ValidationError

class OneOrRangeConverter(BaseConverter):

    def __init__(self, url_map):
        super(OneOrRangeConverter, self).__init__(url_map)
        self.regex = '(?:(\d+|start)(-(\d+|end))?)'

    def to_python(self, value):        
        return value

    def to_url(self, value):
        return value

class OneOrMixedConverter(BaseConverter):

    def __init__(self, url_map):
        super(OneOrMixedConverter, self).__init__(url_map)
        self.regex = '(?:(\d+|start)([-,](\d+|end))*)'

    def to_python(self, value):        
        return value

    def to_url(self, value):
        return value

omas.url_map.converters['onex'] = OneOrMixedConverter
omas.url_map.converters['oner'] = OneOrRangeConverter

def read_MEI(MEI_id):
    """Get MEI file from its identifier, which can be ark, URN, filename, 
    or other identifier. Abort if unreachable.
    """

    # Parse the id parameter as URL
    # If it has a URL scheme, try to get the content,
    # otherwise try to get it as a file.
    url = urlparse(MEI_id)
    if url.scheme == "http" or url.scheme == "https":
        try:
            mei_as_text = requests.get(unquote(MEI_id), timeout=15).content
        except Exception, ex:
            abort(404)
    else:
        try:
            mei_as_text = file(url.path, 'r').read()
        except Exception, ex:
            abort(404)      
    # TODO capture exception here too. Possibly error 400 or better 415 or  and say not MEI file.
    return XmlImport.documentFromText(mei_as_text)

class Information(Resource):
    """Return information about an MEI file. """
    def get(self, MEI_id):      
        meiDoc = read_MEI(MEI_id)
        return jsonify(MusDocInfo(meiDoc).get())

class Address(Resource):
    """Parse an addressing URL and return portion of MEI"""
    def get(self, MEI_id, measures, staves, beats, completeness=None):
        meiDoc = read_MEI(MEI_id)
        XmlExport.meiDocumentToFile(MeiSlicer(meiDoc, measures, staves, beats, completeness).select(), "/tmp/mei.mei")

        return send_from_directory("/tmp", "mei.mei", as_attachment=True, mimetype="application/xml")


# Instantiate Api handler and add routes
api = Api(omas)
api.add_resource(Information, '/<path:MEI_id>/info.json')
api.add_resource(Address, '/<path:MEI_id>/<oner:measures>/<onex:staves>/<oner:beats>',
                 '/<path:MEI_id>/<oner:measures>/<onex:staves>/<oner:beats>/<completeness>')