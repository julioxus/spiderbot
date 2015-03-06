#!/usr/bin/python
# -⁻- coding: UTF-8 -*-

import webapp2
import jinja2
import os
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.api import taskqueue
import urllib2
import time
import validators
import entities


# Declaración del entorno de jinja2 y el sistema de templates.

JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)


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
    
class QueueValidation(webapp2.RequestHandler):
    def post(self):
        
        try:
            root = self.request.get('url')
            max_pags = self.request.get('max_pags')
            depth = self.request.get('depth')
            if max_pags == '':
                max_pags = 50
            if depth == '':
                depth = 1
                
            max_pags = int(max_pags)
            depth = int(depth)
                
            links = validators.getAllLinksRec(root, depth, max_pags)
            
            option = self.request.get('optradio')
            
            print links
            
            for link in links:
                
                #Add the task to the default queue.
                taskqueue.add(url='/validation', params={'url': link[0], 'page_type': link[1], 'optradio': option})
            
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
                page_type = self.request.get('page_type')
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
                    result = validators.validate(f,page_type)
                except:
                    content += "Error: Invalid URL"
                    state = 'ERROR'
                
                if result == '':
                    out += 'Error: Invalid URL. URL must start with http:// or https://'
                    state = 'ERROR'
                         
                try:
                    if page_type == 'css':
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
                code = validators.checkAvailability(f)
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
                    result = validators.validateWCAG(f)
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
            
        #sys_time = time.strftime("%H:%M:%S")
        #sys_date = time.strftime("%d/%m/%Y")
        
        page_result = entities.PageResult()
        
        page_result.url = f
        page_result.content = content
        #report.date = sys_date
        #report.time = sys_time
        page_result.state = state
        
        page_result.put()
        
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
