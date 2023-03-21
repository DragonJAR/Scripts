# -*- coding: utf-8 -*-

print("""
 ____     ___   _____ ____    ___   ____   ___      ___  ____       ____   __ __ 
|    \\   /  _] / ___/|    \\  /   \\ |    \\ |   \\    /  _]|    \\     |    \\ |  |  |
|  D  ) /  [_ (   \\_ |  o  )|     ||  _  ||    \\  /  [_ |  D  )    |  o  )|  |  |
|    / |    _] \\__  ||   _/ |  O  ||  |  ||  D  ||    _]|    /     |   _/ |  ~  |
|    \\ |   [_  /  \\ ||  |   |     ||  |  ||     ||   [_ |    \\  __ |  |   |___, |
|  .  \\|     | \\    ||  |   |     ||  |  ||     ||     ||  .  \\|  ||  |   |     |
|__|\\_||_____|  \\___||__|    \\___/ |__|__||_____||_____||__|\\_||__||__|   |____/ 
                                                                                 
         ______   ___       ____   __    __  ___    __ __  ___ ___  ____         
        |      | /   \\     |    \\ |  |__|  ||   \\  |  |  ||   |   ||    \\        
        |      ||     |    |  o  )|  |  |  ||    \\ |  |  || _   _ ||  o  )       
        |_|  |_||  O  |    |   _/ |  |  |  ||  D  ||  |  ||  \\_/  ||   _/        
          |  |  |     |    |  |   |  `  '  ||     ||  :  ||   |   ||  |          
          |  |  |     |    |  |    \\      / |     ||     ||   |   ||  |          
          |__|   \\___/     |__|     \\_/\\_/  |_____| \\__,_||___|___||__|          
          
       Convierte los hash de Responder.py a formato PWDump - DragonJAR.org
""")
import re
import os
import sys
import argparse

def responder_a_pwdump(hash_responder):
    """Convierte un hash en formato Responder.py a formato PWDump."""
    regex_responder = re.compile(
        r"^(?P<nombre_usuario>[^:]*)[:]{1,2}(?P<dominio>[^:]*):(?P<hash_lm>[A-Fa-f0-9]{16}):(?P<hash_ntlm>[A-Fa-f0-9]{32}):.*$"
    )

    coincidencia = regex_responder.match(hash_responder)

    if coincidencia:
        nombre_usuario = coincidencia.group("nombre_usuario")
        hash_lm = coincidencia.group("hash_lm")
        hash_ntlm = coincidencia.group("hash_ntlm")

        hash_pwdump = f"{nombre_usuario}:0:{hash_lm}:{hash_ntlm}:::"
        return hash_pwdump
    else:
        raise ValueError("Formato de hash Responder no válido")

def procesar_hashes_desde_archivo(archivo):
    try:
        with open(archivo, 'r') as f:
            hashes_responder = f.readlines()
    except IOError as e:
        print(f"Error al abrir o leer el archivo '{archivo}': {e}")
        return

    for i, hash_responder in enumerate(hashes_responder):
        try:
            hash_pwdump = responder_a_pwdump(hash_responder.strip())
            print(hash_pwdump)
        except ValueError as e:
            print(f"Error en la línea {i + 1}: {e}")

def extraer_hashes_desde_logs(ruta_log):
    """Extrae los hashes en formato Responder de un archivo de registro de Responder.py y los convierte a formato PWDump."""
    regex_responder = re.compile(
        r"(?:^\d{2}\/\d{2}\/\d{4} \d{2}:\d{2}:\d{2} (?:AM|PM) - \[(?:.*?)\].*?NTLMv2.*?Hash.*?:\s*(?P<hash_ntlmv2>\S+)$)|(?:^(?P<nombre_usuario>[^:]*)[:]{1,2}(?P<dominio>[^:]*):(?P<hash_lm>[A-Fa-f0-9]{16}):(?P<hash_ntlm>[A-Fa-f0-9]+):.*)"
    )

    try:
        with open(ruta_log, 'r') as f:
            lineas = f.readlines()
    except IOError as e:
        print(f"Error al abrir o leer el archivo '{ruta_log}': {e}")
        return

    for i, linea in enumerate(lineas):
        coincidencia = regex_responder.match(linea.strip())
        if coincidencia:
            try:
                hash_ntlmv2 = coincidencia.group('hash_ntlmv2')
                hash_pwdump = responder_a_pwdump(hash_ntlmv2)
                print("ᐒ Hash NTLMv2 Extraido de los Logs del Responder.py:")
                print(hash_ntlmv2)
                print("ᐒ Hash NTLMv2 convertidos a formato PWDump:")
                print(hash_pwdump)
                print("\n")
            except ValueError as e:
                print(f"Error en la línea {i + 1}: {e}")


def main():
    """Función principal para manejar los argumentos de línea de comandos."""
    parser = argparse.ArgumentParser(description='Convierte hashes en formato Responder a formato PWDump.')
    parser.add_argument('-f', '--file', metavar='', help='Archivo que contiene hashes en formato Responder, un hash por línea.')
    parser.add_argument('-s', '--single', metavar='', help='Hash individual en formato Responder proporcionado como texto.')
    parser.add_argument('-r', '--responder_logs', metavar='', help='Extrae hashes directamente de los archivos de registro (logs) generados por Responder.py.')
    parser.add_argument('-l', '--log_path', metavar='', help='Ruta del archivo de registro de Responder.py si no se encuentra en la ruta predeterminada. Utilizar en conjunto con -r: "-r -l RUTA_DEL_LOG".')

    args = parser.parse_args()

    if args.file:
        procesar_hashes_desde_archivo(args.file)
    elif args.single:
        try:
            hash_pwdump = responder_a_pwdump(args.single)
            print(hash_pwdump)
        except ValueError as e:
            print(f"Error: {e}")

    elif args.responder_logs:
        ruta_defecto = "/usr/share/responder/logs/Responder-Session.log"
        
        if args.log_path:
            ruta_log = args.log_path
        elif os.path.exists(ruta_defecto):
            ruta_log = ruta_defecto
        else:
            print("No se encontró el archivo de registro de Responder.py en la ruta por defecto. Por favor, proporcione la ruta utilizando la opción '-l'.")
            return

        extraer_hashes_desde_logs(ruta_log)
    else:
        print("ᐒ Debes especificar un archivo con la opción '-f', un hash con la opción '-s'\n o si desea extraer los hash de los logs del responder-py directamente usa la opcion -r.\n\n")

if __name__ == "__main__":
    main()