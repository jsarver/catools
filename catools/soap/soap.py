"""
Provides tools for initiating webservices session
"""
from xml.etree import ElementTree as xml
import datetime
import logging
from xml.etree.ElementTree import XMLParser
import os
import yaml
from suds.client import Client

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.NullHandler())


def element_to_dict(element):
    e_dict = {a.text: v.text for a, v in zip(element.getiterator('AttrName'), element.getiterator('AttrValue'))}
    return e_dict


def get_session_from_yaml(yaml_file, session_name):
    if os.path.exists(yaml_file):
        f = open(yaml_file)
        session_data = yaml.load(f)[session_name]
        return SoapSession(session_data['user'], session_data['password'],
                           session_data['host'], session_data['port'])
    else:
        raise NameError("File Does not exist {}".format(yaml_file))


def extract_fields(objXML, attribute_only=False):
    x = XMLParser(encoding='utf-8')
    element_list = xml.fromstring(objXML.encode('utf-8'))
    obj_list = []
    if attribute_only:
        obj_list.append({i.tag: i.attrib for i in element_list[0].getchildren()})
    else:
        for e in element_list.iter('UDSObject'):
            element_dict = element_to_dict(e)
            element_dict['handle'] = e[0].text
            obj_list.append(element_dict)
    return obj_list


class SoapResponse(object):
    def __init__(self, xmlresponse, attribute_only=False):
        self.response = xmlresponse
        self.attribute_only = attribute_only

    def __repr__(self):
        if not self.response:
            return ''
        if str(self.response.__class__) == "<class 'suds.sudsobject.reply'>":
            return self.response.__repr__()
        else:
            return self.response

    def __str__(self):
        if not self.response:
            return ""
        if str(self.response.__class__) == "<class 'suds.sudsobject.reply'>":
            return self.response.__str__()
        else:
            return self.response

    def to_dict(self):
        """
        converts raw xml to dictionary
        :return:
        """
        return extract_fields(objXML=self.response, attribute_only=self.attribute_only)


class SoapService(object):
    def __init__(self, session, service_name):
        self.s = session
        self.name = service_name

    def __call__(self, *args, **kwargs):
        service_method = getattr(self.s.client.service, self.name)
        new_args = list(args)
        for idx, arg in enumerate(new_args):
            if isinstance(arg, list):
                new_args[idx] = self.createArrayOfString(arg)
        for k, v in kwargs.items():
            if isinstance(v, list):
                kwargs[k] = self.createArrayOfString(v)
        return SoapResponse(service_method(self.s.sid, *new_args, **kwargs))

    def createArrayOfString(self, iterable):
        array_of_string = self.s.client.factory.create('ArrayOfString')
        iterable = iterable if iterable else []
        array_of_string.string = iterable
        return array_of_string


def login(host, username, password, port=8080):
    return SoapAPI(SoapSession(username, password, host, port))


class SoapSession(object):
    """This builds a session object used to login to ca webservices."""

    def __init__(self, username, password, host, port=8080, auto_renew=True):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self._sid = None
        self.url = self.get_url()
        self.client = Client(self.url)
        self.last_login = None
        self.auto_renew = auto_renew

    def __repr__(self):
        return "{}@{}".format(self.username, self.host)

    @property
    def sid(self):
        self._sid = self.login()
        return self._sid

    def login(self):
        if not (self.username and self.password):
            raise ValueError('Invalid username or password')
        if self.session_is_expired():
            newsid = self.client.service.login(self.username, self.password)
            self.last_login = datetime.datetime.now()
            return newsid
        else:
            return self._sid

    def session_is_expired(self):
        """
        Takes subtracts last time logged in from current date and
        if the difference in minutes is greater than 90 minutes
        the session has expired.
        :return:
        """
        if not self.last_login:
            return True
        session_limit = 90
        session_duration = datetime.datetime.now() - self.last_login
        return session_duration.seconds / 60 > session_limit

    def get_url(self):
        url = "http://{}:{}/axis/services/USD_R11_WebService?wsdl"
        if not (self.host or self.port):
            raise ValueError("No valid host name supplied")
        else:
            return url.format(self.host, self.port)


