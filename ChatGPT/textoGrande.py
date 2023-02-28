import pyperclip
import sys

# Lee el nombre del archivo de texto como parámetro
if len(sys.argv) < 2:
    print("Error: debes especificar el archivo de texto como parámetro.")
    sys.exit(1)

filename = sys.argv[1]

# Lee el contenido del archivo
with open(filename, "r") as f:
    text = f.read()

# Separa el texto en bloques de 4000 caracteres
block_size = 4000
blocks = [text[i:i+block_size] for i in range(0, len(text), block_size)]

# Muestra la cantidad de bloques de 4000 caracteres
num_blocks = len(blocks)
print(f"El texto se divide en {num_blocks} bloques de {block_size} caracteres.")

# Pregunta al usuario si quiere copiar cada bloque al portapapeles
for i, block in enumerate(blocks):
    print(f"\nBloque {i+1}/{num_blocks}:")
    print(block)
    if input("¿Desea copiar este bloque al portapapeles? (presione Enter para copiar, o escriba 'no' para omitir) ").strip().lower() == "":
        pyperclip.copy(block)
        print("Bloque copiado al portapapeles.")
    else:
        print("Bloque omitido.")
