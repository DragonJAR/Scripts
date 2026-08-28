import os
import sys
import argparse
from collections import Counter

import requests

API_URL = "https://app.emaillistvalidation.com/api/v1/verify"
FINDER_DOMAIN_URL = "https://app.emaillistvalidation.com/api/v1/finder/domain"
API_KEY = "SUAPI"  # pegá acá tu key (evp_...); si está vacío usa ELV_API_KEY

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
    analizador = argparse.ArgumentParser(description='Validador y buscador de correos electrónicos (DragonJAR).')
    grupo = analizador.add_mutually_exclusive_group(required=True)
    grupo.add_argument('-e', '--email', type=str, help='Correo electrónico para validar.')
    grupo.add_argument('-f', '--archivo', type=str, help='Archivo con correos electrónicos para validar.')
    grupo.add_argument('-d', '--dominio', type=str, help='Dominio para buscar correos (finder por dominio).')
    analizador.add_argument('-l', '--limite', type=int, default=5000,
                            help='Máx. correos a recuperar del dominio (por defecto todos; la API página de a 50).')
    return analizador.parse_args()

def obtener_api_key():
    key = API_KEY or os.environ.get("ELV_API_KEY")
    if not key:
        sys.exit("Error: definí API_KEY en el script o exportá ELV_API_KEY")
    return key

def _cabecera():
    print(color(f"{'CORREO':<44} {'ESTADO':<12} {'CONF':>4}  {'DETALLE'}", GRIS))
    print(color("-" * ANCHO, GRIS))

def _fila(correo, estado, conf, detalle=""):
    est, cod = VEREDICTOS.get(estado, (estado.upper(), GRIS)) if estado else ("ERROR", "\033[91m")
    if estado is None:
        est, cod = "ERROR", "\033[91m"
    print(f"{correo:<44} {color(f'{est:<12}', cod)} {str(conf):>4}  {detalle}")

def _estado_apilable(valor):
    """Traduce un estado devuelto por la API a una clave del resumen (o None si es error)."""
    if valor is None:
        return None
    clave = str(valor).lower()
    # La API de verificación devuelve deliverable/undeliverable/risky/unknown
    return {"deliverable": "valid", "undeliverable": "invalid"}.get(clave, clave)

def buscar_dominio(dominio, api_key, limite=5000):
    """Busca correos asociados a un dominio vía /finder/domain.

    La API devuelve como máximo 50 correos por página (limit), pero indica el
    total real; para ver el resto se pagina con `offset` hasta completar
    `limite` (50+ resultados).
    """
    emails = []
    total = None
    credits = 0
    offset = 0
    tam_pagina = 50  # la API no acepta más de 50 por página
    if limite < 1:
        sys.exit("Error: el límite debe ser mayor a 0")
    try:
        while len(emails) < limite:
            respuesta = requests.post(
                FINDER_DOMAIN_URL,
                headers={"Authorization": f"Bearer {api_key}"},
                json={"domain": dominio, "limit": tam_pagina, "offset": offset},
                timeout=45,
            )
            if respuesta.status_code in (401, 403):
                sys.exit(f"Error de autenticación ({respuesta.status_code}): revisá la API key")
            respuesta.raise_for_status()
            datos = respuesta.json()
            if datos.get("success") is False or "error" in datos:
                print(f"{color('ERROR', '\033[91m')} {datos.get('error', datos)}")
                return False
            d = datos.get("data", {})
            total = d.get("total", 0)
            credits = d.get("credits_used", 0)
            pagina = d.get("emails", [])
            if not pagina:
                break
            emails.extend(pagina)
            if len(emails) >= total:
                break
            offset += tam_pagina
    except requests.exceptions.RequestException as e:
        print(f"{color('ERROR', '\033[91m')} al consultar {dominio}: {e}")
        return False

    if limite < total:
        emails = emails[:limite]
    total_real = total
    total = len(emails)
    _cabecera()
    for item in emails:
        correo = item.get("email", "?")
        estado = _estado_apilable(item.get("status"))
        conf = item.get("confidence", "")
        detalle = item.get("reason", "") or ""
        if item.get("is_catch_all"):
            detalle += " · catch-all"
        if item.get("is_role"):
            detalle += " · rol"
        _fila(correo, estado, conf, detalle)
    print(color("=" * ANCHO, GRIS))
    if total < total_real:
        print(f"Dominio {dominio}: mostrando {total} de {total_real} correo(s) · créditos usados: {credits}")
    else:
        print(f"Dominio {dominio}: {total} correo(s) encontrado(s) · créditos usados: {credits}")
    return True

def validar_correo(correo, api_key):
    """Valida un correo, imprime la fila y devuelve el estado normalizado (o None si falló)."""
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
        _fila(correo, None, "", str(e))
        return None
    if datos.get("success") is False or "error" in datos:
        _fila(correo, None, "", str(datos.get("error", datos)))
        return None

    d = datos.get("data", {})
    clave = _estado_apilable(d.get("result", "unknown"))
    razon = d.get("reason", "")
    score = d.get("score", "")
    sugerencia = f"  ¿quisiste decir {d['did_you_mean']}?" if d.get("did_you_mean") else ""
    _fila(correo, clave, score, razon + sugerencia)
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

    _cabecera()
    resumen = Counter(filter(None, (validar_correo(c, api_key) for c in correos)))
    mostrar_resumen(len(correos), resumen)
    return total_sin_errores(len(correos), resumen)

def total_sin_errores(total, resumen):
    return total == sum(resumen.values())

def main():
    mostrar_banner()
    argumentos = analizar_argumentos()
    api_key = obtener_api_key()

    if argumentos.dominio:
        ok = buscar_dominio(argumentos.dominio, api_key, argumentos.limite)
    elif argumentos.email:
        ok = validar_correo(argumentos.email, api_key) is not None
    else:
        ok = validar_correos_desde_archivo(argumentos.archivo, api_key)

    sys.exit(0 if ok else 1)

if __name__ == "__main__":
    main()
