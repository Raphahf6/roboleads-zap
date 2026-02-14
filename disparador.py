import os
import time
import random
import requests
import psycopg2
from datetime import datetime

# --- CONFIGURAÇÕES ---
DATABASE_URL = os.environ.get("DATABASE_URL")
EVOLUTION_URL = os.environ.get("EVOLUTION_URL")
EVOLUTION_KEY = os.environ.get("EVOLUTION_KEY")
INSTANCE_NAME = "Raphael" 

# Limite diário de segurança (apenas para garantir que o loop não fique infinito)
LIMITE_POR_EXECUCAO = 10 

def enviar_zap_humanizado(fone, msg):
    # 1. Limpeza do Número
    num = "".join(filter(str.isdigit, fone))
    if not num.startswith("55"): num = "55" + num
    
    # 2. Configurações da Evolution
    url = f"{EVOLUTION_URL}/message/sendText/{INSTANCE_NAME}"
    headers = {
        "apikey": EVOLUTION_KEY,
        "Content-Type": "application/json"
    }
    
    # 3. Payload com "Delay de Digitação" (Presence)
    # Isso faz aparecer "Digitando..." no celular do cliente
    tempo_digitando = random.randint(3000, 8000) # Entre 3 e 8 segundos
    
    payload = {
        "number": num,
        "options": {
            "delay": tempo_digitando, 
            "presence": "composing", 
            "linkPreview": True 
        },
        "textMessage": {
            "text": msg
        }
    }
    
    try:
        print(f"   Simulando digitação para {num}...")
        r = requests.post(url, json=payload, headers=headers)
        
        if r.status_code == 201:
            return True
        else:
            print(f"   [ERRO API] {r.text}")
            return False
    except Exception as e:
        print(f"   [ERRO CONEXÃO] {e}")
        return False

def job():
    print(f"--- INICIANDO ROBÔ DE DISPARO: {datetime.now()} ---")
    
    if not DATABASE_URL:
        print("ERRO: Variável DATABASE_URL não encontrada.")
        return

    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        # Seleciona APENAS leads pendentes, limitados pelo lote
        cur.execute(f"""
            SELECT id, empresa, telefone, pitch_venda, cidade 
            FROM leads 
            WHERE (status_envio IS NULL OR status_envio = 'Pendente') 
            AND telefone != 'N/A' 
            LIMIT {LIMITE_POR_EXECUCAO}
        """)
        leads = cur.fetchall()
        
        if not leads:
            print("Nenhum lead pendente na fila. O robô vai descansar.")
            return

        print(f"Lote de hoje: {len(leads)} leads para processar.")
        
        for i, lead in enumerate(leads):
            lid, nome, fone, pitch, cidade = lead
            
            print(f"\n[{i+1}/{len(leads)}] Processando: {nome}...")

            # Monta a mensagem se não tiver pitch salvo (Fallback)
            if not pitch:
                pitch = (
                    f"Olá *{nome}*, tudo bem?\n\n"
                    f"Vi que sua empresa em {cidade} está sem site no Google. "
                    f"Isso pode estar custando clientes. Posso te mandar uma proposta?"
                )

            # Tenta Enviar
            sucesso = enviar_zap_humanizado(fone, pitch)
            
            if sucesso:
                cur.execute("UPDATE leads SET status_envio = 'Enviado', data_envio = NOW() WHERE id = %s", (lid,))
                conn.commit()
                print(f"   ✅ SUCESSO! Mensagem entregue.")
            else:
                cur.execute("UPDATE leads SET status_envio = 'Erro' WHERE id = %s", (lid,))
                conn.commit()
                print(f"   ❌ FALHA no envio.")
            
            # --- O SEGREDO DO ANTI-BLOQUEIO (DELAY ALEATÓRIO) ---
            # Se não for o último lead, espera um tempo aleatório
            if i < len(leads) - 1:
                tempo_espera = random.randint(45, 120) # Espera entre 45s e 2 minutos
                print(f"   ⏳ Aguardando {tempo_espera} segundos para parecer humano...")
                time.sleep(tempo_espera)
            
        cur.close()
        conn.close()
        print("\n--- FIM DO LOTE ---")
        
    except Exception as e:
        print(f"ERRO CRÍTICO NO BANCO DE DADOS: {e}")

if __name__ == "__main__":
    job()