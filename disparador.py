import os
import time
import requests
import psycopg2
from datetime import datetime

# --- VARIÁVEIS DE AMBIENTE (Configuraremos no Render) ---
DATABASE_URL = os.environ.get("DATABASE_URL")
EVOLUTION_URL = os.environ.get("EVOLUTION_URL") # ex: https://raphael-zap.onrender.com
EVOLUTION_KEY = os.environ.get("EVOLUTION_KEY") # ex: Suasenha123
INSTANCE_NAME = "Principal" # Nome da instância que você criou na Evolution

def enviar_zap(fone, msg):
    # Limpa numero (apenas digitos)
    num = "".join(filter(str.isdigit, fone))
    
    # Garante o 55 (Brasil)
    if not num.startswith("55"): 
        num = "55" + num
    
    url = f"{EVOLUTION_URL}/message/sendText/{INSTANCE_NAME}"
    
    headers = {
        "apikey": EVOLUTION_KEY,
        "Content-Type": "application/json"
    }
    
    payload = {
        "number": num,
        "options": {
            "delay": 1200, 
            "presence": "composing", 
            "linkPreview": False
        },
        "textMessage": {
            "text": msg
        }
    }
    
    try:
        print(f"Disparando para {num}...")
        r = requests.post(url, json=payload, headers=headers)
        if r.status_code == 201:
            return True
        else:
            print(f"Erro API Evolution: {r.text}")
            return False
    except Exception as e:
        print(f"Erro Conexão: {e}")
        return False

def job():
    print("--- Iniciando Rotina de Disparos ---")
    
    if not DATABASE_URL:
        print("ERRO: DATABASE_URL não configurada.")
        return

    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        # Pega leads que ainda não foram enviados (status_envio NULL ou 'Pendente')
        # Limite de 15 por execução para segurança
        cur.execute("""
            SELECT id, empresa, telefone, pitch_venda 
            FROM leads 
            WHERE (status_envio IS NULL OR status_envio = 'Pendente') 
            AND telefone != 'N/A' 
            LIMIT 15
        """)
        leads = cur.fetchall()
        
        if not leads:
            print("Nenhum lead pendente para hoje.")
            return
            
        print(f"Encontrados {len(leads)} leads pendentes.")
        
        for lead in leads:
            lid, nome, fone, pitch = lead
            
            # Se o pitch vier vazio, usa um genérico
            msg = pitch if pitch else f"Olá {nome}, tudo bem? Vi sua empresa no Google e tenho uma oportunidade para o seu site."
            
            sucesso = enviar_zap(fone, msg)
            
            if sucesso:
                cur.execute("UPDATE leads SET status_envio = 'Enviado', data_envio = NOW() WHERE id = %s", (lid,))
                conn.commit()
                print(f"✅ Enviado para {nome}")
            else:
                cur.execute("UPDATE leads SET status_envio = 'Erro' WHERE id = %s", (lid,))
                conn.commit()
                print(f"❌ Falha para {nome}")
            
            # Espera 45 segundos entre envios (Anti-Ban)
            time.sleep(45)
            
        cur.close()
        conn.close()
        print("--- Rotina Finalizada com Sucesso ---")
        
    except Exception as e:
        print(f"Erro Crítico no Banco de Dados: {e}")

if __name__ == "__main__":
    job()