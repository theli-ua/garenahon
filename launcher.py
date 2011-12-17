#!/usr/bin/env python
import string,cgi,time
from os import curdir, sep
import os
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
import socket,struct,threading,subprocess
import zipfile

WEBSERVER_PORT = 8123
MOD_PATH = "~/.Heroes of Newerth/game/resources_theli_garena.s2z"

try:
    #3.x
    from urllib.request import Request
    from urllib.request import urlopen
    from urllib.parse   import urlencode
    from urllib.parse   import quote
    import urllib.parse as urlparse
    from http.client    import HTTPConnection
    from queue          import Queue
except:
    #2.7
    from urllib2        import Request
    from urllib2        import urlopen
    from urllib         import urlencode
    from urllib         import quote
    import urlparse
    from httplib        import HTTPConnection
    from Queue          import Queue
    
def get_garena_token(user,password):
    HOST = 'Honsng_cs.mmoauth.garena.com'
    PORT = 8005
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((HOST, PORT))
    data = struct.pack('<IHHB16s33s5s',0x3b,0x0101,0x80,0,user,password,'RU')
    s.send(data)
    data = s.recv(42)
    s.close()
    parsed = struct.unpack('<IB32sBI',data)
    return parsed[2]
    
ms = "http://masterserver.cis.s2games.com/"
USER_AGENT = "S2 Games/Heroes of Newerth/2.0.29.1/lac/x86-biarch"
interface_patch_files = ['ui/fe2/matchmaking.package','ui/fe2/main.interface','ui/fe2/store_form_buycoins.package','ui/fe2/store_templates.package','ui/fe2/system_bar.package','ui/fe2/news.package','ui/fe2/public_games.package']

def forward(path,query):
    #print query
    details = urlencode(query).encode('utf8')
    url = Request(ms + path,details)
    url.add_header("User-Agent",USER_AGENT)
    data = urlopen(url).read().decode("utf8", 'ignore') 
    #print data
    return data
garena_token = ''

class MyHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        try:
            self.send_error(404,'File Not Found: %s' % self.path)    
            return
                
        except IOError:
            self.send_error(404,'File Not Found: %s' % self.path)
     

    def do_POST(self):
        global garena_token
        #try:
        if True:
            varLen = int(self.headers['Content-Length'])
            postVars = self.rfile.read(varLen)
            query = dict(urlparse.parse_qsl(postVars))
            if self.path == '/patcher/patcher.php':
                query['os'] = 'wgc'
                query['arch'] = 'i686'
            elif 'f' in query and query['f'] == 'auth':
                garena_token = get_garena_token(query['login'],query['password'])
                query = {'f':'token_auth','token' : garena_token }
            elif 'f' in query and query['f'] == 'garena_register':
                query['token'] = garena_token
            self.send_response(200)
            self.end_headers()
            self.wfile.write(forward(self.path,query));
        #except :
        #    pass
        
def clean_patches(path):
    if os.path.exists(path):
        os.unlink(path)

def patch_matchmaking(path):
    res = zipfile.ZipFile('game/resources0.s2z','r')
    to = zipfile.ZipFile(path,'w')
    patch_login1 = False
    patch_login2 = False
    for f in interface_patch_files:
        out = []
        mm = res.open(f,'U')
        for line in mm:
            if line.find('Login Options') != -1 or line.find('Login Input Box') != -1:
                patch_login1 = True
            elif line.find('Garena NO direct start warning') != -1 or line.find('iris.tga') != -1:
                patch_login2 = True
            if line.find('cl_GarenaEnable') != -1:
                if patch_login1:
                    out.append(line.replace('!cl_GarenaEnable','_theli_GarenaEnable'))
                    patch_login1 = False
                elif patch_login2:
                    out.append(line.replace('cl_GarenaEnable','!_theli_GarenaEnable'))
                    patch_login2 = False
                else:
                    out.append(line.replace('cl_GarenaEnable','_theli_GarenaEnable'))
            else:
                out.append(line)
        to.writestr(f,'\n'.join(out))
    res.close()
    to.close()
def main():
    mod_path = os.path.expanduser(MOD_PATH)
    clean_patches(mod_path)
    server = HTTPServer(('', WEBSERVER_PORT), MyHandler)
    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.daemon = True
    server_thread.start()
    print 'started httpserver...'
    print('starging hon')
    args = ['./hon.sh']
    args.append('-masterserver')
    args.append('localhost:{0}'.format(WEBSERVER_PORT))
    args.append('-region')
    args.append('RU')
    args.append('-webserver')
    args.append('cis.heroesofnewerth.com')

    args.append('-execute')
    #args.append('"set chat_serverPortOverride 11033;set _TMM_Region_saved_RU 1;set _TMM_Region_saved_EU 0;set _TMM_Region_saved_USE 0;set _TMM_Region_saved_USW 0;set _TMM_Region_allow_EU false;set _TMM_Region_allow_USE false;set _TMM_Region_allow_USW false;set _TMM_Region_allow_RU true;set _TMM_Region_selected_EU false;set _TMM_Region_selected_USE false;set _TMM_Region_selected_USW false;set _TMM_Region_selected_RU true;set _TMM_List_Regions RU|USE|USW|EU;set _TMM_lastAvailRegions RU;set _TMM_List_Regions RU"')
    args.append('"set upd_checkForUpdates false;set chat_serverPortOverride 11033; set _theli_GarenaEnable true"')
    
    print ('patching matchmaking interface')
    patch_matchmaking(mod_path)
    
    p = subprocess.Popen(args)
    p.wait()
    print('hon exited, stopping masterserver and cleaning up')
    server.shutdown()
    clean_patches(mod_path)    

if __name__ == '__main__':
    main()

