#!/usr/bin/python
# -⁻- coding: UTF-8 -*-

'''
Spiderbot: Web Validation Robot
Copyright (C) 2015  Julio Martínez Martínez-Checa

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

Contact: julioxus@gmail.com

University of Granada, hereby disclaims all copyright
interest in the program `Spiderbot' written 
by Julio Martínez Martínez-Checa.

signature of Julio Martínez Martínez-Checa, 23 June 2015
Julio Martínez Martínez-Checa, Student at the University of Granada.
'''

import webapp2
import jinja2
import os
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.api import taskqueue
import urllib2
import time
from google.appengine.ext import ndb
import json

from spiderbot import validators
from spiderbot import parsers
import model

DEFAULT_MAX_PAGS = 25
'''páginas por defecto'''
DEFAULT_DEPTH = 2
'''profundidad por defecto'''


# Declaración del entorno de jinja2 y el sistema de templates.

JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)
'''entorno de plantillas jinja2'''

head = JINJA_ENVIRONMENT.get_template('template/head.html').render()
'''cabecera html común'''
footer = JINJA_ENVIRONMENT.get_template('template/footer.html').render()
'''footer html común'''
global error_login
'''mensaje de error al hacer login'''
error_login  = ''

class MainPage(webapp2.RequestHandler):
    '''
    Clase manejadora de la página principal
    '''
    def get(self):
        """
        Respuesta GET de la página principal
        """
        
        if self.request.cookies.get("name"):
            self.response.headers['Content-Type'] = 'text/html'
            progress = 0
            try:
                username = self.request.cookies.get("name")
                user = model.User.query(model.User.name == username).get()  
                total_pages = user.n_links
                if user.validation_type == 'MOBILE':
                    current_pages = model.PageResultGoogle.query(model.PageResultGoogle.user == user.name).count()
                elif user.validation_type == 'RANK':
                    current_pages = model.PageResultGoogle.query(model.PageResultGoogle.user == user.name).count() + model.PageResult.query(model.PageResult.user == user.name).count()
                else:
                    current_pages = model.PageResult.query(model.PageResult.user == user.name).count()
                progress = int((current_pages * 100)/total_pages)
                
            except:
                print ''
            
            template_values={'head': head, 'footer': footer, 'progress':progress, 'DEFAULT_MAX_PAGS': DEFAULT_MAX_PAGS, 'DEFAULT_DEPTH': DEFAULT_DEPTH, 'user': user}
            template = JINJA_ENVIRONMENT.get_template('template/index.html')
            self.response.write(template.render(template_values))
                
        else:
            self.redirect('/login')
        
class login(webapp2.RequestHandler):
    '''
    Clase manejadora de la página de login.
    '''
    def get(self):
        
        """
        Respuesta GET del formulario de login
        """
        
        global error_login
        self.response.headers['Content-Type'] = 'text/html'
        template_values={'error_message': error_login}
        error_login = ''
        template = JINJA_ENVIRONMENT.get_template('template/login.html')
        self.response.write(template.render(template_values))
        
    def post(self):
        """
        Respuesta POST del formulario de login.
        
        @type user: str
        @param user: nombre de usuario
        @type password: str
        @param password: contraseña del usuario
        """
        
        global error_login
        name = self.request.get('user')
        user = model.User.query(model.User.name==name).get()
        if user is None:
            error_login = 'Invalid user name'
            self.redirect('/login')
            return None
        
        if name is not None:
            password = self.request.get('password')
            if user.password==password:
                self.response.headers.add_header('Set-Cookie',"name="+str(user.name))
                self.response.headers['Content-Type'] = 'text/html'
                self.redirect('/')
            else:
                error_login = 'Incorrect password'
                self.redirect('/login')
        else:
            self.response.write('Please, enter a user name')
            
class logout(webapp2.RequestHandler):
    '''
    Clase manejadora del logout
    '''
    def get(self):
        """
        Respuesta GET que cierra la sesión eliminando la cookie
        """
        self.response.headers.add_header("Set-Cookie", "name=; Expires=Thu, 01-Jan-1970 00:00:00 GMT")
        self.redirect('/')

class QueueValidation(webapp2.RequestHandler):
    '''
    Clase manejadora del encolado de validaciones.
    '''
    def post(self):
        """
        Respuesta POST al enviar el formulario de la página de inicio que se encarga
        de obtener los links a partir de la raíz y ejecutar el análisis seleccionado
        metiendo las tareas correspondientes en la cola de tareas.
        
        Las variables de estado del usuario también se modifican usando los parámetros
        seleccionados en el formulario
        
        @type url: str
        @param url: web raíz que se va a analizar
        @type max_pags: int
        @param max_pags: número máximo de páginas que se van a analizar
        @type depth: int
        @param depth: profundidad del análisis
        @type onlyDomain: bool
        @param onlyDomain: indica si es sólo dominio
        @type reg: str
        @param reg: expresión regular que filtra páginas web del análisis
        """
        username = self.request.cookies.get("name")
        user = model.User.query(model.User.name == username).get()
        
        if user.lock == False:
            user.lock = True
            
            root = self.request.get('url')
            max_pags = self.request.get('max_pags')
            depth = self.request.get('depth')
            onlyDomain = self.request.get("onlyDomain")
            reg = self.request.get("reg")
            
            if reg is None: reg = '.*'
            
            if onlyDomain:
                onlyDomain = True
            else:
                onlyDomain = False
                
            if max_pags == '':
                max_pags = DEFAULT_MAX_PAGS
            if depth == '':
                depth = DEFAULT_DEPTH
                
            max_pags = int(max_pags)
            depth = int(depth)
                
            
            option = self.request.get('optradio')
            retrys = 3
            while retrys > 0:
                try:
                    links = validators.getAllLinks(root, depth, max_pags, onlyDomain,reg)
                    retrys = 0
                except:
                    retrys-=1
                    if retrys == 0:
                        self.response.write("Error getting links")
                        return None
            
            user.root_link = root
            user.onlyDomain = onlyDomain
            user.n_links = len(links)
            user.validation_type = option
            
            if option == 'RANK':
                options = ['HTML', "WCAG2-A", "WCAG2-AA", "CHECK AVAILABILITY", "MOBILE"]
                max_pags = DEFAULT_MAX_PAGS
                depth = DEFAULT_DEPTH
                onlyDomain = True
                reg = '.*'
                user.n_links = len(links)*len(options)
            else:
                options = [option]
                
            for option in options:
                links = validators.getAllLinks(root, depth, max_pags, onlyDomain,reg)
                i = 0
                deleted = 0
                
                while i < len(links):
                    if (option == 'WCAG2-A' or option == 'WCAG2-AA' or option == 'MOBILE') and links[i][1] == 'css':
                        del links[i]
                        i = -1
                        deleted += 1
                    i+=1
                
                user.n_links -= deleted
                
                user.put()
                
                alphaqueue = taskqueue.Queue('alphaqueue')
                number = 0
                
                while(user.root_link == ''):
                    time.sleep(1)
                for link in links:
                    #Add the task to the corresponding queue.
                    if option == 'MOBILE':
                        alphaqueue.add(taskqueue.Task(url='/google-validation', params={'url': link[0], 'username': username, 'number': number}),False)
                    else:
                        alphaqueue.add(taskqueue.Task(url='/validation', params={'url': link[0], 'page_type': link[1], 'optradio': option, 'username': username, 'number': number}),False)
                    number += 1
                    
            self.redirect('/')
            
        else:
            self.response.write("You already have pending tasks executing, wait and try again later")
        
