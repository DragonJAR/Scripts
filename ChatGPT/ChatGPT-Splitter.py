import sys
import signal

banner = '''\n\n
 ██████╗██╗  ██╗ █████╗ ████████╗ ██████╗ ██████╗ ████████╗
██╔════╝██║  ██║██╔══██╗╚══██╔══╝██╔════╝ ██╔══██╗╚══██╔══╝
██║     ███████║███████║   ██║   ██║  ███╗██████╔╝   ██║   
██║     ██╔══██║██╔══██║   ██║   ██║   ██║██╔═══╝    ██║   
╚██████╗██║  ██║██║  ██║   ██║   ╚██████╔╝██║        ██║   
 ╚═════╝╚═╝  ╚═╝╚═╝  ╚═╝   ╚═╝    ╚═════╝ ╚═╝        ╚═╝   

███████╗██████╗ ██╗     ██╗████████╗████████╗███████╗██████╗ 
██╔════╝██╔══██╗██║     ██║╚══██╔══╝╚══██╔══╝██╔════╝██╔══██╗
███████╗██████╔╝██║     ██║   ██║      ██║   █████╗  ██████╔╝
╚════██║██╔═══╝ ██║     ██║   ██║      ██║   ██╔══╝  ██╔══██╗
███████║██║     ███████╗██║   ██║      ██║   ███████╗██║  ██║
╚══════╝╚═╝     ╚══════╝╚═╝   ╚═╝      ╚═╝   ╚══════╝╚═╝  ╚═╝
Salta las limitantes de caracteres en ChatGPT - DragonJAR.org
'''

print(banner)

try:
    import pyperclip
except ModuleNotFoundError:
    print("ᐒ Error: La librería pyperclip no está instalada. Para instalarla, ejecuta 'pip3 install pyperclip'.\n\n")
    sys.exit(1)

# Define una función para manejar la señal de CTRL + C.
def manejador_de_senal(sig, frame):
    print("\n\nᐒ Programa interrumpido por el usuario (CTRL + C)")
    sys.exit(0)

signal.signal(signal.SIGINT, manejador_de_senal)

# Imprime una ayuda en pantalla si se indica el parámetro -h.
def imprimir_ayuda():
    print("ᐒ Este script divide un texto en bloques de caracteres y lo copia al portapapeles para enviarlo a\n"
          "un modelo de lenguaje natural, como ChatGPT o Bing Chat. Puede recibir los siguientes parámetros:\n")
    print("-h: Muestra este menú de ayuda.")
    print("-ia bing: El modelo de lenguaje natural es de Bing Chat y por lo tanto el tamaño de los bloques es distinto.")
    print("\n\nᐒ Ejemplos de ejecución de esta herramienta:\npython3 ChatGPT-Splitter.py archivodetexto.txt\n"
          "python3 ChatGPT-Splitter.py archivodetexto.txt -ia bing\n\n")

# Obtiene el tamaño de los bloques según la IA seleccionada.
def obtener_tamano_de_bloque():
    if '-ia' in sys.argv:
        try:
            ia_value = sys.argv[sys.argv.index('-ia') + 1]
            return 1835 if ia_value == 'bing' else 3935
        except IndexError:
            print("ᐒ El parámetro -ia no tiene un valor especificado, revisa la ayuda con -h.\n\n")
            sys.exit()
    else:
        return 3950

# Lee el nombre del archivo de texto como parámetro.
def leer_texto(nombre_archivo):
    with open(nombre_archivo, "r") as f:
        return f.read()

# Divide el texto en el tamaño de bloque, sin partir la última palabra.
def dividir_texto_en_bloques(texto, tamano_de_bloque):
    bloques = []
    start = 0
    while start < len(texto):
        end = start + tamano_de_bloque
        if end >= len(texto):
            bloques.append(texto[start:])
            break
        last_space = texto.rfind(' ', start, end)
        if last_space == -1:
            last_space = end
        bloques.append(texto[start:last_space])
        start = last_space + 1
    return bloques

