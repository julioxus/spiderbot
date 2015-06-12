#!/usr/bin/python
# -⁻- coding: UTF-8 -*-

def parseHTMLValidation(validation, url):
    '''
    Da formato legible parseando el diccionario validation obtenido de
    haber validado el estándar HTML de la url pasada como parámetro.
    
    @type validation: dict
    @param validation: diccionario JSON con el resultado de validar la url
    @type url: str
    @param url: url que se va a parsear
    
    @rtype: dict
    @return: diccionario que contiene los resultados de realizar el parseo:
        - out: texto de salida formateado
        - errors: número de errores encontrados en la validación
        - state: estado de la validación
    '''
    out = ''
    errors = 0
    warnings = 0
    list_errors = []
    state = ''
    
    for msg in validation['messages']:
        if 'lastLine' in msg:
            out += "%(type)s: line %(lastLine)d: %(message)s \n" % msg
        else:
            out += "%(type)s: %(message)s \n" % msg
        if msg['type'] == 'error':
            errors += 1
            if not ["%(message)s" % msg, ["%(lastLine)d" % msg], [url]] in list_errors:
                list_errors.append(["%(message)s" % msg, ["%(lastLine)d" % msg], [url]])
        else:
            warnings += 1
    
    out += "\nErrors: %s \n" % errors
    out += "Warnings: %s" % warnings
    out += "\n\n"
    
    if errors == 0:
        state = 'PASS'
    else:
        state = 'FAIL'
    
    result = {'out':out,'errors':errors, 'state': state, 'list_errors': list_errors}
    return result

def parseCSSValidation(validation, url):
    '''
    Da formato legible parseando el diccionario validation obtenido de
    haber validado el estándar CSS de la url pasada como parámetro.
    
    @type validation: dict
    @param validation: diccionario JSON con el resultado de validar la url
    @type url: str
    @param url: url que se va a parsear
    
    @rtype: dict
    @return: diccionario que contiene los resultados de realizar el parseo:
        - out: texto de salida formateado
        - errors: número de errores encontrados en la validación
        - state: estado de la validación
        - list_errors: lista de errores encontrados en la validación
    '''
    out = ''
    list_errors = []
    errors = validation['cssvalidation']['result']['errorcount']
    warnings = validation['cssvalidation']['result']['warningcount']
    state = ''
    
    if errors > 0:
        for msg in validation['cssvalidation']['errors']:
            out += "error: line %(line)d: %(type)s: %(context)s %(message)s \n" % msg
            if not ["%(message)s" % msg, ["%(line)d" % msg], [url]] in list_errors:
                list_errors.append(["%(message)s" % msg, ["%(line)d" % msg], [url]])
    if warnings > 0:
        for msg in validation['cssvalidation']['warnings']:
            out += "warning: line %(line)d: %(type)s: %(message)s \n" % msg
            
    
    out += "\nErrors: %s \n" % errors
    out += "Warnings: %s" % warnings
    out += "\n\n"
    
    if errors == 0:
        state = 'PASS'
    else:
        state = 'FAIL'
    
    result = {'out':out,'errors':errors, 'state':state, 'list_errors':list_errors}
    return result

def parseAvailabilityValidation(code):
    '''
    Da formato legible parseando el código HTTP de respuesta del servidor.
    
    @type code: int
    @param code: código HTTP que devuelve el servidor
    
    @rtype: dict
    @return: diccionario que contiene los resultados de realizar el parseo:
        - out: texto de salida formateado
        - errors: número de errores encontrados en la validación
        - state: estado de la validación
    '''
    out = ''
    errors = 0
    state = ''
    
    if code >= 200 and code < 300:
        out += str(code) + '\nRequest OK'
        state = 'PASS'
    elif code != -1:
        out += str(code) + '\nRequest FAILED'
        state = 'FAIL'
        errors+=1
    else:
        out += 'Error parsing URL'
        state = 'ERROR'
    
    out += '\n\n'
    
    result = {'out':out, 'errors': errors, 'state': state}
    return result

