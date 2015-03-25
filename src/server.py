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
from webapp2_extras.config import DEFAULT_VALUE
import json


# Declaración del entorno de jinja2 y el sistema de templates.

JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)


class MainPage(webapp2.RequestHandler):
    def get(self):
        if self.request.cookies.get("name"):
            self.response.headers['Content-Type'] = 'text/html'
            
            username = self.request.cookies.get("name")
            user = entities.User.query(entities.User.name == username).get()  
            total_pages = user.n_links
            current_pages = entities.PageResult.query(entities.PageResult.user == user.name).count()
            progress = int((current_pages * 100)/total_pages)
            
            template_values={'progress':progress}
            template = JINJA_ENVIRONMENT.get_template('template/index.html')
            self.response.write(template.render(template_values))
        else:
            self.redirect('/login')
        
class login(webapp2.RequestHandler):
    def get(self):
        self.response.headers['Content-Type'] = 'text/html'
        template_values={}
        template = JINJA_ENVIRONMENT.get_template('template/login.html')
        self.response.write(template.render(template_values))
        
    def post(self):
        name = self.request.get('user')
        user = entities.User.query(entities.User.name==name).get()
        if name is not None:
            password = self.request.get('password')
            if user.password==password:
                self.response.headers.add_header('Set-Cookie',"name="+str(user.name))
                self.response.headers['Content-Type'] = 'text/html'
                self.redirect('/')
            else:
                self.response.write('Incorrect password')
        else:
            self.response.write('Incorrect user')
            
class logout(webapp2.RequestHandler):
    def get(self):
        self.response.headers.add_header("Set-Cookie", "name=; Expires=Thu, 01-Jan-1970 00:00:00 GMT")
        self.redirect('/')

