import os
import json
import base64
from datetime import datetime, timedelta
import paho.mqtt.client as mqtt
import requests

# ========== CONFIGURAÇÕES ==========
MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT = 1883
MQTT_TOPIC = "alarme/#"  # agora ouve tudo que começa com alarme/
GITHUB_REPO = "titoufu/alarme-Malob"
JSON_PATH = "docs/dados.json"
GITHUB_TOKEN = os.environ.get("GH_TOKEN")

dados = []

# ========== CONEXÃO COM MQTT ==========
def on_connect(client, userdata, flags, rc):
    print(f"✅ Conectado ao MQTT com código {rc}")
    client.subscribe(MQTT_TOPIC)
    print(f"📡 Subscrito ao tópico {MQTT_TOPIC}")

# ========== RECEBIMENTO DE MENSAGENS ==========
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

# ========== FILTRAR ÚLTIMAS 24 HORAS ==========
def filtrar_ultimas_24h():
    limite = datetime.utcnow() - timedelta(hours=24)
    return [e for e in dados if datetime.fromisoformat(e["timestamp"]) > limite]

# ========== ATUALIZAR JSON NO GITHUB ==========
def atualizar_json_github():
    if not GITHUB_TOKEN:
        print("❌ GH_TOKEN não definido no ambiente. Abortando upload.")
        return

    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{JSON_PATH}"
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json"
    }

    # Tentar obter o SHA atual do arquivo (se já existir)
    r_get = requests.get(url, headers=headers)
    sha = None
    if r_get.status_code == 200:
        sha = r_get.json().get("sha")
    elif r_get.status_code != 404:
        print(f"❌ Erro ao tentar obter SHA do arquivo existente:")
        print(f"Status: {r_get.status_code}")
        print(f"Resposta: {r_get.text}")
        return

    # Gerar novo conteúdo
    dados_filtrados = filtrar_ultimas_24h()
    conteudo_json = json.dumps(dados_filtrados, indent=2)
    conteudo_b64 = base64.b64encode(conteudo_json.encode()).decode()

    payload = {
        "message": "Atualização automática via MQTT",
        "content": conteudo_b64,
        "sha": sha
    }

    r_put = requests.put(url, headers=headers, json=payload)
    if r_put.status_code in [200, 201]:
        print("✅ dados.json atualizado no GitHub com sucesso!")
    else:
        print("❌ Erro ao atualizar o arquivo no GitHub:")
        print(f"Status: {r_put.status_code}")
        print(f"Resposta: {r_put.text}")

# ========== FUNÇÃO PRINCIPAL ==========
def main():
    if not GITHUB_TOKEN:
        print("❌ ERRO: GH_TOKEN não definido no ambiente do RailWay.")
        return

    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message

    print("🚀 Conectando ao broker MQTT...")
    client.connect(MQTT_BROKER, MQTT_PORT, 60)

    try:
        client.loop_forever()
    except KeyboardInterrupt:
        print("🛑 Encerrando conexão...")
        client.disconnect()

# ========== EXECUÇÃO ==========
if __name__ == "__main__":
    main()
