import os
import json
import base64
from datetime import datetime, timedelta
import paho.mqtt.client as mqtt
import requests

# Configurações
MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT = 1883
MQTT_TOPIC = "alarme/casa"
GITHUB_REPO = "titoufu/alarme-Malob"
JSON_PATH = "docs/dados.json"
GITHUB_TOKEN = os.environ.get("GH_TOKEN")

# Lista para armazenar dados recebidos
dados = []

# Função chamada ao conectar ao MQTT
def on_connect(client, userdata, flags, rc):
    print(f"✅ Conectado ao MQTT com código {rc}")
    client.subscribe(MQTT_TOPIC)

# Função chamada ao receber mensagem
def on_message(client, userdata, msg):
    payload = msg.payload.decode()
    evento = {
        "timestamp": datetime.utcnow().isoformat(),
        "topico": msg.topic,
        "valor": payload
    }
    print(f"📥 Recebido: {evento}")
    dados.append(evento)
    atualizar_json_github()

# Filtra os eventos das últimas 24h
def filtrar_ultimas_24h():
    limite = datetime.utcnow() - timedelta(hours=24)
    return [e for e in dados if datetime.fromisoformat(e["timestamp"]) > limite]

# Atualiza o arquivo JSON no GitHub
def atualizar_json_github():
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{JSON_PATH}"
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json"
    }

    r = requests.get(url, headers=headers)
    sha = None
    if r.status_code == 200:
        sha = r.json().get("sha")

    dados_filtrados = filtrar_ultimas_24h()
    conteudo_json = json.dumps(dados_filtrados, indent=2)
    conteudo_b64 = base64.b64encode(conteudo_json.encode()).decode()

    payload = {
        "message": "Atualização automática via MQTT",
        "content": conteudo_b64,
        "sha": sha
    }

    r = requests.put(url, headers=headers, json=payload)
    if r.status_code in [200, 201]:
        print("✅ dados.json atualizado no GitHub com sucesso!")
    else:
        print(f"❌ Erro ao atualizar: {r.status_code} {r.text}")

# Função principal
def main():
    if not GITHUB_TOKEN:
        print("❌ ERRO: variável GH_TOKEN não definida")
        return

    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message

    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    
    try:
        client.loop_forever()
    except KeyboardInterrupt:
        print("🛑 Encerrando...")
        client.disconnect()

# Execução principal
if __name__ == "__main__":
    main()

