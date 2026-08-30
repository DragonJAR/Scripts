#!/usr/bin/env python3
import sys
import os
import json
import csv
import argparse
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import datetime, timezone

VERSION = "0.7"

BANNER = r"""
 _   _                      ______      _        _____     _                  _
| \ | |                     |  _  \    | |      |  ___|   | |                | |
|  \| |_ __ ___   __ _ _ __ | | | |__ _| |_ __ _| |____  _| |_ _ __ __ _  ___| |_ ___  _ __
| . ` | '_ ` _ \ / _` | '_ \| | | / _` | __/ _` |  __\ \/ / __| '__/ _` |/ __| __/ _ \| '__|
| |\  | | | | | | (_| | |_) | |/ / (_| | || (_| | |___>  <| |_| | | (_| | (__| || (_) | |
\_| \_/_| |_| |_|\__,_| .__/|___/ \__,_|\__\__,_\____/_/\_\__|_|  \__,_|\___|\__\___/|_|
                      | |
                      |_|
                              v{} - DragonJAR.org
""".format(VERSION)

_usar_color = (
    sys.stdout.isatty()
    and not os.environ.get("NO_COLOR")
)

try:
    import colorama
    colorama.init(strip=not _usar_color)
except ImportError:
    pass


class C:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    ROJO = "\033[31m"
    VERDE = "\033[32m"
    AMAR = "\033[33m"
    AZUL = "\033[34m"
    MAGENTA = "\033[35m"
    CIAN = "\033[36m"
    GRIS = "\033[90m"
    BROJO = "\033[1;31m"
    BVERDE = "\033[1;32m"
    BAMAR = "\033[1;33m"
    BAZUL = "\033[1;34m"
    BMAG = "\033[1;35m"
    BCIAN = "\033[1;36m"


def c(texto, *codigos):
    if not _usar_color or not codigos:
        return str(texto)
    return "".join(codigos) + str(texto) + C.RESET


def linea(titulo, ancho=70, color=C.BCIAN):
    return c(f"\n{'─' * ancho}", color) + c(f"\n  {titulo}", color) + c(f"\n{'─' * ancho}", color)


def warn(msg):
    print(c(f"[!] {msg}", C.AMAR), file=sys.stderr)


def error_y_salir(msg, codigo=2):
    print(c(f"[✗] {msg}", C.BROJO), file=sys.stderr)
    sys.exit(codigo)


def categoria_puerto(puerto):
    try:
        p = int(puerto)
    except (ValueError, TypeError):
        return "desconocida"
    if 0 <= p <= 1023:
        return "well-known (0-1023)"
    if 1024 <= p <= 49151:
        return "registrada (1024-49151)"
    if 49152 <= p <= 65535:
        return "dinámica (49152-65535)"
    return "fuera de rango"


