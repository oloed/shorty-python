"""
     _                _
 ___| |__   ___  _ __| |_ _   _ 
/ __| '_ \ / _ \| '__| __| | | |
\__ \ | | | (_) | |  | |_| |_| |
|___/_| |_|\___/|_|   \__|\__, |
                           __/ |
                          |___/ 

Access many URL shortening services from one library.

Python 2.4+
Versions before 2.6 require simplejson.

http://gitorious.org/shorty

MIT License
Copyright (c) 2009 Joshua Roesslein <jroesslein at gmail.com>

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
"""
## !!! This file is machine generated !! ##

from urllib2 import urlopen, Request, URLError, HTTPError, HTTPRedirectHandler, build_opener
from urllib import urlencode, quote
from urlparse import urlparse
from random import randint
import base64

try:
    import json
except:
    import simplejson as json


class ShortyError(Exception):

    def __init__(self, reason):
        self.reason = str(reason)

    def __str__(self):
        return repr(self.reason)

"""Do a http request"""
def request(url, parameters=None, username_pass=None, post_data=None):

    # build url + parameters
    if parameters:
        url_params = '%s?%s' % (url, urlencode(parameters))
    else:
        url_params = url

    # if username and pass supplied, build basic auth header
    headers = {}
    if username_pass:
        headers['Authorization'] = 'Basic %s' % base64.b64encode('%s:%s' % username_pass)

    # send request
    try:
        req = Request(url_params, headers=headers)
        if post_data:
            req.add_data(post_data)
        return urlopen(req)
    except URLError, e:
        raise ShortyError(e)

def get_redirect(url):

    class StopRedirectHandler(HTTPRedirectHandler):
        def http_error_301(self, req, fp, code, smg, headers):
            return None
        def http_error_302(self, req, fp, code, smg, headers):
            return None
    o = build_opener(StopRedirectHandler())
    try:
        o.open(url)
    except HTTPError, e:
        if e.code == 301 or e.code == 302:
            return e.headers['Location']
        else:
            raise ShortyError(e)
    except URLError, e:
        raise ShortyError(e)
    return None

"""Base interface that all services implement."""
class Service(object):

    def shrink(self, bigurl):
        """Take a big url and make it smaller"""
        return None

    def expand(self, tinyurl):
        """Take a tiny url and make it bigger"""
        return get_redirect(tinyurl)

"""
Shrink the given url for the specified service domain.
Returns the tiny url OR None if service not supported.
"""
def shrink(service_domain, bigurl, *args, **kargs):

    s = services.get(service_domain)
    if not s:
        return None
    return s.shrink(bigurl, *args, **kargs)
    
"""
Expand tiny url into its full url.
Returns long url if successful or None if failure.
"""
def expand(tinyurl):

    turl = urlparse(tinyurl)
    domain = turl.netloc.lower()
    if domain.startswith('www.'):
        # strip off www. if present
        domain = domain[4:]
    s = services.get(domain)
    if not s:
        return get_redirect(tinyurl)
    return s.expand(tinyurl)

# urlborg
class Urlborg(Service):

    def __init__(self, apikey=None):
        self.apikey = apikey

    def shrink(self, bigurl):
        if not self.apikey:
            raise ShortyError('Must set an apikey')
        url = 'http://urlborg.com/api/%s/create/%s' % (self.apikey, quote(bigurl))
        resp = request(url)
        turl = resp.read()
        if not turl.startswith('http://'):
            raise ShortyError(turl)
        return turl

    def expand(self, tinyurl):
        if not self.apikey:
            return get_redirect(get_redirect(tinyurl))
        turl = urlparse(tinyurl)
        url = 'http://urlborg.com/api/%s/url/info.json%s' % (self.apikey, turl.path)
        resp = request(url)
        jdata = json.loads(resp.read())
        if jdata.has_key('error'):
            raise ShortyError('Invalid tiny url or apikey')
        return str(jdata['o_url'])

urlborg = Urlborg()

# fwd4me
class Fwd4me(Service):

    ecodes = {
        '1': 'Invalid long url',
        '2': 'Invalid api key',
        '3': 'Account suspended or revoked',
        '4': 'Long url is black listed',
        '5': 'Internal system error'
    }

    def shrink(self, bigurl):
        resp = request('http://api.fwd4.me/', {'url': bigurl})
        data = resp.read()
        if data.startswith('ERROR:'):
            ecode = data.lstrip('ERROR:')
            raise ShortyError(Fwd4me.ecodes.get(ecode, 'Unkown error'))
        else:
            return data

fwd4me = Fwd4me()

# isgd
class Isgd(Service):

    def shrink(self, bigurl):
        resp = request('http://is.gd/api.php', {'longurl': bigurl})
        turl = resp.read()
        if turl.startswith('Error:'):
            raise ShortyError(turl)
        return turl

isgd = Isgd()