class Validation(webapp2.RequestHandler):
    '''
    Clase manejadora de la validación de una página.
    '''
    def post(self):
        '''
        Respuesta POST que realiza una validación de una página en función de los parámetros que se
        le pasen por el método POST.
        
        Esta página se almacenará en la base de datos.
        
        @type optradio: str
        @param optradio: Opción que indica el tipo de página:
            - HTML
            - WCAG2.0-A
            - WCAG2.0-AA
            - CHECK AVAILABILITY
        @type username: str
        @param username: Nombre de usuario que realiza la validación
        @type url: str
        @param url: web que se va a validar
        @type number: int
        @param number: número de la página actual
        '''
        state = 'ERROR'
        retrys = 3
        option = self.request.get('optradio')
        
        while retrys > 0 and (state == 'ERROR' or (state == 'FAIL' and option == 'CHECK AVAILABILITY') ):
            
            content = ''
            
            try:
                f = self.request.get('url')
                page_type = self.request.get('page_type')
            except urllib2.HTTPError, e:
                content += 'Error: ' + e
                state = 'ERROR'
            
            errors = 0
            list_errors = []
            
            
            if option == 'HTML':
                result = ''
                
                try:
                    result = validators.validate(f,page_type)
                    if page_type == 'css':
                        parse = parsers.parseCSSValidation(result, f)                      
                    else:
                        parse = parsers.parseHTMLValidation(result, f)
                    
                    content = parse['out']
                    errors = parse['errors']
                    state = parse['state']
                    list_errors = parse['list_errors']
                    
                except:
                    content += "Error parsing URL. Maybe server IP is blocked by W3C service (http://validator.w3.org/)"
                    state = 'ERROR'
                         
                    
            elif option == 'CHECK AVAILABILITY':
                code = validators.checkAvailability(f)
                parse = parsers.parseAvailabilityValidation(code)
                content = parse['out']
                errors = parse['errors']
                state = parse['state']
                
            elif option == 'WCAG2-A' or option == 'WCAG2-AA':
                try:
                    if option == 'WCAG2-A':
                        result = validators.validateWCAG(f,'WCAG2-A')
                    else:
                        result = validators.validateWCAG(f,'WCAG2-AA')
                    
                    parse = parsers.parseWCAGValidation(result, f)
                    content = parse['out']
                    errors = parse['errors']
                    state = parse['state']
                    list_errors = parse['list_errors']
                    
                except:
                    content += "Achecker service not working properly \n\n"
                    state = 'ERROR'
                
            retrys -= 1
        
        username = self.request.get("username")
        number = int(self.request.get("number"))
        user = model.User.query(model.User.name == username).get()
        
        page_result = model.PageResult()
        page_result.user = user.name
        page_result.url = f
        page_result.content = content
        page_result.state = state
        page_result.errors = errors
        page_result.number = number
        page_result.list_errors = json.dumps(list_errors)
        page_result.validation_type = option
        page_result.put()
        
