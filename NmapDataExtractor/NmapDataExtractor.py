import sys
import xml.etree.ElementTree as ET
from collections import Counter
import argparse

BANNER = """
 _   _                      ______      _        _____     _                  _             
| \ | |                     |  _  \    | |      |  ___|   | |                | |            
|  \| |_ __ ___   __ _ _ __ | | | |__ _| |_ __ _| |____  _| |_ _ __ __ _  ___| |_ ___  _ __ 
| . ` | '_ ` _ \ / _` | '_ \| | | / _` | __/ _` |  __\ \/ / __| '__/ _` |/ __| __/ _ \| '__|
| |\  | | | | | | (_| | |_) | |/ / (_| | || (_| | |___>  <| |_| | | (_| | (__| || (_) | |   
\_| \_/_| |_| |_|\__,_| .__/|___/ \__,_|\__\__,_\____/_/\_\__|_|  \__,_|\___|\__\___/|_|   
                      | |                                                                   
                      |_|                                                                   
                              v0.6 - DragonJAR.org
"""

# Funciones de ayuda
def mostrar_banner():
    print(BANNER)

def mostrar_resultados(contador_ips, contador_puertos, top_n):
    """Mostrar los resultados del análisis."""
    mostrar_informacion_ips(contador_ips, top_n)
    mostrar_informacion_puertos(contador_puertos, top_n)
    print("\n" + "=" * 60 + "\n")

def mostrar_informacion_ips(contador_ips, top_n=10):
    """Mostrar información de IPs."""
    print("\n" + "=" * 60)
    print(" " * 19 + "INFORMACIÓN DE IPs")
    print("=" * 60)
    print("")
    if contador_ips:
        ip_mas_comun, conteo = contador_ips.most_common(1)[0]
        longitud_maxima_ip = max(len(ip) for ip in contador_ips)
        longitud_maxima_conteo = len(str(conteo))
        longitud_maxima_linea = len(str(len(contador_ips)))
        ip_mas_comun_formateada = f"{ip_mas_comun} (Tiene {conteo} puertos)".ljust(longitud_maxima_ip + longitud_maxima_conteo + 5)
        print(f"IP con más puertos: {ip_mas_comun_formateada}")
        print(f"\nTotal de IPs únicas: {len(contador_ips)}\n")
        print(f"Top {top_n} IPs por número de puertos abiertos:\n")
        for indice, (ip, conteo) in enumerate(contador_ips.most_common(top_n), 1):
            ip_formateada = f"{ip}".ljust(longitud_maxima_ip)
            conteo_formateado = f"Tiene {conteo} puerto(s) abiertos".rjust(longitud_maxima_conteo + 8)
            print(f"{str(indice).rjust(longitud_maxima_linea)}) {ip_formateada} - {conteo_formateado}")

        ips_ordenadas = [f"{ip}" for ip, conteo in contador_ips.most_common()]
        print("\nTodas las IPs encontradas ordenadas por número de puertos abiertos que tiene:\n")
        print(", ".join(ips_ordenadas))

def mostrar_informacion_puertos(contador_puertos, top_n):
    """Mostrar información de puertos."""
    print("\n" + "=" * 60)
    print(" " * 19 + "INFORMACIÓN DE PUERTOS")
    print("=" * 60)
    print("")
    if contador_puertos:
        puerto_mas_comun, conteo_puerto_mas_comun = contador_puertos.most_common(1)[0]
        print(f"Puerto más común: Puerto {puerto_mas_comun} (Aparece {conteo_puerto_mas_comun} veces)\n")
        total_puertos_abiertos = sum(contador_puertos.values())
        print(f"Total de puertos abiertos: {total_puertos_abiertos}\n")

        longitud_maxima_conteo = max(len(str(conteo)) for _, conteo in contador_puertos.most_common())
        longitud_maxima_puerto = max(len(str(puerto)) for puerto, _ in contador_puertos.most_common())
        print(f"Puertos más comunes (Top {top_n}):\n")
        for puerto, conteo in contador_puertos.most_common(top_n):
            puerto_formateado = f"Puerto {puerto}".ljust(longitud_maxima_puerto + 7)
            conteo_formateado = f"Aparece {str(conteo).rjust(longitud_maxima_conteo)} veces".rjust(longitud_maxima_conteo + 7)
            print(f"{puerto_formateado} - {conteo_formateado}")
        print("\nTodos los puertos encontrados ordenados por numero de veces que aparece:\n")
        puertos_ordenados = [str(puerto) for puerto, _ in contador_puertos.most_common()]
        print(", ".join(puertos_ordenados))