class QueueValidation(webapp2.RequestHandler):
    def post(self):
        
        username = self.request.cookies.get("name")
        
        try:
            root = self.request.get('url')
            max_pags = self.request.get('max_pags')
            depth = self.request.get('depth')
            onlyDomain = self.request.get("onlyDomain")
            if onlyDomain:
                onlyDomain = True
            else:
                onlyDomain = False
                
            if max_pags == '':
                max_pags = 50
            if depth == '':
                depth = 1
                
            max_pags = int(max_pags)
            depth = int(depth)
                
            links = validators.getAllLinks(root, depth, max_pags, onlyDomain)
            
            option = self.request.get('optradio')
            
            i = 0
            while i < len(links):
                if (option == 'WCAG 2.0' and links[i][1] == 'css'):
                    del links[i]
                    i = -1
                i+=1
            
            user = entities.User.query(entities.User.name == username).get()
            user.n_links = len(links)
            user.root_link = root
            user.validation_type = option
            user.onlyDomain = onlyDomain
            
            if user.lock == False:
                alphaqueue = taskqueue.Queue('alphaqueue')
                number = 0
                user.lock = True
                user.put()
                while(user.root_link == ''):
                    time.sleep(1)
                for link in links:
                    #Add the task to the default queue.
                    alphaqueue.add(taskqueue.Task(url='/validation', params={'url': link[0], 'page_type': link[1], 'optradio': option, 'username': username, 'number': number}),False)
                    number += 1
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
            
            errors = 0
            warnings = 0
            list_errors = []
            
            option = self.request.get('optradio')
            
            if option == 'HTML':
                out = ''
        
                result = ''
                try:
                    result = validators.validate(f,page_type)
                except:
                    content += "Error parsing URL"
                    state = 'ERROR'
                         
                try:
                    if page_type == 'css':
                        errorcount = result['cssvalidation']['result']['errorcount']
                        warningcount = result['cssvalidation']['result']['warningcount']
                        
                        if errorcount > 0:
                            for msg in result['cssvalidation']['errors']:
                                out += "error: line %(line)d: %(type)s: %(context)s %(message)s \n" % msg
                                list_errors.append("%(message)s" % msg)
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
                                list_errors.append("%(message)s" % msg)
                            else:
                                warnings += 1
                    
                    out += "\nErrors: %s \n" % errors
                    out += "Warnings: %s" % warnings
                    
                    content += out
                    
                    if errors == 0:
                        state = 'PASS'
                    else:
                        state = 'FAIL'
                    
                except:
                    content += out
                    state = 'ERROR'
                
                content += '\n\n'
                    
            elif option == 'CHECK AVAILABILITY':
                code = validators.checkAvailability(f)
                if code >= 200 and code < 300:
                    content += str(code) + '\nRequest OK'
                    state = 'PASS'
                elif code != -1:
                    content += str(code) + '\nRequest FAILED'
                    state = 'FAIL'
                    errors+=1
                else:
                    content += 'Error parsing URL'
                    state = 'ERROR'
                
                content += '\n\n'
                
            elif option == 'WCAG 2.0':
                try:
                    out = ''
                    result = validators.validateWCAG(f)
                    
                    state = result['state']
                    errors = len(result['errors']['lines'])
                    warnings = len(result['warnings']['lines'])
                    
                    for i in range(0,errors):
                        line = result['errors']['lines'][i]
                        message = result['errors']['messages'][i]
                        code = result['errors']['codes'][i]
                        out += "Error: %(line)s %(message)s \n %(code)s \n\n" % \
                        {'line': line, 'message': message, 'code': code}
                        list_errors.append("%s" % message)
                        
                    for i in range(0,warnings):
                        line = result['warnings']['lines'][i]
                        message = result['warnings']['messages'][i]
                        code = result['warnings']['codes'][i]
                        out += "Warning: %(line)s %(message)s \n %(code)s \n\n" % \
                        {'line': line, 'message': message, 'code': code}                      
                        
                    out += "\nErrors: %s \n" % errors
                    out += "Warnings: %s" % warnings
                    
                    content += out
                    
                except:
                    content += "Achecker service not working properly"
                    state = 'ERROR'
                    content += '\n\n'
                
            retrys -= 1
        
        username = self.request.get("username")
        number = int(self.request.get("number"))
        user = entities.User.query(entities.User.name == username).get()
        
        page_result = entities.PageResult()
        page_result.user = user.name
        page_result.url = f
        page_result.content = content
        page_result.state = state
        page_result.errors = errors
        page_result.number = number
        page_result.list_errors = json.dumps(list_errors)
        page_result.put()
        
      
class Reports(webapp2.RequestHandler):
    def get(self):
        if self.request.cookies.get("name"):
            
            username = self.request.cookies.get("name")
            user = entities.User.query(entities.User.name == username).get()
            qry = entities.PageResult.query(entities.PageResult.user == user.name).order(entities.PageResult.number)
            error_message = ''
            try:
                qry.count()
            except:
                error_message = 'Error accessing the database: Required more quota than is available. Come back after 24h.'
                
            if qry.count() == user.n_links:
                
                report = entities.Report()
                report.web = user.root_link
                report.validation_type = user.validation_type
                report.onlyDomain = user.onlyDomain
                report.user = user.name
                report.results = qry.fetch()
                report.pages = len(report.results)
                
                error_pages = 0
                errors = 0
                for result in report.results:
                    if result.state == 'FAIL':
                        error_pages+=1
                    errors += result.errors
                report.error_pages = error_pages
                report.errors = errors
                
                try:
                    report.put()
                    
                    ndb.delete_multi(
                        entities.PageResult.query(entities.PageResult.user == user.name).fetch(keys_only=True)
                    )
                    
                    # Reset global variables for user
                    user.n_links = -1
                    user.root_link = ''
                    user.validation_type = ''
                    user.onlyDomain = None
                    user.lock = False
                    user.put()
                    time.sleep(2)
                    self.redirect('/reports')
                except:
                    error_message = 'Error: Unable to update database: too much errors in your website: '+user.root_link
                
                    
                ndb.delete_multi(
                    entities.PageResult.query(entities.PageResult.user == user.name).fetch(keys_only=True)
                )
                
                # Reset global variables for user
                user.n_links = -1
                user.root_link = ''
                user.validation_type = ''
                user.onlyDomain = None
                user.lock = False
                user.put()
                
            self.response.headers['Content-Type'] = 'text/html'
            reports = entities.Report.query().fetch()
            
            username = self.request.cookies.get("name")
            user = entities.User.query(entities.User.name == username).get()  
            total_pages = user.n_links
            current_pages = entities.PageResult.query(entities.PageResult.user == user.name).count()
            progress = int((current_pages * 100)/total_pages)
            
            template_values={'reports':reports, 'error_message': error_message, 'progress':progress}
            template = JINJA_ENVIRONMENT.get_template('template/reports.html')
            self.response.write(template.render(template_values))
        else:
            self.redirect('/login')
        