def insertReport(username,validation_type,isRank):
    '''
    Inserta informe ejecutado por el usuario username de tipo validation_type
    e indicamos si se trata de parte de informe de ranking.
    
    El informe obtiene las páginas analizadas de la base de datos usando los parámetros
    de entrada proporcionados. A partir de las páginas cuenta las páginas con error y
    la lista de errores. Con estos valores calcula la puntuación que se le asignará.
    
    Si el informe es de Ranking y ya existía se actualiza en lugar de crear uno nuevo.
    
    @type username: str
    @param username: nombre de usuario
    @type validation_type: str
    @param validation_type: tipo de validación. Los valores que puede tomar son:
        - HTML
        - WCAG2.0-A
        - WCAG2.0-AA
        - CHECK AVAILABILITY
    @type isRank: bool
    @param isRank: indica si es parte de un informe de ranking
    '''
    list_errors = []
    user = model.User.query(model.User.name == username).get()
    qry = model.PageResult.query(model.PageResult.user == user.name).filter(model.PageResult.validation_type == validation_type).order(model.PageResult.number)
   
    report = None
    
    # Actualizar informe de ranking si ya existe
    if isRank:
        report = model.Report.query(model.Report.isRank == True).filter(model.Report.validation_type == validation_type).filter(model.Report.web == user.root_link).get()
                
        if report is None:
            report = model.Report()
    else:
        report = model.Report()

    # Crear el objeto informe con todos los parámetros obtenidos
    report.web = user.root_link
    report.validation_type = validation_type
    report.onlyDomain = user.onlyDomain
    report.user = user.name
    report.results = qry.fetch()
    report.pages = len(report.results)
    report.isRank = isRank
    
    # Contar los errores y páginas con error encontradas
    error_pages = 0
    errors = 0
    for result in report.results:
        if result.state == 'FAIL' or result.state == 'ERROR':
            error_pages+=1
        errors += result.errors
        
        list_errors.extend(json.loads(result.list_errors))

        # Borrar elementos repetidos en la lista
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
    
    # Completar el objeto informe con los datos obtenidos anteriormente
    report.error_pages = error_pages
    report.errors = errors
    report.list_errors = json.dumps(list_errors);

    
    # Eliminar las páginas sueltas de la base de datos que ya se han intruducido en el informe
    ndb.delete_multi(
        model.PageResult.query(model.PageResult.user == user.name).filter(model.PageResult.validation_type == validation_type).fetch(keys_only=True)
    )
    
    # Calcular puntuación
     
    distinct_errors = (len(json.loads(report.list_errors)))
    error_pages = float(report.error_pages)
    pages = float(report.pages)
    
    # Calcular los dos valores usados para calcular la puntuación
    
    value1 = error_pages / pages # Ratio de páginas con error
     
    if pages > 0:
        value2 = distinct_errors / pages # Errores distintos por página
    else:
        value2 = 0
        
    
    # Normalización de valores
     
    # Para el primer valor estableceremos el rango [0 1]
    # Obviamente nunca habrá mas páginas que páginas con error por tanto el peor caso
    # seria un resultado de 1 que implica que todas las paginas muestran errores
    # El mejor caso seria un valor de 0 que implica que no existen paginas con errores
     
    # Para tener una puntuación sobre 10 multiplicamos el valor y obtenemos el inverso
     
    value1_norm = 10 - value1 * 10
     
     
    # Para el segundo valor establecermos el rango [0 100]
     
    # 0 implica que no existen errores distintos y sería la maxima nota
    # 10 implicaria que existen mas de 10 fallos distintos por página con error
    # Limitamos en 10 por tanto
    
    
    # Función ajustada a la curva
    
    a = 1.595;
    b = 0.005949;
    
    value2 = a*value2/(1+b*value2*value2)
     
    if value2>=10:
        value2 = 10
     
    # Obtener el inverso para normalizar
     
    value2_norm = 10 - value2;
     
    # Calcular la puntuacion final
     
    score = round(0.25 * value1_norm + 0.75 * value2_norm,1)
    if validation_type == 'CHECK AVAILABILITY':
        score = round(value1_norm)
    
    report.score = score
    
    # Insertar informe en la base de datos
    report.put()
        

      
class Reports(webapp2.RequestHandler):
    '''
    Clase manejadora de la página de visualización e inserción de los informes.
    '''
    def get(self):
        '''
        Respuesta GET de la página de informes. Se encarga de mostrar los informes realizados por
        el usuario.
        
        Además se encarga de insertar los informes cuando el proceso de validación termina.
        '''
        if self.request.cookies.get("name"):
            
            username = self.request.cookies.get("name")
            error_message = ''
            reports = ''
            reportsGoogle = ''
            progress = 0
            
            try: 
                user = model.User.query(model.User.name == username).get()
                qry = model.PageResult.query(model.PageResult.user == user.name).order(model.PageResult.number)
                qry2 = model.PageResultGoogle.query(model.PageResultGoogle.user == user.name).order(model.PageResultGoogle.number)
    
                if user.validation_type == 'MOBILE' and qry2.count() == user.n_links:
                    insertGoogleReport(username,False)
                    
                    # Reinicia las variables de estado del usuario
                    user.n_links = -1
                    user.root_link = ''
                    user.validation_type = ''
                    user.onlyDomain = None
                    user.lock = False
                    user.put()
                    
                    self.redirect('/reports')
                        
                elif user.validation_type != 'MOBILE' and qry.count() == user.n_links:
                    insertReport(username,user.validation_type,False)
                
                    # Reinicia las variables de estado del usuario
                    user.n_links = -1
                    user.root_link = ''
                    user.validation_type = ''
                    user.onlyDomain = None
                    user.lock = False
                    user.put()
                        
                    self.redirect('/reports')
                       
                reports = model.Report.query().fetch()
                reportsGoogle = model.ReportGoogle.query().fetch()
                
                user = model.User.query(model.User.name == username).get()  
                total_pages = user.n_links
                if user.validation_type == 'MOBILE':
                    current_pages = model.PageResultGoogle.query(model.PageResultGoogle.user == user.name).count()
                elif user.validation_type == 'RANK':
                    current_pages = model.PageResultGoogle.query(model.PageResultGoogle.user == user.name).count() + model.PageResult.query(model.PageResult.user == user.name).count()
                else:
                    current_pages = model.PageResult.query(model.PageResult.user == user.name).count()
                progress = int((current_pages * 100)/total_pages)
                
            except:
                error_message = 'Error accessing the database: Required more quota than is available. Come back after 24h.'
                
            self.response.headers['Content-Type'] = 'text/html'
            
            template_values={'head': head, 'footer': footer, 'reports':reports, 'reportsGoogle':reportsGoogle, 'error_message': error_message, 'progress':progress, 'user': user}
            template = JINJA_ENVIRONMENT.get_template('template/reports.html')
            self.response.write(template.render(template_values))
        
        else:
            self.redirect('/login')
            
            
class ReportViewer(webapp2.RequestHandler):
    '''
    Clase manejadora de la visualización de un informe.
    '''
    def get(self):
        '''
        Respuesta GET de la vista general de un informe. Muestra el informe pasado como argumento al
        método GET.
        
        @type id: long
        @param id: identificador del informe que se está visualizando.
        '''
        if self.request.cookies.get("name"):
            report_id = long(self.request.get('id'))
            reports = model.Report.query().fetch()
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
        user = model.User.query(model.User.name == username).get()  
        total_pages = user.n_links
        if user.validation_type == 'MOBILE':
            current_pages = model.PageResultGoogle.query(model.PageResultGoogle.user == user.name).count()
        elif user.validation_type == 'RANK':
            current_pages = model.PageResultGoogle.query(model.PageResultGoogle.user == user.name).count() + model.PageResult.query(model.PageResult.user == user.name).count()
        else:
            current_pages = model.PageResult.query(model.PageResult.user == user.name).count()
        progress = int((current_pages * 100)/total_pages)
            
        template_values={'head': head, 'footer': footer, 'report':report, 'list_errors': list_errors, 'pages':pages, 'progress':progress, 'user': user}
        template = JINJA_ENVIRONMENT.get_template('template/report_view.html')
        self.response.write(template.render(template_values))
        
