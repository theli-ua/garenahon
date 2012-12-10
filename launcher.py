#!/usr/bin/env python
import os,sys,stat
import socket,struct,threading,subprocess
import zipfile
import select
from hashlib import sha1
from platform import system

abspath = ''
WEBSERVER_PORT = 8123
masterserver_international = 'masterserver.hon.s2games.com'
USER_AGENT = "S2 Games/Heroes of Newerth/2.0.29.1/lac/x86-biarch"
CURRENT_REGION = None
REGIONAL_OS = None

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
'ui/scripts/regions.lua',
]
latest_version = None
garena_token = ''
DEBUG = False

try:
    #3.x
    from urllib.request import Request
    from urllib.request import urlopen
    from urllib.parse   import urlencode
    from urllib.parse   import quote
    import urllib.parse as urlparse
    from http.client    import HTTPConnection
    from queue          import Queue
    from http.server    import BaseHTTPRequestHandler, HTTPServer
except:
    #2.x
    from urllib2        import Request
    from urllib2        import urlopen
    from urllib         import urlencode
    from urllib         import quote
    import urlparse
    from httplib        import HTTPConnection
    from Queue          import Queue
    from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer

try:
    parse_qs = urlparse.parse_qs
except:
    import cgi
    parse_qs = cgi.parse_qs

try:
    unicode = unicode
except NameError:
    # 'unicode' is undefined, must be Python 3
    str = str
    unicode = str
    bytes = bytes
    basestring = (str,bytes)
else:
    # 'unicode' exists, must be Python 2
    str = str
    unicode = unicode
    bytes = str
    basestring = basestring

def debug(*args):
    if DEBUG:
        print(args)

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
            if isinstance(obj, (int, float, bool)):
                return 'i:%i;' % obj
            if isinstance(obj, basestring):
                if unicode != str and isinstance(obj, unicode):
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
            if isinstance(obj, (int)):
                return 'i:%s;' % obj
            if isinstance(obj, float):
                return 'd:%s;' % obj
            if isinstance(obj, basestring):
                if unicode != str and isinstance(obj, unicode):
                    obj = obj.encode(charset, errors)
                return 's:%i:"%s";' % (len(obj), obj)
            if isinstance(obj, (list, tuple, dict)):
                out = []
                if isinstance(obj, dict):
                    try:
                        iterable = obj.iteritems()
                    except:
                        iterable = obj.items()
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

def getVerInfo(os,arch,masterserver,version = None, repair = False, current_version = None):
    details = {'version' : '0.0.0.0', 'os' : os ,'arch' : arch}
    if current_version is not None:
        details['current_version'] = current_version
    if version is not None:
        details['version'] = version
    if repair:
        details['repair'] = 1
    else:
        details['update'] = 1

    details = urlencode(details).encode('utf8')
    try:
        url = Request('http://{0}/patcher/patcher.php'.format(masterserver),details)
    except:
        url = Request('http://%s/patcher/patcher.php' % masterserver,details)

    url.add_header("User-Agent",USER_AGENT)
    data = urlopen(url).read().decode("utf8", 'ignore') 
    debug('Info from patchserver:')
    debug(data)
    d = unserialize(data)
    return d

def get_garena_token(user,password):
    debug('Trying to get garena token','user:',user)
    PORT = 8005
    #try:
        #ip_region = urlopen('http://75.126.149.34:6008/').read()
    #except:
        #debug(sys.exc_type,sys.exc_value)
        #debug(sys.exc_traceback)
        #debug(sys.exc_info())
        #ip_region = 'RU'.encode('utf8')
    ip_region = 'XX'.encode('utf8')
    debug('ip_region',ip_region)

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((GARENA_AUTH_SERVER, PORT))

    user = user.encode('utf8')
    password = password.encode('utf8')

    data = struct.pack('<IHHB16s33s5s',0x3b,0x0101,0x80,0,user,password,ip_region)
    s.send(data)
    data = s.recv(42)
    debug('Data from garena server: ',data)
    s.close()
    parsed = struct.unpack('<IB32sBI',data)
    return parsed[2]
    

def forward(path,query):
    debug('Forward request',path,query)
    details = urlencode(query,True).encode('utf8')
    try:
        url = Request('http://{0}{1}'.format(GARENA_MASTERSERVER, path),details)
    except:
        url = Request('http://%s%s' % (GARENA_MASTERSERVER, path),details)
    url.add_header("User-Agent",USER_AGENT)
    data = urlopen(url).read()
    debug('Data from masterserver: ',data)
    return data

