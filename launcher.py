#!/usr/bin/env python
import os,sys
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
import socket,struct,threading,subprocess
import zipfile
from platform import system

abspath = ''
WEBSERVER_PORT = 8123
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
current_version = None
patchurl_1 = None
patchurl_2 = None
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

def unserialize(s):
    return _unserialize_var(s)[0]

def _unserialize_var(s):
    return (
        { 'i' : _unserialize_int
        , 'b' : _unserialize_bool
        , 'd' : _unserialize_double
        , 'n' : _unserialize_null
        , 's' : _unserialize_string
        , 'a' : _unserialize_array
        }[s[0].lower()](s[2:]))

def _unserialize_int(s):
    x = s.partition(';')
    return (int(x[0]), x[2])

def _unserialize_bool(s):
    x = s.partition(';')
    return (x[0] == '1', x[2])

def _unserialize_double(s):
    x = s.partition(';')
    return (float(x[0]), x[2])

def _unserialize_null(s):
    return (None, s)

def _unserialize_string(s):
    (l, _, s) = s.partition(':')
    return (s[1:int(l)+1], s[int(l)+3:])

def _unserialize_array(s):
    (l, _, s) = s.partition(':')
    a, k, s = {}, None, s[1:]

    for i in range(0, int(l) * 2):
        (v, s) = _unserialize_var(s)

        if k != None:
            a[k] = v
            k = None
        else:
            k = v
    return (a,s[1:])   

def dumps(data, charset='utf-8', errors='strict', object_hook=None):
    """Return the PHP-serialized representation of the object as a string,
    instead of writing it to a file like `dump` does.
    """
    def _serialize(obj, keypos):
        if keypos:
            if isinstance(obj, (int, long, float, bool)):
                return 'i:%i;' % obj
            if isinstance(obj, basestring):
                if isinstance(obj, unicode):
                    obj = obj.encode(charset, errors)
                return 's:%i:"%s";' % (len(obj), obj)
            if obj is None:
                return 's:0:"";'
            raise TypeError('can\'t serialize %r as key' % type(obj))
        else:
            if obj is None:
                return 'N;'
            if isinstance(obj, bool):
                return 'b:%i;' % obj
            if isinstance(obj, (int, long)):
                return 'i:%s;' % obj
            if isinstance(obj, float):
                return 'd:%s;' % obj
            if isinstance(obj, basestring):
                if isinstance(obj, unicode):
                    obj = obj.encode(charset, errors)
                return 's:%i:"%s";' % (len(obj), obj)
            if isinstance(obj, (list, tuple, dict)):
                out = []
                if isinstance(obj, dict):
                    iterable = obj.iteritems()
                else:
                    iterable = enumerate(obj)
                for key, value in iterable:
                    out.append(_serialize(key, True))
                    out.append(_serialize(value, False))
                return 'a:%i:{%s}' % (len(obj), ''.join(out))
            if isinstance(obj, phpobject):
                return 'O%s%s' % (
                    _serialize(obj.__name__, True)[1:-1],
                    _serialize(obj.__php_vars__, False)[1:]
                )
            if object_hook is not None:
                return _serialize(object_hook(obj), False)
            raise TypeError('can\'t serialize %r' % type(obj))
    return _serialize(data, False)

def getVerInfo(os,arch,masterserver):
    details = urlencode({'version' : '0.0.0.0', 'os' : os ,'arch' : arch}).encode('utf8')
    url = Request('http://{0}/patcher/patcher.php'.format(masterserver),details)
    url.add_header("User-Agent",USER_AGENT)
    data = urlopen(url).read().decode("utf8", 'ignore') 
    d = unserialize(data)
    return d

def get_garena_token(user,password):
    PORT = 8005
    try:
        ip_region = urlopen('http://75.126.149.34:6008/').read()
    except:
        ip_region = 'RU'

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((GARENA_AUTH_SERVER, PORT))
    data = struct.pack('<IHHB16s33s5s',0x3b,0x0101,0x80,0,user[0],password[0],ip_region)
    s.send(data)
    data = s.recv(42)
    s.close()
    parsed = struct.unpack('<IB32sBI',data)
    return parsed[2]
    

