import barcode
from barcode.writer import ImageWriter

# Sequência de números (ITF é numérico)
codigo_itf = "75697996900000001241301001518627700000021001"

# Configurações personalizadas do ImageWriter
options = {
    "write_text": False,
    "module_width": 0.25,  # Largura de cada módulo/barra (padrão é 0.2)
    "module_height": 15.0,  # Altura das barras (ajuste conforme necessário)
    "quiet_zone": 10,  # Margem em branco nas laterais (aumente se os números cortarem)
    "font_size": 10,  # Tamanho da fonte para os números
    "text_distance": 5.0,  # Distância entre os números e as barras
}

# Gerar o código de barras ITF
barcode_format = "itf"  # Especifica o formato ITF
output_file = "codigo_itf"

# Salva como imagem
barcode_obj = barcode.get(barcode_format, codigo_itf, writer=ImageWriter())
barcode_obj.save(output_file, options = options)

print("Imagem ITF gerada com sucesso!")