class MyHTTPServer(HTTPServer):
    def __init__(self, params, handler):
        HTTPServer.__init__(self,params,handler)
        self.__is_shut_down = threading.Event()
        self.__serving = False
        self.requests = []

    def serve_forever(self, poll_interval=0.5):
        #hasattr(BaseHTTPServer.HTTPServer, '_handle_request_noblock'):
        if sys.hexversion >= 0x020600f0:
            HTTPServer.serve_forever(self, poll_interval) # 2.6
        else:
            self._serve_forever(poll_interval) # 2.5
    def _serve_forever(self, poll_interval=0.5):
        """Handle one request at a time until shutdown.

        Polls for shutdown every poll_interval seconds. Ignores
        self.timeout. If you need to do periodic tasks, do them in
        another thread.
        """
        self.__serving = True
        self.__is_shut_down.clear()
        while self.__serving:
            # XXX: Consider using another file descriptor or
            # connecting to the socket to wake this up instead of
            # polling. Polling reduces our responsiveness to a
            # shutdown request and wastes cpu at all other times.
            r, w, e = select.select([self], [], [], poll_interval)
            if r:
                self.handle_request()
        self.__is_shut_down.set()
    def shutdown(self):
        for r in self.requests: 
            try:
                r.shutdown(socket.SHUT_RDWR)
                r.close()
            except Exception:
                pass
        if hasattr(HTTPServer, 'shutdown'):
            HTTPServer.shutdown(self)
        else:
            self.__serving = False
            self.__is_shut_down.wait()
    def finish_request(self, request, client_address):
        self.requests.append(request)
        HTTPServer.finish_request(self, request, client_address)
        self.requests.remove(request)

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
        global latest_version
        global GARENA_AUTH_SERVER
        if True:
            self.send_response(200)
            self.end_headers()

            varLen = int(self.headers['Content-Length'])
            postVars = self.rfile.read(varLen).decode('utf8')
            query = parse_qs(postVars)
            if self.path == '/patcher/patcher.php':
                latest_version['current_version'] = query['current_version'][0]
                data = dumps(latest_version)
                try:
                    self.wfile.write(data)
                except:
                    self.wfile.write(bytes(data,'UTF-8'))
                return
            elif 'f' in query and GARENA_AUTH_SERVER is not None \
                    and (query['f'][0] == 'auth' or query['f'][0] == ['auth']):
                try:
                    if isinstance(query['password'], list):
                        query['password'] = query['password'][0]
                        query['login'] = query['login'][0]
                    garena_token = get_garena_token(query['login'],query['password'])
                    query = {'f':'token_auth','token' : garena_token }
                    #s:11:"garena_auth"
                    data = forward(self.path,query)
                    try:
                        data = data.replace('s:11:"garena_auth"','s:4:"auth"')
                    except:
                        data = data.decode('utf-8').replace('s:11:"garena_auth"','s:4:"auth"')
                    try:
                        self.wfile.write(data)
                    except:
                        self.wfile.write(bytes(data,'UTF-8'))
                    return
                except:
                    debug(sys.exc_type,sys.exc_value)
                    debug(sys.exc_traceback)
                    debug(sys.exc_info())
                    try:
                        debug(sys.exc_type,sys.exc_value)
                        debug(sys.exc_traceback)
                        debug(sys.exc_info())
                    except:
                        debug('exception during garena auth request')
                    data = 'a:2:{i:0;b:0;s:4:"auth";s:29:"Invalid Nickname or Password.";}'
                    try:
                        self.wfile.write(data)
                    except:
                        self.wfile.write(bytes(data,'UTF-8'))
                    return
            elif 'f' in query and query['f'][0] == 'garena_register':
                query['token'] = garena_token
            self.wfile.write(forward(self.path,query));
        
def clean_patches(path):
    if os.path.exists(path):
        os.unlink(path)