def forward(path,query):
    details = urlencode(query,True).encode('utf8')
    url = Request('http://{0}/{1}'.format(GARENA_MASTERSERVER, path),details)
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
                response = unserialize('a:2:{i:0;a:7:{s:4:"name";s:7:"version";s:7:"version";s:7:"2.5.5.1";s:14:"compat_version";s:5:"0.0.0";s:2:"os";s:3:"wgc";s:4:"arch";s:4:"i686";s:3:"url";s:30:"http://dl.heroesofnewerth.com/";s:4:"url2";s:29:"http://patch.hon.s2games.com/";}s:7:"version";s:7:"2.5.5.1";}')
                response[0]['version'] = current_version
                response['version'] = current_version
                #response[0]['url'] = patchurl_1
                #response[0]['url2'] = patchurl_2
                response[0]['os'] = HOST_OS
                response[0]['arch'] = HOST_ARCH
                self.wfile.write(dumps(response))
                return
            elif 'f' in query and query['f'][0] == 'auth':
                try:
                    garena_token = get_garena_token(query['login'],query['password'])
                    query = {'f':'token_auth','token' : garena_token }
                except:
                    self.wfile.write('a:2:{i:0;b:0;s:4:"auth";s:29:"Invalid Nickname or Password.";}')
                    return
            elif 'f' in query and query['f'][0] == 'garena_register':
                query['token'] = garena_token
            self.wfile.write(forward(self.path,query));
        #except :
        #    pass
        
def clean_patches(path):
    if os.path.exists(path):
        os.unlink(path)

def patch_matchmaking(path):
    dpath = os.path.dirname(path)
    if not os.path.exists(dpath):
        os.makedirs(dpath)
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

def find_latest_version():
    global current_version,patchurl_1,patchurl_2
    wgc_version = getVerInfo('wgc','i686',GARENA_MASTERSERVER)['version']
    wgc_version = wgc_version.split('.')
    verinfo = getVerInfo(HOST_OS,HOST_ARCH,masterserver_international) 
    baseurl = verinfo[0]['url'] + HOST_OS + '/' + HOST_ARCH + '/'
    baseurl2 = verinfo[0]['url2'] + HOST_OS + '/' + HOST_ARCH + '/'
    patchurl_1 = verinfo[0]['url']
    patchurl_2 = verinfo[0]['url2']
    while int(wgc_version[-1]) >= 0:
        if wgc_version[-1] == '0':
            ver = '.'.join(wgc_version[:-1])
        else:
            ver = '.'.join(wgc_version)
        url1 = '{0}/{1}/manifest.xml.zip'.format(baseurl,ver)
        url2 = '{0}/{1}/manifest.xml.zip'.format(baseurl2,ver)
        try:
            if urlopen(url1).getcode() == 200:
                current_version = '.'.join(wgc_version)
                break
        except:pass
        try:
            if urlopen(url2).getcode() == 200:
                current_version = '.'.join(wgc_version)
                break
        except:pass
        wgc_version[-1] = str(int(wgc_version[-1]) - 1)
    print "Found latest appropriate version: {0}".format(current_version)


def update_honpatch():
    global current_version
    if not os.path.exists('honpatch.py'):
        print('honpatch not found,will use ingame updater')
        return
    from honpatch import getVerInfo,Manifest,fetch_single
    #get latest windows garena version
    wgc_version = getVerInfo('wgc','i686',GARENA_MASTERSERVER)['version']
    if not os.path.exists('manifest.xml'):
        #sourceManifest = Manifest()
        print('No manifest.xml found in {0}, you need to place launcher.py in HoN directory'.format(abspath))
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
    global WEBSERVER_PORT,abspath,GARENA_MASTERSERVER,GARENA_WEBSERVER,GARENA_AUTH_SERVER
    if len(sys.argv) < 2 or sys.argv[1] not in ['cis','sea']:
        print('You need to specify region on command line, like')
        print('./launcher.py cis')
        print('or')
        print('./launcher.py sea')
        sys.exit(1)
    if sys.argv[1] == 'cis':
        GARENA_WEBSERVER = 'cis.heroesofnewerth.com'
        GARENA_AUTH_SERVER = 'Honsng_cs.mmoauth.garena.com'
        GARENA_MASTERSERVER = 'masterserver.cis.s2games.com'
    else:
        GARENA_WEBSERVER = 'garena.heroesofnewerth.com'
        GARENA_AUTH_SERVER = 'hon.auth.garenanow.com'
        GARENA_MASTERSERVER = 'masterserver.garena.s2games.com'


    abspath = os.path.abspath(__file__)
    dname = os.path.dirname(abspath)
    os.chdir(dname)
    
    print('checking for HoN updates')
    if not os.path.exists('honpatch.py'):
        find_latest_version()
    else:
        update_honpatch()

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
    if sys.argv[1] == 'cis':
        args.append('-region')
        args.append('RU')
    args.append('-webserver')
    args.append(GARENA_WEBSERVER)

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

