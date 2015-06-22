#!/bin/bash

if [[ $EUID -ne 0 ]]; then
	echo "Debes tener permisos de administrador para ejecutar el script"

else

	echo 'Desinstalando aplicación...'

	if [ ! -d /usr/local/bin/spiderbot ]; then
		echo 'El programa ya está desinstalado'
	else
		rm -rf /usr/local/bin/spiderbot
		rm /etc/init.d/spiderbot
	fi

	echo '¡Listo!'

fi