import logging
import urllib2
import json
import ssl
import base64
import StringIO
import xml.etree.ElementTree as ET
import urlparse
import re

'''
 An API for accessing Artifactory (4.0+)
 
 The API is for testing and not for general usage. As such, functionality such as uploading/downloading is not 
 implemented.
 
 APIs for:
  * Users
  * Permissions
  * Configurations
  * Artifacts
'''

class ArtifactoryAccess:
    def __init__(self, url, username, password, ignore_cert = False, exlog=False):
        self.log = logging.getLogger(__name__)
        self.url = url.rstrip('/')
        self.ignore_cert = ignore_cert
        self.json = re.compile(r'^application/(?:[^;]+\+)?json(?:;.+)?$')
        self.xml = re.compile(r'^application/(?:[^;]+\+)?xml(?:;.+)?$')
        self.exlog = exlog
        # Set up the connection
        headers = {'User-Agent': 'Artifactory Python Test API'}
        enc = base64.b64encode(username + ':' + password)
        headers['Authorization'] = "Basic " + enc
        url_comp = urlparse.urlparse(self.url)
        self.connection = url_comp.scheme, url_comp.netloc, url_comp.path, headers

    # Get a list of all the users
    def get_users(self):
        return self.get_call_wrapper('/api/security/users')

    # Get detailed info of a specific user
    # False if no such user exists or there was an error getting it
    def get_user(self, username):
        return self.get_call_wrapper('/api/security/users/' + username)

    # Get a list of all the groups
    def get_groups(self):
        return self.get_call_wrapper('/api/security/groups')

    # Get detailed info of a specific group
    # False if no such user exists
    def get_group(self, group_name):
        return self.get_call_wrapper('/api/security/groups/' + group_name)

    # Get a list of all the permissions
    def get_permissions(self):
        return self.get_call_wrapper('/api/security/permissions')

    # Get detailed info of a specific permission
    def get_permission(self, permission_name):
        return self.get_call_wrapper('/api/security/permissions/' + permission_name)

    # Ping the Artifactory instance
    # @return True if Artifactory responds with 200, else False
    def ping(self):
        return self.get_call_wrapper('/api/system/ping') != False

    # True if the artifact exists at the specified path
    def artifact_exists(self, repo_name, artifact_path):
        return self.get_artifact_details(repo_name, artifact_path) != False

    # Get detailed info of the item
    # False if no such artifact exists
    def get_artifact_details(self, repo_name, artifact_path):
        return self.get_call_wrapper('/api/storage/' + repo_name + '/' + artifact_path.lstrip('/'))

    # Get a list of all the repositories
    def get_repositories(self):
        return self.get_call_wrapper('/api/repositories')

    # Get detailed info of the repository
    # False if no such repository exists
    def get_repository(self, repo_name):
        return self.get_call_wrapper('/api/repositories/' + repo_name)

    # Get license info
    def get_license(self):
        return self.get_call_wrapper('/api/system/license')


    # Get the full Artifactory configuration
    def get_configuration(self):
        return self.get_call_wrapper('/api/system/configuration')

    # Install a license into an Artifactory instance
    def install_license(self, license_contents):
        try:
            response = self.dorequest('POST', '/api/system/license', {'licenseKey': license_contents})
            return response
        except Exception as ex:
            return False

    def get_call_wrapper(self, arg):
        try:
            response = self.dorequest('GET', arg)
            return response
        except Exception as ex:
            return False

    # Helper REST method
    def dorequest(self, method, path, body=None):
        resp, stat, msg, ctype = None, None, None, None
        headers = {}
        if isinstance(body, (dict, list, tuple)):
            body = json.dumps(body)
            headers['Content-Type'] = 'application/json'
        elif isinstance(body, ET.ElementTree):
            fobj = StringIO.StringIO()
            body.write(fobj)
            body = fobj.getvalue()
            fobj.close()
            headers['Content-Type'] = 'application/xml'
        scheme, host, rootpath, extraheaders = self.connection
        headers.update(extraheaders)
        url = urlparse.urlunsplit((scheme, host, rootpath + path, '', ''))
        req = MethodRequest(url, body, headers, method=method)
        self.log.info("Sending %s request to %s.", method, url)
        try:
            if self.ignore_cert:
                ctx = ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
                resp = urllib2.urlopen(req, context=ctx)
            else: resp = urllib2.urlopen(req)
            stat = resp.getcode()
            ctype = resp.info().get('Content-Type', 'application/octet-stream')
        except urllib2.HTTPError as ex:
            if self.exlog: self.log.exception("Error making request:\n%s", ex.read())
            stat = ex.code
        except urllib2.URLError as ex:
            if self.exlog: self.log.exception("Error making request:")
            stat = ex.reason
        if not isinstance(stat, (int, long)) or stat < 200 or stat >= 300:
            msg = "Unable to " + method + " " + path + ": " + str(stat) + "."
            raise Exception(msg)
        try:
            if self.json.match(ctype) != None: msg = json.load(resp)
            elif self.xml.match(ctype) != None: msg = ET.parse(resp)
            else: msg = resp.read()
        except: pass
        return msg

# REST Helper methods
class MethodRequest(urllib2.Request):
    def __init__(self, *args, **kwargs):
        if 'method' in kwargs:
            self._method = kwargs['method']
            del kwargs['method']
        else: self._method = None
        urllib2.Request.__init__(self, *args, **kwargs)

    def get_method(self, *args, **kwargs):
        if self._method is not None: return self._method
        return urllib2.Request.get_method(self, *args, **kwargs)