def analizar_xml(ruta):
    try:
        arbol = ET.parse(ruta)
    except FileNotFoundError:
        error_y_salir(f"Archivo no encontrado: {ruta}")
    except ET.ParseError as e:
        error_y_salir(f"XML inválido en {ruta}: {e}")
    except OSError as e:
        error_y_salir(f"Error de E/S leyendo {ruta}: {e}")

    raiz = arbol.getroot()

    meta = {
        "scanner": raiz.get("scanner", ""),
        "args": raiz.get("args", ""),
        "start_epoch": raiz.get("start", ""),
        "start_str": raiz.get("startstr", ""),
        "version_nmap": raiz.get("version", ""),
        "version_xml": raiz.get("xmloutputversion", ""),
    }

    scaninfo = []
    for si in raiz.findall("scaninfo"):
        scaninfo.append({
            "type": si.get("type", ""),
            "protocol": si.get("protocol", ""),
            "numservices": si.get("numservices", ""),
        })
    meta["scaninfo"] = scaninfo

    runstats = {}
    rs = raiz.find("runstats")
    if rs is not None:
        fin = rs.find("finished")
        hs = rs.find("hosts")
        runstats = {
            "finished_time": fin.get("time") if fin is not None else "",
            "finished_str": fin.get("timestr") if fin is not None else "",
            "elapsed_sec": fin.get("elapsed") if fin is not None else "",
            "exit": fin.get("exit") if fin is not None else "",
            "hosts_total": hs.get("total") if hs is not None else "",
            "hosts_up_reportado": hs.get("up") if hs is not None else "",
            "hosts_down_reportado": hs.get("down") if hs is not None else "",
        }
    meta["runstats"] = runstats

    hosts = []
    c_ips = Counter()
    c_puertos = Counter()
    c_servicios = Counter()
    c_productos = Counter()
    c_protocolos = Counter()
    c_estados = Counter()
    c_os = Counter()
    c_hostnames = Counter()
    c_razones = Counter()
    c_scripts = Counter()
    c_categorias = Counter()
    c_extraports = Counter()
    c_cpe = Counter()
    c_vendor = Counter()
    c_uptime_dias = []

    for host in raiz.findall("host"):
        status = host.find("status")
        if status is not None and status.get("state") != "up":
            continue

        ipv4 = ipv6 = mac = None
        vendor_mac = ""
        for addr in host.findall("address"):
            atipo = addr.get("addrtype")
            if atipo == "ipv4":
                ipv4 = addr.get("addr")
            elif atipo == "ipv6":
                ipv6 = addr.get("addr")
            elif atipo == "mac":
                mac = addr.get("addr")
                vendor_mac = addr.get("vendor", "")
                if vendor_mac:
                    c_vendor[vendor_mac] += 1
        ip = ipv4 or ipv6
        if not ip:
            continue

        hostnames = []
        hn_el = host.find("hostnames")
        if hn_el is not None:
            for hn in hn_el.findall("hostname"):
                nombre = hn.get("name", "")
                if nombre:
                    hostnames.append({"name": nombre, "type": hn.get("type", "")})
                    c_hostnames[nombre] += 1

        sistemas = []
        os_el = host.find("os")
        if os_el is not None:
            for om in os_el.findall("osmatch"):
                nombre = om.get("name", "")
                if nombre:
                    sistemas.append({"name": nombre, "accuracy": om.get("accuracy", "0")})
                    c_os[nombre] += 1
                for oc in om.findall("osclass"):
                    cpe = oc.find("cpe")
                    if cpe is not None and cpe.text:
                        c_cpe[cpe.text.strip()] += 1

        puertos_data = []
        scripts_host = []
        ports_el = host.find("ports")
        if ports_el is not None:
            for ep in ports_el.findall("extraports"):
                estado_ep = ep.get("state", "unknown")
                try:
                    c_extraports[estado_ep] += int(ep.get("count", "0"))
                except ValueError:
                    pass

            for p in ports_el.findall("port"):
                proto = p.get("protocol", "")
                portid = p.get("portid", "")
                state_el = p.find("state")
                estado = state_el.get("state", "unknown") if state_el is not None else "unknown"
                razon = state_el.get("reason", "") if state_el is not None else ""
                if razon:
                    c_razones[razon] += 1
                c_estados[estado] += 1

                svc_el = p.find("service")
                svc = svc_prod = svc_ver = svc_extra = ""
                cpe_svc = ""
                if svc_el is not None:
                    svc = svc_el.get("name", "")
                    svc_prod = svc_el.get("product", "")
                    svc_ver = svc_el.get("version", "")
                    svc_extra = svc_el.get("extrainfo", "")
                    if svc:
                        c_servicios[svc] += 1
                    if svc_prod:
                        c_productos[svc_prod] += 1
                    cpe = svc_el.find("cpe")
                    if cpe is not None and cpe.text:
                        cpe_svc = cpe.text.strip()
                        c_cpe[cpe_svc] += 1
                if proto:
                    c_protocolos[proto] += 1

                if estado == "open":
                    c_puertos[portid] += 1
                    c_categorias[categoria_puerto(portid)] += 1

                scripts_puerto = []
                for s in p.findall("script"):
                    sid = s.get("id", "")
                    sout = s.get("output", "")
                    scripts_puerto.append({"id": sid, "output": sout})
                    if sid:
                        c_scripts[sid] += 1
                    scripts_host.append({"ip": ip, "port": portid, "id": sid, "output": sout})

                puertos_data.append({
                    "port": portid,
                    "protocol": proto,
                    "state": estado,
                    "reason": razon,
                    "service": svc,
                    "product": svc_prod,
                    "version": svc_ver,
                    "extrainfo": svc_extra,
                    "cpe": cpe_svc,
                    "scripts": scripts_puerto,
                })

            for s in ports_el.findall("script"):
                sid = s.get("id", "")
                sout = s.get("output", "")
                if sid:
                    c_scripts[sid] += 1
                scripts_host.append({"ip": ip, "port": "", "id": sid, "output": sout})

        times = None
        t_el = host.find("times")
        if t_el is not None:
            times = {
                "srtt_ms": round(float(t_el.get("srtt", "0")) / 1000, 2) if t_el.get("srtt") else None,
                "rttvar_ms": round(float(t_el.get("rttvar", "0")) / 1000, 2) if t_el.get("rttvar") else None,
                "timeout_ms": round(float(t_el.get("to", "0")) / 1000, 2) if t_el.get("to") else None,
            }

        uptime_dias = None
        up_el = host.find("uptime")
        if up_el is not None and up_el.get("seconds"):
            try:
                uptime_dias = round(int(up_el.get("seconds")) / 86400, 1)
                c_uptime_dias.append(uptime_dias)
            except ValueError:
                pass

        distance = None
        d_el = host.find("distance")
        if d_el is not None and d_el.get("value"):
            distance = d_el.get("value")

        abiertos = sum(1 for p in puertos_data if p["state"] == "open")
        c_ips[ip] = abiertos

        hosts.append({
            "ip": ip,
            "ipv4": ipv4,
            "ipv6": ipv6,
            "mac": mac,
            "mac_vendor": vendor_mac,
            "hostnames": hostnames,
            "os": sistemas,
            "times": times,
            "uptime_days": uptime_dias,
            "distance_hops": distance,
            "open_count": abiertos,
            "ports": puertos_data,
            "scripts": scripts_host,
        })

    total_abiertos = sum(v for k, v in c_estados.items() if k == "open")
    return {
        "meta": meta,
        "hosts": hosts,
        "resumen": {
            "hosts_up": len(hosts),
            "puertos_abiertos": total_abiertos,
            "ips_unicas": len(c_ips),
            "con_hostname": sum(1 for h in hosts if h["hostnames"]),
            "con_os": sum(1 for h in hosts if h["os"]),
            "con_scripts": sum(1 for h in hosts if h["scripts"]),
            "total_scripts": sum(c_scripts.values()),
            "con_mac": sum(1 for h in hosts if h["mac"]),
            "con_uptime": len(c_uptime_dias),
            "uptime_promedio_dias": round(sum(c_uptime_dias) / len(c_uptime_dias), 1) if c_uptime_dias else 0,
            "cpe_unicos": len(c_cpe),
        },
        "contadores": {
            "ips": c_ips,
            "puertos": c_puertos,
            "servicios": c_servicios,
            "productos": c_productos,
            "protocolos": c_protocolos,
            "estados": c_estados,
            "os": c_os,
            "hostnames": c_hostnames,
            "razones": c_razones,
            "scripts": c_scripts,
            "categorias": c_categorias,
            "extraports": c_extraports,
            "cpe": c_cpe,
            "vendor": c_vendor,
        },
    }


