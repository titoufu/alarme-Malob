import os
import json
import base64
from datetime import datetime, timedelta, UTC
import paho.mqtt.client as mqtt
import requests

# ========== CONFIGURAÇÕES ==========
MQTT_BROKER = "bdc89afc1d5c447e8cbd83f65005162d.s2.eu.hivemq.cloud"
MQTT_PORT = 8883  # porta segura com TLS
MQTT_TOPIC = "alarme/#"

GITHUB_REPO = "titoufu/alarme-Malob"
JSON_PATH = "docs/dados.json"

# Variáveis de ambiente
GITHUB_TOKEN = os.environ.get("GH_TOKEN")
MQTT_USER = "TitoUFU"
MQTT_PASS = "Tito1k58!"
#MQTT_USER = os.environ.get("MQTT_USER")
#MQTT_PASS = os.environ.get("MQTT_PASS")

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
        "timestamp": datetime.now(UTC).isoformat(),
        "topico": msg.topic,
        "valor": payload
    }
    print(f"📥 Recebido: {evento}")
    dados.append(evento)
    atualizar_json_github()

# ========== FILTRAR ÚLTIMAS 24 HORAS ==========
def filtrar_ultimas_24h():
    limite = datetime.now(UTC) - timedelta(hours=24)
    return [e for e in dados if datetime.fromisoformat(e["timestamp"]) > limite]

# ========== ATUALIZAR JSON NO GITHUB ==========
def atualizar_json_github():
    if not GITHUB_TOKEN:
        print("❌ GH_TOKEN não definido. Abortando upload.")
        return

    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{JSON_PATH}"
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json"
    }

    r_get = requests.get(url, headers=headers)
    sha = None
    if r_get.status_code == 200:
        sha = r_get.json().get("sha")
    elif r_get.status_code != 404:
        print(f"❌ Erro ao obter SHA do arquivo existente:")
        print(f"Status: {r_get.status_code}")
        print(f"Resposta: {r_get.text}")
        return

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
        print("❌ GH_TOKEN não definido.")
        return

    client = mqtt.Client()
    if MQTT_USER and MQTT_PASS:
        client.username_pw_set(MQTT_USER, MQTT_PASS)
    client.tls_set()


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