def patch_matchmaking(path):
    global CURRENT_REGION
    dpath = os.path.dirname(path)
    if not os.path.exists(dpath):
        os.makedirs(dpath)
    res = zipfile.ZipFile('game/resources0.s2z','r')
    to = zipfile.ZipFile(path,'w')
    patch_login1 = False
    patch_login2 = False
    for f in interface_patch_files:
        debug('Trying to patch file ',f)
        out = []
        try:
            mm = res.read(f).decode('utf8').splitlines()
        except:
            debug(sys.exc_type,sys.exc_value)
            debug(sys.exc_traceback)
            debug(sys.exc_info())
            continue

        if CURRENT_REGION == 'lat':
            for line in mm:
                if line.find('ssl="true"') != -1:
                    out.append(line.replace('ssl="true"','ssl="false"'))
                    out.append(line)
                elif line.find('region_latinamerica') != -1:
                    out.append(line.replace('region_latinamerica','_theli_region_latinamerica'))
                else:
                    out.append(line)
        else:
            for line in mm:
                if line.find('Login Options') != -1 or line.find('Login Input Box') != -1 \
                        or line.find('name="main_login_user"') != -1:
                    patch_login1 = True
                elif line.find('Garena NO direct start warning') != -1 or line.find('iris.tga') != -1:
                    patch_login2 = True
                if line.find('cl_GarenaEnable') != -1:
                    out.append(line.replace('cl_GarenaEnable','_theli_GarenaEnable'))
                elif line.find('region_garena') != -1:
                    out.append(line.replace('region_garena','_theli_region_garena'))
                elif line.find('ssl="true"') != -1:
                    out.append(line.replace('ssl="true"','ssl="false"'))
                elif line.find("['loginSytem'] = false") != -1:
                    out.append(line.replace("['loginSytem'] = false","['loginSytem'] = true"))
                elif line.find('regions.lua') != -1:
                    out.append('<panel color="invisible" noclick="true" name="theliLoginStatusHelper" />')
                    out.append(line)
                else:
                    out.append(line)
            if f == 'ui/scripts/regions.lua':
                out.append("""

    local function theliLoginStatus(self, accountStatus, statusDescription, isLoggedIn, pwordExpired, isLoggedInChanged, updaterStatus)
        -- println('^cLoginStatus - accountStatus: ' .. tostring(accountStatus) .. ' | statusDescription: ' .. tostring(statusDescription)  .. ' | isLoggedIn: ' .. tostring(isLoggedIn)  .. ' | pwordExpired: ' .. tostring(pwordExpired)  .. ' | isLoggedInChanged: ' .. tostring(isLoggedInChanged)  ..  ' | updaterStatus: ' .. tostring(updaterStatus) )
        if (statusDescription == "#GA002000") then
            Trigger('GarenaClientLoginResponse', statusDescription)
        -- else
        --    Trigger('GarenaClientLoginResponse', param0)
        end
    end
    interface:GetWidget("theliLoginStatusHelper"):RegisterWatch('LoginStatus', theliLoginStatus)

    """)
            to.writestr(f,'\n'.join(out))
    res.close()
    to.close()

def find_latest_version():
    global latest_version, REGIONAL_OS
    wgc_version = getVerInfo(REGIONAL_OS,'i686',GARENA_MASTERSERVER)['version']
    debug('Regional version: ',wgc_version)
    wgc_version = wgc_version.split('.')
    latest_version = getVerInfo(HOST_OS,HOST_ARCH,masterserver_international) 
    debug('International version info: ',latest_version)
    baseurl = latest_version[0]['url'] + HOST_OS + '/' + HOST_ARCH + '/'
    baseurl2 = latest_version[0]['url2'] + HOST_OS + '/' + HOST_ARCH + '/'
    patchurl_1 = latest_version[0]['url']
    patchurl_2 = latest_version[0]['url2']
    #just in case there was non-windows hotfix
    wgc_version[-1] = str(int(wgc_version[-1]) + 2)
    manifest = None
    while int(wgc_version[-1]) >= 0:
        if wgc_version[-1] == '0':
            ver = '.'.join(wgc_version[:-1])
        else:
            ver = '.'.join(wgc_version)
        debug('Trying version: ',ver)
        try:
            url1 = '{0}/{1}/manifest.xml.zip'.format(baseurl,ver)
            url2 = '{0}/{1}/manifest.xml.zip'.format(baseurl2,ver)
        except:
            url1 = '%s/%s/manifest.xml.zip' % (baseurl,ver)
            url2 = '%s/%s/manifest.xml.zip' % (baseurl2,ver)

        try:
            manifest = urlopen(url1)
            current_version = '.'.join(wgc_version)
            break
        except:
            pass

        try:
            manifest = urlopen(url2)
            current_version = '.'.join(wgc_version)
            break
        except:
            pass

        wgc_version[-1] = str(int(wgc_version[-1]) - 1)

    try:
        print ("Found latest appropriate version: {0}".format(current_version))
    except:
        print ("Found latest appropriate version: %s" % (current_version))
    if current_version != latest_version['version']:
        manifest_data = manifest.read()
        latest_version[0]['latest_manifest_checksum'] = sha1(manifest_data).hexdigest()
        latest_version[0]['latest_manifest_size'] = str(len(manifest_data))
        latest_version['version'] = current_version
        latest_version[0]['version'] = current_version
        latest_version[0]['latest_version'] = current_version