def analizar_txt(ruta):
    try:
        with open(ruta, "r", encoding="utf-8", errors="replace") as f:
            lineas = f.readlines()
    except FileNotFoundError:
        error_y_salir(f"Archivo no encontrado: {ruta}")
    except OSError as e:
        error_y_salir(f"Error de E/S leyendo {ruta}: {e}")

    c_ips = Counter()
    c_puertos = Counter()
    malas = 0
    for num, linea_raw in enumerate(lineas, 1):
        l = linea_raw.strip()
        if not l:
            continue
        ip, sep, puerto = l.partition(":")
        if sep and ip and puerto.isdigit():
            c_ips[ip] += 1
            c_puertos[int(puerto)] += 1
        else:
            malas += 1
            warn(f"Línea {num} mal formada: '{l}'")

    hosts = [{"ip": ip, "open_count": n, "ports": [], "hostnames": [], "os": [], "scripts": [], "mac": None, "ipv4": ip, "ipv6": None, "times": None, "mac_vendor": "", "uptime_days": None, "distance_hops": None}
             for ip, n in c_ips.items()]
    return {
        "meta": {},
        "hosts": hosts,
        "resumen": {
            "hosts_up": len(c_ips),
            "puertos_abiertos": sum(c_puertos.values()),
            "ips_unicas": len(c_ips),
            "con_hostname": 0,
            "con_os": 0,
            "con_scripts": 0,
            "total_scripts": 0,
            "con_mac": 0,
            "con_uptime": 0,
            "uptime_promedio_dias": 0,
            "cpe_unicos": 0,
        },
        "contadores": {
            "ips": c_ips,
            "puertos": c_puertos,
            "servicios": Counter(),
            "productos": Counter(),
            "protocolos": Counter(),
            "estados": Counter(),
            "os": Counter(),
            "hostnames": Counter(),
            "razones": Counter(),
            "scripts": Counter(),
            "categorias": Counter(),
            "extraports": Counter(),
            "cpe": Counter(),
            "vendor": Counter(),
        },
        "lineas_malas": malas,
    }


