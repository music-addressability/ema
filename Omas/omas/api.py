# coding=UTF-8
from urllib import unquote

import requests
from werkzeug.routing import BaseConverter
from flask import jsonify, send_file, make_response
from flask.ext.restful import Api, Resource

from omas import omas
from omas import meiinfo
from omas import meislicer
from omas.exceptions import CannotReadMEIException
from omas.exceptions import BadApiRequest
from omas.exceptions import CannotWriteMEIException
from omas.exceptions import CannotAccessRemoteMEIException
from omas.exceptions import UnknownMEIReadException


# CONVERTERS
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


class MEIServiceResource(Resource):
    """ Common methods for MEI Service Requests """

    def get_external_mei(self, meiaddr):
        r = requests.get(unquote(meiaddr), timeout=15)
        # Exeunt stage left if something went wrong.
        if r.status_code != requests.codes.ok:
            if r.status_code == 404:
                raise CannotAccessRemoteMEIException("The MEI File could not be found")
            else:
                raise UnknownMEIReadException("An unknown error ocurred. Status code: {0}".format(r.status_code))

        return r.content


# RESOURCES
class Information(MEIServiceResource):
    """Return information about an MEI file. """
    def get(self, MEI_id):
        # if url.scheme == "http" or url.scheme == "https":

        # the requests library shouldn't normally raise an exception, should it? 
        # If it fails it should return a status code....
        try:
            mei_as_text = self.get_external_mei(MEI_id)
        except CannotAccessRemoteMEIException as ex:
            message, status = jsonify({"message": ex.message}), 400
            return make_response(message, status)
        except UnknownMEIReadException as ex:
            message, status = jsonify({"message": ex.message}), 500
            return make_response(message, status)

        try:
            parsed_mei = meiinfo.read_MEI(mei_as_text)
        except CannotReadMEIException as ex:
            # return a 500 server error with the exception message
            message, status = jsonify({"message": ex.message}), 500
            return make_response(message, status)

        # it's possible that this will raise some exceptions too, so break it out.
        try:
            mus_doc_info = meiinfo.MusDocInfo(parsed_mei).get()
        except BadApiRequest as ex:
            message, status = jsonify({"message": ex.message}), 500
            return make_response(message, status)

        return jsonify(mus_doc_info)


class Address(MEIServiceResource):
    """Parse an addressing URL and return portion of MEI"""
    def get(self, MEI_id, measures, staves, beats, completeness=None):
        mei_as_text = self.get_external_mei(MEI_id)

        try:
            parsed_mei = meiinfo.read_MEI(mei_as_text)
        except CannotReadMEIException as ex:
            message, status = jsonify({"message": ex.message}), 500
            return make_response(message, status)

        try:
            mei_slice = meislicer.MeiSlicer(parsed_mei, measures, staves, beats, completeness).select()
        except BadApiRequest as ex:
            message, status = jsonify({"message": ex.message}), 400
            return make_response(message, status)

        # this will write it to a temporary directory automatically
        try:
            filename = meiinfo.write_MEI(mei_slice)
        except CannotWriteMEIException as ex:
            message, status = jsonify({"message": ex.message}), 500
            return make_response(message, status)

        return send_file(filename, as_attachment=True, mimetype="application/xml")


# Instantiate Api handler and add routes
api = Api(omas)
api.add_resource(Information, '/<path:MEI_id>/info.json')
api.add_resource(Address, '/<path:MEI_id>/<oner:measures>/<onex:staves>/<oner:beats>',
                 '/<path:MEI_id>/<oner:measures>/<onex:staves>/<oner:beats>/<completeness>')