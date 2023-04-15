# -*- coding: utf-8 -*-
from burp import IBurpExtender, IHttpListener
from java.net import URL
import os

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

class BurpExtender(IBurpExtender, IHttpListener):
    URL_EXTENSIONS = ('.php', '.aspx', '.asp', '.jsp', '.jspx')
    BACKUP_EXTENSIONS = {'.bak', '.zip', '.tar.gz', '.1', '.old', '.orig'}
    url_cache = set()

    def registerExtenderCallbacks(self, callbacks):
        self._callbacks = callbacks
        self._helpers = callbacks.getHelpers()
        callbacks.setExtensionName("Backup Detective")
        callbacks.registerHttpListener(self)
        print("   Backup Detective is loaded successfully\n")

    def processHttpMessage(self, toolFlag, messageIsRequest, messageInfo):
        if messageIsRequest:
            return

        url = self.get_url_without_query(messageInfo.getUrl())
        url = URL(url)
        path = url.getPath()
        if not path.endswith(self.URL_EXTENSIONS):
            return

        if url.toString() in self.url_cache:
            print("URL already scanned: " + str(url))
            return

        self.url_cache.add(url.toString())
        print("Requesting to: " + str(url))
        self.check_backup_files(url)

    def check_backup_files(self, url):
        http_service = self._helpers.buildHttpService(url.getHost(), self.get_port(url), url.getProtocol())
        backup_urls = self.get_backup_urls(url)
        for backup_url in backup_urls:
            response = self.make_request(backup_url, http_service)
            if response.getStatusCode() == 200:
                print("⚠ Backup ⚠ Found ⚠: " + str(backup_url))

    def get_backup_urls(self, url):
        path, ext = os.path.splitext(url.getPath())
        backup_urls = []
        for backup_ext in self.BACKUP_EXTENSIONS:
            backup_ext_with_original = ext + backup_ext
            backup_url = URL(url.toString().replace(ext, backup_ext_with_original))
            backup_urls.append(backup_url)
            backup_url_no_ext = URL(url.toString().rstrip(ext) + backup_ext)
            backup_urls.append(backup_url_no_ext)
        return backup_urls

    def make_request(self, url, http_service):
        request = self._helpers.buildHttpRequest(url)
        return self._callbacks.makeHttpRequest(http_service, request)

    def get_port(self, url):
        port = url.getPort()
        if port == -1:
            port = 80 if url.getProtocol() == 'http' else 443
        return port

    def get_url_without_query(self, url):
        return str(url).split('?')[0]