class PageViewer(webapp2.RequestHandler):
    '''
    Clase manejadora de la página de un informe.
    '''
    def get(self):
        '''
        Respuesta GET de la página de un informe. Muestra el informe pasado como argumento al
        método GET.
        
        @type id: long
        @param id: identificador del informe que se está visualizando.
        @type number: int
        @param number: número de página que se está visualizando
        '''
        if self.request.cookies.get("name"):
            number = int(self.request.get("number"))
            report_id = long(self.request.get('id'))
            reports = model.Report.query().fetch()
            report = ''
            for r in reports:
                if r.key.id() == report_id:
                    report = r
                    break
        else:
            self.redirect('/login')
        
        username = self.request.cookies.get("name")
        user = model.User.query(model.User.name == username).get()  
        total_pages = user.n_links
        if user.validation_type == 'MOBILE':
            current_pages = model.PageResultGoogle.query(model.PageResultGoogle.user == user.name).count()
        elif user.validation_type == 'RANK':
            current_pages = model.PageResultGoogle.query(model.PageResultGoogle.user == user.name).count() + model.PageResult.query(model.PageResult.user == user.name).count()
        else:
            current_pages = model.PageResult.query(model.PageResult.user == user.name).count()
        progress = int((current_pages * 100)/total_pages)
        
        template_values={'head':head, 'footer':footer, 'result':report.results[number],'progress':progress, 'user':user}
        template = JINJA_ENVIRONMENT.get_template('template/page_view.html')
        self.response.write(template.render(template_values))
        
class GetScanProgress(webapp2.RequestHandler):
    '''
    Clase manejadora del progreso de validación.
    '''
    def get(self):
        '''
        Respuesta GET que obtiene el progreso de la validación que se está realizando. Este método
        es llamado por todas las páginas mediante AJAX.
        '''
        username = self.request.cookies.get("name")
        user = model.User.query(model.User.name == username).get()
        
        total_pages = user.n_links
        if user.validation_type == 'MOBILE':
            current_pages = model.PageResultGoogle.query(model.PageResultGoogle.user == user.name).count()
        elif user.validation_type == 'RANK':
            current_pages = model.PageResultGoogle.query(model.PageResultGoogle.user == user.name).count() + model.PageResult.query(model.PageResult.user == user.name).count()
        else:
            current_pages = model.PageResult.query(model.PageResult.user == user.name).count()
        progress = int((current_pages * 100)/total_pages)
        
        self.response.write(json.dumps(progress))
        
class Rankings(webapp2.RequestHandler):
    '''
    Clase manejadora de la página de visualización de los Rankings.
    '''
    def get(self):
        '''
        Respuesta GET que obtiene las puntuaciones de los tests de ranking para mostrarlos.
        '''
        if self.request.cookies.get("name"):
            self.response.headers['Content-Type'] = 'text/html'
            progress = 0
            error_message = ''
            scores = []
            html_scores = []
            wcag2A_scores = []
            wcag2AA_scores = []
            availability_scores = []
            mobile_scores = []
            
            webs = []
            
            try:
                username = self.request.cookies.get("name")
                user = model.User.query(model.User.name == username).get()  
                total_pages = user.n_links
                if user.validation_type == 'MOBILE':
                    current_pages = model.PageResultGoogle.query(model.PageResultGoogle.user == user.name).count()
                elif user.validation_type == 'RANK':
                    current_pages = model.PageResultGoogle.query(model.PageResultGoogle.user == user.name).count() + model.PageResult.query(model.PageResult.user == user.name).count()
                else:
                    current_pages = model.PageResult.query(model.PageResult.user == user.name).count()
                progress = int((current_pages * 100)/total_pages)
                
                reportsRank = model.ReportRank.query().fetch()
                for r in reportsRank:
                    scores.append(r.score)
                    html_scores.append(model.Report.get_by_id(long(r.html_test)).score)
                    wcag2A_scores.append(model.Report.get_by_id(long(r.wcag2A_test)).score)
                    wcag2AA_scores.append(model.Report.get_by_id(long(r.wcag2AA_test)).score)
                    availability_scores.append(model.Report.get_by_id(long(r.availability_test)).score)
                    mobile_scores.append(model.ReportGoogle.get_by_id(long(r.mobile_test)).score)
                    webs.append(r.web)
                
            except:
                error_message = 'Error accessing the database: Required more quota than is available. Come back after 24h.'
        
        else:
            self.redirect('/login')
        
        template_values={'head': head, 'footer': footer, 'progress':progress,'scores':scores, 'html_scores': html_scores, 'wcag2A_scores': wcag2A_scores,
                         'wcag2AA_scores': wcag2AA_scores, 'availability_scores': availability_scores,
                         'mobile_scores': mobile_scores, 'webs':webs, 'error_message':error_message, 'user': user}
        template = JINJA_ENVIRONMENT.get_template('template/rankings.html')
        self.response.write(template.render(template_values))
    
