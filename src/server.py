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
            progress = 0
            try:
                username = self.request.cookies.get("name")
                user = entities.User.query(entities.User.name == username).get()  
                total_pages = user.n_links
                if user.validation_type == 'MOBILE':
                    current_pages = entities.PageResultGoogle.query(entities.PageResultGoogle.user == user.name).count()
                else:
                    current_pages = entities.PageResult.query(entities.PageResult.user == user.name).count()
                progress = int((current_pages * 100)/total_pages)
                
            except:
                error_message = 'Error accessing the database: Required more quota than is available. Come back after 24h.'
            
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
                if (option == 'WCAG 2.0' or option == 'MOBILE') and links[i][1] == 'css':
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
                    if option == 'MOBILE':
                        alphaqueue.add(taskqueue.Task(url='/google-validation', params={'url': link[0], 'username': username, 'number': number}),False)
                    else:
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
        retrys = 4
        
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
                    content += "Error parsing URL. Maybe server IP is blocked by W3C service (http://validator.w3.org/)"
                    state = 'ERROR'
                         
                try:
                    if page_type == 'css':
                        errorcount = result['cssvalidation']['result']['errorcount']
                        warningcount = result['cssvalidation']['result']['warningcount']
                        
                        if errorcount > 0:
                            for msg in result['cssvalidation']['errors']:
                                out += "error: line %(line)d: %(type)s: %(context)s %(message)s \n" % msg
                                if not ["%(message)s" % msg, ["%(line)d" % msg], [f]] in list_errors:
                                    list_errors.append(["%(message)s" % msg, ["%(line)d" % msg], [f]])
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
                                if not ["%(message)s" % msg, ["%(lastLine)d" % msg], [f]] in list_errors:
                                        list_errors.append(["%(message)s" % msg, ["%(lastLine)d" % msg], [f]])
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
                        if not ["%s" % message, [line], [f]] in list_errors:
                            list_errors.append(["%s" % message, [line], [f]])
                        
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
            error_message = ''
            reports = ''
            progress = 0
            list_errors = []
            try:
                user = entities.User.query(entities.User.name == username).get()
                qry = entities.PageResult.query(entities.PageResult.user == user.name).order(entities.PageResult.number)
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
                        if result.state == 'FAIL' or result.state == 'ERROR':
                            error_pages+=1
                        errors += result.errors
                        
                        list_errors.extend(json.loads(result.list_errors))
            
                        # Delete repeated elements in the list
                        i = 0
                        while i < len(list_errors)-1:
                            j = i+1
                            while j < len(list_errors):
                                if (list_errors[i][0] == list_errors[j][0]):
                                    list_errors[i][1].append(list_errors[j][1][0])
                                    list_errors[i][2].append(list_errors[j][2][0])
                                    del list_errors[j]
                                    j = i
                                j+=1
                            i+=1
                        
                    report.error_pages = error_pages
                    report.errors = errors
                    report.list_errors = json.dumps(list_errors);
                
                    try:
                        report.put()
                        
                    except:
                        error_message = 'Error: Unable to update database: too many errors in your website: '+user.root_link
                    
                        
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
                    
                    
                    
                    # Calculate score
                     
                    distinct_errors = (len(json.loads(report.list_errors)))
                    error_pages = float(report.error_pages)
                    pages = float(report.pages)
                    
                    # Calculate the two values used by the score
                    value1 = error_pages / pages # Number of error pages ratio
                     
                    if error_pages > 0:
                        value2 = distinct_errors / error_pages # Distinct errors by error page (estimated mean)
                    else:
                        value2 = 0
                    
                    # Normalize both values
                     
                    # Para el primer valor estableceremos el rango [0 1]
                    # Obviamente nunca habrá mas páginas que páginas con error por tanto el peor caso
                    # seria un resultado de 1 que implica que todas las paginas muestran errores
                    # El mejor caso seria un valor de 0 que implica que no existen paginas con errores
                     
                    # Para tener una puntuación sobre 10 multiplicamos el valor y obtenemos el inverso
                     
                    value1_norm = 10 - value1 * 10
                     
                     
                    # Para el segundo valor establecermos el rango [0 100]
                     
                    # 0 implica que no existen errores distintos y sería la maxima nota
                    # 100 implicaria que existen mas de 100 fallos distintos por página con error
                    # Limitamos en 100 por tanto
                     
                    if value2>=100:
                        value2 = 100
                     
                    # Dividimos el resultado entre 10 para puntuar sobre 10 y obtenemos el inverso
                     
                    value2_norm = 10 - value2 / 10;
                     
                    # Ya podemos calcular la puntuacion
                     
                    score = round(0.5 * value1_norm + 0.5 * value2_norm,1)
                    
                    report.score = score
                    report.put()
                                
                reports = entities.Report.query().fetch()
                
                
                username = self.request.cookies.get("name")
                user = entities.User.query(entities.User.name == username).get()  
                total_pages = user.n_links
                if user.validation_type == 'MOBILE':
                    current_pages = entities.PageResultGoogle.query(entities.PageResultGoogle.user == user.name).count()
                else:
                    current_pages = entities.PageResult.query(entities.PageResult.user == user.name).count()
                progress = int((current_pages * 100)/total_pages)
                
            except:
                error_message = 'Error accessing the database: Required more quota than is available. Come back after 24h.'
                
            self.response.headers['Content-Type'] = 'text/html'
            
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
        list_errors = json.loads(report.list_errors)
        
        
        username = self.request.cookies.get("name")
        user = entities.User.query(entities.User.name == username).get()  
        total_pages = user.n_links
        if user.validation_type == 'MOBILE':
            current_pages = entities.PageResultGoogle.query(entities.PageResultGoogle.user == user.name).count()
        else:
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
        if user.validation_type == 'MOBILE':
            current_pages = entities.PageResultGoogle.query(entities.PageResultGoogle.user == user.name).count()
        else:
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
        if user.validation_type == 'MOBILE':
            current_pages = entities.PageResultGoogle.query(entities.PageResultGoogle.user == user.name).count()
        else:
            current_pages = entities.PageResult.query(entities.PageResult.user == user.name).count()
            
        progress = int((current_pages * 100)/total_pages)
        
        self.response.write(json.dumps(progress))
        
