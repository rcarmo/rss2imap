#!/usr/bin/python
"""rss2email: get RSS feeds emailed to you
http://rss2email.infogami.com

Usage:
  new [emailaddress] (create new feedfile)
  email newemailaddress (update default email)
  run [--no-send] [num],
  add feedurl [emailaddress] [folder]
  list
  reset
  delete n
  pause n
  unpause n
  opmlexport
  opmlimport filename
"""
__version__ = "2.71-rcarmo"
__author__ = "Lindsey Smith (lindsey@allthingsrss.com)"
__copyright__ = "(C) 2004 Aaron Swartz. GNU GPL 2 or 3."
___contributors__ = ["Dean Jackson", "Brian Lalor", "Joey Hess", 
                     "Matej Cepl", "Martin 'Joey' Schulze", 
                     "Marcel Ackermann (http://www.DreamFlasher.de)", 
                     "Rui Carmo (http://the.taoofmac.com)",
                     "Lindsey Smith (maintainer)", "Erik Hetzner",
                     "Aaron Swartz (original author)" ]

### Import Modules ###

import os, sys, re, time
import socket, urllib2, urlparse, imaplib, smtplib
urllib2.install_opener(urllib2.build_opener())
import string, csv, StringIO
import hashlib, base64
import traceback, types
from types import *
import threading, subprocess
import cPickle as pickle

from email.MIMEText import MIMEText
from email.Header import Header
from email.Utils import parseaddr, formataddr
             
import feedparser
feedparser.USER_AGENT = "rss2email/"+__version__+ " +https://github.com/rcarmo/rss2email"

import html2text as h2t
from summarize import summarize

DEFAULT_IMAP_FOLDER = "INBOX"

# Read options from config file if present.
sys.path.insert(0,".")
try:
    from config import *
except:
    pass

h2t.UNICODE_SNOB = UNICODE_SNOB
h2t.LINKS_EACH_PARAGRAPH = LINKS_EACH_PARAGRAPH
h2t.BODY_WIDTH = BODY_WIDTH
html2text = h2t.html2text


