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
import sys

# Declaración del entorno de jinja2 y el sistema de templates.

JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)

html_validator_url = 'http://validator.w3.org/check'
css_validator_url = 'http://jigsaw.w3.org/css-validator/validator'

def message(msg):
    print >> sys.stderr, msg


def validate(filename):
    '''
    Validate file and return JSON result as dictionary.
    'filename' can be a file name or an HTTP URL.
    Return '' if the validator does not return valid JSON.
    Raise OSError if curl command returns an error status.
    '''
    
    if filename.startswith('http://'):
        # Submit URI with GET.
        if filename.endswith('.css'):
            payload = {'uri': filename, 'output': 'json', 'warning': 0}
            encoded_args = urllib.urlencode(payload)
            url = css_validator_url + '/?' + encoded_args
            r = urllib2.urlopen(url)
            print url

            
        else:
            payload = {'uri': filename, 'output': 'json', 'warning': 0}
            encoded_args = urllib.urlencode(payload)
            url = html_validator_url + '/?' + encoded_args
            r = urllib2.urlopen(url)
    
        try:   
            result = json.load(r)
        except ValueError:
            result = 'Error al procesar json'
        time.sleep(2)   # Be nice and don't hog the free validator service.
        return result
    else:
        return 'Error: URL no empieza por http://'

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
        
        f = self.request.get('url')
        
        errors = 0
        warnings = 0

        out += "validating: %s ...\n" % f
        result = ''
        result = validate(f)
        
        if type(result) == 'str':
            out += result
        
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
        
urls = [('/',MainPage),
        ('/login',login),
        ('/validation',Validation),
       ]

application = webapp2.WSGIApplication(urls, debug=True)


def main():
    run_wsgi_app(application)

if __name__ == "__main__":
    main()