class ReportViewer(webapp2.RequestHandler):
    def get(self):
        if self.request.cookies.get("name"):
            report_id = long(self.request.get('id'))
            reports = entities.Report.query().fetch()
            report = ''
            for r in reports:
                if r.key.id() == report_id:
                    report = r
                    break
            pages = len(report.results)
        else:
            self.redirect('/login')
        list_errors = []
        for result in report.results:    
            list_errors.extend(json.loads(result.list_errors))

        # Delete repeated elements in the list
        i = 0
        while i < len(list_errors)-1:
            j = i+1
            while j < len(list_errors):
                if (list_errors[i] == list_errors[j]):
                    del list_errors[j]
                    j = i
                j+=1
            i+=1
        
        username = self.request.cookies.get("name")
        user = entities.User.query(entities.User.name == username).get()  
        total_pages = user.n_links
        current_pages = entities.PageResult.query(entities.PageResult.user == user.name).count()
        progress = int((current_pages * 100)/total_pages)
            
        template_values={'report':report, 'list_errors': list_errors, 'pages':pages, 'progress':progress}
        template = JINJA_ENVIRONMENT.get_template('template/report_view.html')
        self.response.write(template.render(template_values))
        
class PageViewer(webapp2.RequestHandler):
    def get(self):
        if self.request.cookies.get("name"):
            number = int(self.request.get("number"))
            report_id = long(self.request.get('id'))
            reports = entities.Report.query().fetch()
            report = ''
            for r in reports:
                if r.key.id() == report_id:
                    report = r
                    break
        else:
            self.redirect('/login')
        
        username = self.request.cookies.get("name")
        user = entities.User.query(entities.User.name == username).get()  
        total_pages = user.n_links
        current_pages = entities.PageResult.query(entities.PageResult.user == user.name).count()
        progress = int((current_pages * 100)/total_pages)
        
        template_values={'result':report.results[number],'progress':progress}
        template = JINJA_ENVIRONMENT.get_template('template/page_view.html')
        self.response.write(template.render(template_values))
        
class GetScanProgress(webapp2.RequestHandler):
    def get(self):
        username = self.request.cookies.get("name")
        user = entities.User.query(entities.User.name == username).get()
        
        total_pages = user.n_links
        current_pages = entities.PageResult.query(entities.PageResult.user == user.name).count()
        progress = int((current_pages * 100)/total_pages)
        
        self.response.write(json.dumps(progress))
    
        
urls = [('/',MainPage),
        ('/login',login),
        ('/validation',Validation),
        ('/qvalidation',QueueValidation),
        ('/reports',Reports),
        ('/viewreport',ReportViewer),
        ('/viewpage',PageViewer),
        ('/logout',logout),
        ('/progress',GetScanProgress),
       ]

application = webapp2.WSGIApplication(urls, debug=True)


def main():
    os.environ['TZ'] = 'Europe/Madrid'
    time.tzset()
    run_wsgi_app(application)

if __name__ == "__main__":
    main()