class Rankings(webapp2.RequestHandler):
    def get(self):
        
        if self.request.cookies.get("name"):
            self.response.headers['Content-Type'] = 'text/html'
            progress = 0
            reports = []
            scores = []
            webs = []
            
            try:
                username = self.request.cookies.get("name")
                user = entities.User.query(entities.User.name == username).get()  
                total_pages = user.n_links
                if user.validation_type == 'MOBILE':
                    current_pages = entities.PageResultGoogle.query(entities.PageResultGoogle.user == user.name).count()
                else:
                    current_pages = entities.PageResult.query(entities.PageResult.user == user.name).count()
                progress = int((current_pages * 100)/total_pages)
                
                reports = entities.Report.query().fetch()
                for r in reports:
                    scores.append(r.score)
                    webs.append(r.web)
                
            except:
                error_message = 'Error accessing the database: Required more quota than is available. Come back after 24h.'
        
        else:
            self.redirect('/login')
        
        template_values={'progress':progress,'scores':scores,'webs':webs}
        template = JINJA_ENVIRONMENT.get_template('template/rankings.html')
        self.response.write(template.render(template_values))
    
class GoogleValidation(webapp2.RequestHandler):
    def post(self):
        
        url = self.request.get('url')
        result = validators.GoogleMobileValidation(url)
        
        ruleResults = result['formattedResults']['ruleResults']
        scoreUsability = result['ruleGroups']['USABILITY']['score']
        scoreSpeed = result['ruleGroups']['SPEED']['score']
        ruleNames = []
        ruleImpacts = []
        types = []
        summaries = []
        urlBlocks = []
        
        index = 0
        for r in ruleResults:
            ruleNames.append(result['formattedResults']['ruleResults'][r]['localizedRuleName'])
            ruleImpacts.append(result['formattedResults']['ruleResults'][r]['ruleImpact'])
            types.append(result['formattedResults']['ruleResults'][r]['groups'][0])
            if 'summary' in result['formattedResults']['ruleResults'][r]:
                summary = result['formattedResults']['ruleResults'][r]['summary']
                
                summaryParsed = summary['format']
                if 'args' in summary:
                    for i in range(0,len(summary['args'])):
                        if summary['args'][i]['key'] == 'LINK':
                            summaryParsed = summaryParsed.replace('{{BEGIN_LINK}}','<a href='+summary['args'][i]['value']+'>')
                            summaryParsed = summaryParsed.replace('{{END_LINK}}','</a>')
                        else:
                            summaryParsed = summaryParsed.replace('{{'+summary['args'][i]['key']+'}}', summary['args'][i]['value'])
            else:
                summaryParsed = 'No summary for this rule'
            
            summaries.append(summaryParsed)
            
            v = []
            urlBlocks.append(v)
                
            if 'urlBlocks' in result['formattedResults']['ruleResults'][r]:
                
                for block in result['formattedResults']['ruleResults'][r]['urlBlocks']:
                    urlBlockHeader = block['header']
                
                    urlBlockHeaderParsed = urlBlockHeader['format']
                    if 'args' in urlBlockHeader:
                        for i in range(0,len(urlBlockHeader['args'])):
                            if urlBlockHeader['args'][i]['key'] == 'LINK':
                                urlBlockHeaderParsed = urlBlockHeaderParsed.replace('{{BEGIN_LINK}}','<a href='+urlBlockHeader['args'][i]['value']+'>')
                                urlBlockHeaderParsed = urlBlockHeaderParsed.replace('{{END_LINK}}','</a>')
                            else:
                                urlBlockHeaderParsed = urlBlockHeaderParsed.replace('{{'+urlBlockHeader['args'][i]['key']+'}}', urlBlockHeader['args'][i]['value'])
                    
                    urlBlockUrlsList = []
                        
                    if 'urls' in block:    
                        urlBlockUrls = block['urls']
                        for u in range(0,len(urlBlockUrls)):
                            res = urlBlockUrls[u]['result']
                            resultParsed = res['format']
                            if 'args' in res:
                                for j in range(0,len(res['args'])):
                                    if res['args'][j]['key'] == 'LINK':
                                        resultParsed = resultParsed.replace('{{BEGIN_LINK}}','<a href='+res['args'][j]['value']+'>')
                                        resultParsed = resultParsed.replace('{{END_LINK}}','</a>')
                                    else:
                                        resultParsed = resultParsed.replace('{{'+res['args'][j]['key']+'}}', res['args'][j]['value'])
                                        
                            urlBlockUrlsList.append(resultParsed)
                    
                    urlBlock = {'urlBlockHeader': urlBlockHeaderParsed, 'urlBlockUrlsList': urlBlockUrlsList}
                    urlBlocks[index].append(urlBlock)
                    
            index+=1
        
        
        username = self.request.get("username")
        number = int(self.request.get("number"))
        user = entities.User.query(entities.User.name == username).get()
        
        content = { 'scoreUsability': scoreUsability,
            'scoreSpeed': scoreSpeed,
            'ruleNames': ruleNames,
            'ruleImpacts': ruleImpacts,
            'types': types,
            'summaries': summaries,
            'urlBlocks': urlBlocks
        }
        
        page_result = entities.PageResultGoogle()
        page_result.user = user.name
        page_result.url = url
        page_result.scoreSpeed = scoreSpeed
        page_result.scoreUsability = scoreUsability
        page_result.content = json.dumps(content)
        page_result.number = number
        page_result.put()
        

