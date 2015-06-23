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

from google.appengine.api import urlfetch
import urllib
import json
import lxml.html
import urllib2
import re

# APIs REST para validar
html_validator_url = 'http://validator.w3.org/check'
'''URL del validador HTML'''
css_validator_url = 'http://jigsaw.w3.org/css-validator/validator'
'''URL del validador CSS'''
wcag_validator_url = 'http://achecker.ca/checkacc.php'
'''URL del validador WCAG'''
ACHECKER_ID = '8d50ba76d166da61bdc9dfa3c97247b32dd1014c'
'''Clave para usar la API de AChecker'''
pagespeed_api_url = 'https://www.googleapis.com/pagespeedonline/v2/runPagespeed'
'''URL del validador de Google para móviles'''
GOOGLE_API_KEY = 'AIzaSyDmU2XjCiUJdMyDDhX8AQ8n-4vye8i5Uzk'
'''Clave para usar la API de Google'''

def validate(filename,page_type):
    '''
    Valida una web HTML o CSS y devuelve un JSON resultado como diccionario.
    
    @type finename: str
    @param filename: nombre de URL HTTP
    @type page_type: str
    @param paga_type: tipo de página que se quiere validar. Puede ser:
        - html
        - css
        
    @rtype: dict
    @return: diccionario JSON que contiene los resultados de la validación. Si la validación no es correcta devuelve ''
    '''
    
    if filename.startswith('http://') or filename.startswith('https://'):
        # Envía URI con GET.
        urlfetch.set_default_fetch_deadline(120)
        if page_type == 'css':
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
        return result
    else:
        return ''

    
def validateWCAG(filename,guide):
    '''
    Valida una web con el estándar WCAG 2.0
    
    @type filename: str
    @param filename: nombre de URL HTTP
    @type guide: str
    @param guide: directrices de WCAG 2.0. Puede ser:
        - WCAG2-A
        - WCAG2-AA
        - WCAG2-AAA
        
    @rtype: dict
    @return: diccionario que contiene los resultados de la validación. Si la validación no es correcta devuelve ''
    '''
    urlfetch.set_default_fetch_deadline(120)
    code = checkAvailability(filename)
    if code >= 200 and code < 300:
        payload = {'uri': filename, 'id': ACHECKER_ID, 'guide': guide, 'output': 'html'}
        encoded_args = urllib.urlencode(payload)
        url = wcag_validator_url + '/?' + encoded_args 
        print url
        r = urllib2.urlopen(url)
        text = r.read()
        result = lxml.html.document_fromstring(text)
        
        parse_dic = {'state': '', 'errors': {'lines': [], 'messages': []}, 'codes': [],\
                                 'warnings': {'lines': [], 'messages': [], 'codes': []}}
                    
        parse_dic['errors']['lines'] = result.xpath('//li[@class="msg_err"]/em//text()')
        parse_dic['errors']['messages'] = result.xpath('//li[@class="msg_err"]/span/a[@target]//text()')
        parse_dic['errors']['codes'] = result.xpath('//li[@class="msg_err"]//code[@class="input"]//text()')
        
        parse_dic['warnings']['lines'] = result.xpath('//li[@class="msg_info"]/em//text()')
        parse_dic['warnings']['messages'] = result.xpath('//li[@class="msg_info"]/span/a[@target]//text()')
        parse_dic['warnings']['codes'] = result.xpath('//li[@class="msg_info"]//code[@class="input"]//text()')
        
        
        if len(parse_dic['errors']['lines']) == 0:
            parse_dic['state'] = 'PASS'
        else:
            parse_dic['state'] = 'FAIL'
        
        return parse_dic
        
    else:
        return ''
    