class SoapAPI(object):
    """
    Web Services Interface
    """

    def __init__(self, session):
        # returns suds client interface and sid
        self.cl = session.client
        self.sid = session.sid
        self._session = session

    def __getattr__(self, service_name):
        return SoapService(self._session, service_name)

    def searchObjects(self, objType, searchCriteria, maxRows=-1, returnAttributes=None):
        returnAttributes = returnAttributes if returnAttributes else []
        return self.doSelect(objType, searchCriteria, maxRows, attributes=returnAttributes)

    def updateObject(self, obj_handle, attribute_changes, return_attributes=None):
        attribute_changes = self.createArrayOfString(attribute_changes)
        return_attributes = self.createArrayOfString(return_attributes)
        return self.cl.service.updateObject(self.sid, obj_handle, attribute_changes, return_attributes)

    def createRequest(self, creator_handle, attrvals, return_attributes=None,string_template="",attributes=None,
                      reqHandle="", reqNumber=""):
        attrvals = self.createArrayOfString(attrvals)
        return_attributes = self.createArrayOfString(return_attributes)
        attributes = self.createArrayOfString(attributes)
        results=self.cl.service.createRequest(self.sid, creator_handle, attrvals,return_attributes,string_template,attributes,
                                      reqHandle,reqNumber)
        return results

    def listAttributes(self, obj_name, convert_to_dict=True):
        objresults = self.getObjectTypeInformation(obj_name)
        if convert_to_dict:
            attributes = extract_fields(objXML=objresults.response, attribute_only=convert_to_dict)
        else:
            return objresults.response
        return attributes

    def extractHandle(self, suds_xml):
        return xml.fromstring(suds_xml)[0][0].text

    def isMember(self, user, group):
        ismember = self.doSelect("grpmem", "member = U'{}' and group = U'{}'".format(user, group), )
        if ismember:
            logger.debug("User: {} is in group: {}".format(user, group))
        else:
            logger.debug("User {} Not in group: {}".format(user, group))
        return ismember

    def addToGroup(self, user, group):
        logger.info("Adding user: {} to group {}".format(user, group))
        if not self.isMember(user, group):
            self.cl.service.addMemberToGroup(self.sid, "cnt:{}".format(user), "cnt:{}".format(group))

    def createArrayOfString(self, iterable):
        array_of_string = self.cl.factory.create('ArrayOfString')
        iterable = iterable if iterable else []
        array_of_string.string = iterable
        return array_of_string

    def removeFromGroup(self, user, group):
        logger.info("removing user: {} from group {}".format(user, group))
        if self.isMember(user, group):
            self.removeMemberFromGroup("cnt:{}".format(user), "cnt:{}".format(group))

    def updateRequest(self, ref_num, **kwargs):
        logger.info("updating Request {}".format(ref_num))
        request_handle = self.searchObjects('cr', "ref_num='{}'".format(ref_num), maxRows=1)[0]['handle']
        update_attributes = list(kwargs.items())
        results = self.updateObject(request_handle, update_attributes)
        logger.info("Update Successful")
        return results


    def tansferRequest(self, ref_num, group=None, assignee=None, message=""):
        request_handle = self.searchObjects('cr', "ref_num='{}'".format(ref_num), maxRows=1)[0]['handle']
        user_handle = self.cl.service.getHandleForUserid(self.sid, self._session.username)
        assignee_handle = "cnt:{}".format(assignee) if assignee else ""
        group_handle = "cnt:{}".format(group) if assignee_handle else ""
        setAssignee = 1 if assignee else 0
        setGroup = 1 if group else 0
        if group or assignee:
            self.cl.service.transfer(self.sid, user_handle, request_handle,
                                     message, setAssignee, assignee_handle,
                                     setGroup, group_handle, 0, "")
        else:
            logger.exception("No Group or assignee specified")


if __name__ == '__main__':
    pass