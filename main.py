import os
import time
import json
import base64
from datetime import datetime, timedelta
import paho.mqtt.client as mqtt
import requests

MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT = 1883
MQTT_TOPIC = "alarme/casa"  # coloque seu tópico aqui
GITHUB_REPO = "titoufu/alarme-Malob"
JSON_PATH = "docs/dados.json"
GITHUB_TOKEN = os.environ.get("GH_TOKEN")

dados = []

def on_connect(client, userdata, flags, rc):
    print(f"Conectado MQTT com código {rc}")
    client.subscribe(MQTT_TOPIC)

def on_message(client, userdata, msg):
    payload = msg.payload.decode()
    evento = {
        "timestamp": datetime.utcnow().isoformat(),
        "topico": msg.topic,
        "valor": payload
    }
    print(f"Recebido: {evento}")
    dados.append(evento)

def filtrar_ultimas_24h():
    limite = datetime.utcnow() - timedelta(hours=24)
    return [e for e in dados if datetime.fromisoformat(e["timestamp"]) > limite]

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
        print("Arquivo dados.json atualizado no GitHub com sucesso!")
    else:
        print(f"Erro ao atualizar arquivo: {r.status_code} {r.text}")

def main():
    if not GITHUB_TOKEN:
        print("ERRO: variável GH_TOKEN não definida")
        return

    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message

    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_start()

    try:
        while True:
            time.sleep(300)  # Atualiza a cada 5 minutos
            atualizar_json_github()
    except KeyboardInterrupt:
        print("Encerrando...")
    finally:
        client.loop_stop()
        client.disconnect()

if __name__ == "__main__":
    main()
