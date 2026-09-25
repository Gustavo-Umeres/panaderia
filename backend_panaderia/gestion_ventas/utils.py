# gestion_ventas/utils.py

def numero_a_letras(num):
    # Your existing numero_a_letras implementation
    unidades = ['', 'un', 'dos', 'tres', 'cuatro', 'cinco', 'seis', 'siete', 'ocho', 'nueve']
    dieces = ['diez', 'once', 'doce', 'trece', 'catorce', 'quince', 'dieciséis', 'diecisiete', 'dieciocho', 'diecinueve']
    decenas = ['', '', 'veinte', 'treinta', 'cuarenta', 'cincuenta', 'sesenta', 'setenta', 'ochenta', 'noventa']
    centenas = ['', 'ciento', 'doscientos', 'trescientos', 'cuatrocientos', 'quinientos', 'seiscientos', 'setecientos', 'ochocientos', 'novecientos']

    def covertir_grupo(n):
        output = []
        c = n // 100
        d = (n % 100) // 10
        u = n % 10

        if c > 0:
            if c == 1 and (d > 0 or u > 0):
                output.append("cien")
            else:
                output.append(centenas[c])

        if d == 1:
            output.append(dieces[u])
        elif d > 1:
            output.append(decenas[d])
            if u > 0:
                output.append(unidades[u])
        elif u > 0:
            output.append(unidades[u])

        return " ".join(output)

    if num == 0:
        return "CERO SOLES"

    num_str = str(f'{num:.2f}') # Ensure it's a string with 2 decimal places
    parts = num_str.split('.')
    enteros = int(parts[0])
    decimales = int(parts[1])

    letras = []
    if enteros == 1:
        letras.append("UN")
    elif enteros > 1:
        millones = enteros // 1_000_000
        miles = (enteros % 1_000_000) // 1_000
        unidades_enteras = enteros % 1_000

        if millones > 0:
            letras.append(covertir_grupo(millones))
            letras.append("MILLONES" if millones > 1 else "MILLON")
        if miles > 0:
            letras.append(covertir_grupo(miles))
            letras.append("MIL")
        if unidades_enteras > 0:
            letras.append(covertir_grupo(unidades_enteras))

    letras.append("SOLES")

    if decimales > 0:
        letras.append(f"CON {decimales}/100") # Format as /100 for cents
    else:
        letras.append("Y 00/100")

    return " ".join(letras).strip().upper()