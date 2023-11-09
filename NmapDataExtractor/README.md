# NmapDataExtractor


## Descripción
`NmapDataExtractor` es un sencillo script de Python diseñado para simplificar la tarea de analizar y sintetizar la información obtenida a través de escaneos de red realizados con Nmap. En el contexto de pentesting, donde los profesionales enfrentan el desafío de descubrir tantas vulnerabilidades como sea posible en un lapso limitado, es crucial priorizar los activos con mayor superficie de ataque, que tienen más probabilidades de presentar problemas de seguridad. Esta herramienta facilita la identificación y categorización de direcciones IP y puertos abiertos, proporcionando a los pentesters una visión clara de la superficie de ataque. Esto permite enfocar los esfuerzos en aquellos activos con un mayor número de servicios expuestos y, por ende, un potencial más alto de contener vulnerabilidades de seguridad.

## Funcionalidades
- Procesa la salida de Nmap en formatos `.xml` y `.txt`.
- El script organiza las IPs y puertos detectados, destacando las IPs con más servicios y los puertos más recurrentes, para ayudar a enfocarse en los activos más expuestos de la red.
- El script clasifica direcciones IP y puertos, destacando los más comunes en TOP´s y priorizando aquellos que requieren más atención. Presenta los datos de forma clara y ordenada, separados por comas para facilitar su uso con otras herramientas.

## Archivos de Ejemplo
El repositorio incluye dos archivos de ejemplo que demuestran los formatos de entrada que la herramienta puede procesar:
- `prueba.txt`: un archivo de texto en el que cada línea contiene una dirección IP y un puerto, separados por dos puntos (`:`).
- `prueba.xml`: un archivo en formato XML que simula una salida de escaneo de Nmap, generado con el parámetro `-oX`.

## Instalación
No se requiere instalación adicional para este script, todos los modulos son standar de python. Simplemente descargue los archivos del repositorio en su sistema local.

## Uso
Para ejecutar el script, puede usar el siguiente comando en la terminal:
```bash
python3 NmapDataExtractor.py <ruta_del_archivo> [-t <top_n>]
```

- `<ruta_al_archivo>` debe ser la ruta al archivo de salida de Nmap (`.xml` o `.txt en formato IP:PUERTO`).
- `-t <top_n>` es un parámetro opcional para especificar la cantidad de los puertos más comunes a mostrar (el valor predeterminado es 10).
- `-todo` es opcional y se utiliza para definir el número máximo de elementos en el "top". Este valor se establece tomando el mayor entre el número de IPs y el número de puertos.

## Ejemplo de Uso
Para analizar el archivo de ejemplo `prueba.txt` y mostrar los 10 puertos más comunes, ejecute:
```bash
python3 NmapDataExtractor.py prueba.txt
```

Para procesar el archivo `prueba.xml` y mostrar los 20 puertos más comunes, use:
```bash
python3 NmapDataExtractor.py prueba.xml -t 20
```
[![asciicast](https://asciinema.org/a/qKtWuEcq2f6V267MbTKjU440f.svg)](https://asciinema.org/a/qKtWuEcq2f6V267MbTKjU440f)

## Contribuir
Las contribuciones son bienvenidas. Por favor, haga un fork del repositorio, realice sus cambios y envíe un pull request con sus mejoras.