class GoogleReports(webapp2.RequestHandler):
    def get(self):
        if self.request.cookies.get("name"):
            
            username = self.request.cookies.get("name")
            error_message = ''
            reports = ''
            progress = 0
            
            try:
                user = entities.User.query(entities.User.name == username).get()
                qry = entities.PageResultGoogle.query(entities.PageResultGoogle.user == user.name).order(entities.PageResultGoogle.number)
                if qry.count() == user.n_links:
                
                    report = entities.ReportGoogle()
                    report.web = user.root_link
                    report.validation_type = user.validation_type
                    report.onlyDomain = user.onlyDomain
                    report.user = user.name
                    report.results = qry.fetch()
                    report.pages = len(report.results)
                
                    try:
                        report.put()
                        
                    except:
                        error_message = 'Error: Unable to update database: too many errors in your website: '+user.root_link
                    
                        
                    ndb.delete_multi(
                        entities.PageResultGoogle.query(entities.PageResultGoogle.user == user.name).fetch(keys_only=True)
                    )
                    
                    # Reset global variables for user
                    user.n_links = -1
                    user.root_link = ''
                    user.validation_type = ''
                    user.onlyDomain = None
                    user.lock = False
                    user.put()
                    
                    
                    
                    # Calculate score
                    
                    scoreUsability = 0
                    scoreSpeed = 0
                    
                    for result in report.results:
                        content = json.loads(result.content)
                        scoreUsability = scoreUsability + content['scoreUsability']
                        scoreSpeed = scoreSpeed + content['scoreSpeed']
                    
                    scoreUsability = scoreUsability/len(report.results)
                    scoreSpeed = scoreSpeed/len(report.results)
                        
                    
                    report.scoreUsability = scoreUsability
                    report.scoreSpeed = scoreSpeed
                    report.put()
                                
                reports = entities.ReportGoogle.query().fetch()
                
                username = self.request.cookies.get("name")
                user = entities.User.query(entities.User.name == username).get()  
                total_pages = user.n_links
                if user.validation_type == 'MOBILE':
                    current_pages = entities.PageResultGoogle.query(entities.PageResultGoogle.user == user.name).count()
                else:
                    current_pages = entities.PageResult.query(entities.PageResult.user == user.name).count()
                progress = int((current_pages * 100)/total_pages)
                
            except:
                error_message = 'Error accessing the database: Required more quota than is available. Come back after 24h.'
                
            self.response.headers['Content-Type'] = 'text/html'
            
            template_values={'reports':reports, 'error_message': error_message, 'progress':progress}
            template = JINJA_ENVIRONMENT.get_template('template/google_reports.html')
            self.response.write(template.render(template_values))
        
        else:
            self.redirect('/login')
        
        
