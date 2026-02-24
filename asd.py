import requests

url = "https://api-new.paineloffice.click/auth/login"

payload = {
    "username": "lembraguru",
    "password": "277886vd79"
}

try:
    response = requests.post(url, json=payload)
    
    # 200 ou 201 são códigos de sucesso
    if response.status_code in [200, 201]:
        print("Login realizado com sucesso!")
        
        # Transforma a resposta de texto para um dicionário Python
        dados = response.json()
        
        # Extrai o token
        meu_token = dados.get("token")
        meu_id = dados.get("id")
        
        print(f"Seu Token é: {meu_token}")
        print(f"Seu ID de usuário é: {meu_id}")
        
    else:
        print(f"Erro inesperado. Status: {response.status_code}")
        print(f"Resposta: {response.text}")

except Exception as e:
    print(f"Erro ao conectar: {e}")