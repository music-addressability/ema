# coding=UTF-8
from flask import jsonify
from flask.ext.restful import reqparse, abort, Api, Resource
from omas import omas

from pymei import XmlImport
from musdocinfo import MusDocInfo

from urlparse import urlparse
import requests

def read_MEI(MEI_id):
    """Get MEI file from its identifier, which can be ark, URN, filename, 
    or other identifier. Abort if unreachable.
    """

    # Parse the id parameter as URL
    # If it has a URL scheme, try to get the content,
    # otherwise try to get it as a file.
    url = urlparse(MEI_id)
    print url
    if url.scheme == "http" or url.scheme == "https":
        try:
            mei_as_text = requests.get(MEI_id, timeout=15).content
        except Exception, ex:
            abort(404)
    else:
        try:
            mei_as_text = file(url.path, 'r').read()
        except Exception, ex:
            abort(404)        
    return XmlImport.documentFromText(mei_as_text)

class Information(Resource):
    """Return information about an MEI file. """
    def get(self, MEI_id):      
        meiDoc = read_MEI(MEI_id)
        return jsonify(MusDocInfo(meiDoc).get())

class Test(Resource):
    def get(self, fun):
        return fun

# Instantiate Api handler and add routes
api = Api(omas)
api.add_resource(Information, '/<path:MEI_id>/info.json')
api.add_resource(Test, '/test/<string:fun>')