class GoogleValidation(webapp2.RequestHandler):
    '''
    Clase manejadora de la validación de un informe de Google para móviles.
    '''
    def post(self):
        '''
        Respuesta POST que valida una página del test de móviles de Google.
        
        Esta página se almacenará en la base de datos.
        
        @type url: str
        @param url: página web que se validará
        @type username: str
        @param username: usuario que realiza la validación
        @type number: int
        @param number: número de página que se va a validar
        '''
        url = self.request.get('url')
        result = validators.GoogleMobileValidation(url)
        
        parse = parsers.parseGoogleValidation(result,url)
        
        username = self.request.get("username")
        number = int(self.request.get("number"))
        user = model.User.query(model.User.name == username).get()
        
        content = { 'head': head, 'footer': footer, 'scoreUsability': parse['scoreUsability'],
            'scoreSpeed': parse['scoreSpeed'],
            'ruleNames': parse['ruleNames'],
            'ruleImpacts': parse['ruleImpacts'],
            'types': parse['types'],
            'summaries': parse['summaries'],
            'urlBlocks': parse['urlBlocks']
        }
        
        page_result = model.PageResultGoogle()
        page_result.user = user.name
        page_result.url = url
        page_result.scoreSpeed = parse['scoreSpeed']
        page_result.scoreUsability = parse['scoreUsability']
        page_result.content = json.dumps(content)
        page_result.number = number
        page_result.put()
        

def insertGoogleReport(username,isRank):
    '''
    Inserta informe ejecutado por el usuario username del test de móviles de Google,
    e indicamos si se trata de un informe de ranking.
    
    El informe obtiene las páginas analizadas de la base de datos usando los parámetros
    de entrada proporcionados. Obtiene la puntuación de usabilidad y velocidad de cada
    página, realizando una media de cada una para obtener la nota general de cada
    categoría. Finalmente calcula la nota final del test usando la media geométrica de
    ambas puntuaciones mencionadas anteriormente.
    
    Si el informe es de Ranking y ya existía se actualiza en lugar de crear uno nuevo.
    
    @type username: str
    @param username: nombre de usuario
    @type isRank: bool
    @param isRank: indica si es parte de un informe de ranking
    '''
    user = model.User.query(model.User.name == username).get()
    qry = model.PageResultGoogle.query(model.PageResultGoogle.user == user.name).order(model.PageResultGoogle.number)
       
    # Update if rank report of this web already exists
    if isRank:
        report = model.ReportGoogle.query(model.ReportGoogle.isRank == True).filter(model.ReportGoogle.web == user.root_link ).get()
        if report == None:
            report = model.ReportGoogle()
    else:
        report = model.ReportGoogle()
    report.web = user.root_link
    report.validation_type = 'MOBILE'
    report.onlyDomain = user.onlyDomain
    report.user = user.name
    report.results = qry.fetch()
    report.pages = len(report.results)
    report.isRank = isRank

    report.put()
        
    ndb.delete_multi(
        model.PageResultGoogle.query(model.PageResultGoogle.user == user.name).fetch(keys_only=True)
    )
    
    
    # Calculate score
    
    scoreUsability = 0.0
    scoreSpeed = 0.0
    
    for result in report.results:
        content = json.loads(result.content)
        scoreUsability = scoreUsability + content['scoreUsability']
        scoreSpeed = scoreSpeed + content['scoreSpeed']
    
    scoreUsability = scoreUsability/len(report.results)
    scoreSpeed = scoreSpeed/len(report.results)
    
    # Scale results from 100 to 10
    scoreUsability /= 10.0
    scoreSpeed /= 10.0
        
    
    report.scoreUsability = round(scoreUsability,1)
    report.scoreSpeed = round(scoreSpeed,1)
    report.score = round(((scoreSpeed * scoreUsability)**(1/2.0)),1)
    report.put()
        
        
class GoogleReportViewer(webapp2.RequestHandler):
    '''
    Clase manejadora de la visaulización de un informe de Google para móviles.
    '''
    def get(self):
        '''
        Respuesta GET de la vista general de un informe de test de móvil de Google.
        
        @type id: long
        @param id: identificador del informe que se está visualizando
        '''
        if self.request.cookies.get("name"):
            report_id = long(self.request.get('id'))
            reports = model.ReportGoogle.query().fetch()
            report = ''
            for r in reports:
                if r.key.id() == report_id:
                    report = r
                    break
                        
            pages = len(report.results)
        else:
            self.redirect('/login')
        
        
        username = self.request.cookies.get("name")
        user = model.User.query(model.User.name == username).get()  
        total_pages = user.n_links
        if user.validation_type == 'MOBILE':
            current_pages = model.PageResultGoogle.query(model.PageResultGoogle.user == user.name).count()
        elif user.validation_type == 'RANK':
            current_pages = model.PageResultGoogle.query(model.PageResultGoogle.user == user.name).count() + model.PageResult.query(model.PageResult.user == user.name).count()
        else:
            current_pages = model.PageResult.query(model.PageResult.user == user.name).count()
        progress = int((current_pages * 100)/total_pages)
        
        
        template_values={'head': head, 'footer': footer, 'report':report, 'pages':pages, 'progress':progress, 'user': user}
        template = JINJA_ENVIRONMENT.get_template('template/google_report_view.html')
        self.response.write(template.render(template_values))
        
class GooglePageViewer(webapp2.RequestHandler):
    '''
    Clase manejadora de una página de un informe de Google para móviles.
    '''
    def get(self):
        '''
        Respuesta GET de la vista de una página de un informe de test de móvil de Google.
        
        @type id: long
        @param id: identificador del informe que se está visualizando
        @type number: int
        @param number: número de página que se está visualizando
        '''
        if self.request.cookies.get("name"):
            number = int(self.request.get("number"))
            report_id = long(self.request.get('id'))
            reports = model.ReportGoogle.query().fetch()
            report = ''
            for r in reports:
                if r.key.id() == report_id:
                    report = r
                    break
        else:
            self.redirect('/login')
        
        username = self.request.cookies.get("name")
        user = model.User.query(model.User.name == username).get()  
        total_pages = user.n_links
        if user.validation_type == 'MOBILE':
            current_pages = model.PageResultGoogle.query(model.PageResultGoogle.user == user.name).count()
        else:
            current_pages = model.PageResult.query(model.PageResult.user == user.name).count()
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
            'head': head, 'footer': footer, 
            'web': report.web,
            'scoreUsability': scoreUsability,
            'scoreSpeed': scoreSpeed,
            'ruleNames': ruleNames,
            'ruleImpacts': ruleImpacts,
            'types': types,
            'summaries': summaries,
            'urlBlocks': urlBlocks,
            'progress' : progress,
            'user': user
        }
        
        template = JINJA_ENVIRONMENT.get_template('template/google_page_view.html')
        self.response.write(template.render(template_values))

