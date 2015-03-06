#!/usr/bin/python
# -⁻- coding: UTF-8 -*-

import webapp2
import jinja2
import os
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext import ndb
from google.appengine.api import urlfetch
from google.appengine.api import taskqueue
import urllib
import urllib2
import time
import json
import re
import lxml.html

# Declaración del entorno de jinja2 y el sistema de templates.

JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)

# REST APIs for validation
html_validator_url = 'http://validator.w3.org/check'
css_validator_url = 'http://jigsaw.w3.org/css-validator/validator'
wcag_validator_url = 'http://achecker.ca/checkacc.php'
ACHECKER_ID = '8d50ba76d166da61bdc9dfa3c97247b32dd1014c'


def validate(filename,type):
    '''
    Validate file and return JSON result as dictionary.
    'filename' can be a file name or an HTTP URL.
    Return '' if the validator does not return valid JSON.
    Raise OSError if curl command returns an error status.
    '''
    
    if filename.startswith('http://') or filename.startswith('https://'):
        # Submit URI with GET.
        urlfetch.set_default_fetch_deadline(60)
        if type == 'css':
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
        payload = {'uri': filename, 'id': ACHECKER_ID, 'guide': 'WCAG2-AA', 'output': 'html'}
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
def getAllLinksRec(root,depth):
    
    links = []
    if not root.endswith('/'):
        root = root + '/'
    links.append(str(root))
    i = 0
    
    while len(links) < depth:
        
        #connect to a URL
        website = urllib2.urlopen(links[i])
        
        #read html code
        html = website.read()
        
        dom =  lxml.html.fromstring(html)
        
        aux = []
        
        document_links = dom.xpath('//a/@href')
        header_css_links = dom.xpath("//link/@href[rel='stylesheet']")
        header_normal_links= dom.xpath("//link/@href")
        header_normal_links = list(set(header_normal_links) - set(header_css_links))
        
        for link in document_links: # select the url in href for all a tags(links)
            if link.startswith('http'):
                if not (link in links) and not (link in aux):
                    aux.append(link)
            else:
                if link.startswith('/'):
                    link = link[1:]   
                link = root + link
                if not (link in links) and not (link in aux):
                    aux.append(link)                
        
        for link in aux:
            if link.endswith('.jpg') or link.endswith('.png') or link.endswith('.js') or link.endswith('.ico'):
                    aux.remove(link)
        
        links.extend(aux) 
                 
        print len(links)
        while len(links) > depth:
            links.pop()
        
        print len(links)
        print depth 
        
        i+=1
    
    return links

class MainPage(webapp2.RequestHandler):
    
    def get(self):
        self.response.headers['Content-Type'] = 'text/html'
        template_values={}
        template = JINJA_ENVIRONMENT.get_template('template/index.html')
        self.response.write(template.render(template_values))
        
class login(webapp2.RequestHandler):
    
    def get(self):
        self.response.headers['Content-Type'] = 'text/html'
        template_values={}
        template = JINJA_ENVIRONMENT.get_template('template/login.html')
        self.response.write(template.render(template_values))
        
class Report(ndb.Model):
    url = ndb.StringProperty()
    type = ndb.StringProperty()
    content = ndb.TextProperty()
    date = ndb.StringProperty()
    time = ndb.StringProperty()
    user = ndb.StringProperty()
    state = ndb.StringProperty()
    
class QueueValidation(webapp2.RequestHandler):
    def post(self):
        
        try:
            root = self.request.get('url')
            max_pags = self.request.get('max_pags')
            if max_pags == '':
                max_pags = 50
                
            max_pags = int(max_pags)
                
            links = getAllLinksRec(root, max_pags)
            
            option = self.request.get('optradio')
            
            for link in links:
                
                #Add the task to the default queue.
                taskqueue.add(url='/validation', params={'url': link, 'optradio': option})
            
            self.redirect('/')
        except:
            self.response.write("Error: Invalid URL")
            return None
        
class Validation(webapp2.RequestHandler):
    def post(self):
        
        state = 'ERROR'
        retrys = 2
        
        while retrys > 0 and state == 'ERROR':
            
            content = ''
            
            try:
                f = self.request.get('url')
            except urllib2.HTTPError, e:
                content += 'Error: ' + e
                state = 'ERROR'
            
            option = self.request.get('optradio')
            
            if option == 'val_html':
                out = ''
                errors = 0
                warnings = 0
        
                result = ''
                try:
                    result = validate(f)
                except:
                    content += "Error: Invalid URL"
                    state = 'ERROR'
                
                if result == '':
                    out += 'Error: Invalid URL. URL must start with http:// or https://'
                    state = 'ERROR'
                         
                try:
                    p = re.compile(r'\.css*')
                    if p.search(f):
                        errorcount = result['cssvalidation']['result']['errorcount']
                        warningcount = result['cssvalidation']['result']['warningcount']
                        
                        if errorcount > 0:
                            for msg in result['cssvalidation']['errors']:
                                out += "error: line %(line)d: %(type)s: %(context)s %(message)s \n" % msg
                        if warningcount > 0:
                            for msg in result['cssvalidation']['warnings']:
                                out += "warning: line %(line)d: %(type)s: %(message)s \n" % msg
                        
                        errors += errorcount
                        warnings += warningcount
                    else:
                        for msg in result['messages']:
                            if 'lastLine' in msg:
                                out += "%(type)s: line %(lastLine)d: %(message)s \n" % msg
                            else:
                                out += "%(type)s: %(message)s \n" % msg
                            if msg['type'] == 'error':
                                errors += 1
                            else:
                                warnings += 1
                    
                    out += "\nErrors: %s \n" % errors
                    out += "Warnings: %s" % warnings
                    
                    content += out.replace("\n", "<br />")
                    
                    if errors == 0:
                        state = 'PASS'
                    else:
                        state = 'FAIL'
                    
                except:
                    content += out.replace("\n", "<br />")
                    state = 'ERROR'
                
                content += '<br/><br/>'
                    
            elif option == 'check_availability':
                code = checkAvailability(f)
                if code >= 200 and code < 300:
                    content += str(code) + '<br/>Request OK'
                    state = 'PASS'
                elif code != -1:
                    content += str(code) + '<br/>Request FAILED'
                    state = 'FAIL'
                else:
                    content += 'Error: Invalid URL'
                    state = 'ERROR'
                
                content += '<br/><br/>'
                    
            elif option == 'val_wcag':
                try:
                    result = validateWCAG(f)
                    if result:
                        content += result
                        state = 'OK'
                    else:
                        content += "Error: Invalid URL. URL must start with http:// or https://"
                        state = 'ERROR'
                except:
                    content += "Error: Deadline exceeded while waiting for HTTP response"
                    state = 'ERROR'
                
                content += '<br/><br/>'
                
            retrys -= 1
            
        sys_time = time.strftime("%H:%M:%S")
        sys_date = time.strftime("%d/%m/%Y")
        
        report = Report()
        
        report.url = f
        report.type = option
        report.content = content
        report.date = sys_date
        report.time = sys_time
        report.state = state
        
        report.put()
        
urls = [('/',MainPage),
        ('/login',login),
        ('/validation',Validation),
        ('/qvalidation',QueueValidation),
       ]

application = webapp2.WSGIApplication(urls, debug=True)


def main():
    os.environ['TZ'] = 'Europe/Madrid'
    time.tzset()
    run_wsgi_app(application)

if __name__ == "__main__":
    main()