class GoogleReportViewer(webapp2.RequestHandler):
    def get(self):
        
        if self.request.cookies.get("name"):
            report_id = long(self.request.get('id'))
            reports = entities.ReportGoogle.query().fetch()
            report = ''
            for r in reports:
                if r.key.id() == report_id:
                    report = r
                    break
            pages = len(report.results)
        else:
            self.redirect('/login')
        
        
        username = self.request.cookies.get("name")
        user = entities.User.query(entities.User.name == username).get()  
        total_pages = user.n_links
        if user.validation_type == 'MOBILE':
            current_pages = entities.PageResultGoogle.query(entities.PageResultGoogle.user == user.name).count()
        else:
            current_pages = entities.PageResult.query(entities.PageResult.user == user.name).count()
        progress = int((current_pages * 100)/total_pages)
        
        
        template_values={'report':report, 'pages':pages, 'progress':progress}
        template = JINJA_ENVIRONMENT.get_template('template/google_report_view.html')
        self.response.write(template.render(template_values))
        
class GooglePageViewer(webapp2.RequestHandler):
    def get(self):
        if self.request.cookies.get("name"):
            number = int(self.request.get("number"))
            report_id = long(self.request.get('id'))
            reports = entities.ReportGoogle.query().fetch()
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
        if user.validation_type == 'MOBILE':
            current_pages = entities.PageResultGoogle.query(entities.PageResultGoogle.user == user.name).count()
        else:
            current_pages = entities.PageResult.query(entities.PageResult.user == user.name).count()
        progress = int((current_pages * 100)/total_pages)
        
        content = json.loads(report.results[number].content)
        scoreUsability = content['scoreUsability']
        scoreSpeed = content['scoreSpeed']
        ruleNames = content['ruleNames']
        ruleImpacts = content['ruleImpacts']
        types = content['types']
        summaries = content['summaries']
        urlBlocks = content['urlBlocks']
        
        
        template_values={
            'web': report.web,
            'scoreUsability': scoreUsability,
            'scoreSpeed': scoreSpeed,
            'ruleNames': ruleNames,
            'ruleImpacts': ruleImpacts,
            'types': types,
            'summaries': summaries,
            'urlBlocks': urlBlocks,
            'progress' : progress
        }
        
        template = JINJA_ENVIRONMENT.get_template('template/google_page_view.html')
        self.response.write(template.render(template_values))