def main():
    global WEBSERVER_PORT,abspath,GARENA_MASTERSERVER,GARENA_WEBSERVER,\
            GARENA_AUTH_SERVER,DEBUG,CURRENT_REGION,REGIONAL_OS
    if len(sys.argv) < 2 or sys.argv[1] not in ['cis','sea','lat']:
        print('You need to specify region on command line, like')
        print('./launcher.py cis')
        print('or')
        print('./launcher.py sea')
        print('or')
        print('./launcher.py lat')
        sys.exit(1)
    if sys.argv[1] == 'cis':
        GARENA_WEBSERVER = 'cis.heroesofnewerth.com'
        GARENA_AUTH_SERVER = 'Honsng_cs.mmoauth.garena.com'
        GARENA_MASTERSERVER = 'masterserver.cis.s2games.com'
        REGIONAL_OS = 'wgc'
    elif sys.argv[1] == 'sea':
        GARENA_WEBSERVER = 'garena.heroesofnewerth.com'
        GARENA_AUTH_SERVER = 'hon.auth.garenanow.com'
        GARENA_MASTERSERVER = 'masterserver.garena.s2games.com'
        REGIONAL_OS = 'wgc'
    elif sys.argv[1] == 'lat':
        GARENA_WEBSERVER = 'lat.heroesofnewerth.com'
        GARENA_AUTH_SERVER = None
        GARENA_MASTERSERVER = 'masterserver.lat.s2games.com'
        REGIONAL_OS = 'wbc'

    CURRENT_REGION = sys.argv[1]

    if len(sys.argv) > 2 and sys.argv[2] == '-d':
        DEBUG = True

    abspath = os.path.abspath(__file__)
    dname = os.path.dirname(abspath)
    os.chdir(dname)
    
    print('checking for HoN updates')
    find_latest_version()

    mod_path = os.path.expanduser(MOD_PATH)
    clean_patches(mod_path)
    started = False
    while not started:
        try:
            server = MyHTTPServer(('', WEBSERVER_PORT), MyHandler)
            started = True
        except:
            try:
                print("Local port {0} is busy, trying {1}".format(WEBSERVER_PORT,WEBSERVER_PORT + 1))
            except:
                print("Local port %s is busy, trying %s" % (WEBSERVER_PORT,WEBSERVER_PORT + 1))
            WEBSERVER_PORT += 1
    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.daemon = True
    server_thread.start()
    print('started httpserver...')
    print('starging hon')
    args = [HON_BINARY]
    args.append('-masterserver')
    try:
        args.append('127.0.0.1:{0}'.format(WEBSERVER_PORT))
    except:
        args.append('127.0.0.1:%d' % (WEBSERVER_PORT))
    args.append('-region')
    if CURRENT_REGION == 'cis':
        args.append('ru')
    elif CURRENT_REGION == 'sea':
        args.append('sea')
    elif CURRENT_REGION == 'lat':
        args.append('lat')

    args.append('-webserver')
    args.append(GARENA_WEBSERVER)

    startup = 'set chat_serverPortOverride 11033;'
    if CURRENT_REGION == 'lat':
        startup += 'set _theli_region_latinamerica true;'
    else:
        startup += ' set _theli_GarenaEnable true;'
        startup += ' set _theli_region_garena true;'
    startup += ' set login_useSRP false;'
    args.append('-execute')
    try:
        args.append('"{0}"'.format(startup))
    except:
        args.append('"%s"' % startup )

    args.append('-config')
    args.append(CURRENT_REGION)

    print ('Patching interface')
    patch_matchmaking(mod_path)
    
    try:
        p = subprocess.Popen(args)
    except (OSError, ):
        err = sys.exc_info()[1]
        if err.errno == 13:
            os.chmod(HON_BINARY,stat.S_IRWXU | stat.S_IROTH | stat.S_IXOTH | stat.S_IRGRP | stat.S_IXGRP)
            p = subprocess.Popen(args)
    p.wait()
    print('hon exited, stopping masterserver and cleaning up')
    clean_patches(mod_path)    
    server.shutdown()

if __name__ == '__main__':
    main()
