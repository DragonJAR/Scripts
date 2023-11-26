import requests
import argparse
import json

API_URL = "https://app.emaillistvalidation.com/api/verifEmailv2"
API_KEY = "AQUIAPI"

def mostrar_banner():
    """
    Muestra el banner ASCII al inicio.
    """
    banner = """

    __      __   _ _     _       _             
    \ \    / /  | (_)   | |     | |            
   __\ \  / /_ _| |_  __| | __ _| |_ ___  _ __ 
  / _ \ \/ / _` | | |/ _` |/ _` | __/ _ \| '__|
 |  __/\  / (_| | | | (_| | (_| | || (_) | |   
  \___| \/ \__,_|_|_|\__,_|\__,_|\__\___/|_|   
                                by DragonJAR    
                                                                                                   
    """
    print(banner)

def analizar_argumentos():
    analizador = argparse.ArgumentParser(description='Validador de correos electrónicos.')
    grupo = analizador.add_mutually_exclusive_group(required=True)
    grupo.add_argument('-e', '--email', type=str, help='Correo electrónico para validar.')
    grupo.add_argument('-f', '--archivo', type=str, help='Archivo con correos electrónicos.')
    return analizador.parse_args()

def formatear_correo(correo, ancho=50):
    return correo.ljust(ancho)

def obtener_mensaje_validacion(resultado):
    mensajes = {"valid": "Válido", "invalid": "No Válido"}
    return mensajes.get(resultado, "Resultado desconocido")

def realizar_peticion_api(correo):
    parametros = {"secret": API_KEY, "email": correo}
    try:
        respuesta = requests.get(API_URL, params=parametros, verify=True)
        respuesta.raise_for_status()
        return respuesta.json()
    except requests.exceptions.RequestException as e:
        return {"Error": str(e)}

def validar_correo(correo):
    datos = realizar_peticion_api(correo)
    mensaje = f"Error: {datos['Error']}" if "Error" in datos else obtener_mensaje_validacion(datos.get("Result"))
    print(f"{formatear_correo(correo)} - {mensaje}")

def validar_correos_desde_archivo(ruta_archivo):
    try:
        with open(ruta_archivo, 'r') as archivo:
            for correo in map(str.strip, archivo):
                if correo:
                    validar_correo(correo)
    except (FileNotFoundError, IOError) as e:
        print(f"Error al procesar el archivo: {e}")

def main():
    mostrar_banner()
    argumentos = analizar_argumentos()

    if argumentos.email:
        validar_correo(argumentos.email)
    elif argumentos.archivo:
        validar_correos_desde_archivo(argumentos.archivo)

if __name__ == "__main__":
    main()