# cligs
class Cligs(Service):

    def __init__(self, apikey=None, appid=None):
        self.apikey = apikey
        self.appid = appid

    def shrink(self, bigurl, title=None):
        parameters = {'url': bigurl}
        if title:
            parameters['title'] = title
        if self.apikey:
            parameters['key'] = self.apikey
        if self.appid:
            parameters['appid'] = self.appid
        resp = request('http://cli.gs/api/v1/cligs/create', parameters)
        return resp.read()

    def expand(self, tinyurl):
        # TODO: debug this some more, not working properly
        '''resp = request('http://cli.gs/api/v1/cligs/expand', {'clig': tinyurl})
        return resp.read()'''
        return get_redirect(tinyurl)

cligs = Cligs()

# fongs
class Fongs(Service):

    def shrink(self, bigurl, tag=None):
        parameters = {'url': bigurl}
        if tag:
            parameters['linkname'] = tag
        resp = request('http://fon.gs/create.php', parameters)
        data = resp.read()
        if data.startswith('OK:'):
            return data.lstrip('OK: ')
        elif data.startswith('MODIFIED:'):
            return data.lstrip('MODIFIED: ')
        else:
            raise ShortyError(data)

    # check if the given tag is taken
    # returns true if available false if taken
    def check(self, tag):
        resp = request('http://fon.gs/check.php', {'linkname': tag})
        data = resp.read()
        if data.startswith('AVAILABLE'):
            return True
        elif data.startswith('TAKEN'):
            return False
        else:
            raise ShortyError(data)

    def expand(self, tinyurl):
        if tinyurl[-1] != '/':
            turl = tinyurl + '/'
        else:
            turl = tinyurl
        return Service.expand(self, turl)

fongs = Fongs()

# tweetburner
class Tweetburner(Service):

    def shrink(self, bigurl):
        resp = request('http://tweetburner.com/links', post_data='link[url]=%s' % bigurl)
        return resp.read()

tweetburner = Tweetburner()

# bitly
class Bitly(Service):

    version = '2.0.1'

    def __init__(self, login=None, apikey=None, password=None):
        self.login = login
        self.apikey = apikey
        self.password = password

    def _setup(self):
        parameters = {'version': self.version}
        if self.apikey:
            parameters['apiKey'] = self.apikey
            parameters['login'] = self.login
            username_pass = None
        elif self.password:
            username_pass = (self.login, self.password)
        else:
            raise ShortyError('Must set an apikey or password')
        return parameters, username_pass

    def shrink(self, bigurl):
        if not self.login:
            raise ShortyError('Must set a login')
        parameters, username_pass = self._setup()
        parameters['longUrl'] = bigurl
        resp = request('http://api.bit.ly/shorten', parameters, username_pass)
        jdata = json.loads(resp.read())
        if jdata['errorCode'] != 0:
            raise ShortyError(jdata['errorMessage'])
        return str(jdata['results'][bigurl]['shortUrl'])

    def expand(self, tinyurl):
        if not self.login:
            return get_redirect(tinyurl)
        parameters, username_pass = self._setup()
        parameters['shortUrl'] = tinyurl
        resp = request('http://api.bit.ly/expand', parameters, username_pass)
        jdata = json.loads(resp.read())
        if jdata['errorCode'] != 0:
            raise ShortyError(jdata['errorMessage'])
        return str(jdata['results'].values()[0]['longUrl'])

bitly = Bitly()

# trim
class Trim(Service):

    def __init__(self, apikey=None, username_pass=None):
        self.apikey = apikey
        self.username_pass = username_pass

    def shrink(self, bigurl, custom=None, searchtags=None, privacycode=None,
                newtrim=False, sandbox=False):
        parameters = {}
        parameters['url'] = bigurl
        if custom:
            parameters['custom'] = custom
        if searchtags:
            parameters['searchtags'] = searchtags
        if privacycode:
            parameters['privacycode'] = privacycode
        if newtrim:
            parameters['newtrim'] = '1'
        if sandbox:
            parameters['sandbox'] = '1'
        if self.apikey:
            parameters['api_key'] = self.apikey
        resp = request('http://api.tr.im/api/trim_url.json', parameters, self.username_pass)
        jdata = json.loads(resp.read())
        self.status = (int(jdata['status']['code']), str(jdata['status']['message']))
        if not 200 <= self.status[0] < 300:
            raise ShortyError(self.status[1])
        self.trimpath = str(jdata['trimpath'])
        self.reference = str(jdata['reference'])
        self.destination = str(jdata['destination'])
        self.domain = str(jdata['domain'])
        return str(jdata['url'])

    def expand(self, tinyurl):
        turl = urlparse(tinyurl)
        if turl.netloc != 'tr.im' and turl.netloc != 'www.tr.im':
            raise ShortyError('Not a valid tr.im url')
        parameters = {'trimpath': turl.path.strip('/')}
        if self.apikey:
            parameters['api_key'] = self.apikey
        resp = request('http://api.tr.im/api/trim_destination.json', parameters)
        jdata = json.loads(resp.read())
        self.status = (int(jdata['status']['code']), str(jdata['status']['message']))
        if not 200 <= self.status[0] < 300:
            raise ShortyError(self.status[1])
        return str(jdata['destination'])

trim = Trim()

