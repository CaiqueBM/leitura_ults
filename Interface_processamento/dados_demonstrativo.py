import os
import subprocess
import re
import sys
import sqlite3

# Adiciona o diretório pai ao sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

import configparser

config = configparser.ConfigParser()
config.read(os.path.join(parent_dir, 'config.ini'))

# Função para extrair os textos
def extrair_texto_pdf(pdf_path):
    try:
        
        # Adiciona o diretório pai ao sys.path
        current_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Caminho para o executável destrinchaPDF
        destrincha_path = os.path.join(current_dir, 'destrinchaPDF')
        
        # Comando a ser executado
        comando = [destrincha_path, pdf_path]
        
        # Configuração do ambiente
        env = os.environ.copy()  # Copia o ambiente atual
        env['DOTNET_SYSTEM_GLOBALIZATION_INVARIANT'] = '1'
        
        # Adiciona a configuração para o diretório de extração do bundle
        env['DOTNET_BUNDLE_EXTRACT_BASE_DIR'] = './tmp/dotnet_bundles'
        
        # Garante que o diretório de extração existe
        os.makedirs('./tmp/dotnet_bundles', exist_ok=True)
        
        # Executa o comando e captura a saída
        resultado = subprocess.run(comando,
                                   env=env,
                                   capture_output=True,
                                   text=True,
                                   check=True)
        
        # Retorna o texto de saída
        return resultado.stdout
    except subprocess.CalledProcessError as e:
        print(f"Erro ao executar o destrinchaPDF: {e}")
        print(f"Saída de erro: {e.stderr}")
        return None
    except Exception as e:
        print(f"Erro inesperado: {e}")
        return None
    
def remove_zeros(text):
    # Este padrão procura por zeros no início de um número
    # (?<!\d) garante que não há um dígito antes (para não afetar números como 101)
    # 0+ captura um ou mais zeros
    # (?=\d) garante que há um dígito após os zeros (para não remover todos os zeros)
    pattern = r'(?<!\d)0+(?=\d)'
    return re.sub(pattern, '', text)

def guardar_dados(instalacao, receptoras):
    db_clientes = config['database']['dbclientes']
    
    
    meses = {
            "jan": "1", "fev": "2", "mar": "3", "abr": "4",
            "mai": "5", "jun": "6", "jul": "7", "ago": "8",
            "set": "9", "out": "10", "nov": "11", "dez": "12"
            }
    
    dados = []
    for receptora in receptoras:
    
        mes_split = receptora['mes_ano'].split('/')[0]
        ano_split = receptora['mes_ano'].split('/')[1]
        mes_corrigido = remove_zeros(meses[mes_split])
        mes_producao = f"{mes_corrigido}/20{ano_split}"
        
        energia = receptora['energia'].replace('.','').replace(',','.')
        
        percentual_alocado = receptora['porcentagem'].replace(',','.').replace('%','')
    
        instalacao_receptora = remove_zeros(receptora['instalacao'])

    
        dados.append({
            'mes_ano': mes_producao,
            'instalacao_receptora': instalacao_receptora,
            'montante': energia,
            'percentual_alocado': percentual_alocado,
            'instalacao_usina': instalacao,
        })
        
        
    conn = sqlite3.connect(db_clientes)
    cursor = conn.cursor()
    
    print("\r\n")
    print(f"DADOS COMPLETOS DEMONSTRATIVO: {dados}")
    print("\r\n")
    
    for dado in dados:
    
        cursor.execute(f"""INSERT OR REPLACE INTO demonstrativo(
            MES_PRODUCAO,
            RECEPTORA,
            MONTANTE,
            PERCENTUAL_ALOCADO,
            GERADORA
        ) VALUES ('{dado['mes_ano']}', '{dado['instalacao_receptora']}', '{dado['montante']}', '{dado['percentual_alocado']}', '{dado['instalacao_usina']}');
        """)

    conn.commit()
    cursor.close()
    conn.close()
    
def busca_demonstrativo(path):
    
    
    numero_instalacao = None
    receptoras = []

    if path is not None:
        try:
            texto_extraido = extrair_texto_pdf(path)
            
            linhas = texto_extraido.split('\n')
            
            for linha in linhas:
                match_instalacao = re.search(r'\w+/\d{4}\s+(?P<instalacao>\d+)', linha)
                if match_instalacao and numero_instalacao == None:
                    numero_instalacao_match = match_instalacao.group('instalacao')
                    numero_instalacao = remove_zeros(numero_instalacao_match)

                match_receptoras = re.search(r'(?P<mes_ano>\w{3}/\d{2})\s+(?P<instalacao>\d+)\s+(?P<energia>[\d.,]+)\s+(?P<porcentagem>[\d.,]+%)', linha)
                if match_receptoras:
                    receptoras.append(match_receptoras.groupdict())

            guardar_dados(numero_instalacao, receptoras)
            
        except Exception as e:
            print(f"Erro inesperado: {e}")
            return None
        
        
        
# path = "/media/hdfs/ULT/16 - Nova apuracao/2025/Janeiro/Geradoras/ULT/160993441/Demonstrativo/160993441dmtt ULT 1 jan25.pdf"
# busca_demonstrativo(path)