class Users(webapp2.RequestHandler):
    def get(self):
        
        if self.request.cookies.get("name"):
        
            username = self.request.cookies.get("name")
            user = entities.User.query(entities.User.name == username).get()  
            total_pages = user.n_links
            if user.validation_type == 'MOBILE':
                current_pages = entities.PageResultGoogle.query(entities.PageResultGoogle.user == user.name).count()
            else:
                current_pages = entities.PageResult.query(entities.PageResult.user == user.name).count()
            progress = int((current_pages * 100)/total_pages)
            
            users = entities.User.query().fetch()
            
            template_values={'progress':progress,'users':users}
            template = JINJA_ENVIRONMENT.get_template('template/users.html')
            self.response.write(template.render(template_values))
        
        else:
            self.redirect('/login')

class EditUser(webapp2.RequestHandler):
    def post(self):
        
        full_name = self.request.get("edit-full_name")
        email = self.request.get("edit-email")
        group = self.request.get("edit-group")
        password = self.request.get("edit-password")
        name = self.request.get("name")
        
        user = entities.User.query(entities.User.name==name).get()
        if full_name != "": user.full_name = full_name
        if email != "": user.email = email
        if group != "": user.group = group
        if password != "": user.password = password
        
        user.put()
        
        time.sleep(0.1)
        self.redirect("/users")
        
class DeleteUser(webapp2.RequestHandler):
    def post(self):

        name = self.request.get("name")
        
        user = entities.User.query(entities.User.name==name).get()
        
        user.key.delete()
        
        time.sleep(0.1)
        self.redirect("/users")
        
class CreateUser(webapp2.RequestHandler):
    def post(self):

        name = self.request.get("create-name")
        full_name = self.request.get("create-full_name")
        email = self.request.get("create-email")
        group = self.request.get("create-group")
        password = self.request.get("create-password")
        
        user = entities.User()
        
        user.name = name
        user.full_name = full_name
        user.email = email
        user.group = group
        user.password = password
        
        user.put()
        
        time.sleep(0.1)
        self.redirect("/users")
        
        
urls = [('/',MainPage),
        ('/login',login),
        ('/validation',Validation),
        ('/qvalidation',QueueValidation),
        ('/reports',Reports),
        ('/viewreport',ReportViewer),
        ('/viewpage',PageViewer),
        ('/logout',logout),
        ('/progress',GetScanProgress),
        ('/rankings',Rankings),
        ('/google-reports',GoogleReports),
        ('/google-validation',GoogleValidation),
        ('/google-viewreport',GoogleReportViewer),
        ('/google-viewpage',GooglePageViewer),
        ('/users',Users),
        ('/edit-user',EditUser),
        ('/create-user',CreateUser),
        ('/delete-user',DeleteUser),
       ]

application = webapp2.WSGIApplication(urls, debug=True)


def main():
    os.environ['TZ'] = 'Europe/Madrid'
    time.tzset()
    run_wsgi_app(application)

if __name__ == "__main__":
    main()
