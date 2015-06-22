#!/bin/bash

if [[ $EUID -ne 0 ]]; then
	echo "Debes tener permisos de administrador para ejecutar el script"

else

	echo 'Instalando aplicación...'

	if [ ! -d /usr/local/bin/spiderbot ]; then
		echo 'Copiando archivos en el sistema...'
		cp -r . /usr/local/bin/spiderbot
	fi

	sudo cp spiderbot /etc/init.d

	sudo update-rc.d spiderbot defaults
	sudo service spiderbot start

	echo '¡Listo!'

fi