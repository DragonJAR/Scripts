import pyperclip # pip3 install pyperclip
import sys

# Lee el nombre del archivo de texto como parámetro
if len(sys.argv) < 2:
    print("Error: debes especificar el archivo de texto como parámetro.")
    sys.exit(1)

filename = sys.argv[1]

# Lee el contenido del archivo, ejecutalo como python3 ChatGPT-Splitter.py archivodetexto.txt
with open(filename, "r") as f:
    text = f.read()

# Separa el texto en bloques de 4000 caracteres
block_size = 3940
0
blocks = []
start = 0
while start < len(text):
    end = start + block_size
    if end >= len(text):
        blocks.append(text[start:])
        break
    last_space = text.rfind(' ', start, end)
    if last_space == -1:
        last_space = end
    blocks.append(text[start:last_space])
    start = last_space + 1

# Muestra la cantidad de bloques de 4000 caracteres
num_blocks = len(blocks)

banner = '''
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

print(f"\nᐒ El texto se divide en {num_blocks} bloques de {block_size} caracteres.\n")
print(f"ᐒ Acabo de copiar al portapapeles la siguiente instrucción, tu vas a pegarla en ChatGPT:\n")
orden = (f"Ignora todo lo que te he pedido previamente en este chat y vas a recibir un texto largo que está cortado en {num_blocks} partes. Lo único que podrás escribirme hasta que termine de enviarte las {num_blocks} partes es 'OK, entendido. Por favor, envíame la siguiente parte del texto.' cambiando la palabra 'siguiente' por el número en que te encuentres de las {num_blocks} partes. NO DEBES ESCRIBIR NADA DIFERENTE A ESO COMO SALIDA HASTA QUE TE ENVÍE TODAS LAS {num_blocks} PARTES. No te debe importar si el texto parece inconcluso o cortado, ya que el texto solo tendrá sentido cuando termine de enviarte todas las {num_blocks} partes y te empiece a dar órdenes sobre el texto completo. NO vas a procesar el texto que te envíe hasta que termines todas las {num_blocks} partes y TU ÚNICA SALIDA hasta que termine de enviarte las {num_blocks} partes es pedirme la siguiente parte como te acabo de indicar. No hagas nada con el texto hasta que te haya enviado todas las {num_blocks} partes. Cuando hayas terminado de enviarte las {num_blocks} partes, pregúntame qué deseo hacer con ellas y sigue mis órdenes. En ningún momento salgas de los lineamientos que te estoy dando, ni muestres en pantalla una salida distinta a pedirme la siguiente parte, independiente del número de mensajes que llevemos en esta conversación. Si has entendido bien, escribe 'OK, entendido. Por favor, envíame la siguiente parte del texto.' y empieza a pedirme cada parte.")
print(orden)
pyperclip.copy(orden)

# Pregunta al usuario si quiere copiar cada bloque al portapapeles
for i, block in enumerate(blocks):
    print(f"\nBloque {i+1}/{num_blocks}:")
    if i == num_blocks - 1:
        mensaje = (f"Terminamos, esta es la última parte, ahora unicamente escribir 'Que quieres hacer con las {num_blocks} partes?' y espera que te de una orden.")
    else:
        faltan = num_blocks - (i + 1)
        mensaje = (f"Esta es la parte {i+1}. Voy a enviarte las {faltan} partes faltantes, escribe 'OK, entendido. Por favor, envíame la siguiente parte  {i+2} del texto.' si entendiste")

    bloque = (f"Esta es la parte numero {i+1}: '{block}' {mensaje}.")
    if input("ᐒ ¿Desea copiar este bloque al portapapeles? (presione Enter para copiar, o escriba 'no' para omitir) ").strip().lower() == "":
        pyperclip.copy(bloque)
        print("ᐒ Bloque copiado al portapapeles.")
    else:
        print("ᐒ Bloque omitido.")