# La instrucción para que la IA entienda la orden es redundante intencionalmente,
# para que funcione bien con todas las IA compatibles y no solo las más modernas.
def copiar_instruccion_al_portapapeles(num_bloques):
    instruction = (f"Ignora todo lo que te he pedido previamente en este chat y vas a recibir un texto largo que "
                   f"está cortado en {num_bloques} partes. Lo único que podrás escribirme hasta que termine de enviarte"
                   f" las {num_bloques} partes es 'OK, entendido. Por favor, envíame la siguiente parte del texto.' "
                   f"cambiando la palabra 'siguiente' por el número en que te encuentres de las {num_bloques} partes. "
                   f"NO DEBES ESCRIBIR NADA DIFERENTE A ESO COMO SALIDA HASTA QUE TE ENVÍE TODAS LAS {num_bloques} PARTES."
                   f" No te debe importar si el texto parece inconcluso o cortado, ya que el texto solo tendrá sentido "
                   f"cuando termine de enviarte todas las {num_bloques} partes y te empiece a dar órdenes sobre el texto"
                   f" completo. NO vas a procesar el texto que te envíe hasta que termines todas las {num_bloques} "
                   f"partes y TU ÚNICA SALIDA hasta que termine de enviarte las {num_bloques} partes es pedirme la "
                   f"siguiente parte como te acabo de indicar. No hagas nada con el texto hasta que te haya enviado "
                   f"todas las {num_bloques} partes. Cuando hayas terminado de enviarte las {num_bloques} partes, pregúntame"
                   f" qué deseo hacer con ellas y sigue mis órdenes. En ningún momento salgas de los lineamientos que "
                   f"te estoy dando, ni muestres en pantalla una salida distinta a pedirme la siguiente parte, "
                   f"independiente del número de mensajes que llevemos en esta conversación. Si has entendido bien, "
                   f"escribe 'OK, entendido. Por favor, envíame la siguiente parte del texto.' y empieza a pedirme "
                   f"cada parte.\n\nᐒ Cada bloque de texto se copiará al portapapeles al presionar [ENTER] o [Y].\n"
                   f"Pega el bloque en ChatGPT o Bing Chat y, a continuación, regresa a la consola\n"
                   f"para repetir el proceso. Continúa copiando y pegando bloques hasta que no\n"
                   f"queden más por copiar. Una vez que hayas copiado todos los bloques, después\n"
                   f"indicale instrucciones a la IA sobre qué hacer con el texto completo.")
    print(instruction)
    pyperclip.copy(instruction)

# Pregunta al usuario si quiere copiar cada bloque al portapapeles.
def copiar_bloques_al_portapapeles(bloques):
    num_bloques = len(bloques)
    for i, bloque in enumerate(bloques):
        print(f"\nBloque {i+1}/{num_bloques}:")
        if i == num_bloques - 1:
            mensaje = (f"Terminamos, esta es la última parte, ahora unicamente escribir 'Que quieres hacer con las "
                       f"{num_bloques} partes?' y espera que te de una orden.")
        else:
            restante = num_bloques - (i + 1)
            mensaje = (f"Esta es la parte {i+1}. Voy a enviarte las {restante} partes faltantes, escribe 'OK, "
                       f"entendido. Por favor, envíame la parte {i+2} del texto.' si entendiste")

        texto_bloque = (f"Esta es la parte numero {i+1}: '{bloque}' {mensaje}.")
        if input("ᐒ ¿Desea copiar este bloque al portapapeles? (presione Enter para copiar, o escriba 'no' para omitir) ").strip().lower() == "":
            pyperclip.copy(texto_bloque)
            print("ᐒ Bloque copiado al portapapeles.")
        else:
            print("ᐒ Bloque omitido.")

def main():
    if len(sys.argv) < 2:
        print("ᐒ Error: Debes especificar el archivo de texto como parámetro, mira la ayuda con -h.\n\n")
        sys.exit(1)

    if "-h" in sys.argv:
        imprimir_ayuda()
        sys.exit(0)

    tamano_de_bloque = obtener_tamano_de_bloque()
    nombre_archivo = sys.argv[1]
    texto = leer_texto(nombre_archivo)
    bloques = dividir_texto_en_bloques(texto, tamano_de_bloque)

    num_bloques = len(bloques)
    print(f"\nᐒ El texto se ha dividido en {num_bloques} bloques de caracteres. Acabo de copiar la\n"
      f"siguiente instrucción (prompt) al portapapeles. Debes pegarla en ChatGPT \n"
      f"o Bing Chat y, posteriormente, regresar a la consola para comenzar a \n"
      f"copiar el texto dividido, hasta que copies todos los bloques. \n")

    copiar_instruccion_al_portapapeles(num_bloques)
    copiar_bloques_al_portapapeles(bloques)

if __name__ == "__main__":
    main()