class Users(webapp2.RequestHandler):
    '''
    Clase manejadora de la página de edición de usuarios.
    '''
    def get(self):
        '''
        Respuesta GET de la visualización de usuarios registrados en el sistema.
        
        Obtiene la lista de usuarios registrados y muestra sus datos.
        
        En caso de que el usuario que intente acceder a esta vista no sea del grupo
        "Admin" recibirá el mensaje: "Unauthorized".
        '''
        error_message = ''
        progress = 0
        users = ''
        if self.request.cookies.get("name"):
            try:
                username = self.request.cookies.get("name")
                user = model.User.query(model.User.name == username).get()
                if(user.group == 'Admin'):
                    total_pages = user.n_links
                    if user.validation_type == 'MOBILE':
                        current_pages = model.PageResultGoogle.query(model.PageResultGoogle.user == user.name).count()
                    elif user.validation_type == 'RANK':
                        current_pages = model.PageResultGoogle.query(model.PageResultGoogle.user == user.name).count() + model.PageResult.query(model.PageResult.user == user.name).count()
                    else:
                        current_pages = model.PageResult.query(model.PageResult.user == user.name).count()
                    progress = int((current_pages * 100)/total_pages)
                    
                    users = model.User.query().fetch()
                else:
                    self.response.write("Unauthorized")
                
            except:
                error_message = 'Error accessing the database: Required more quota than is available. Come back after 24h.'
                
            template_values={'head':head, 'footer':footer, 'progress':progress,'users':users, 'user':user, 'error_message':error_message}
            template = JINJA_ENVIRONMENT.get_template('template/users.html')
            self.response.write(template.render(template_values))
                
        else:
            self.redirect('/login')

class EditUser(webapp2.RequestHandler):
    '''
    Clase manejadora del proceso de edidión de un usuario.
    '''
    def post(self):
        '''
        Respuesta POST que edita los campos del usuario pasados como parámetro.
        El identificador del usuario es su nombre, y este campo no será modificable.
        
        En caso de que el usuario que intente acceder a este método no sea del grupo
        "Admin" recibirá el mensaje: "Unauthorized".
        
        @type edit-full_name: str
        @param edit-full_name: nombre completo nuevo
        @type edit-email: str
        @param edit-email: email nuevo
        @type edit-group: str
        @param edit-group: grupo nuevo
        @type name: str
        @param name: identificador de usuario que se va a modificar
        '''
        username = self.request.cookies.get("name")
        user = model.User.query(model.User.name == username).get()
        if(user.group == 'Admin'):
            full_name = self.request.get("edit-full_name")
            email = self.request.get("edit-email")
            group = self.request.get("edit-group")
            password = self.request.get("edit-password")
            name = self.request.get("name")
            
            user = model.User.query(model.User.name==name).get()
            if full_name != "": user.full_name = full_name
            if email != "": user.email = email
            if group != "": user.group = group
            if password != "": user.password = password
            
            user.put()
            
            time.sleep(0.1)
            self.redirect("/users")
        else:
            self.response.write("Unauthorized")
        
class DeleteUser(webapp2.RequestHandler):
    '''
    Clase manejadora del proceso de borrado de un usuario.
    '''
    def post(self):
        '''
        Respuesta POST que elimina un usuario de la base de datos identificado por name.
        
        En caso de que el usuario que intente acceder a este método no sea del grupo
        "Admin" recibirá el mensaje: "Unauthorized".
        
        @type name: str
        @param name: identificador del usuario que se va a eliminar
        '''
        username = self.request.cookies.get("name")
        user = model.User.query(model.User.name == username).get()
        if(user.group == 'Admin'):
            name = self.request.get("name")
            
            user = model.User.query(model.User.name==name).get()
            
            user.key.delete()
            
            time.sleep(0.1)
            self.redirect("/users")
        else:
            self.response.write("Unauthorized")
        
class CreateUser(webapp2.RequestHandler):
    '''
    Clase manejadora del proceso de creación de un usuario.
    '''
    def post(self):
        '''
        Respuesta POST que crea un usuario a partir de los campos pasados como parámetro.
        El identificador del usuario es su nombre, y este campo no será modificable.
        
        En caso de que el usuario que intente acceder a este método no sea del grupo
        "Admin" recibirá el mensaje: "Unauthorized".
        
        @type create-name: str
        @param create-name: nombre e identificador de usuario
        @type create-full_name: str
        @param create-full_name: nombre completo
        @type create-email: str
        @param create-email: email
        @type create-group: str
        @param create-group: grupo
        '''
        name = self.request.get("create-name")
        full_name = self.request.get("create-full_name")
        email = self.request.get("create-email")
        group = self.request.get("create-group")
        password = self.request.get("create-password")
        
        username = self.request.cookies.get("name")
        user = model.User.query(model.User.name == username).get()
        if(user.group == 'Admin'):    
            if(model.User.query(model.User.name == name).get() is None):
                user = model.User()
                
                user.name = name
                user.full_name = full_name
                user.email = email
                user.group = group
                user.password = password
                
                user.put()
            
                time.sleep(0.1)
                self.redirect("/users")
            else:
                self.response.write("That user already exists")
        else:
            self.response.write("Unauthorized")
        
class DeleteReport(webapp2.RequestHandler):
    '''
    Clase manejadora del proceso de borrado de un informe.
    '''
    def post(self):
        '''
        Respuesta POST que elimina un informe de la base de datos
        a partir de su id pasada como parámetro.
        
        @type id: long
        @param id: identificador del informe
        '''
        reportID = long(self.request.get("id"))
        
        report = model.Report.get_by_id(reportID)
        if report is None:
            report = model.ReportGoogle.get_by_id(reportID)
        report.key.delete()
        
        time.sleep(0.1)
        self.redirect("/reports")
        
