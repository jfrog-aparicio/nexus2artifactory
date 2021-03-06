import os
import re
import ssl
import json
import time
import Queue
import base64
import logging
import urllib
import urllib2
import hashlib
import threading

class PutRequest(urllib2.Request):
    def __init__(self, *args, **kwargs):
        urllib2.Request.__init__(self, *args, **kwargs)

    def get_method(self, *args, **kwargs):
        return 'PUT'

class Upload(object):
    def __init__(self, scr, parent):
        self.log = logging.getLogger(__name__)
        self.scr = scr
        self.parent = parent
        self.filelock = threading.RLock()
        self.threadct = 4
        self.ts = 0

    def upload(self, conf):
        self.log.info("Uploading artifacts.")
        hashall = conf["Repository Migration Setup"]["Hash All Artifacts"]
        newts = int(1000*time.time())
        url, headers = self.getconndata()
        queue = Queue.Queue(2*self.threadct)
        thargs = queue, url, headers, hashall
        threads = []
        self.log.info("Creating %d threads.", self.threadct)
        for _ in xrange(self.threadct):
            t = threading.Thread(target=self.runThread, args=thargs)
            threads.append(t)
            t.start()
        self.log.info("Threads created successfully.")
        for f in self.filelistgenerator(conf): queue.put(f)
        for _ in xrange(self.threadct): queue.put(None)
        for t in threads: t.join()
        self.log.info("All artifacts successfully uploaded.")
        self.ts = newts
        self.parent.prog.stepsmap['Artifacts'][1] = True

    def getconndata(self):
        urlp = self.parent.url
        url = urlp[0] + '://' + urlp[1] + urlp[2]
        enc = base64.b64encode(self.parent.user + ':' + self.parent.pasw)
        headers = {'User-Agent': 'nex2art', 'Authorization': "Basic " + enc}
        return url, headers

    def filelistgenerator(self, conf):
        repomap = self.scr.nexus.repomap
        storage = os.path.join(self.scr.nexus.path, 'storage')
        for name, src in conf["Repository Migration Setup"].items():
            if not isinstance(src, dict): continue
            if src['available'] != True: continue
            if src["Migrate This Repo"] != True: continue
            if repomap and name in repomap and 'class' in repomap[name]:
                if repomap[name]['class'] != 'local': continue
            path = None
            if repomap and name in repomap and 'localurl' in repomap[name]:
                path = repomap[name]['localurl']
                path = re.sub('^file:/(.):/', '\\1:/', path)
                path = re.sub('^file:/', '/', path)
                path = os.path.abspath(path)
            else: path = os.path.join(storage, name)
            if not os.path.isdir(path): continue
            metapath = os.path.join(path, '.nexus', 'attributes')
            files = os.listdir(path)
            try: files.remove('.nexus')
            except ValueError: pass
            try: files.remove('.meta')
            except ValueError: pass
            try: files.remove('archetype-catalog.xml')
            except ValueError: pass
            while len(files) > 0:
                f = files.pop()
                if f.endswith('.md5') or f.endswith('.sha1'): continue
                ap = os.path.join(path, f)
                mp = os.path.join(metapath, f)
                if os.path.isdir(ap):
                    def joinall(x): return os.path.join(f, x)
                    files.extend(map(joinall, os.listdir(ap)))
                else: yield ap, mp, src["Repo Name (Artifactory)"]

    def runThread(self, queue, url, headers, hashall):
        while True:
            item = queue.get()
            if item == None: break
            path, metapath, repo = item
            stat = None
            metadata = self.acquireMetadata(path, metapath, hashall)
            modif, store, sha1, md5 = metadata
            if modif != None and modif < self.ts:
                self.incFileCount(repo + ':' + store)
                continue
            puturl = url + urllib.quote(repo + store)
            chksumheaders = {'X-Checksum-Deploy': 'true'}
            chksumheaders['X-Checksum-Sha1'] = sha1
            chksumheaders['X-Checksum-Md5'] = md5
            chksumheaders.update(headers)
            self.log.info("Deploying artifact checksum %s (%s) to %s.",
                          sha1, md5, puturl)
            req = PutRequest(puturl, headers=chksumheaders)
            try:
                if self.scr.sslnoverify:
                    ctx = ssl.create_default_context()
                    ctx.check_hostname = False
                    ctx.verify_mode = ssl.CERT_NONE
                    stat = urllib2.urlopen(req, context=ctx).getcode()
                else: stat = urllib2.urlopen(req).getcode()
            except urllib2.HTTPError as ex:
                if ex.code == 404:
                    self.log.info("Artifact not found, upload required.")
                else:
                    msg = "Error deploying artifact checksum:\n%s"
                    self.log.exception(msg, ex.read())
                stat = ex.code
            except urllib2.URLError as ex:
                self.log.exception("Error deploying artifact checksum:")
                stat = ex.reason
            if stat == 404: stat = self.deployArtifact(puturl, path, headers)
            if not isinstance(stat, (int, long)) or stat < 200 or stat >= 300:
                self.log.error("Unable to deploy artifact to %s.", puturl)
                self.incFileCount(repo + ':' + store, True)
            else:
                self.deployString(puturl + '.sha1', sha1, headers)
                self.deployString(puturl + '.md5', md5, headers)
                self.log.info("Successfully deployed artifact to %s.", puturl)
                self.incFileCount(repo + ':' + store)

    def deployArtifact(self, url, path, headers):
        stat = None
        artifactheaders = {'Content-Type': 'application/octet-stream'}
        try:
            artifactheaders['Content-Length'] = str(os.stat(path).st_size)
            artifactheaders.update(headers)
            with open(path, 'r') as f:
                self.log.info("Uploading artifact to %s.", url)
                req = PutRequest(url, f, artifactheaders)
                try:
                    if self.scr.sslnoverify:
                        ctx = ssl.create_default_context()
                        ctx.check_hostname = False
                        ctx.verify_mode = ssl.CERT_NONE
                        stat = urllib2.urlopen(req, context=ctx).getcode()
                    else: stat = urllib2.urlopen(req).getcode()
                except urllib2.HTTPError as ex:
                    self.log.exception("Error uploading artifact:\n%s", ex.read())
                    stat = ex.code
                except urllib2.URLError as ex:
                    self.log.exception("Error uploading artifact:")
                    stat = ex.reason
        except BaseException as ex:
            self.log.exception("Error uploading artifact:")
            stat = str(ex)
        return stat

    def deployString(self, url, content, headers):
        stat = None
        artifactheaders = {'Content-Type': 'application/octet-stream'}
        artifactheaders['Content-Length'] = str(len(content))
        artifactheaders.update(headers)
        self.log.info("Uploading artifact to %s.", url)
        req = PutRequest(url, content, artifactheaders)
        try:
            if self.scr.sslnoverify:
                ctx = ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
                stat = urllib2.urlopen(req, context=ctx).getcode()
            else: stat = urllib2.urlopen(req).getcode()
        except urllib2.HTTPError as ex:
            self.log.exception("Error uploading artifact:\n%s", ex.read())
            stat = ex.code
        except urllib2.URLError as ex:
            self.log.exception("Error uploading artifact:")
            stat = ex.reason
        return stat

    def acquireMetadata(self, path, metapath, hashall):
        modif, store, sha1, md5, js = None, None, None, None, None
        if not hashall:
            try:
                with open(metapath, 'r') as meta: js = json.load(meta)
                try: modif = int(js['storageItem-modified'])
                except: pass
                try: store = js['storageItem-path']
                except: pass
                try: sha1 = js['digest.sha1']
                except: pass
                try: md5 = js['digest.md5']
                except: pass
            except: pass
            if sha1 == None:
                try:
                    with open(path + '.sha1', 'r') as f: sha1 = f.read()
                except: pass
            if md5 == None:
                try:
                    with open(path + '.md5', 'r') as f: md5 = f.read()
                except: pass
        if store == None:
            for i, c in enumerate(path):
                if c != metapath[i]:
                    store = path[path.rfind("/", 0, i):]
                    break
        if sha1 == None:
            try:
                h = hashlib.sha1()
                with open(path, 'rb') as f:
                    for chunk in iter(lambda: f.read(4096), b''): h.update(chunk)
                sha1 = h.hexdigest()
            except: pass
        if md5 == None:
            try:
                h = hashlib.md5()
                with open(path, 'rb') as f:
                    for chunk in iter(lambda: f.read(4096), b''): h.update(chunk)
                md5 = h.hexdigest()
            except: pass
        return modif, store, sha1, md5

    def incFileCount(self, fname, error=False):
        with self.filelock:
            self.parent.prog.currentartifact = fname
            self.parent.prog.stepsmap['Artifacts'][4] += 1
            if error: self.parent.prog.stepsmap['Artifacts'][3] += 1
            self.parent.prog.refresh()
