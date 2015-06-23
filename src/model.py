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

from google.appengine.ext import ndb

class PageResult(ndb.Model):
    '''
    Modelo de validación HTML, CSS, WCAG 2.0 o disponibilidad de una página web.
    '''
    user = ndb.StringProperty()
    '''Usuario que ha realizado la validación'''
    validation_type = ndb.StringProperty()
    '''
    Tipo de validación, puede ser de tipo:
        - HTML
        - WCAG2-A
        - WCAG2-AA
        - CHECK AVAILABILITY
    '''
    url = ndb.StringProperty()
    '''URL validada'''
    content = ndb.TextProperty()
    '''Resultado de la validación con mensajes de error y advertencia'''
    state = ndb.StringProperty()
    '''Estado de la validación'''
    errors = ndb.IntegerProperty()
    '''Número de errores de la validación'''
    list_errors = ndb.TextProperty()
    '''Lista de errores de la validación'''
    number = ndb.IntegerProperty()
    '''Número de página para establecer un orden'''
    
class PageResultGoogle(ndb.Model):
    '''
    Modelo de validación de Google para móviles de una página web.
    '''
    user = ndb.StringProperty()
    '''Usuario que ha realizado la validación'''
    url = ndb.StringProperty()
    '''URL validada'''
    scoreUsability = ndb.FloatProperty()
    '''Puntuación obtenida en el test de experiencia de usuario'''
    scoreSpeed = ndb.FloatProperty()
    '''Puntuación obtenida en el test de velocidad'''
    content = ndb.TextProperty()
    '''Cadena JSON con el resultado de la validación estructurado'''
    number = ndb.IntegerProperty()
    '''Número de página para establecer un orden'''
    
class Report(ndb.Model):
    '''
    Modelo de informe para validaciones HTML, WCAG 2.0 y disponibilidad de una web completa validada.
    '''
    web = ndb.StringProperty()
    '''Página raíz'''
    validation_type = ndb.StringProperty()
    '''
    Tipo de validación. Puede ser:
        - HTML
        - WCAG2-A
        - WCAG2-AA
        - CHECK AVAILABILITY
    '''
    user = ndb.StringProperty()
    '''Usuario que ha realizado la validación'''
    onlyDomain = ndb.BooleanProperty()
    '''¿Es de sólo dominio?'''
    isRank = ndb.BooleanProperty(default=False)
    '''¿Es un informe de Ranking?'''
    results = ndb.LocalStructuredProperty(PageResult, repeated=True, keep_keys=True, compressed=True)
    '''Lista de páginas validadadas en el informe'''
    pages = ndb.IntegerProperty()
    '''Número de páginas'''
    error_pages = ndb.IntegerProperty()
    '''Número de páginas con algún error'''
    errors = ndb.IntegerProperty()
    '''Número total de errores'''
    list_errors = ndb.TextProperty()
    '''Lista de errores'''
    score = ndb.FloatProperty()
    '''Puntuación obtenida'''
    date = ndb.DateProperty(auto_now=True)
    '''Fecha en la que se realizó la validación'''
    time = ndb.TimeProperty(auto_now=True)
    '''Hora en la que se realizó la validación'''
    
class ReportGoogle(ndb.Model):
    '''
    Modelo de informe de Google para móviles de una web completa validada.
    '''
    web = ndb.StringProperty()
    '''Página raíz'''
    validation_type = ndb.StringProperty()
    '''
    Tipo de validación. Sólo puede tomar el valor MOBILE, pero se deja
    este campo para posibles futuras ampliaciones.
    '''
    user = ndb.StringProperty()
    '''Usuario que ha realizado la validación'''
    onlyDomain = ndb.BooleanProperty()
    '''¿Es de sólo dominio?'''
    isRank = ndb.BooleanProperty(default=False)
    '''¿Es un informe de Ranking?'''
    results = ndb.LocalStructuredProperty(PageResultGoogle, repeated=True, keep_keys=True,compressed=True)
    '''Lista de páginas validadadas en el informe'''
    pages = ndb.IntegerProperty()
    '''Número de páginas'''
    scoreUsability = ndb.FloatProperty()
    '''Puntuación media del test experiencia de usuario'''
    scoreSpeed = ndb.FloatProperty()
    '''Puntuación media del test de velocidad'''
    score = ndb.FloatProperty()
    '''Puntuación obtenida'''
    date = ndb.DateProperty(auto_now=True)
    '''Fecha en la que se realizó la validación'''
    time = ndb.TimeProperty(auto_now=True)
    '''Hora en la que se realizó la validación'''

class User(ndb.Model):
    '''
    Modelo de usuario del sistema
    '''
    name = ndb.StringProperty()
    '''Nombre. Identifica al usuario.'''
    full_name = ndb.StringProperty()
    '''Nombre completo'''
    group = ndb.StringProperty()
    '''Grupo de usuarios al que pertenece'''
    password = ndb.StringProperty()
    '''Contraseña'''
    email = ndb.StringProperty()
    '''Correo electrónico'''
    n_links = ndb.IntegerProperty(default=-1)
    '''
    Variable de estado. Número de páginas que se van a
    validar cuando se está realizando una validación.
    
    Cuando no se está validado toma el valor -1
    '''
    root_link = ndb.StringProperty()
    '''
    Variable de estado. Enlace de la web que se está validando.
    '''
    validation_type = ndb.StringProperty()
    '''
    Variable de estado. Indica el tipo de validación que se está
    realizando.
    '''
    onlyDomain = ndb.BooleanProperty()
    '''
    Variable de estado. Indica si estamos realizando una validación de
    sólo dominio.
    '''
    lock = ndb.BooleanProperty(default=False)
    '''
    Variable de estado. Cerrojo que se activa cuando estamos realizando
    una validación y se desactiva cuando termina.
    '''
    
class ReportRank(ndb.Model):
    '''
    Modelo de informe de Ranking
    '''
    web = ndb.StringProperty()
    '''Página raíz'''
    user = ndb.StringProperty()
    '''Usuario que ha realizado la validación'''
    score = ndb.FloatProperty()
    '''Puntuación global obtenida'''
    html_test = ndb.StringProperty()
    '''Identificador del informe HTML/CSS asociado'''
    wcag2A_test = ndb.StringProperty()
    '''Identificador del informe WCAG 2.0 A asociado'''
    wcag2AA_test = ndb.StringProperty()
    '''Identificador del informe WCAG 2.0 AA asociado'''
    availability_test = ndb.StringProperty()
    '''Identificador del informe de disponibilidad asociado'''
    mobile_test = ndb.StringProperty()
    '''Identificador del informe para móviles de Google asociado'''