FROM ubuntu:latest
MAINTAINER Julio Martínez Martínez-Checa <julioxus@gmail.com>

#Instalar Python con todas las dependencias

RUN apt-get update
RUN apt-get -y install python python-setuptools build-essential python-dev
RUN easy_install pip

# Instalamos git y clonamos el repositorio
RUN apt-get install -y git
RUN git clone https://github.com/julioxus/spiderbot.git

# Descargamos los submódulos que faltan, GAE en este caso
# e iniciamos la instalación de la aplicación que incluye 
# el demonio de la misma
RUN cd spiderbot && \
git submodule init && \
git submodule sync && \
git submodule update && \
chmod 755 install.sh && \
bash install.sh

# Iniciamos el servicio
RUN service spiderbot restart