# Funciones principales de procesamiento
def leer_archivo_txt(ruta_archivo):
    """Leer líneas de un archivo de texto."""
    try:
        with open(ruta_archivo, 'r') as archivo:
            return archivo.readlines()
    except Exception as e:
        print(f"No se pudo leer el archivo {ruta_archivo}: {e}")
        sys.exit(1)

def analizar_lineas_txt(lineas):
    """Analizar líneas de texto y contar IPs y puertos."""
    contador_ips = Counter()
    contador_puertos = Counter()
    for num_linea, linea in enumerate(lineas, 1):
        ip, separador, puerto = linea.strip().partition(':')
        if separador:
            contador_ips[ip] += 1
            contador_puertos[puerto] += 1
        else:
            print(f"Advertencia: Línea {num_linea} mal formada '{linea.strip()}'")
    return contador_ips, contador_puertos

def extraer_puertos_abiertos_xml(ruta_archivo_xml):
    """Extraer puertos abiertos de un archivo XML."""
    try:
        arbol = ET.parse(ruta_archivo_xml)
    except Exception as e:
        print(f"No se pudo leer el archivo XML: {e}")
        sys.exit(1)
    
    raiz = arbol.getroot()
    puertos_abiertos = [
        f"{host.find('address').get('addr')}:{puerto.get('portid')}"
        for host in raiz.findall('host')
        if (host.find('address') is not None and host.find('address').get('addrtype') == 'ipv4')
        for puerto in host.find('ports').findall('port')
        if puerto.find('state').get('state') == 'open'
    ]
    return puertos_abiertos

def procesar_archivo(nombre_archivo, top_n, mostrar_todo=False):
    """Procesar archivo y mostrar resultados. Ajustado para manejar la opción -todo."""
    extension = nombre_archivo.rsplit('.', 1)[-1].lower()
    if extension == 'txt':
        lineas = leer_archivo_txt(nombre_archivo)
        contador_ips, contador_puertos = analizar_lineas_txt(lineas)
    elif extension == 'xml':
        puertos_abiertos = extraer_puertos_abiertos_xml(nombre_archivo)
        contador_ips, contador_puertos = analizar_lineas_txt(puertos_abiertos)
    else:
        print("Formato de archivo no soportado. Utilice .xml o .txt.")
        sys.exit(1)

    # Ajustar el valor de top_n si se proporcionó la opción -todo
    if mostrar_todo:
        top_n = max(len(contador_ips), sum(contador_puertos.values()))

    mostrar_resultados(contador_ips, contador_puertos, top_n)

# Función de entrada del programa
def main():
    mostrar_banner()
    analizador = argparse.ArgumentParser(description="Extractor de Datos de Nmap")
    analizador.add_argument("archivo", help="Ruta al archivo de resultados de Nmap")
    analizador.add_argument("-t", "--top", type=int, default=10, help="Número de top puertos a mostrar")
    analizador.add_argument("-todo", action="store_true", help="Muestra todos los datos disponibles")
    
    argumentos = analizador.parse_args()
    
    procesar_archivo(argumentos.archivo, argumentos.top, argumentos.todo)

if __name__ == '__main__':
    main()
