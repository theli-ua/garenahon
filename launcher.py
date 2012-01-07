#!/usr/bin/env python
import os,sys
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
import socket,struct,threading,subprocess
import zipfile
from platform import system

WEBSERVER_PORT = 8123
ms = "masterserver.cis.s2games.com"
masterserver_international = 'masterserver.hon.s2games.com'
USER_AGENT = "S2 Games/Heroes of Newerth/2.0.29.1/lac/x86-biarch"

if system() == 'Linux':
    MOD_PATH = "~/.Heroes of Newerth/game/resources_theli_garena.s2z"
    HOST_OS = 'lac'
    HOST_ARCH = 'x86-biarch'
    HON_BINARY = './hon.sh'
else:
    HOST_OS = 'mac'
    HOST_ARCH = 'universal'
    MOD_PATH = '~/Library/Application Support/Heroes of Newerth/game/resources_theli_garena.s2z'
    HON_BINARY = './HoN'

#interface_patch_files = ['ui/fe2/matchmaking.package','ui/fe2/main.interface','ui/fe2/store_form_buycoins.package','ui/fe2/store_templates.package','ui/fe2/system_bar.package','ui/fe2/news.package','ui/fe2/public_games.package']
interface_patch_files = [
'ui/fe2/changelog.package',
'ui/fe2/communicator.package',
'ui/fe2/create_account.package',
'ui/fe2/creategame.package',
'ui/fe2/form_create_account.package',
'ui/fe2/form_create_paid_account.package',
'ui/fe2/form_create_subaccount.package',
'ui/fe2/form_gift_account.package',
'ui/fe2/form_purchase_name_change.package',
'ui/fe2/form_reset_stats.package',
'ui/fe2/form_upgrade_account.package',
'ui/fe2/form_upgrade_friend.package',
'ui/fe2/main.interface',
'ui/fe2/main_tooltips.package',
'ui/fe2/matchmaking.package',
'ui/fe2/news.package',
'ui/fe2/player_stats.package',
'ui/fe2/public_games.package',
'ui/fe2/store_form_buycoins.package',
'ui/fe2/store_form_namechange.package',
'ui/fe2/store.package',
'ui/fe2/store_templates.package',
'ui/fe2/system_bar.package',
'ui/fe2/ui_items_2.interface',
]
current_version = ''
garena_token = ''

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
    data = struct.pack('<IHHB16s33s5s',0x3b,0x0101,0x80,0,user[0],password[0],'RU')
    s.send(data)
    data = s.recv(42)
    s.close()
    parsed = struct.unpack('<IB32sBI',data)
    return parsed[2]
    

def forward(path,query):
    details = urlencode(query,True).encode('utf8')
    url = Request('http://{0}/{1}'.format(ms, path),details)
    url.add_header("User-Agent",USER_AGENT)
    data = urlopen(url).read().decode("utf8", 'ignore') 
    return data

class MyHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        print('get')
        print('self')
        try:
            self.send_error(404,'File Not Found: %s' % self.path)    
            return
                
        except IOError:
            self.send_error(404,'File Not Found: %s' % self.path)
     

    def do_POST(self):
        global garena_token
        global current_version
        #try:
        if True:
            self.send_response(200)
            self.end_headers()

            varLen = int(self.headers['Content-Length'])
            postVars = self.rfile.read(varLen)
            query = urlparse.parse_qs(postVars)
            if self.path == '/patcher/patcher.php':
                #query['os'] = 'wgc'
                #query['arch'] = 'i686'
                #self.wfile.write('a:2:{i:0;a:7:{s:4:"name";s:7:"version";s:7:"version";s:5:"{0}";s:14:"compat_version";s:5:"0.0.0";s:2:"os";s:3:"lac";s:4:"arch";s:10:"x86-biarch";s:3:"url";s:30:"http://dl.heroesofnewerth.com/";s:4:"url2";s:29:"http://patch.hon.s2games.com/";}s:7:"version";s:7:"{0}";}'.format(current_version))
                return
            elif 'f' in query and query['f'][0] == 'auth':
                garena_token = get_garena_token(query['login'],query['password'])
                query = {'f':'token_auth','token' : garena_token }
            elif 'f' in query and query['f'][0] == 'garena_register':
                query['token'] = garena_token
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
            elif line.find('ssl="true"'):
                out.append(line.replace('ssl="true"','ssl="false"'))
            else:
                out.append(line)
        to.writestr(f,'\n'.join(out))
    res.close()
    to.close()
        

