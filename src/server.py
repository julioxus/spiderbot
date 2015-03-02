#!/usr/bin/python
# -⁻- coding: UTF-8 -*-

import webapp2
import jinja2
import os
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext import ndb
from google.appengine.api import urlfetch
import urllib
import urllib2
import time
import json

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


def validate(filename):
    '''
    Validate file and return JSON result as dictionary.
    'filename' can be a file name or an HTTP URL.
    Return '' if the validator does not return valid JSON.
    Raise OSError if curl command returns an error status.
    '''
    
    if filename.startswith('http://') or filename.startswith('https://'):
        # Submit URI with GET.
        urlfetch.set_default_fetch_deadline(60)
        if filename.endswith('.css'):
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
        time.sleep(2)   # Be nice and don't hog the free validator service.
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
        
class Validation(webapp2.RequestHandler):
    def post(self):
        
        out = ""
        
        try:
            f = self.request.get('url')
        except urllib2.HTTPError, e:
            self.response.write('Error: ' + e)
            return None
        
        option = self.request.get('optradio')
        
        if option == 'val_html':
            errors = 0
            warnings = 0
    
            out += "validating: %s ...\n" % f
            result = ''
            try:
                result = validate(f)
            except:
                self.response.write("Error: Invalid URL")
                return None
            
            if result == '':
                out += 'Error: Invalid URL. URL must start with http:// or https://'
                     
            try:
                if f.endswith('.css'):
                    errorcount = result['cssvalidation']['result']['errorcount']
                    warningcount = result['cssvalidation']['result']['warningcount']
                    
                    for msg in result['cssvalidation']['errors']:
                        out += "error: line %(line)d: %(type)s: %(context)s %(message)s \n" % msg
                    
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
                
                self.response.write(out.replace("\n", "<br />"))
                
            except:
                self.response.write(out.replace("\n", "<br />"))
                
        elif option == 'check_availability':
            code = checkAvailability(f)
            if code >= 200 and code < 300:
                self.response.write(str(code) + '<br/>Request OK')
            elif code != -1:
                self.response.write(str(code) + '<br/>Request FAILED')
            else:
                self.response.write('Error: Invalid URL')
                
        elif option == 'val_wcag':
            try:
                result = validateWCAG(f)
                if result:
                    self.response.write(result)
                else:
                    self.response.write("Error: Invalid URL. URL must start with http:// or https://")
            except:
                self.response.write("Error: Deadline exceeded while waiting for HTTP response")
                return None
        
        
urls = [('/',MainPage),
        ('/login',login),
        ('/validation',Validation),
       ]

application = webapp2.WSGIApplication(urls, debug=True)


def main():
    run_wsgi_app(application)

if __name__ == "__main__":
    main()