class DeleteRankingReport(webapp2.RequestHandler):
    '''
    Clase manejadora del proceso de borrado de un informe de Ranking.
    '''
    def post(self):
        '''
        Respuesta POST que elimina un informe de Ranking de la base de datos
        a partir de su id pasada como parámetro. Elimina también, por tanto,
        los cinco informes asociados a éste.
        
        @type id: long
        @param id: identificador del informe
        '''
        reportID = long(self.request.get("id"))
        
        reportRank = model.ReportRank.get_by_id(reportID)
        
        model.Report.get_by_id(long(reportRank.html_test)).key.delete()
        model.Report.get_by_id(long(reportRank.wcag2A_test)).key.delete()
        model.Report.get_by_id(long(reportRank.wcag2AA_test)).key.delete()
        model.Report.get_by_id(long(reportRank.availability_test)).key.delete()
        model.ReportGoogle.get_by_id(long(reportRank.mobile_test)).key.delete()
        
        reportRank.key.delete()
        
        time.sleep(0.1)
        self.redirect("/ranking-reports")
        
class RankingReports(webapp2.RequestHandler):
    '''
    Clase manejadora de la página de visualizción e inserción de los informes de Ranking.
    '''
    def get(self):
        '''
        Respuesta GET que muestra los informes de Ranking.
        
        Si se ha completado una validación de tipo Ranking se insertarán en la base de datos
        los cinco informes asociados y el informe de tipo Ranking que los referencia.
        Al insertar este informe se calcula la puntuación global, que se trata de la media geométrica
        de la puntuación de los cinco informes asociados.
        
        Si ya existía un informe de Ranking de la misma web se actualiza en lugar de crear uno nuevo.
        '''
        if self.request.cookies.get("name"):
            
            username = self.request.cookies.get("name")
            error_message = ''
            reports = ''
            progress = 0
            
            try:    
                user = model.User.query(model.User.name == username).get()
                qry = model.PageResult.query(model.PageResult.user == user.name).order(model.PageResult.number)
                qry2 = model.PageResultGoogle.query(model.PageResultGoogle.user == user.name).order(model.PageResultGoogle.number)
                    
                if qry.count() + qry2.count() == user.n_links and user.validation_type == 'RANK':
                    
                    insertReport(username,'HTML',True)
                    insertReport(username,'WCAG2-A',True)
                    insertReport(username,'WCAG2-AA',True)
                    insertReport(username,'CHECK AVAILABILITY',True)
                    insertGoogleReport(username,True)
                        
                    html_test = None
                    wcag2A_test = None
                    wcag2AA_test = None
                    availability_test = None
                    
                    # Obtenemos los informes asociados de la base de datos:
                    
                    html_test = model.Report.query(model.Report.isRank == True).filter(model.Report.validation_type == 'HTML')\
                    .filter(model.Report.web == user.root_link).get()
                    
                    wcag2A_test = model.Report.query(model.Report.isRank == True).filter(model.Report.validation_type == 'WCAG2-A')\
                    .filter(model.Report.web == user.root_link).get()
                            
                    wcag2AA_test = model.Report.query(model.Report.isRank == True).filter(model.Report.validation_type == 'WCAG2-AA')\
                    .filter(model.Report.web == user.root_link).get()
                            
                    availability_test = model.Report.query(model.Report.isRank == True).filter(model.Report.validation_type == 'CHECK AVAILABILITY')\
                    .filter(model.Report.web == user.root_link).get()
                            
                    mobile_test = model.ReportGoogle.query(model.ReportGoogle.isRank == True).filter(model.ReportGoogle.web == user.root_link).get()
                    
                    # Creamos un informe de Ranking. Si ya existía uno lo actualizamos
                    reportRank = None
                    reportsRank = model.ReportRank.query().fetch()
                    for report in reportsRank:
                        if report.web == user.root_link:
                            reportRank = report
                    
                    if reportRank is None:
                        reportRank = model.ReportRank()
                    
                    reportRank.web = user.root_link
                    reportRank.user = user.name
                    reportRank.html_test = str(html_test.key.id())
                    reportRank.wcag2A_test = str(wcag2A_test.key.id())
                    reportRank.wcag2AA_test = str(wcag2AA_test.key.id())
                    reportRank.availability_test = str(availability_test.key.id())
                    reportRank.mobile_test = str(mobile_test.key.id())
                    
                    # Para calcular la puntuación usamos la media geométrica de las puntuaciones de cada informe
                    
                    reportRank.score = round(((html_test.score * wcag2A_test.score * wcag2AA_test.score * availability_test.score * mobile_test.score)**(1/5.0)),1)
                    
                    reportRank.put()
                
                    # Resetear las variables de estado del usuario
                    user.n_links = -1
                    user.root_link = ''
                    user.validation_type = ''
                    user.onlyDomain = None
                    user.lock = False
                    user.put()
                    
                    time.sleep(1)
                    self.redirect('/ranking-reports')
                
                reports = model.ReportRank.query().fetch()
                
                username = self.request.cookies.get("name")
                user = model.User.query(model.User.name == username).get()  
                total_pages = user.n_links
                if user.validation_type == 'MOBILE':
                    current_pages = model.PageResultGoogle.query(model.PageResultGoogle.user == user.name).count()
                elif user.validation_type == 'RANK':
                    current_pages = model.PageResultGoogle.query(model.PageResultGoogle.user == user.name).count() + model.PageResult.query(model.PageResult.user == user.name).count()
                else:
                    current_pages = model.PageResult.query(model.PageResult.user == user.name).count()
                progress = int((current_pages * 100)/total_pages)
                
            except:
                error_message = 'Error accessing the database: Required more quota than is available. Come back after 24h.'
                
            self.response.headers['Content-Type'] = 'text/html'
            
            template_values={'head': head, 'footer': footer, 'reports':reports, 'error_message': error_message, 'progress':progress, 'user': user}
            template = JINJA_ENVIRONMENT.get_template('template/ranking_reports.html')
            self.response.write(template.render(template_values))
        
        else:
            self.redirect('/login')
            
