import requests
import json

# URL do seu webhook
webhook_url = "https://webhook.tagarela/f7ef5f99-159f-4706-9df9-773a37b31c4c"

# Dados em formato de dicionário Python
dados = {
    "name": "Ricardo"
}

# Enviando a requisição POST com os dados em JSON
try:
    response = requests.post(webhook_url, json=dados)

    # Verifica se a requisição foi bem sucedida
    response.raise_for_status()

    print("Webhook enviado com sucesso!")
    print(f"Status da resposta: {response.status_code}")

except requests.exceptions.HTTPError as errh:
    print(f"Erro HTTP: {errh}")
except requests.exceptions.ConnectionError as errc:
    print(f"Erro de Conexão: {errc}")
except requests.exceptions.Timeout as errt:
    print(f"Erro de Timeout: {errt}")
except requests.exceptions.RequestException as err:
    print(f"Algo deu errado: {err}")