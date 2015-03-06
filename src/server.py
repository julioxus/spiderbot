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
from google.appengine.ext import ndb
from time import sleep


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

# Global variables for each user (User entity in the future)

n_links = {'admin': 0}
root_link = {'admin': ''}
lock = {'admin': False}

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
                
            links = validators.getAllLinks(root, depth, max_pags)
            
            option = self.request.get('optradio')
            
            global n_links
            global root_link
            global lock
            n_links['admin'] = len(links)
            root_link['admin'] = root
            
            if lock['admin'] == False:
                for link in links:
                    
                    #Add the task to the default queue.
                    taskqueue.add(url='/validation', params={'url': link[0], 'page_type': link[1], 'optradio': option})
                lock['admin'] = True
                self.redirect('/')
            else:
                self.response.write("You already have pending tasks executing, wait and try again later")
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
            
        global n_links
        global root_link
        global lock
        
        page_result = entities.PageResult()
        page_result.web = root_link['admin']
        page_result.url = f
        page_result.content = content
        page_result.state = state
        page_result.put()
        sleep(1)
        current_links = entities.PageResult.query(entities.PageResult.web == root_link['admin']).count()
        current_links = entities.PageResult.query(entities.PageResult.web == root_link['admin']).count()
        
        print current_links
        print n_links['admin']
        
        if current_links == n_links['admin']:
            report = entities.Report()
            report.web = root_link['admin']
            report.validation_type = option
            report.user = 'admin'
            qry = entities.PageResult.query(entities.PageResult.web == root_link['admin'])
            report.results = qry.fetch()
            
            report.put()
            ndb.delete_multi(
                entities.PageResult.query(entities.PageResult.web == root_link['admin']).fetch(keys_only=True)
            )
            
            # Reset global variables for user
            n_links['admin'] = 0
            root_link['admin'] = ''
            lock['admin'] = False
            
class Reports(webapp2.RequestHandler):
    def get(self):
        self.response.headers['Content-Type'] = 'text/html'
        template_values={}
        template = JINJA_ENVIRONMENT.get_template('template/reports.html')
        self.response.write(template.render(template_values))
        
urls = [('/',MainPage),
        ('/login',login),
        ('/validation',Validation),
        ('/qvalidation',QueueValidation),
        ('/reports',Reports)
       ]

application = webapp2.WSGIApplication(urls, debug=True)


def main():
    os.environ['TZ'] = 'Europe/Madrid'
    time.tzset()
    run_wsgi_app(application)

if __name__ == "__main__":
    main()
