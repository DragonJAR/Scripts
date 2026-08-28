import os
import sys
import argparse
from collections import Counter

import requests

API_URL = "https://app.emaillistvalidation.com/api/v1/verify"
API_KEY = "API"  # pegá acá tu key (evp_...); si está vacío usa ELV_API_KEY

RESET, GRIS = "\033[0m", "\033[90m"
VEREDICTOS = {
    "valid":   ("VÁLIDO",      "\033[92m"),
    "invalid": ("NO VÁLIDO",   "\033[91m"),
    "risky":   ("RIESGO",      "\033[93m"),
    "unknown": ("DESCONOCIDO", "\033[96m"),
}
ANCHO = 78

def color(texto, codigo):
    return f"{codigo}{texto}{RESET}" if sys.stdout.isatty() else texto

def mostrar_banner():
    banner = r"""

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

def obtener_api_key():
    key = API_KEY or os.environ.get("ELV_API_KEY")
    if not key:
        sys.exit("Error: definí API_KEY en el script o exportá ELV_API_KEY")
    return key

def validar_correo(correo, api_key):
    """Valida un correo, imprime la fila y devuelve el veredicto (o None si falló)."""
    try:
        respuesta = requests.post(
            API_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            json={"email": correo},
            timeout=30,
        )
        if respuesta.status_code in (401, 403):
            sys.exit(f"Error de autenticación ({respuesta.status_code}): revisá la API key")
        respuesta.raise_for_status()
        datos = respuesta.json()
    except requests.exceptions.RequestException as e:
        print(f"{correo:<40} {color('ERROR', '\033[91m'):<9} {e}")
        return None
    if datos.get("success") is False or "error" in datos:
        print(f"{correo:<40} {color('ERROR', '\033[91m'):<9} {datos.get('error', datos)}")
        return None

    d = datos.get("data", {})
    clave = d.get("result", "unknown")
    etiqueta, codigo = VEREDICTOS.get(clave, (clave.upper(), GRIS))
    razon = d.get("reason", "")
    score = str(d.get("score", ""))
    sugerencia = f"  ¿quisiste decir {d['did_you_mean']}?" if d.get("did_you_mean") else ""
    print(f"{correo:<40} {color(f'{etiqueta:<11}', codigo)} {razon:<14} {score:>4}{sugerencia}")
    return clave

def mostrar_resumen(total, resumen):
    print(color("=" * ANCHO, GRIS))
    print(f"Resumen: {total} correos procesados")
    for clave in ("valid", "invalid", "risky", "unknown"):
        if clave in resumen:
            etiqueta, codigo = VEREDICTOS[clave]
            barra = "█" * resumen[clave]
            print(f"  {color(f'{etiqueta:<11}', codigo)} {resumen[clave]:>4}  {color(barra, codigo)}")
    errores = total - sum(resumen.values())
    if errores:
        print(f"  {color(f'{'ERROR':<11}', '\033[91m')} {errores:>4}")

def validar_correos_desde_archivo(ruta_archivo, api_key):
    try:
        with open(ruta_archivo, 'r') as archivo:
            correos = [c for c in map(str.strip, archivo) if c]
    except (FileNotFoundError, IOError) as e:
        sys.exit(f"Error al procesar el archivo: {e}")
    if not correos:
        sys.exit("El archivo no contiene correos.")

    print(color(f"{'CORREO':<40} {'ESTADO':<11} {'RAZÓN':<14} {'SCORE':>4}", GRIS))
    print(color("-" * ANCHO, GRIS))
    resumen = Counter(filter(None, (validar_correo(c, api_key) for c in correos)))
    mostrar_resumen(len(correos), resumen)
    return total_sin_errores(len(correos), resumen)

def total_sin_errores(total, resumen):
    return total == sum(resumen.values())

def main():
    mostrar_banner()
    argumentos = analizar_argumentos()
    api_key = obtener_api_key()

    if argumentos.email:
        ok = validar_correo(argumentos.email, api_key) is not None
    else:
        ok = validar_correos_desde_archivo(argumentos.archivo, api_key)

    sys.exit(0 if ok else 1)

if __name__ == "__main__":
    main()
