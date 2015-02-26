#!/usr/bin/python
# -⁻- coding: UTF-8 -*-

import webapp2
import jinja2
import os
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext import ndb
import urllib
import urllib2
import time
import json

# Declaración del entorno de jinja2 y el sistema de templates.

JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)

html_validator_url = 'http://validator.w3.org/check'
css_validator_url = 'http://jigsaw.w3.org/css-validator/validator'


def validate(filename):
    '''
    Validate file and return JSON result as dictionary.
    'filename' can be a file name or an HTTP URL.
    Return '' if the validator does not return valid JSON.
    Raise OSError if curl command returns an error status.
    '''
    
    if filename.startswith('http://') or filename.startswith('https://'):
        # Submit URI with GET.
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
            
            try:
                response = urllib2.urlopen(f)
                code = response.getcode()
                self.response.write(code)
                self.response.write('<br/>Request OK')
                
                response.close()
                
            except urllib2.HTTPError, e:
                code =  e.getcode()
                self.response.write(code)
                self.response.write('<br/>Request FAILED')
                
            except:
                self.response.write('Error: Invalid URL')
        
        
urls = [('/',MainPage),
        ('/login',login),
        ('/validation',Validation),
       ]

application = webapp2.WSGIApplication(urls, debug=True)


def main():
    run_wsgi_app(application)

if __name__ == "__main__":
    main()
