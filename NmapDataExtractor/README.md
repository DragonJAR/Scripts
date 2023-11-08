# NmapDataExtractor


## Descripción
`NmapDataExtractor` es un script de Python sencillo diseñado para analizar y resumir los datos provenientes de escaneos de red efectuados con Nmap. Esta herramienta se especializa en identificar y clasificar direcciones IP y puertos abiertos, simplificando la labor de auditores y pentesters al ofrecer una visión clara de la superficie de ataque, lo que permite priorizar los activos según la cantidad de servicios expuestos.

## Funcionalidades
- Procesa la salida de Nmap en formatos `.xml` y `.txt`.
- Extrae y contabiliza las IPs y puertos encontrados permitiendo ver facilmente los mas expuestos.
- Presenta un resumen ordenado de IPs y puertos, destacando los más recurrentes y generando tops.

## Archivos de Ejemplo
El repositorio incluye dos archivos de ejemplo que demuestran los formatos de entrada que la herramienta puede procesar:
- `prueba.txt`: un archivo de texto en el que cada línea contiene una dirección IP y un puerto, separados por dos puntos (`:`).
- `prueba.xml`: un archivo en formato XML que simula una salida de escaneo de Nmap, generado con el parámetro `-oX`.

## Instalación
No se requiere instalación adicional para este script, todos los modulos son standar de python. Simplemente descargue los archivos del repositorio en su sistema local.

## Uso
Para ejecutar el script, puede usar el siguiente comando en la terminal:
\```bash
python3 NmapDataExtractor.py <ruta_del_archivo> [-t <top_n>]
\```

- `<ruta_al_archivo>` debe ser la ruta al archivo de salida de Nmap (`.xml` o `.txt en formato IP:PUERTO`).
- `-t <top_n>` es un parámetro opcional para especificar la cantidad de los puertos más comunes a mostrar (el valor predeterminado es 10).

## Ejemplo de Uso
Para analizar el archivo de ejemplo `prueba.txt` y mostrar los 10 puertos más comunes, ejecute:
\```bash
python3 NmapDataExtractor.py prueba.txt
\```

Para procesar el archivo `prueba.xml` y mostrar los 20 puertos más comunes, use:
\```bash
python3 NmapDataExtractor.py prueba.xml -t 20
\```

## Contribuir
Las contribuciones son bienvenidas. Por favor, haga un fork del repositorio, realice sus cambios y envíe un pull request con sus mejoras.
