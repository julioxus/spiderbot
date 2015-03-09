#!/usr/bin/python
# -⁻- coding: UTF-8 -*-

from google.appengine.api import urlfetch
import urllib
import json
import lxml.html
import urllib2

# REST APIs for validation
html_validator_url = 'http://validator.w3.org/check'
css_validator_url = 'http://jigsaw.w3.org/css-validator/validator'
wcag_validator_url = 'http://achecker.ca/checkacc.php'
ACHECKER_ID = '8d50ba76d166da61bdc9dfa3c97247b32dd1014c'

def validate(filename,page_type):
    '''
    Validate file and return JSON result as dictionary.
    'filename' can be a file name or an HTTP URL.
    Return '' if the validator does not return valid JSON.
    Raise OSError if curl command returns an error status.
    '''
    
    if filename.startswith('http://') or filename.startswith('https://'):
        # Submit URI with GET.
        urlfetch.set_default_fetch_deadline(60)
        if page_type == 'css':
            payload = {'uri': filename, 'output': 'json', 'warning': 0}
            encoded_args = urllib.urlencode(payload)
            url = css_validator_url + '/?' + encoded_args
            r = urllib2.urlopen(url)
            
        else:
            payload = {'uri': filename, 'output': 'json', 'warning': 0}
            encoded_args = urllib.urlencode(payload)
            url = html_validator_url + '/?' + encoded_args
            r = urllib2.urlopen(url)
     
        result = json.load(r)
        #time.sleep(2)   # Be nice and don't hog the free validator service.
        return result
    else:
        return ''

    
def validateWCAG(filename):
    urlfetch.set_default_fetch_deadline(60)
    code = checkAvailability(filename)
    if code >= 200 and code < 300:
        payload = {'uri': filename, 'id': ACHECKER_ID, 'guide': 'WCAG2-AA', 'output': 'rest'}
        encoded_args = urllib.urlencode(payload)
        url = wcag_validator_url + '/?' + encoded_args 
        print url
        r = urllib2.urlopen(url)
        result = r.read()
        return result
    else:
        return ''
    
def checkAvailability(filename):
    try:
        response = urllib2.urlopen(filename)
        code = response.getcode()
        
        response.close()
        return code
        
    except urllib2.HTTPError, e:
        code =  e.getcode()
        return code
        
    except:
        return -1
    
# Get all links from a root url given a depth scan level
def getAllLinks(root,depth,max_pages):
    
    links = []
    if not root.endswith('/'):
        root = root + '/'
    links.append((str(root),'html'))
    max_reached = False
    i = 0
    
    for i in range(0,depth):
        
        #connect to a URL
        website = urllib2.urlopen(links[i][0])
        
        #read html code
        html = website.read()
        
        dom =  lxml.html.fromstring(html)
        
        aux = []
        
        document_links = dom.xpath('//a/@href | //link/@href')
        css_links = dom.xpath('//*[@rel="stylesheet"]/@href')
        
        for link in document_links: # select the url in href for all a and link tags(links)
            
            if link in css_links:
                page_type = 'css'
            else:
                page_type = 'html'
            
            if link.startswith('http'):
                if not ((link,page_type) in links) and not ((link,page_type) in aux):
                    aux.append((link,page_type))
            else:
                if link.startswith('/'):
                    link = link[1:]   
                link = root + link
                if not ((link,page_type) in links) and not ((link,page_type) in aux):
                    aux.append((link,page_type))               
        
        for link in aux:
            if link[0].endswith('.jpg') or link[0].endswith('.png') or link[0].endswith('.js') or \
            link[0].endswith('.ico') or len(link[0]) >= 500:
                    aux.remove(link)
        
        links.extend(aux) 
                 
        while len(links) > max_pages:
            links.pop()
            max_reached = True
            
        if max_reached:
            break
    
    return links

def html_decode(s):
    """
    Returns the ASCII decoded version of the given HTML string. This does
    NOT remove normal HTML tags like <p>.
    """
    htmlCodes = (
            ("'", '&#39;'),
            ('"', '&quot;'),
            ('>', '&gt;'),
            ('<', '&lt;'),
            ('&', '&amp;')
            )
    for code in htmlCodes:
        s = s.replace(code[1], code[0])
    return s
