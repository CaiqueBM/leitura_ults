import requests
from datetime import datetime

data_atual = datetime.now().strftime("%Y-%m-%d")
# ids = [578496, 667618]
ids = [578496, 667618, 686932, 767468]

for usina_id in ids:
    url = f"https://app.solarz.com.br/shareable/generation/day?usinaId={usina_id}&day={data_atual}&unitePortals=true"

    for tentativa in range(5):  # Tentar buscar os dados até 5 vezes
        resposta = requests.get(url)
        if resposta.status_code == 200:
            # Processar os dados da resposta
            dados = resposta.json()
            print("Carregamento concluído!")
            break  # Se os dados foram carregados com sucesso, saia do loop
        else:
            print(f"Tentativa {tentativa + 1}: Falha ao carregar os dados. Tentando novamente...")
    else:
        # Se todas as tentativas falharam, imprima uma mensagem e prossiga para o próximo id
        print("Todas as tentativas falharam. Pulando para o próximo id.")
        dados = 0  # Atribuir valor 0 para dados quando todas as tentativas falharam