# agd
class Agd(Service):

    def shrink(self, bigurl, tag=None, password=None, expires=None):
        post_param = {'url': bigurl}
        if tag:
            post_param['tag'] = tag
        if password:
            post_param['pass'] = password
        if expires:
            post_param['validTill'] = expires
        resp = request('http://a.gd/?module=ShortURL&file=Add&mode=API',
                        post_data = urlencode(post_param))
        url = resp.read()
        if url.startswith('http://'):
            return url
        else:
            raise ShortyError(url[url.find('>')+1:url.rfind('<')])

agd = Agd()

# digg
class Digg(Service):

    def __init__(self, appkey=None):
        self.appkey = appkey
        self.itemid = None
        self.view_count = None

    def shrink(self, bigurl):
        if not self.appkey:
            raise ShortyError('Must set an appkey')
        resp = request('http://services.digg.com/url/short/create',
            {'url': bigurl, 'appkey': self.appkey, 'type': 'json'})
        jdata = json.loads(resp.read())['shorturls'][0]
        self.itemid = jdata['itemid']
        self.view_count = jdata['view_count']
        return str(jdata['short_url'])

    def expand(self, tinyurl):
        if self.appkey:
            turl = urlparse(tinyurl)
            if turl.netloc != 'digg.com' and turl.netloc != 'www.digg.com':
                raise ShortyError('Not a valid digg url')
            resp = request('http://services.digg.com/url/short/%s' % quote(
                            turl.path.strip('/')),
                            {'appkey': self.appkey, 'type': 'json'})
            jdata = json.loads(resp.read())['shorturls'][0]
            self.itemid = jdata['itemid']
            self.view_count = jdata['view_count']
            return str(jdata['link'])
        else:
            self.itemid = None
            self.view_count = None
            return get_redirect(tinyurl)

digg = Digg()

# chilpit
class Chilpit(Service):

    def shrink(self, bigurl):
        resp = request('http://chilp.it/api.php', {'url': bigurl})
        url = resp.read()
        if url.startswith('http://'):
            return url
        else:
            raise ShortyError(url)

    def expand(self, tinyurl):
        turl = urlparse(tinyurl)
        if turl.netloc.lstrip('www.') != 'chilp.it':
            raise ShortyError('Not a chilp.it url')
        resp = request('http://p.chilp.it/api.php?' + turl.path.strip('/'))
        url = resp.read()
        if url.startswith('http://'):
            return url
        else:
            raise ShortyError(url)

    # get click stats of the tinyurl
    def stats(self, tinyurl):
        turl = urlparse(tinyurl)
        if turl.netloc.lstrip('www.') != 'chilp.it':
            raise ShortyError('Not a chilp.it url')
        resp = request('http://s.chilp.it/api.php?' + turl.query)
        hit_count = resp.read()
        try:
            return int(hit_count)
        except:
            raise ShortyError('Url not found or invalid')

chilpit = Chilpit()

# sandbox
class Sandbox(Service):

    def __init__(self, length=4, letters='abcdefghijklmnopqrstuvwxyz'):
        self.urls = {}
        self.letters = letters
        self.length = length
        self.base = len(letters) - 1

    def shrink(self, bigurl):
        # generate the tiny path
        tpath = ''
        while True:
            for i in range(self.length):
                tpath += self.letters[randint(0, self.base)]
            if self.urls.has_key(tpath):
                # tpath already in use, regen another
                tpath = ''
            else:
                break

        # store url and return tiny link
        self.urls[tpath] = bigurl
        return 'http://sandbox.com/' + tpath

    def expand(self, tinyurl):
        # lookup big url and return
        turl = urlparse(tinyurl)
        if turl.netloc != 'sandbox.com':
            raise ShortyError('Not a sandbox url')
        return self.urls.get(turl.path.strip('/'))

sandbox = Sandbox()

# tinyurl
class Tinyurl(Service):

    def shrink(self, bigurl):
        resp = request('http://tinyurl.com/api-create.php', {'url': bigurl})
        return resp.read()

tinyurl = Tinyurl()

# bukme
class Bukme(Service):

    def _process(self, resp):
        # bukme returns some markup after the url, so chop it off
        url = resp[:resp.find('<')]
        if url.startswith('http://'):
            return url
        else:
            raise ShortyError(url)

    def shrink(self, bigurl, tag=None):
        parameters = {'url': bigurl}
        if tag:
            parameters['buk'] = tag
        resp = request('http://buk.me/api.php', parameters)
        return self._process(resp.read())

    def expand(self, tinyurl):
        resp = request('http://buk.me/api.php', {'rev': tinyurl})
        return self._process(resp.read())

bukme = Bukme()

services = {
    'a.gd': agd,
    'chilp.it': chilpit,
    'digg.com': digg,
    'tweetburner.com': tweetburner,
    'buk.me': bukme,
    'twurl.nl': tweetburner,
    'tr.im': trim,
    'cli.gs': cligs,
    'urlborg.com': urlborg,
    'is.gd': isgd,
    'fon.gs': fongs,
    'ub0.cc': urlborg,
    'tinyurl.com': tinyurl,
    'bit.ly': bitly,
    'fwd4.me': fwd4me,
    'sandbox.com': sandbox,
}
