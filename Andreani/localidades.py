#esto realiza un filtro a data_arg para obtener el provincia, localidad y codigo postal de un usuario.
import json

def eleccion_usuario(lista):
    if lista:
        for i, item in enumerate(lista):
            print(f"{i + 1}. {item}")

        while True:
            try:
                index = int(input("Selecciona una opcion (número): ")) - 1
                if 0 <= index < len(lista):
                    break
                else:
                    print("Selección inválida. Por favor, elige un número válido.")
            except ValueError:
                print("Entrada no válida. Ingresa un número válido.")
        return index


# Cargar el archivo JSON
with open("data_arg.json", "r") as f:
    data_arg = json.load(f)

#lista de provincias de Argentina:
nombres_provincias = list({item["provincia"] for item in data_arg})
nombres_provincias.sort()

print('Provincias disponibles:')
index = eleccion_usuario(nombres_provincias)
provincia_seleccionada = nombres_provincias[index]
#print(provincia_seleccionada)

#lista de localidades de la provincia seleccionada:
nombres_localidades = []

for i in data_arg:
    if i['provincia'] == provincia_seleccionada:
        nombres_localidades.append(i["localidad"])

nombres_localidades.sort()

print(f'Localidades disponibles en la provincia de {provincia_seleccionada}:')
index = eleccion_usuario(nombres_localidades)
localidad_seleccionada = nombres_localidades[index]


# lista de codigos postales de la localidad seleccionada por el usuario:
codigos_postales = []

for i in data_arg:
    if i['localidad'] == localidad_seleccionada:
        codigos_postales.extend(i["codigosPostales"])

codigos_postales.sort()

print(f'Codigos postales disponibles en la localidad de {localidad_seleccionada}:')
index = eleccion_usuario(codigos_postales)
codigo_postal_seleccionado = codigos_postales[index]


