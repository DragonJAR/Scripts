# Scripts - Herramientas útiles para pruebas de penetración

1. [Compartido.scf](https://github.com/DragonJAR/Scripts/blob/master/Compartido.scf)
  * Archivo en formato SCF (Shell Command Files) que facilita la ejecución forzada del consumo de un recurso de red. Este archivo es fácilmente modificable y tiene como objetivo obtener el hash del sistema.
2. [DAPwner.cna](https://github.com/DragonJAR/Scripts/blob/master/DAPwner.cna)
  * Script de Cortana que simplifica la automatización de procesos en Armitage, permitiendo detectar nuevas sesiones, extraer contraseñas e información de los sistemas comprometidos y ejecutar comandos automáticamente.
3. [DMA - autoexploit.rc](https://github.com/DragonJAR/Scripts/blob/master/DMA%20-%20autoexploit.rc)
  * Script de Ruby que automatiza el proceso de ejecución de exploits en Metasploit, optimizando el tiempo y los recursos durante la prueba de penetración.
4. [DMA - ejecutar.rc](https://github.com/DragonJAR/Scripts/blob/master/DMA%20-%20ejecutar.rc)
  * Este script enumera una serie de módulos de Meterpreter que se ejecutarán automáticamente en cada máquina comprometida, incluyendo la recopilación de información sobre aplicaciones, dispositivos, archivos y usuarios.
5. [Hijacking-via-PDF.pdf](https://github.com/DragonJAR/Scripts/blob/master/Hijacking-via-PDF.pdf)
  * Este archivo PDF malicioso contiene un formulario XFA (XML Forms Architecture) diseñado para leer el contenido de una página web específica ([http://localhost/secreto.php](http://localhost/secreto.php)) y enviar esa información a otra página web ([http://atacante.com/guardar.php](http://atacante.com/guardar.php)). Su objetivo es extraer información del usuario o del sistema y enviarla a un atacante.
6. [Responder\_to\_PWDump.py](https://github.com/DragonJAR/Scripts/blob/master/Responder_to_PWDump.py)
  * Script de Python que convierte los hashes de Responder.py a formato PWDump, permitiendo procesar hashes desde un archivo, convertir un solo hash en formato Responder a PWDump y extraer hashes directamente de los archivos de registro generados por Responder.py.
7. [all-domain-extensions.txt](https://github.com/DragonJAR/Scripts/blob/master/all-domain-extensions.txt)
  * Archivo que contiene todas las posibles extensiones de dominio existentes en internet, con el objetivo de identificar dominios registrados relacionados a una palabra clave específica.
8. [google-url-extractor.js](https://github.com/DragonJAR/Scripts/blob/master/google-url-extractor.js)
  * Script en JavaScript que, al agregarse como un "favorito" en el navegador, permite extraer todas las URLs de los resultados de búsqueda de Google, facilitando la recopilación de enlaces para análisis posterior.
9. [katz.js](https://github.com/DragonJAR/Scripts/blob/master/katz.js)
  * Versión de Mimikatz convertida a .js utilizando DotNetToJScript, lo que permite ejecutar la herramienta en entornos donde la versión original de Mimikatz no sería compatible o detectable.
10. [mergeness.py](https://github.com/DragonJAR/Scripts/blob/master/mergeness.py)
  * Script en Python que permite unir varios resultados de Nessus en formato .nessus, con el fin de contar con todos los fallos detectados en un solo archivo, simplificando el análisis y la gestión de vulnerabilidades.
11. [ChatGPT-Splitter.py](https://github.com/DragonJAR/Scripts/blob/master/ChatGPT/ChatGPT-Splitter.py)
  * Pequeño script en Python que permite superar las limitaciones de caracteres en ChatGPT y Bing Chat, facilitando el envío de textos de gran tamaño. El script divide el texto en segmentos adecuados para su procesamiento y luego permite realizar acciones sobre el contenido enviado sin restricciones de longitud.
12. [NmapDataExtractor](https://github.com/DragonJAR/Scripts/tree/master/NmapDataExtractor)
  * NmapDataExtractor es un sencillo script de Python diseñado para simplificar la tarea de analizar y sintetizar la información obtenida a través de escaneos de red realizados con Nmap. En el contexto de pentesting, donde los profesionales enfrentan el desafío de descubrir tantas vulnerabilidades como sea posible en un lapso limitado, es crucial priorizar los activos con mayor superficie de ataque, que tienen más probabilidades de presentar problemas de seguridad. Esta herramienta facilita la identificación y categorización de direcciones IP y puertos abiertos, proporcionando a los pentesters una visión clara de la superficie de ataque. Esto permite enfocar los esfuerzos en aquellos activos con un mayor número de servicios expuestos y, por ende, un potencial más alto de contener vulnerabilidades de seguridad.
13. [eValidator.py](https://github.com/DragonJAR/Scripts/tree/master/eValidator.py)
  * eValidator.py es un script realiza validaciones mediante la API de emaillistvalidation.com, con el objetivo de verificar la existencia real de direcciones de correo electrónico específicas. Además, al utilizar el parámetro -f junto con un archivo, el script es capaz de validar cada dirección de correo electrónico contenida en el archivo, línea por línea.
14. [Invoke-Nanodump.ps1](https://github.com/DragonJAR/Scripts/tree/master/Invoke-Nanodump.ps1)
  * Invoke-Nanodump.ps1 es una implementacion de nanodumo (https://github.com/fortra/nanodump) para powershell basado en https://github.com/NotMedic/Invoke-Nanodump/tree/main y ofuscado para evitar detecciónes.