def update():
    global current_version
    if not os.path.exists('honpatch.py'):
        print('honpatch not found,cannot update!!!!')
        return
    from honpatch import getVerInfo,Manifest,fetch_single
    #get latest windows garena version
    wgc_version = getVerInfo('wgc','i686',ms)['version']
    if not os.path.exists('manifest.xml'):
        sourceManifest = Manifest()
    else:
        sourceManifest = Manifest(xmlpath='manifest.xml')
    if wgc_version == sourceManifest.version:
        print('Already up to date')
        return
    verinfo = getVerInfo('lac','x86-biarch',masterserver_international) 
    if verinfo['version'] == wgc_version:
        destver = wgc_version
    else:
        import tempfile,shutil
        fetchdir = tempfile.mkdtemp()
        baseurl = verinfo[0]['url'] + HOST_OS + '/' + HOST_ARCH + '/'
        baseurl2 = verinfo[0]['url2'] + HOST_OS + '/' + HOST_ARCH + '/'
        if not fetch_single(baseurl,baseurl2,wgc_version,'manifest.xml',fetchdir,4):
            print("Can't find {1} version {0}".format(wgc_version,system()))
            wgc_version = wgc_version.split('.')
            wgc_version[-1] = '0'
            wgc_version = '.'.join(wgc_version)
            print('Trying {0}'.format(wgc_version))
            if sourceManifest.version == wgc_version:
                print('Nothing to update')
                return
            if not fetch_single(baseurl,baseurl2,wgc_version,'manifest.xml',fetchdir,4):
                print('Can''t fetch that too :(')
                return
        if sourceManifest.version == wgc_version:
            print('Nothing to update')
            return
        args = [sys.executable,'honpatch.py'] 
        current_version = wgc_version
        if sourceManifest.version == '0.0.0.0':
            args += ['-d','.']
        else:
            args += ['-s','.']
        args += ['--os',HOST_OS]
        args += ['--arch',HOST_ARCH]
        args += ['-v',wgc_version]
        args += ['--masterserver',masterserver_international]
        p = subprocess.Popen(args)
        print('patching hon to version {0}'.format(wgc_version))
        p.wait()
    
def main():
    global WEBSERVER_PORT
    abspath = os.path.abspath(__file__)
    dname = os.path.dirname(abspath)
    os.chdir(dname)
    
    print('checking for HoN updates')
    update()

    mod_path = os.path.expanduser(MOD_PATH)
    clean_patches(mod_path)
    started = False
    while not started:
        try:
            server = HTTPServer(('', WEBSERVER_PORT), MyHandler)
            started = True
        except:
            print("Local port {0} is busy, trying {1}".format(WEBSERVER_PORT,WEBSERVER_PORT + 1))
            WEBSERVER_PORT += 1
    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.daemon = True
    server_thread.start()
    print 'started httpserver...'
    print('starging hon')
    args = [HON_BINARY]
    args.append('-masterserver')
    args.append('localhost:{0}'.format(WEBSERVER_PORT))
    args.append('-region')
    args.append('RU')
    args.append('-webserver')
    args.append('cis.heroesofnewerth.com')

    args.append('-execute')
    args.append('"set chat_serverPortOverride 11033; set _theli_GarenaEnable true"')
    
    print ('patching matchmaking interface')
    patch_matchmaking(mod_path)
    
    p = subprocess.Popen(args)
    p.wait()
    print('hon exited, stopping masterserver and cleaning up')
    server.shutdown()
    clean_patches(mod_path)    

if __name__ == '__main__':
    main()

