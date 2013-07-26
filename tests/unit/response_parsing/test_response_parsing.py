import os
import re
import glob
import json
import pprint
import logging
import difflib

import botocore.session
from botocore.response import XmlResponse, JSONResponse

log = logging.getLogger(__name__)

def check_dicts(xmlfile, d1, d2):
    if d1 != d2:
        log.debug('-' * 40)
        log.debug(xmlfile)
        log.debug('-' * 40)
        log.debug(pprint.pformat(d1))
        log.debug('-' * 40)
        log.debug(pprint.pformat(d2))
    if not d1 == d2:
        # Borrowed from assertDictEqual, though this doesn't
        # handle the case when unicode literals are used in one
        # dict but not in the other (and we want to consider them
        # as being equal).
        pretty_d1 = pprint.pformat(d1, width=1).splitlines()
        pretty_d2 = pprint.pformat(d2, width=1).splitlines()
        diff = ('\n' + '\n'.join(difflib.ndiff(pretty_d1, pretty_d2)))
        raise AssertionError("Dicts are not equal:\n%s" % diff)


def save_jsonfile(jsonfile, r):
    """
    This is a little convenience when creating new tests.
    You just have to drop the XML file into the data directory
    and then, if not JSON file is present, this code will
    create the JSON file and dump the parsed value into it.
    Of course, you need to validate that the JSON is correct
    but it makes it easy to bootstrap more tests.
    """
    if not os.path.isfile(jsonfile):
        fp = open(jsonfile, 'w')
        json.dump(r.get_value(), fp, indent=4)
        fp.close()


def test_xml_parsing():
    for dp in ['responses', 'errors']:
        data_path = os.path.join(os.path.dirname(__file__), 'xml')
        data_path = os.path.join(data_path, dp)
        session = botocore.session.get_session()
        xml_files = glob.glob('%s/*.xml' % data_path)
        service_names = set()
        for fn in xml_files:
            service_names.add(os.path.split(fn)[1].split('-')[0])
        for service_name in service_names:
            service = session.get_service(service_name)
            service_xml_files = glob.glob('%s/%s-*.xml' % (data_path,
                                                           service_name))
            for xmlfile in service_xml_files:
                dirname, filename = os.path.split(xmlfile)
                basename = os.path.splitext(filename)[0]
                jsonfile = os.path.join(dirname, basename + '.json')
                sn, opname = basename.split('-', 1)
                opname = opname.split('#')[0]
                operation = service.get_operation(opname)
                r = XmlResponse(session, operation)
                fp = open(xmlfile)
                xml = fp.read()
                fp.close()
                r.parse(xml, 'utf-8')
                save_jsonfile(jsonfile, r)
                fp = open(jsonfile)
                data = json.load(fp)
                fp.close()
                yield check_dicts, xmlfile, r.get_value(), data


def test_json_parsing():
    input_path = os.path.join(os.path.dirname(__file__), 'json')
    input_path = os.path.join(input_path, 'inputs')
    output_path = os.path.join(os.path.dirname(__file__), 'json')
    output_path = os.path.join(output_path, 'outputs')
    session = botocore.session.get_session()
    jsonfiles = glob.glob('%s/*.json' % input_path)
    service_names = set()
    for fn in jsonfiles:
        service_names.add(os.path.split(fn)[1].split('-')[0])
    for service_name in service_names:
        service = session.get_service(service_name)
        service_input_files = glob.glob('%s/%s-*.json' % (input_path,
                                                          service_name))
        for inputfile in service_input_files:
            dirname, filename = os.path.split(inputfile)
            outputfile = os.path.join(output_path, filename)
            basename = os.path.splitext(filename)[0]
            sn, opname = basename.split('-', 1)
            operation = service.get_operation(opname)
            r = JSONResponse(session, operation)
            fp = open(inputfile)
            jsondoc = fp.read()
            fp.close()
            r.parse(jsondoc, 'utf-8')
            save_jsonfile(outputfile, r)
            fp = open(outputfile)
            data = json.load(fp)
            fp.close()
            yield check_dicts, inputfile, r.get_value(), data
