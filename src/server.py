#!/usr/bin/python
# -⁻- coding: UTF-8 -*-

import webapp2
import jinja2
import os
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext import ndb
import urllib
import time
import json
import commands
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
    quoted_filename = urllib.quote(filename)
    if filename.startswith('http://'):
        # Submit URI with GET.
        if filename.endswith('.css'):
            cmd = ('curl -sG -d uri=%s -d output=json -d warning=0 %s'
                    % (quoted_filename, css_validator_url))
        else:
            cmd = ('curl -sG -d uri=%s -d output=json %s'
                    % (quoted_filename, html_validator_url))
            
    
        status,output = commands.getstatusoutput(cmd)
        if status != 0:
            raise OSError (status, 'failed: %s' % cmd)
    
        try:
            result = json.loads(output)
        except ValueError:
            result = ''
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
        
        f = self.request.get('url')
        
        errors = 0
        warnings = 0

        message('validating: %s ...' % f)
        retrys = 0
        while retrys < 2:
            result = validate(f)
            if result:
                break
            retrys += 1
            message('retrying: %s ...' % f)
        else:
            message('failed: %s' % f)
            errors += 1

        if f.endswith('.css'):
            errorcount = result['cssvalidation']['result']['errorcount']
            warningcount = result['cssvalidation']['result']['warningcount']
            errors += errorcount
            warnings += warningcount
            if errorcount > 0:
                message('errors: %d' % errorcount)
            if warningcount > 0:
                message('warnings: %d' % warningcount)
        else:
            for msg in result['messages']:
                if 'lastLine' in msg:
                    message('%(type)s: line %(lastLine)d: %(message)s' % msg)
                else:
                    message('%(type)s: %(message)s' % msg)
                if msg['type'] == 'error':
                    errors += 1
                else:
                    warnings += 1


urls = [('/',MainPage),
        ('/login',login),
        ('/validation',Validation),
       ]

application = webapp2.WSGIApplication(urls, debug=True)


def main():
    run_wsgi_app(application)

if __name__ == "__main__":
    main()