def render_humano(d, top_n_valor, mostrar_todo):
    meta = d["meta"]
    res = d["resumen"]
    cnt = d["contadores"]

    print(c(BANNER, C.BCIAN))

    if meta:
        print(linea("METADATOS DEL ESCANEO"))
        if meta.get("start_epoch"):
            try:
                fecha = datetime.fromtimestamp(int(meta["start_epoch"]), tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
            except (ValueError, OSError, OverflowError):
                fecha = meta["start_epoch"]
            print(f"  Fecha           : {c(fecha, C.BVERDE)}")
        if meta.get("start_str"):
            print(f"  Fecha (local)   : {meta['start_str']}")
        if meta.get("args"):
            print(f"  Comando         : {c(meta['args'], C.GRIS)}")
        if meta.get("version_nmap"):
            print(f"  Versión Nmap    : {meta['version_nmap']} (XML {meta.get('version_xml', 'n/a')})")
        if meta.get("scaninfo"):
            print("  Tipos de escaneo:")
            for si in meta["scaninfo"]:
                print(f"    - {si['type']}/{si['protocol']} ({si['numservices']} servicios)")
        rs = meta.get("runstats") or {}
        if rs:
            print(f"  Duración        : {c(rs.get('elapsed_sec', '?') + ' s', C.CIAN)}")
            print(f"  Resultado       : {c(rs.get('exit', '?'), C.BVERDE if rs.get('exit') == 'success' else C.AMAR)}")
            if rs.get("hosts_total"):
                print(f"  Hosts (runstats): {rs['hosts_up_reportado']} up / {rs['hosts_down_reportado']} down / {rs['hosts_total']} total")

    print(linea("RESUMEN GENERAL"))
    print(f"  Hosts activos        : {c(res['hosts_up'], C.BVERDE)}")
    print(f"  Puertos abiertos     : {c(res['puertos_abiertos'], C.BVERDE)}")
    print(f"  IPs únicas           : {c(res['ips_unicas'], C.BVERDE)}")
    if meta:
        extras = []
        if res["con_hostname"]:
            extras.append(f"hostnames={res['con_hostname']}")
        if res["con_os"]:
            extras.append(f"OS detectado={res['con_os']}")
        if res["con_scripts"]:
            extras.append(f"scripts={res['con_scripts']}")
        if res["con_mac"]:
            extras.append(f"MACs={res['con_mac']}")
        if res.get("cpe_unicos"):
            extras.append(f"CPEs={res['cpe_unicos']}")
        if res.get("con_uptime"):
            extras.append(f"uptime medio={res['uptime_promedio_dias']}d")
        if extras:
            print(f"  Extras               : {c(', '.join(extras), C.CIAN)}")

    if cnt["estados"] or cnt["extraports"]:
        print(linea("ESTADOS DE PUERTO"))
        colores_estado = {"open": C.BVERDE, "closed": C.ROJO, "filtered": C.AMAR}
        max_len = max((len(k) for k in cnt["estados"]), default=8)
        for estado, n in cnt["estados"].most_common():
            color = colores_estado.get(estado, C.GRIS)
            print(f"  {estado.ljust(max_len)} (listados) {c(str(n).rjust(6), color)}")
        for estado, n in cnt["extraports"].most_common():
            color = colores_estado.get(estado, C.GRIS)
            print(f"  {estado.ljust(max_len)} (extraports) {c(str(n).rjust(6), color)}")

    if cnt["protocolos"]:
        print(linea("PROTOCOLOS"))
        for proto, n in cnt["protocolos"].most_common():
            print(f"  {proto:<8} {c(str(n).rjust(6), C.BAZUL)}")

    if cnt["categorias"]:
        print(linea("CATEGORÍAS DE PUERTOS ABIERTOS"))
        for cat, n in cnt["categorias"].most_common():
            print(f"  {cat:<28} {c(str(n).rjust(6), C.BMAG)}")

    if cnt["puertos"]:
        print(linea(f"PUERTOS ABIERTOS MÁS COMUNES (TOP {top_n_valor})"))
        max_puerto = max(len(str(p)) for p in cnt["puertos"])
        max_conteo = max(len(str(v)) for v in cnt["puertos"].values())
        max_barra = max(n for _, n in cnt["puertos"].most_common(top_n_valor)) or 1
        for puerto, n in cnt["puertos"].most_common(top_n_valor):
            barra = "█" * max(1, round(n * 40 / max_barra))
            print(f"  {c('Puerto ' + str(puerto).ljust(max_puerto), C.BAMAR)}  {c(str(n).rjust(max_conteo), C.BVERDE)}  {c(barra, C.GRIS)}")

    if cnt["ips"]:
        print(linea(f"IPS CON MÁS PUERTOS ABIERTOS (TOP {top_n_valor})"))
        max_ip = max(len(ip) for ip in cnt["ips"])
        max_conteo = max(len(str(v)) for v in cnt["ips"].values())
        for i, (ip, n) in enumerate(cnt["ips"].most_common(top_n_valor), 1):
            destacado = C.BROJO if n >= 5 else C.AMAR if n >= 3 else C.GRIS
            print(f"  {c(str(i).rjust(4), C.DIM)}. {ip.ljust(max_ip)}  {c(str(n).rjust(max_conteo), destacado)}")

    if cnt["servicios"]:
        print(linea(f"SERVICIOS DETECTADOS (TOP {top_n_valor})"))
        for svc, n in cnt["servicios"].most_common(top_n_valor):
            print(f"  {svc:<24} {c(str(n).rjust(6), C.BCIAN)}")

    if cnt["productos"]:
        print(linea(f"PRODUCTOS DETECTADOS (TOP {top_n_valor})"))
        for prod, n in cnt["productos"].most_common(top_n_valor):
            print(f"  {prod:<36} {c(str(n).rjust(6), C.BAZUL)}")

    if cnt["os"]:
        print(linea(f"SISTEMAS OPERATIVOS DETECTADOS (TOP {top_n_valor})"))
        for so, n in cnt["os"].most_common(top_n_valor):
            print(f"  {so:<40} {c(str(n).rjust(6), C.BMAG)}")

    if cnt["hostnames"]:
        print(linea(f"HOSTNAMES ENCONTRADOS (TOP {top_n_valor})"))
        for hn, n in cnt["hostnames"].most_common(top_n_valor):
            print(f"  {hn:<40} {c(str(n).rjust(6), C.VERDE)}")

    if cnt["cpe"]:
        print(linea(f"CPE DETECTADOS (TOP {top_n_valor})"))
        for cpe, n in cnt["cpe"].most_common(top_n_valor):
            print(f"  {c(cpe, C.BAZUL):<55} {c(str(n).rjust(6), C.CIAN)}")

    if cnt["vendor"]:
        print(linea("VENDORS MAC"))
        for v, n in cnt["vendor"].most_common():
            print(f"  {v:<30} {c(str(n).rjust(6), C.BMAG)}")

    if cnt["scripts"]:
        print(linea(f"SCRIPTS NSE EJECUTADOS (TOP {top_n_valor})"))
        for sid, n in cnt["scripts"].most_common(top_n_valor):
            print(f"  {sid:<32} {c(str(n).rjust(6), C.BAMAR)}")

    if cnt["razones"]:
        print(linea("RAZONES DE ESTADO"))
        for razon, n in cnt["razones"].most_common(10):
            print(f"  {razon:<24} {c(str(n).rjust(6), C.GRIS)}")

    if mostrar_todo:
        if cnt["ips"]:
            print(linea("TODAS LAS IPs POR PUERTOS ABIERTOS"))
            print("  " + ", ".join(ip for ip, _ in cnt["ips"].most_common()))
        if cnt["puertos"]:
            print(linea("TODOS LOS PUERTOS POR FRECUENCIA"))
            print("  " + ", ".join(str(p) for p, _ in cnt["puertos"].most_common()))

    print(c("\n" + "─" * 70, C.BCIAN))


def serializar(d):
    def ccnt(x):
        return {str(k): v for k, v in x.items()}
    return {
        "version": VERSION,
        "meta": d["meta"],
        "resumen": d["resumen"],
        "contadores": {k: ccnt(v) for k, v in d["contadores"].items()},
        "hosts": d["hosts"],
    }


def render_json(d):
    print(json.dumps(serializar(d), indent=2, ensure_ascii=False))


def render_csv(d, fh):
    escritor = csv.writer(fh)
    escritor.writerow(["ip", "mac", "vendor", "hostname", "os", "port", "protocol", "state", "reason", "service", "product", "version", "extrainfo", "cpe", "scripts"])
    for h in d["hosts"]:
        hostname = "; ".join(x["name"] for x in h["hostnames"]) if h["hostnames"] else ""
        so = "; ".join(f"{x['name']}({x['accuracy']}%)" for x in h["os"]) if h["os"] else ""
        scripts = "; ".join(x["id"] for x in h["scripts"]) if h["scripts"] else ""
        if not h["ports"]:
            escritor.writerow([h["ip"], h["mac"] or "", h.get("mac_vendor", "") or "", hostname, so, "", "", "", "", "", "", "", "", "", scripts])
        for p in h["ports"]:
            scrits_puerto = "; ".join(x["id"] for x in p["scripts"]) if p["scripts"] else ""
            escritor.writerow([h["ip"], h["mac"] or "", h.get("mac_vendor", "") or "", hostname, so,
                               p["port"], p["protocol"], p["state"], p["reason"],
                               p["service"], p["product"], p["version"], p["extrainfo"],
                               p.get("cpe", ""), scrits_puerto or scripts])


def main():
    analizador = argparse.ArgumentParser(
        prog="NmapDataExtractor",
        description=f"v{VERSION} - Extrae y analiza datos de resultados Nmap (.xml, .txt). Salida coloreada, JSON o CSV.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  %(prog)s escaneo.xml                     # análisis coloreado en pantalla
  %(prog)s escaneo.xml -t 20               # muestra top 20 en cada sección
  %(prog)s escaneo.xml --json > out.json   # salida JSON completa para pipelines
  %(prog)s escaneo.xml --csv > out.csv     # salida CSV plano (host×puerto)
  %(prog)s escaneo.xml --todo              # muestra todos los datos sin truncar
        """)
    analizador.add_argument("archivo", help="Ruta al archivo de resultados Nmap (.xml o .txt)")
    analizador.add_argument("-t", "--top", type=int, default=10, metavar="N",
                            help="Número de elementos a mostrar en cada top (default: 10)")
    analizador.add_argument("-todo", "--todo", action="store_true",
                            help="Muestra todos los datos disponibles en pantalla")
    analizador.add_argument("--json", action="store_true",
                            help="Salida en formato JSON (ignora colores y --todo)")
    analizador.add_argument("--csv", action="store_true",
                            help="Salida en formato CSV plano (una fila por host×puerto)")
    analizador.add_argument("--no-color", action="store_true",
                            help="Desactiva colores (también respeta la variable NO_COLOR)")

    args = analizador.parse_args()

    if args.top < 1:
        analizador.error("El valor de --top debe ser mayor o igual a 1")
    if args.json and args.csv:
        analizador.error("Las opciones --json y --csv son mutuamente excluyentes")
    if args.no_color:
        global _usar_color
        _usar_color = False

    extension = args.archivo.rsplit(".", 1)[-1].lower()
    if extension == "xml":
        datos = analizar_xml(args.archivo)
    elif extension == "txt":
        datos = analizar_txt(args.archivo)
    else:
        error_y_salir(f"Formato no soportado: .{extension}. Use .xml o .txt", codigo=1)

    if args.json:
        render_json(datos)
    elif args.csv:
        render_csv(datos, sys.stdout)
    else:
        top_n = args.top
        if args.todo:
            top_n = max(len(datos["contadores"]["ips"]), len(datos["contadores"]["puertos"]), 1)
        if not datos["resumen"]["hosts_up"]:
            warn("No se encontraron hosts activos en el archivo.")
            sys.exit(0)
        render_humano(datos, top_n, args.todo)


if __name__ == "__main__":
    main()
