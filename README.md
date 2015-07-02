Spiderbot
----------------------------------

**Proyecto fin de grado**

Aplicación web que valida los documentos web conforme a los formatos estándares y normativas para la accesibilidad.

![logo](https://raw.githubusercontent.com/julioxus/spiderbot/master/src/static/images/logo.png)

## Instalación

Actualizamos repositorios e instalamos python y pip

    sudo apt-get update
    apt-get -y install python python-setuptools build-essential python-dev
    easy_install pip

Instalamos git y clonamos el repositorio

    apt-get install -y git
    git clone https://github.com/julioxus/spiderbot.git

Descargamos los submódulos que faltan, GAE en este caso e iniciamos la instalación de la aplicación que incluye el demonio de la misma

    cd spiderbot && \
    git submodule init && \
    git submodule sync && \
    git submodule update && \
    chmod 755 install.sh && \
    sudo ./install.sh
    
## Desinstalación
    sudo ./uninstall.sh
    
## Ejecutar servicio
    sudo service spirderbot start
    
## Parar servicio
    sudo service spiderbot stop
    
## Usuario administrador inicial
 * Usuario: admin
 * Contraseña: 1234

## Versión actual de la aplicación en funcionamiento:

[Spiderbot](http://spiderbot-ugr.appspot.com/)

* Usuario de prueba: test
* Contraseña: 1234

## Contenedor Docker preparado

https://registry.hub.docker.com/u/julioxus/spiderbot/

    sudo docker pull julioxus/spiderbot

## Requisitos de la aplicación

La aplicación realizará las siguientes tareas:

* [X] Validar documentos HTML
* [X] Validar documentos CSS
* [X] Validar documentos conforme a la normativa WCAG 2.0
* [X] Comprobar disponibilidad de las URLS de un sitio web completo
* [X] Elegir nivel de recursividad para el escaneo de una dirección web
* [X] Realizar informe de los análisis
* [X] Programar escaneo automatizado de una web completa
* [X] Registro y seguimiento de usuarios que podrán programar sus propios escaneos automatizados
* [X] Validar experiencia de usuario y velocidad de carga en versiones móviles

La aplicación, además, deberá estar desplegada en un servicio cloud gratuito como Google App Engine.