class RankingReportViewer(webapp2.RequestHandler):
    '''
    Clase manejadora de la visualización de un informe de Raking.
    '''
    def get(self):
        '''
        Respuesta GET de la vista de un informe de Ranking. Muestra los informes
        asociados al informe de Ranking pasado como argumento al método GET.
        
        @type id: long
        @param id: identificador del informe de Ranking que se está visualizando.
        '''
        if self.request.cookies.get("name"):
            
            username = self.request.cookies.get("name")
            error_message = ''
            reports = ''
            reportsGoogle = ''
            progress = 0
            rankID = self.request.get("id")
            
            try:
                rankID = long(rankID)
                reportsRank = model.ReportRank.query().fetch()
                reportRank = ''
                for r in reportsRank:
                    if r.key.id() == rankID:
                        reportRank = r
                        break
                        
                reports = []
                reports.append(model.Report.get_by_id(long(reportRank.html_test)))
                reports.append(model.Report.get_by_id(long(reportRank.wcag2A_test)))
                reports.append(model.Report.get_by_id(long(reportRank.wcag2AA_test)))
                reports.append(model.Report.get_by_id(long(reportRank.availability_test)))
                
                reportsGoogle = []
                reportsGoogle.append(model.ReportGoogle.get_by_id(long(reportRank.mobile_test)))
                
                user = model.User.query(model.User.name == username).get()  
                total_pages = user.n_links
                if user.validation_type == 'MOBILE':
                    current_pages = model.PageResultGoogle.query(model.PageResultGoogle.user == user.name).count()
                elif user.validation_type == 'RANK':
                    current_pages = model.PageResultGoogle.query(model.PageResultGoogle.user == user.name).count() + model.PageResult.query(model.PageResult.user == user.name).count()
                else:
                    current_pages = model.PageResult.query(model.PageResult.user == user.name).count()
                progress = int((current_pages * 100)/total_pages)
                
            except:
                error_message = 'Error accessing the database: Required more quota than is available. Come back after 24h.'
                
            self.response.headers['Content-Type'] = 'text/html'
            
            template_values={'head': head, 'footer': footer, 'reports':reports, 'reportsGoogle':reportsGoogle, 'error_message': error_message, 'progress':progress, 'user':user}
            template = JINJA_ENVIRONMENT.get_template('template/ranking_reports_viewer.html')
            self.response.write(template.render(template_values))
        
        else:
            self.redirect('/login')
            
class CancelValidation(webapp2.RequestHandler):
    '''
    Clase manejadora del proceso de cancelación de una validación en curso.
    '''
    def get(self):
        '''
        Respuesta POST que cancela el proceso de validación de una web.
        
        Para la cancelación se detienen las tareas que se encuentran en la cola,
        se eliminan las páginas guardadas en la base de datos hasta el momento y 
        se reinician las variables de estado del usuario.
        '''
        
        if self.request.cookies.get("name"):
            
            username = self.request.cookies.get("name")
            user = model.User.query(model.User.name == username).get()
        
            alphaqueue = taskqueue.Queue('alphaqueue')
            alphaqueue.purge()
            
            time.sleep(2)
            
            ndb.delete_multi(
                model.PageResult.query().fetch(keys_only=True)
            )
            
            ndb.delete_multi(
                model.PageResultGoogle.query().fetch(keys_only=True)
            )
            
            # Reset global variables for user
            user.n_links = -1
            user.root_link = ''
            user.validation_type = ''
            user.onlyDomain = None
            user.lock = False
            user.put()
            
            self.redirect('/')
        
        else:
            self.redirect('/login')
        
class NotFound(webapp2.RequestHandler):
    '''
    Clase manejadora de la página de error al no encontrar el recurso indicado.
    '''
    def get(self):
        '''
        Respuesta GET de la página que maneja las peticiones no encontradas
        en el servidor. Devuelve un mensaje de error diciendo que el recurso solicitado
        no se ha encontrado.
        '''
        
        error_message = 'The page you are trying to access does not exist'
        if self.request.cookies.get("name"):
            
            username = self.request.cookies.get("name")
            user = model.User.query(model.User.name == username).get()
            
            total_pages = user.n_links
            if user.validation_type == 'MOBILE':
                current_pages = model.PageResultGoogle.query(model.PageResultGoogle.user == user.name).count()
            elif user.validation_type == 'RANK':
                current_pages = model.PageResultGoogle.query(model.PageResultGoogle.user == user.name).count() + model.PageResult.query(model.PageResult.user == user.name).count()
            else:
                current_pages = model.PageResult.query(model.PageResult.user == user.name).count()
            progress = int((current_pages * 100)/total_pages)
            
        self.response.headers['Content-Type'] = 'text/html'
            
        template_values={'head': head, 'footer': footer, 'error_message': error_message, 'progress':progress, 'user':user}
        template = JINJA_ENVIRONMENT.get_template('template/notfound.html')
        self.response.write(template.render(template_values))
        
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
        ('/google-validation',GoogleValidation),
        ('/google-viewreport',GoogleReportViewer),
        ('/google-viewpage',GooglePageViewer),
        ('/users',Users),
        ('/edit-user',EditUser),
        ('/create-user',CreateUser),
        ('/delete-user',DeleteUser),
        ('/ranking-reports',RankingReports),
        ('/ranking-reports-viewer',RankingReportViewer),
        ('/delete-report',DeleteReport),
        ('/delete-ranking-report',DeleteRankingReport),
        ('/cancel-validation',CancelValidation),
        ('/.*', NotFound),
       ]
'''Lista de URLs del servicio asociadas a su clase controladora'''

application = webapp2.WSGIApplication(urls, debug=True)
'''aplicación WSGI Webapp2'''

def main():
    '''
    Main que ejecuta la aplicación WSGI de Webapp2
    '''
    os.environ['TZ'] = 'Europe/Madrid'
    time.tzset()
    run_wsgi_app(application)

if __name__ == "__main__":
    main()