def send(sender, recipient, subject, body, contenttype, datetime, extraheaders=None, mailserver=None, folder=None):
    """Send an email.
    
    All arguments should be Unicode strings (plain ASCII works as well).
    
    Only the real name part of sender and recipient addresses may contain
    non-ASCII characters.
    
    The email will be properly MIME encoded and delivered though SMTP to
    localhost port 25.  This is easy to change if you want something different.
    
    The charset of the email will be the first one out of the list
    that can represent all the characters occurring in the email.
    """

    # Header class is smart enough to try US-ASCII, then the charset we
    # provide, then fall back to UTF-8.
    header_charset = 'ISO-8859-1'
    
    # We must choose the body charset manually
    for body_charset in CHARSET_LIST:
        try:
            body.encode(body_charset)
        except (UnicodeError, LookupError):
            pass
        else:
            break

    # Split real name (which is optional) and email address parts
    sender_name, sender_addr = parseaddr(sender)
    recipient_name, recipient_addr = parseaddr(recipient)
    
    # We must always pass Unicode strings to Header, otherwise it will
    # use RFC 2047 encoding even on plain ASCII strings.
    sender_name = str(Header(unicode(sender_name), header_charset))
    recipient_name = str(Header(unicode(recipient_name), header_charset))
    
    # Make sure email addresses do not contain non-ASCII characters
    sender_addr = sender_addr.encode('ascii')
    recipient_addr = recipient_addr.encode('ascii')
    
    # Create the message ('plain' stands for Content-Type: text/plain)
    msg = MIMEText(body.encode(body_charset), contenttype, body_charset)
    if IMAP_OVERRIDE_TO:
        msg['To'] = IMAP_OVERRIDE_TO
    else:
        msg['To'] = formataddr((recipient_name, recipient_addr))
    msg['Subject'] = Header(unicode(subject), header_charset)
    for hdr in extraheaders.keys():
        try:
            msg[hdr] = Header(unicode(extraheaders[hdr], header_charset))
        except:
            msg[hdr] = Header(extraheaders[hdr])
        
    fromhdr = formataddr((sender_name, sender_addr))
    if IMAP_MUNGE_FROM:
        msg['From'] = extraheaders['X-MUNGED-FROM']
    else:
        msg['From'] = fromhdr

    msg_as_string = msg.as_string()

    if IMAP_SEND:
        if not mailserver:
            try:
                (host,port) = IMAP_SERVER.split(':',1)
            except ValueError:
                host = IMAP_SERVER
                port = 993 if IMAP_SSL else 143
            try:
                if IMAP_SSL:
                    mailserver = imaplib.IMAP4_SSL(host, port)
                else:
                    mailserver = imaplib.IMAP4(host, port)
                # speed up interactions on TCP connections using small packets
                mailserver.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                mailserver.login(IMAP_USER, IMAP_PASS)
            except KeyboardInterrupt:
                raise
            except Exception, e:
                print >>warn, ""
                print >>warn, ('Fatal error: could not connect to mail server "%s"' % IMAP_SERVER)
                print >>warn, ('Check your config.py file to confirm that IMAP_SERVER and other mail server settings are configured properly')
                if hasattr(e, 'reason'):
                    print >>warn, "Reason:", e.reason
                sys.exit(1)
        if not folder:
            folder = DEFAULT_IMAP_FOLDER
        #mailserver.debug = 4
        if mailserver.select(folder)[0] == 'NO':
            print >>warn, ("%s does not exist, creating" % folder)
            mailserver.create(folder)
            mailserver.subscribe(folder)
        mailserver.append(folder,'',imaplib.Time2Internaldate(datetime), msg_as_string)
        return mailserver

    elif SMTP_SEND:
        if not mailserver: 
            
            try:
                if SMTP_SSL:
                    mailserver = smtplib.SMTP_SSL()
                else:
                    mailserver = smtplib.SMTP()
                mailserver.connect(SMTP_SERVER)
            except KeyboardInterrupt:
                raise
            except Exception, e:
                print >>warn, ""
                print >>warn, ('Fatal error: could not connect to mail server "%s"' % SMTP_SERVER)
                print >>warn, ('Check your config.py file to confirm that SMTP_SERVER and other mail server settings are configured properly')
                if hasattr(e, 'reason'):
                    print >>warn, "Reason:", e.reason
                sys.exit(1)
                    
            if AUTHREQUIRED:
                try:
                    mailserver.ehlo()
                    if not SMTP_SSL: mailserver.starttls()
                    mailserver.ehlo()
                    mailserver.login(SMTP_USER, SMTP_PASS)
                except KeyboardInterrupt:
                    raise
                except Exception, e:
                    print >>warn, ""
                    print >>warn, ('Fatal error: could not authenticate with mail server "%s" as user "%s"' % (SMTP_SERVER, SMTP_USER))
                    print >>warn, ('Check your config.py file to confirm that SMTP_SERVER and other mail server settings are configured properly')
                    if hasattr(e, 'reason'):
                        print >>warn, "Reason:", e.reason
                    sys.exit(1)
                    
        mailserver.sendmail(sender, recipient, msg_as_string)
        return mailserver

    else:
        try:
            p = subprocess.Popen(["/usr/sbin/sendmail", recipient], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
            p.communicate(msg_as_string)
            status = p.returncode
            assert status != None, "just a sanity check"
            if status != 0:
                print >>warn, ""
                print >>warn, ('Fatal error: sendmail exited with code %s' % status)
                sys.exit(1)
        except:
            print '''Error attempting to send email via sendmail. Possibly you need to configure your config.py to use a SMTP server? Please refer to the rss2email documentation or website (http://rss2email.infogami.com) for complete documentation of config.py. The options below may suffice for configuring email:
# 1: Use SMTP_SERVER to send mail.
# 0: Call /usr/sbin/sendmail to send mail.
SMTP_SEND = 0

SMTP_SERVER = "smtp.yourisp.net:25"
AUTHREQUIRED = 0 # if you need to use SMTP AUTH set to 1
SMTP_USER = 'username'  # for SMTP AUTH, set SMTP username here
SMTP_PASS = 'password'  # for SMTP AUTH, set SMTP password here
'''
            sys.exit(1)
        return None


warn = sys.stderr
    
if QP_REQUIRED:
    print >>warn, "QP_REQUIRED has been deprecated in rss2email."


unix = 0
try:
    import fcntl
# A pox on SunOS file locking methods   
    if (sys.platform.find('sunos') == -1): 
        unix = 1
except:
    pass
        
socket_errors = []
for e in ['error', 'gaierror']:
    if hasattr(socket, e): socket_errors.append(getattr(socket, e))

### Utility Functions ###

import threading
class TimeoutError(Exception): pass

class InputError(Exception): pass

def timelimit(timeout, function):
#    def internal(function):
        def internal2(*args, **kw):
            """
            from http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/473878
            """
            class Calculator(threading.Thread):
                def __init__(self):
                    threading.Thread.__init__(self)
                    self.result = None
                    self.error = None
                
                def run(self):
                    try:
                        self.result = function(*args, **kw)
                    except:
                        self.error = sys.exc_info()
            
            c = Calculator()
            c.setDaemon(True) # don't hold up exiting
            c.start()
            c.join(timeout)
            if c.isAlive():
                raise TimeoutError
            if c.error:
                raise c.error[0], c.error[1]
            return c.result
        return internal2
#    return internal
    

def isstr(f): return isinstance(f, type('')) or isinstance(f, type(u''))
def ishtml(t): return type(t) is type(())
def contains(a,b): return a.find(b) != -1
def unu(s): # I / freakin' hate / that unicode
    if type(s) is types.UnicodeType: return s.encode('utf-8')
    else: return s

### Parsing Utilities ###

def getContent(entry, HTMLOK=0):
    """Select the best content from an entry, deHTMLizing if necessary.
    If raw HTML is best, an ('HTML', best) tuple is returned. """
    
    # How this works:
    #  * We have a bunch of potential contents. 
    #  * We go thru looking for our first choice. 
    #    (HTML or text, depending on HTMLOK)
    #  * If that doesn't work, we go thru looking for our second choice.
    #  * If that still doesn't work, we just take the first one.
    #
    # Possible future improvement:
    #  * Instead of just taking the first one
    #    pick the one in the "best" language.
    #  * HACK: hardcoded HTMLOK, should take a tuple of media types
    
    conts = entry.get('content', [])
    
    if entry.get('summary_detail', {}):
        conts += [entry.summary_detail]
    
    if conts:
        if HTMLOK:
            for c in conts:
                if contains(c.type, 'html'): return ('HTML', c.value)
    
        if not HTMLOK: # Only need to convert to text if HTML isn't OK
            for c in conts:
                if contains(c.type, 'html'):
                    return html2text(c.value)
        
        for c in conts:
            if c.type == 'text/plain': return c.value
    
        return conts[0].value   
    
    return ""

def getID(entry):
    """Get best ID from an entry."""
    if TRUST_GUID:
        if 'id' in entry and entry.id: 
            # Newer versions of feedparser could return a dictionary
            if type(entry.id) is DictType:
                return entry.id.values()[0]

            return entry.id

    content = getContent(entry)
    if content and content != "\n": return hashlib.sha1(unu(content)).hexdigest()
    if 'link' in entry: return entry.link
    if 'title' in entry: return hashlib.sha1(unu(entry.title)).hexdigest()

def getName(r, entry):
    """Get the best name."""

    if NO_FRIENDLY_NAME: return ''

    feed = r.feed
    if hasattr(r, "url") and r.url in OVERRIDE_FROM.keys():
        return OVERRIDE_FROM[r.url]
    
    name = feed.get('title', '')

    if 'name' in entry.get('author_detail', []): # normally {} but py2.1
        if entry.author_detail.name:
            if name: name += ": "
            det=entry.author_detail.name
            try:
                name +=  entry.author_detail.name
            except UnicodeDecodeError:
                name +=  unicode(entry.author_detail.name, 'utf-8')

    elif 'name' in feed.get('author_detail', []):
        if feed.author_detail.name:
            if name: name += ", "
            name += feed.author_detail.name
    
    return name


def getMungedFrom(r):
    """Generate a better From."""

    feed = r.feed
    if hasattr(r, "url") and r.url in OVERRIDE_FROM.keys():
        return OVERRIDE_FROM[r.url]
    
    name = feed.get('title', 'unknown').lower()
    pattern = re.compile('[\W_]+',re.UNICODE)
    re.sub(pattern, '', name)
    name = "%s <%s@%s>" % (feed.get('title','Unnamed Feed'), name.replace(' ','_'), urlparse.urlparse(r.url).netloc)
    return name


def validateEmail(email, planb):
    """Do a basic quality check on email address, but return planb if email doesn't appear to be well-formed"""
    email_parts = email.split('@')
    if len(email_parts) != 2:
        return planb
    return email
    
def getEmail(r, entry):
    """Get the best email_address. If the best guess isn't well-formed (something@somthing.com), use DEFAULT_FROM instead"""
    
    feed = r.feed
        
    if FORCE_FROM: return DEFAULT_FROM
    
    if hasattr(r, "url") and r.url in OVERRIDE_EMAIL.keys():
        return validateEmail(OVERRIDE_EMAIL[r.url], DEFAULT_FROM)
    
    if 'email' in entry.get('author_detail', []):
        return validateEmail(entry.author_detail.email, DEFAULT_FROM)
    
    if 'email' in feed.get('author_detail', []):
        return validateEmail(feed.author_detail.email, DEFAULT_FROM)
        
    if USE_PUBLISHER_EMAIL:
        if 'email' in feed.get('publisher_detail', []):
            return validateEmail(feed.publisher_detail.email, DEFAULT_FROM)
        
        if feed.get("errorreportsto", ''):
            return validateEmail(feed.errorreportsto, DEFAULT_FROM)
            
    if hasattr(r, "url") and r.url in DEFAULT_EMAIL.keys():
        return DEFAULT_EMAIL[r.url]
    return DEFAULT_FROM

### Simple Database of Feeds ###

class Feed:
    def __init__(self, url, to, folder=None):
        self.url, self.etag, self.modified, self.seen = url, None, None, {}
        self.active = True
        self.to = to
        self.folder = folder

def load(lock=1):
    if not os.path.exists(feedfile):
        print 'Feedfile "%s" does not exist.  If you\'re using r2e for the first time, you' % feedfile
        print "have to run 'r2e new' first."
        sys.exit(1)
    try:
        feedfileObject = open(feedfile, 'r')
    except IOError, e:
        print "Feedfile could not be opened: %s" % e
        sys.exit(1)
    feeds = pickle.load(feedfileObject)
    
    if lock:
        locktype = 0
        if unix:
            locktype = fcntl.LOCK_EX
            fcntl.flock(feedfileObject.fileno(), locktype)
        #HACK: to deal with lock caching
        feedfileObject = open(feedfile, 'r')
        feeds = pickle.load(feedfileObject)
        if unix: 
            fcntl.flock(feedfileObject.fileno(), locktype)
    if feeds: 
        for feed in feeds[1:]:
            if not hasattr(feed, 'active'): 
                feed.active = True
        
    return feeds, feedfileObject

def unlock(feeds, feedfileObject):
    if not unix: 
        pickle.dump(feeds, open(feedfile, 'w'))
    else:   
        fd = open(feedfile+'.tmp', 'w')
        pickle.dump(feeds, fd)
        fd.flush()
        os.fsync(fd.fileno())
        fd.close()
        os.rename(feedfile+'.tmp', feedfile)
        fcntl.flock(feedfileObject.fileno(), fcntl.LOCK_UN)

#@timelimit(FEED_TIMEOUT)       
def parse(url, etag, modified):
    if PROXY == '':
        return feedparser.parse(url, etag, modified)
    else:
        proxy = urllib2.ProxyHandler( {"http":PROXY} )
        return feedparser.parse(url, etag, modified, handlers = [proxy])    
    
        
### Program Functions ###

def add(*args):
    if len(args) == 2 and contains(args[1], '@') and not contains(args[1], '://'):
        urls, to = [args[0]], args[1]
        folder = None
    elif len(args) >= 2:
        urls, to, folder = [args[0]], None, ' '.join(args[1:])
    else:
        urls, to, folder = args, None, None
    
    feeds, feedfileObject = load()
    if (feeds and not isstr(feeds[0]) and to is None) or (not len(feeds) and to is None):
        print "No email address has been defined. Please run 'r2e email emailaddress' or"
        print "'r2e add url emailaddress'."
        sys.exit(1)
    for url in urls: feeds.append(Feed(url, to, folder))
    unlock(feeds, feedfileObject)


### HTML Parser for grabbing links and images ###

from HTMLParser import HTMLParser
class Parser(HTMLParser):
    def __init__(self, tag = 'a', attr = 'href'):
        HTMLParser.__init__(self)
        self.tag = tag
        self.attr = attr
        self.attrs = []
    def handle_starttag(self, tag, attrs):
        if tag == self.tag:
            attrs = dict(attrs)
            if self.attr in attrs:
                self.attrs.append(attrs[self.attr])


### CSV dialect for parsing IMAP responses
class mailboxlist(csv.excel):
    delimiter = ' '


csv.register_dialect('mailboxlist',mailboxlist)


def uid(data):
    m = re.match('\d+ \(UID (?P<uid>\d+)\)', data)
    return m.group('uid')


def run(num=None):
    feeds, feedfileObject = load()
    mailserver = None
    try:
        # We store the default to address as the first item in the feeds list.
        # Here we take it out and save it for later.
        default_to = ""
        if feeds and isstr(feeds[0]): default_to = feeds[0]; ifeeds = feeds[1:] 
        else: ifeeds = feeds
        
        if num: ifeeds = [feeds[num]]
        feednum = 0
        
        for f in ifeeds:
            try: 
                feednum += 1
                if not f.active: continue
                
                if VERBOSE: print >>warn, 'I: Processing [%d] "%s"' % (feednum, f.url)
                r = {}
                try:
                    r = timelimit(FEED_TIMEOUT, parse)(f.url, f.etag, f.modified)
                except TimeoutError:
                    print >>warn, 'W: feed [%d] "%s" timed out' % (feednum, f.url)
                    continue
                
                # Handle various status conditions, as required
                if 'status' in r:
                    if r.status == 301: f.url = r['url']
                    elif r.status == 410:
                        print >>warn, "W: feed gone; deleting", f.url
                        feeds.remove(f)
                        continue
                
                http_status = r.get('status', 200)
                if VERBOSE > 1: print >>warn, "I: http status", http_status
                http_headers = r.get('headers', {
                  'content-type': 'application/rss+xml', 
                  'content-length':'1'})
                exc_type = r.get("bozo_exception", Exception()).__class__
                if http_status != 304 and not r.entries and not r.get('version', ''):
                    if http_status not in [200, 302]: 
                        print >>warn, "W: error %d [%d] %s" % (http_status, feednum, f.url)

                    elif contains(http_headers.get('content-type', 'rss'), 'html'):
                        print >>warn, "W: looks like HTML [%d] %s"  % (feednum, f.url)

                    elif http_headers.get('content-length', '1') == '0':
                        print >>warn, "W: empty page [%d] %s" % (feednum, f.url)

                    elif hasattr(socket, 'timeout') and exc_type == socket.timeout:
                        print >>warn, "W: timed out on [%d] %s" % (feednum, f.url)
                    
                    elif exc_type == IOError:
                        print >>warn, 'W: "%s" [%d] %s' % (r.bozo_exception, feednum, f.url)
                    
                    elif hasattr(feedparser, 'zlib') and exc_type == feedparser.zlib.error:
                        print >>warn, "W: broken compression [%d] %s" % (feednum, f.url)
                    
                    elif exc_type in socket_errors:
                        exc_reason = r.bozo_exception.args[1]
                        print >>warn, "W: %s [%d] %s" % (exc_reason, feednum, f.url)

                    elif exc_type == urllib2.URLError:
                        if r.bozo_exception.reason.__class__ in socket_errors:
                            exc_reason = r.bozo_exception.reason.args[1]
                        else:
                            exc_reason = r.bozo_exception.reason
                        print >>warn, "W: %s [%d] %s" % (exc_reason, feednum, f.url)
                    
                    elif exc_type == AttributeError:
                        print >>warn, "W: %s [%d] %s" % (r.bozo_exception, feednum, f.url)
                    
                    elif exc_type == KeyboardInterrupt:
                        raise r.bozo_exception
                        
                    elif r.bozo:
                        print >>warn, 'E: error in [%d] "%s" feed (%s)' % (feednum, f.url, r.get("bozo_exception", "can't process"))

                    else:
                        print >>warn, "=== rss2email encountered a problem with this feed ==="
                        print >>warn, "=== See the rss2email FAQ at http://www.allthingsrss.com/rss2email/ for assistance ==="
                        print >>warn, "=== If this occurs repeatedly, send this to lindsey@allthingsrss.com ==="
                        print >>warn, "E:", r.get("bozo_exception", "can't process"), f.url
                        print >>warn, r
                        print >>warn, "rss2email", __version__
                        print >>warn, "feedparser", feedparser.__version__
                        print >>warn, "html2text", h2t.__version__
                        print >>warn, "Python", sys.version
                        print >>warn, "=== END HERE ==="
                    continue
                
                r.entries.reverse()
                
                for entry in r.entries:
                    id = getID(entry)
                    
                    # If TRUST_GUID isn't set, we get back hashes of the content.
                    # Instead of letting these run wild, we put them in context
                    # by associating them with the actual ID (if it exists).
                    
                    frameid = entry.get('id')
                    if not(frameid): frameid = id
                    if type(frameid) is DictType:
                        frameid = frameid.values()[0]
                    
                    # If this item's ID is in our database
                    # then it's already been sent
                    # and we don't need to do anything more.
                    
                    if frameid in f.seen:
                        if f.seen[frameid] == id: continue

                    if not (f.to or default_to):
                        print "No default email address defined. Please run 'r2e email emailaddress'"
                        print "Ignoring feed %s" % f.url
                        break
                    
                    if 'title_detail' in entry and entry.title_detail:
                        title = entry.title_detail.value
                        if contains(entry.title_detail.type, 'html'):
                            title = html2text(title)
                    else:
                        title = getContent(entry)[:70]

                    title = title.replace("\n", " ").strip()
                    
                    datetime = time.gmtime()

                    if DATE_HEADER:
                        for datetype in DATE_HEADER_ORDER:
                            kind = datetype+"_parsed"
                            if kind in entry and entry[kind]: datetime = entry[kind]
                        
                    link = entry.get('link', "")
                    
                    from_addr = getEmail(r, entry)
                    
                    name = h2t.unescape(getName(r, entry))
                    fromhdr = formataddr((name, from_addr,))
                    tohdr = (f.to or default_to)
                    subjecthdr = title
                    datehdr = time.strftime("%a, %d %b %Y %H:%M:%S -0000", datetime)
                    useragenthdr = "rss2email"
                    
                    # Add post tags, if available
                    tagline = ""
                    if 'tags' in entry:
                        tags = entry.get('tags')
                        taglist = []
                        if tags:
                            for tag in tags:
                                taglist.append(tag['term'])
                        if taglist:
                            tagline = ",".join(taglist)
                    
                    extraheaders = {'Date': datehdr, 'User-Agent': useragenthdr, 'X-RSS-Feed': f.url, 'Message-ID': '<%s>' % hashlib.sha1(id.encode('utf-8')).hexdigest(), 'X-RSS-ID': id, 'X-RSS-URL': link, 'X-RSS-TAGS' : tagline, 'X-MUNGED-FROM': getMungedFrom(r), 'References': ''}
                    if BONUS_HEADER != '':
                        for hdr in BONUS_HEADER.strip().splitlines():
                            pos = hdr.strip().find(':')
                            if pos > 0:
                                extraheaders[hdr[:pos]] = hdr[pos+1:].strip()
                            else:
                                print >>warn, "W: malformed BONUS HEADER", BONUS_HEADER 
                    
                    entrycontent = getContent(entry, HTMLOK=HTML_MAIL)
                    contenttype = 'plain'
                    content = ''
                    if THREAD_ON_TAGS and len(tagline):
                        extraheaders['References'] += ''.join([' <%s>' % hashlib.sha1(t.strip().encode('utf-8')).hexdigest() for t in tagline.split(',')])
                    if USE_CSS_STYLING and HTML_MAIL:
                        contenttype = 'html'
                        content = "<html>\n" 
                        content += '<head><meta http-equiv="Content-Type" content="text/html"><style>' + STYLE_SHEET + '</style></head>\n'
                        content += '<body style="word-wrap: break-word; -webkit-nbsp-mode: space; -webkit-line-break: after-white-space;">\n'
                        content += '<div id="entry">\n'
                        content += '<h1 class="header"'
                        content += '><a href="'+link+'">'+subjecthdr+'</a></h1>\n'
                        if ishtml(entrycontent):
                            body = entrycontent[1].strip()
                            if SUMMARIZE:
                                content += '<div class="summary">%s</div>' % (summarize(html2text(body, plaintext=True), SUMMARIZE) + "<hr>")
                        else:
                            body = entrycontent.strip()
                            if SUMMARIZE:
                                content += '<div class="summary">%s</div>' % (summarize(body, SUMMARIZE) + "<hr>")
                        if THREAD_ON_LINKS:
                            parser = Parser()
                            parser.feed(body)
                            extraheaders['References'] += ''.join([' <%s>' % hashlib.sha1(h.strip().encode('utf-8')).hexdigest() for h in parser.attrs])
                        if INLINE_IMAGES_DATA_URI:
                            parser = Parser(tag='img', attr='src')
                            parser.feed(body)
                            for src in parser.attrs:
                                try:
                                    img = feedparser._open_resource(src, None, None, feedparser.USER_AGENT, link, [], {})
                                    data = img.read()
                                    if hasattr(img, 'headers'):
                                        headers = dict((k.lower(), v) for k, v in dict(img.headers).items())
                                        ctype = headers.get('content-type', None)
                                        if ctype and INLINE_IMAGES_DATA_URI:
                                            body = body.replace(src,'data:%s;base64,%s' % (ctype, base64.b64encode(data)))
                                except:
                                    print >>warn, "Could not load image: %s" % src
                                    pass
                        if body != '':  
                            content += '<div id="body">\n' + body + '</div>\n'
                        content += '\n<p class="footer">URL: <a href="'+link+'">'+link+'</a>'
                        if hasattr(entry,'enclosures'):
                            for enclosure in entry.enclosures:
                                if (hasattr(enclosure, 'url') and enclosure.url != ""):
                                    content += ('<br/>Enclosure: <a href="'+enclosure.url+'">'+enclosure.url+"</a>\n")
                                if (hasattr(enclosure, 'src') and enclosure.src != ""):
                                    content += ('<br/>Enclosure: <a href="'+enclosure.src+'">'+enclosure.src+'</a><br/><img src="'+enclosure.src+'"\n')
                        if 'links' in entry:
                            for extralink in entry.links:
                                if ('rel' in extralink) and extralink['rel'] == u'via':
                                    extraurl = extralink['href']
                                    extraurl = extraurl.replace('http://www.google.com/reader/public/atom/', 'http://www.google.com/reader/view/')
                                    viatitle = extraurl
                                    if ('title' in extralink):
                                        viatitle = extralink['title']
                                    content += '<br/>Via: <a href="'+extraurl+'">'+viatitle+'</a>\n'
                        content += '</p></div>\n'
                        content += "\n\n</body></html>"
                    else:   
                        if ishtml(entrycontent):
                            contenttype = 'html'
                            content = "<html>\n" 
                            content = ("<html><body>\n\n" + 
                                       '<h1><a href="'+link+'">'+subjecthdr+'</a></h1>\n\n' +
                                       entrycontent[1].strip() + # drop type tag (HACK: bad abstraction)
                                       '<p>URL: <a href="'+link+'">'+link+'</a></p>' )
                                       
                            if hasattr(entry,'enclosures'):
                                for enclosure in entry.enclosures:
                                    if enclosure.url != "":
                                        content += ('Enclosure: <a href="'+enclosure.url+'">'+enclosure.url+"</a><br/>\n")
                            if 'links' in entry:
                                for extralink in entry.links:
                                    if ('rel' in extralink) and extralink['rel'] == u'via':
                                        content += 'Via: <a href="'+extralink['href']+'">'+extralink['title']+'</a><br/>\n'
                                                                
                            content += ("\n</body></html>")
                        else:
                            content = entrycontent.strip() + "\n\nURL: "+link
                            if hasattr(entry,'enclosures'):
                                for enclosure in entry.enclosures:
                                    if enclosure.url != "":
                                        content += ('\nEnclosure: ' + enclosure.url + "\n")
                            if 'links' in entry:
                                for extralink in entry.links:
                                    if ('rel' in extralink) and extralink['rel'] == u'via':
                                        content += '<a href="'+extralink['href']+'">Via: '+extralink['title']+'</a>\n'

                    mailserver = send(fromhdr, tohdr, subjecthdr, content, contenttype, datetime, extraheaders, mailserver, f.folder)
            
                    f.seen[frameid] = id
                    
                f.etag, f.modified = r.get('etag', None), r.get('modified', None)
            except (KeyboardInterrupt, SystemExit):
                raise
            except:
                print >>warn, "=== rss2email encountered a problem with this feed ==="
                print >>warn, "=== See the rss2email FAQ at http://www.allthingsrss.com/rss2email/ for assistance ==="
                print >>warn, "=== If this occurs repeatedly, send this to lindsey@allthingsrss.com ==="
                print >>warn, "E: could not parse", f.url
                traceback.print_exc(file=warn)
                print >>warn, "rss2email", __version__
                print >>warn, "feedparser", feedparser.__version__
                print >>warn, "html2text", h2t.__version__
                print >>warn, "Python", sys.version
                print >>warn, "=== END HERE ==="
                continue

    finally:        
        unlock(feeds, feedfileObject)
        if mailserver:
            if IMAP_MARK_AS_READ:
                for folder in IMAP_MARK_AS_READ:
                    mailserver.select(folder)
                    res, data = mailserver.search(None, '(UNSEEN UNFLAGGED)')
                    if res == 'OK':
                        items = data[0].split()
                        for i in items:
                            res, data = mailserver.fetch(i, "(UID)")
                            if data[0]:
                                u = uid(data[0])
                                res, data = mailserver.uid('STORE', u, '+FLAGS', '(\Seen)')
            if IMAP_MOVE_READ_TO:
                typ, data = mailserver.list(pattern='*')
                # Parse folder listing as a CSV dialect (automatically removes quotes)
                reader = csv.reader(StringIO.StringIO('\n'.join(data)),dialect='mailboxlist')
                # Iterate over each folder
                for row in reader:
                    folder = row[-1:][0]
                    if folder == IMAP_MOVE_READ_TO or '\Noselect' in row[0]:
                        continue
                    mailserver.select(folder)
                    res, data = mailserver.search(None, '(SEEN UNFLAGGED)')
                    if res == 'OK':
                        items = data[0].split()
                        for i in items:
                            res, data = mailserver.fetch(i, "(UID)")
                            if data[0]:
                                u = uid(data[0])
                                res, data = mailserver.uid('COPY', u, IMAP_MOVE_READ_TO)
                                if res == 'OK':
                                    res, data = mailserver.uid('STORE', u, '+FLAGS', '(\Deleted)')
                                    mailserver.expunge()
            try:
                mailserver.quit()
            except:
                mailserver.logout()

def list():
    feeds, feedfileObject = load(lock=0)
    default_to = ""
    default_folder = DEFAULT_IMAP_FOLDER
    
    if feeds and isstr(feeds[0]):
        default_to = feeds[0]; ifeeds = feeds[1:]; i=1
        print "default email:", default_to
    else: ifeeds = feeds; i = 0
    for f in ifeeds:
        active = ('[ ]', '[*]')[f.active]
        print `i`+':',active, f.url, '(to: '+(f.to or (default_to+' (default)'))+', ' + 'folder: '+(f.folder or (default_folder+' (default))'))
        if not (f.to or default_to):
            print "   W: Please define a default address with 'r2e email emailaddress'"
        i+= 1

def opmlexport():
    import xml.sax.saxutils
    feeds, feedfileObject = load(lock=0)
    
    if feeds:
        print '<?xml version="1.0" encoding="UTF-8"?>\n<opml version="1.0">\n<head>\n<title>rss2email OPML export</title>\n</head>\n<body>'
        for f in feeds[1:]:
            url = xml.sax.saxutils.escape(f.url)
            print '<outline type="rss" text="%s" xmlUrl="%s"/>' % (url, url)
        print '</body>\n</opml>'

def opmlimport(importfile):
    importfileObject = None
    print 'Importing feeds from', importfile
    if not os.path.exists(importfile):
        print 'OPML import file "%s" does not exist.' % feedfile
    try:
        importfileObject = open(importfile, 'r')
    except IOError, e:
        print "OPML import file could not be opened: %s" % e
        sys.exit(1)
    try:
        import xml.dom.minidom
        dom = xml.dom.minidom.parse(importfileObject)
        newfeeds = dom.getElementsByTagName('outline')
    except:
        print 'E: Unable to parse OPML file'
        sys.exit(1)

    feeds, feedfileObject = load(lock=1)
    
    import xml.sax.saxutils
    
    for f in newfeeds:
        if f.hasAttribute('xmlUrl'):
            feedurl = f.getAttribute('xmlUrl')
            print 'Adding %s' % xml.sax.saxutils.unescape(feedurl)
            feeds.append(Feed(feedurl, None))
            
    unlock(feeds, feedfileObject)

def delete(n):
    feeds, feedfileObject = load()
    if (n == 0) and (feeds and isstr(feeds[0])):
        print >>warn, "W: ID has to be equal to or higher than 1"
    elif n >= len(feeds):
        print >>warn, "W: no such feed"
    else:
        print >>warn, "W: deleting feed %s" % feeds[n].url
        feeds = feeds[:n] + feeds[n+1:]
        if n != len(feeds):
            print >>warn, "W: feed IDs have changed, list before deleting again"
    unlock(feeds, feedfileObject)
    
def toggleactive(n, active):
    feeds, feedfileObject = load()
    if (n == 0) and (feeds and isstr(feeds[0])):
        print >>warn, "W: ID has to be equal to or higher than 1"
    elif n >= len(feeds):
        print >>warn, "W: no such feed"
    else:
        action = ('Pausing', 'Unpausing')[active]
        print >>warn, "%s feed %s" % (action, feeds[n].url)
        feeds[n].active = active
    unlock(feeds, feedfileObject)
    
def reset():
    feeds, feedfileObject = load()
    if feeds and isstr(feeds[0]):
        ifeeds = feeds[1:]
    else: ifeeds = feeds
    for f in ifeeds:
        if VERBOSE: print "Resetting %d already seen items" % len(f.seen)
        f.seen = {}
        f.etag = None
        f.modified = None
    
    unlock(feeds, feedfileObject)
    
def email(addr):
    feeds, feedfileObject = load()
    if feeds and isstr(feeds[0]): feeds[0] = addr
    else: feeds = [addr] + feeds
    unlock(feeds, feedfileObject)

if __name__ == '__main__':
    args = sys.argv
    try:
        if len(args) < 3: raise InputError, "insufficient args"
        feedfile, action, args = args[1], args[2], args[3:]
        
        if action == "run": 
            if args and args[0] == "--no-send":
                def send(sender, recipient, subject, body, contenttype, datetime, extraheaders=None, mailserver=None, folder=None):
                    if VERBOSE: print 'Not sending:', unu(subject)

            if args and args[-1].isdigit(): run(int(args[-1]))
            else: run()

        elif action == "email":
            if not args:
                raise InputError, "Action '%s' requires an argument" % action
            else:
                email(args[0])

        elif action == "add": add(*args)

        elif action == "new": 
            if len(args) == 1: d = [args[0]]
            else: d = []
            pickle.dump(d, open(feedfile, 'w'))

        elif action == "list": list()

        elif action in ("help", "--help", "-h"): print __doc__

        elif action == "delete":
            if not args:
                raise InputError, "Action '%s' requires an argument" % action
            elif args[0].isdigit():
                delete(int(args[0]))
            else:
                raise InputError, "Action '%s' requires a number as its argument" % action

        elif action in ("pause", "unpause"):
            if not args:
                raise InputError, "Action '%s' requires an argument" % action
            elif args[0].isdigit():
                active = (action == "unpause")
                toggleactive(int(args[0]), active)
            else:
                raise InputError, "Action '%s' requires a number as its argument" % action

        elif action == "reset": reset()

        elif action == "opmlexport": opmlexport()

        elif action == "opmlimport": 
            if not args:
                raise InputError, "OPML import '%s' requires a filename argument" % action
            opmlimport(args[0])

        else:
            raise InputError, "Invalid action"
        
    except InputError, e:
        print "E:", e
        print
        print __doc__

