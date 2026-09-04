# -*- coding: utf-8 -*-
from burp import IBurpExtender, IHttpListener, IExtensionStateListener, IScanIssue
from java.net import URL
from Queue import Queue
import os
import threading

banner = '''
       ____             _                   
      |  _ \           | |                  
      | |_) | __ _  ___| | ___   _ _ __     
      |  _ < / _` |/ __| |/ | | | | '_ \    
      | |_) | (_| | (__|   <| |_| | |_) |   
      |____/ \__,_|\___|_|\_\\__,_| .__/    
   _____       _            _   _ | |       
  |  __ \     | |          | | (_)|_|       
  | |  | | ___| |_ ___  ___| |_ ___   _____ 
  | |  | |/ _ | __/ _ \/ __| __| \ \ / / _ \\
  | |__| |  __| ||  __| (__| |_| |\ V |  __/
  |_____/ \___|\__\___|\___|\__|_| \_/ \___|
                                            
 Burpsuite Plugin for searching backups files
'''

print(banner)


class BackupScanIssue(IScanIssue):
    ISSUE_NAME = "Backup file found"
    SEVERITY = "High"
    CONFIDENCE = "Firm"
    ISSUE_BACKGROUND = ("Developers sometimes leave backup copies of source-controlled files on the "
                        "web server. These files may contain source code, credentials or sensitive "
                        "configuration data.")
    REMEDIATION_BACKGROUND = ("Remove backup files from the web root and prevent backup artifacts "
                              "from being deployed with the application.")

    def __init__(self, http_service, url, http_messages, detail):
        self._http_service = http_service
        self._url = url
        self._http_messages = http_messages
        self._detail = detail

    def getUrl(self):
        return self._url

    def getIssueName(self):
        return self.ISSUE_NAME

    def getIssueType(self):
        return -1

    def getSeverity(self):
        return self.SEVERITY

    def getConfidence(self):
        return self.CONFIDENCE

    def getIssueBackground(self):
        return self.ISSUE_BACKGROUND

    def getRemediationBackground(self):
        return self.REMEDIATION_BACKGROUND

    def getIssueDetail(self):
        return self._detail

    def getRemediationDetail(self):
        return None

    def getHttpMessages(self):
        return self._http_messages

    def getHttpService(self):
        return self._http_service


class BurpExtender(IBurpExtender, IHttpListener, IExtensionStateListener):
    URL_EXTENSIONS = ('.php', '.aspx', '.asp', '.jsp', '.jspx')
    BACKUP_EXTENSIONS = ('.bak', '.zip', '.tar.gz', '.1', '.old', '.orig')
    HEAD_REJECTED_CODES = (403, 405, 501)
    SCAN_WORKERS = 6

    def registerExtenderCallbacks(self, callbacks):
        self._callbacks = callbacks
        self._helpers = callbacks.getHelpers()
        self._url_cache = set()
        self._cache_lock = threading.Lock()
        self._scan_queue = Queue()
        self._workers = [
            threading.Thread(target=self._scan_worker) for _ in range(self.SCAN_WORKERS)
        ]
        for w in self._workers:
            w.daemon = True
            w.start()
        callbacks.setExtensionName("Backup Detective")
        callbacks.registerHttpListener(self)
        callbacks.registerExtensionStateListener(self)
        print("   Backup Detective is loaded successfully\n")

    def processHttpMessage(self, toolFlag, messageIsRequest, messageInfo):
        if messageIsRequest:
            return
        try:
            raw = messageInfo.getUrl()
            url = URL(raw.getProtocol(), raw.getHost(), raw.getPort(), raw.getPath())
            path = url.getPath()
            if not (path.lower().endswith(self.URL_EXTENSIONS) or (path.endswith('/') and len(path) > 1)):
                return
            url_str = url.toString()
            with self._cache_lock:
                if url_str in self._url_cache:
                    return
                self._url_cache.add(url_str)
            print("Requesting to: " + url_str)
            self._scan_queue.put(url)
        except Exception as e:
            print("[!] Backup Detective: " + str(e))

    def _scan_worker(self):
        while True:
            url = self._scan_queue.get()
            try:
                if url is None:
                    return
                self._check_backup_files(url)
            except Exception as e:
                print("[!] scan error for " + str(url) + ": " + str(e))
            finally:
                self._scan_queue.task_done()

    def _check_backup_files(self, url):
        http_service = self._helpers.buildHttpService(
            url.getHost(), self._default_port(url), url.getProtocol())
        for backup_url in self._build_backup_urls(url):
            response = self._probe(http_service, backup_url, 'HEAD')
            status = self._status_of(response)
            if status != 200 and status in self.HEAD_REJECTED_CODES:
                response = self._probe(http_service, backup_url, 'GET')
                status = self._status_of(response)
            if status == 200:
                self._register_finding(http_service, backup_url, response)

    def _probe(self, http_service, url, method):
        request = self._helpers.buildHttpMessage(
            self._request_headers(http_service, url, method), None)
        return self._callbacks.makeHttpRequest(http_service, request)

    def _status_of(self, response):
        if response is None or response.getResponse() is None:
            return None
        return self._helpers.analyzeResponse(response.getResponse()).getStatusCode()

    def _request_headers(self, http_service, url, method):
        host = http_service.getHost()
        if http_service.getPort() not in (80, 443):
            host += ':' + str(http_service.getPort())
        return [method + ' ' + (url.getFile() or '/') + ' HTTP/1.1',
                'Host: ' + host,
                'User-Agent: Backup-Detective/1.0']

    def _register_finding(self, http_service, backup_url, response):
        finding_url = str(backup_url)
        detail = ("The application exposes a possible backup file at <b>" + finding_url + "</b>. "
                  "Backup files often contain source code, credentials or sensitive configuration.")
        self._callbacks.addScanIssue(BackupScanIssue(
            http_service, backup_url, [response], detail))
        print("[+] BACKUP FOUND: " + finding_url)

    def _build_backup_urls(self, url):
        url_str = url.toString()
        path = url.getPath()
        ext = os.path.splitext(path)[1]
        if ext:
            base = url_str[:-len(ext)]
            for backup_ext in self.BACKUP_EXTENSIONS:
                yield URL(base + ext + backup_ext)
                yield URL(base + backup_ext)
        elif path.endswith('/') and len(path) > 1:
            stem = url_str[:-1]
            for backup_ext in self.BACKUP_EXTENSIONS:
                yield URL(stem + backup_ext)

    @staticmethod
    def _default_port(url):
        if url.getPort() != -1:
            return url.getPort()
        return 443 if url.getProtocol() == 'https' else 80

    def extensionUnloaded(self):
        for _ in range(len(self._workers)):
            self._scan_queue.put(None)
        for w in self._workers:
            w.join(timeout=1)