def parseWCAGValidation(validation, url):
    '''
    Da formato legible parseando el diccionario validation obtenido de
    haber validado el estándar WCAG 2.0 de la url pasada como parámetro.
    
    @type validation: dict
    @param validation: diccionario JSON con el resultado de validar la url
    @type url: str
    @param url: url que se va a parsear
    
    @rtype: dict
    @return: diccionario que contiene los resultados de realizar el parseo:
        - out: texto de salida formateado
        - errors: número de errores encontrados en la validación
        - state: estado de la validación
        - list_errors: lista de errores encontrados en la validación
    '''
    out = ''
    list_errors = []
    state = validation['state']
    errors = len(validation['errors']['lines'])
    warnings = len(validation['warnings']['lines'])
    
    # Limit warnings to save disk space
    if warnings > 100: warnings = 100
    
    for i in range(0,errors):
        try:
            line = validation['errors']['lines'][i]
            message = validation['errors']['messages'][i]
            code = validation['errors']['codes'][i]
            out += "Error: %(line)s %(message)s \n %(code)s \n\n" % \
            {'line': line, 'message': message, 'code': code}
            if not ["%s" % message, [line], [url]] in list_errors:
                list_errors.append(["%s" % message, [line], [url]])
        except:
            break
        
    for i in range(0,warnings):
        try:
            line = validation['warnings']['lines'][i]
            message = validation['warnings']['messages'][i]
            code = validation['warnings']['codes'][i]
            out += "Warning: %(line)s %(message)s \n %(code)s \n\n" % \
            {'line': line, 'message': message, 'code': code}  
        except:
            break                    
        
    out += "\nErrors: %s \n" % errors
    out += "Warnings: %s" % warnings
    
    result = {'out':out,'errors':errors, 'state': state, 'list_errors':list_errors}
    return result
    
def parseGoogleValidation(validation, url):
    
    '''
    Da formato legible parseando el diccionario validation obtenido de
    haber validado el estándar CSS de la url pasada como parámetro.
    
    @type validation: dict
    @param validation: diccionario JSON con el resultado de validar la url
    @type url: str
    @param url: url que se va a parsear
    
    @rtype: dict
    @return: diccionario que contiene los resultados de realizar el parseo:
        
        - scoreUsability: puntuación de experiencia de usuario
        - scoreSpeed: puntuación de velocidad de carga
        - ruleNames: lista con los nombres de las reglas
        - ruleImpacts: lista con los impactos de las reglas
        - types: lista con los tipos de variable
        - summaries: lista de resúmenes de las reglas
        - urlBlocks: lista de bloques de URLs
    '''
    
    ruleResults = validation['formattedResults']['ruleResults']
    scoreUsability = validation['ruleGroups']['USABILITY']['score']
    scoreSpeed = validation['ruleGroups']['SPEED']['score']
    ruleNames = []
    ruleImpacts = []
    types = []
    summaries = []
    urlBlocks = []
    
    index = 0
    for r in ruleResults:
        ruleNames.append(validation['formattedResults']['ruleResults'][r]['localizedRuleName'])
        ruleImpacts.append(validation['formattedResults']['ruleResults'][r]['ruleImpact'])
        types.append(validation['formattedResults']['ruleResults'][r]['groups'][0])
        if 'summary' in validation['formattedResults']['ruleResults'][r]:
            summary = validation['formattedResults']['ruleResults'][r]['summary']
            
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
            
        if 'urlBlocks' in validation['formattedResults']['ruleResults'][r]:
            
            for block in validation['formattedResults']['ruleResults'][r]['urlBlocks']:
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
    
    result = {'scoreUsability': scoreUsability,
        'scoreSpeed': scoreSpeed,
        'ruleNames': ruleNames,
        'ruleImpacts': ruleImpacts,
        'types': types,
        'summaries': summaries,
        'urlBlocks': urlBlocks
    }
    return result