def checkAvailability(filename):
    '''
    Comprueba la disponibilidad de una web.
    
    @type filename: str
    @param filename: nombre de la URL HTTP
    
    @rtype: int
    @return: código que devuelve el servidor ante la petición GET
    '''
    urlfetch.set_default_fetch_deadline(60)
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
def getAllLinks(root,depth,max_pages,onlyDomain, reg='.*'):
    '''
    Algoritmo principal de la araña. Obtiene los links de la página raíz root con una búsqueda en anchura,
    determinada por una profundidad de búsqueda depth y número máximo de páginas max_pages. Puede filtrar
    páginas si se indica que sólo busque en su propio dominio o usar una expresión reguar reg.
    
    @type root: str
    @param root: página raíz
    @type depth: int
    @param depth: profundidad de búsqueda
    @type max_pages: int
    @param max_pages: links que se obtendrán como máximo
    @type onlyDomain: bool
    @param onlyDomain: indica si se quieren filtar páginas que estén sólo en su dominio
    @type reg: str
    @param reg: expresión regular para filtrar páginas en la obtención de links
    
    @rtype: list
    @return: lista de enlaces compuesta por objetos de tipo tupla con dos valores:
        - 0: nombre del enlace
        - 1: tipo de enlace: html o css
    '''
    links = []
    if not root.endswith('/'):
        root = root + '/'
    links.append((str(root),'html'))
    max_reached = False
    pattern = re.compile(reg);
    
    n = 0 # Número de enlaces HTML encontrados hasta el momento
    i = 0 # Enlace analizando actualmente
    
    while n < depth:
        if links[i][1] != 'css':
            try:
                # Establecer conexión con la URL
                website = urllib2.urlopen(links[i][0])
                # Leer el código HTML
                html = website.read()
            except urllib2.HTTPError, error:
                html = error.read()
            
            dom =  lxml.html.fromstring(html)
            
            document_links = dom.xpath('//a/@href | //link/@href') # lista de links totales
            css_links = dom.xpath('//*[@rel="stylesheet"]/@href') # lista de links CSS
            nofollow_links = dom.xpath('//*[@rel="nofollow"]/@href') # Las etiquetas "nofollow" no se analizarán
            alternate_links = dom.xpath('//*[@rel="alternate"]/@href') # Las etiquetas "alternate" no se analizarán
            
            for link in document_links: # recorremos los links
                
                # Si se encuentra la expresión regular       
                if pattern.search(link):
                    
                    # Descartamos los enlaces que contengan lo siguiente:
                    if not(link.endswith('.jpg') or link.endswith('.png') or link.endswith('.js') or \
                    link.endswith('.ico') or link.endswith('.gif') or link.endswith('.iso') or link.endswith('.mp3') or \
                    link.endswith('.pdf') or  link.endswith('.xml') or len(link) > 450 or ('mailto' in link) or \
                    root == link+'/' or ('#' in link) or ('JavaScript:' in link) or ('javascript:' in link) or
                    (link in nofollow_links) or (link in alternate_links)):
                               
                        if link in css_links:
                            page_type = 'css'
                        else:
                            page_type = 'html'
                            
                        
                        if link.startswith('http'):
                            if not ((link,page_type) in links):
                                if onlyDomain:
                                    if link.startswith(root):
                                            links.append((link,page_type))
                                else:
                                    links.append((link,page_type))
                        else:
                            if link.startswith('/'):
                                link = link[1:]  
                            link = root + link
                            if not ((link,page_type) in links):
                                links.append((link,page_type))               
                                 
                        while len(links) > max_pages:
                            links.pop()
                            max_reached = True
                            
                        if max_reached:
                            break
            n+=1
            
        i+=1
        
    if not pattern.search(links[0][0]):
        del links [0]
        
    return links

def html_decode(s):
    """
    Returns the ASCII decoded version of the given HTML string. This does
    NOT remove normal HTML tags like <p>.
    """
    htmlCodes = (
            ("'", '&#39;'),
            ('"', '&quot;'),
            ('>', '&gt;'),
            ('<', '&lt;'),
            ('&', '&amp;')
            )
    for code in htmlCodes:
        s = s.replace(code[1], code[0])
    return s

def GoogleMobileValidation(filename):
    '''
    Valida la página filename usando el validador de Google para móviles.
    
    @type filename: str
    @param filename: nombre de la URL HTTP
    
    @rtype: dict
    @return: diccionario JSON que contiene los resultados de la validación. Si la validación no es correcta devuelve ''
    '''
    if filename.startswith('http://') or filename.startswith('https://'):
        # Submit URI with GET.
        urlfetch.set_default_fetch_deadline(60)
        payload = {'url': filename, 'key': GOOGLE_API_KEY, 'strategy': 'mobile', 'locale':'en_US'}
        encoded_args = urllib.urlencode(payload)
        url = pagespeed_api_url + '/?' + encoded_args
        r = urllib2.urlopen(url)
     
        result = json.load(r)
        return result
    else:
        return ''
