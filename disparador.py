import os
import time
import random
import requests
import psycopg2
from datetime import datetime

# --- CONFIGURAÇÕES ---
DATABASE_URL = os.environ.get("DATABASE_URL")
# Agora aponta para o seu novo app no Render (ex: https://sniper-core.onrender.com)
ZAP_ENGINE_URL = os.environ.get("ZAP_ENGINE_URL") 
LIMITE_POR_EXECUCAO = 10 

def enviar_zap_humanizado(fone, msg):
    # 1. Limpeza do Número
    num = "".join(filter(str.isdigit, fone))
    if not num.startswith("55"): num = "55" + num
    
    # 2. Configurações para o Novo Motor Baileys
    # Passamos os parâmetros via Query String para a rota /send
    tempo_digitando = random.randint(3000, 8000) # Entre 3 e 8 segundos
    
    params = {
        "num": num,
        "msg": msg,
        "delay": tempo_digitando # Motor cuidará do 'typing...'
    }
    
    try:
        print(f"   Simulando digitação ({tempo_digitando}ms) e enviando para {num}...")
        # Chamada para o seu novo motor Node.js
        r = requests.get(f"{ZAP_ENGINE_URL}/send", params=params, timeout=30)
        
        if r.status_code == 200:
            return True
        else:
            print(f"   [ERRO MOTOR] {r.text}")
            return False
    except Exception as e:
        print(f"   [ERRO CONEXÃO] {e}")
        return False

def job():
    print(f"--- INICIANDO ROBÔ DE DISPARO (BAILEYS CORE): {datetime.now()} ---")
    
    if not DATABASE_URL:
        print("ERRO: Variável DATABASE_URL não encontrada.")
        return
    if not ZAP_ENGINE_URL:
        print("ERRO: Variável ZAP_ENGINE_URL não encontrada.")
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
                print(f"   ✅ SUCESSO! Mensagem entregue via Sniper Core.")
            else:
                cur.execute("UPDATE leads SET status_envio = 'Erro' WHERE id = %s", (lid,))
                conn.commit()
                print(f"   ❌ FALHA no envio.")
            
            # --- ANTI-BLOQUEIO (DELAY ALEATÓRIO ENTRE LEADS) ---
            if i < len(leads) - 1:
                tempo_espera = random.randint(45, 120) 
                print(f"   ⏳ Aguardando {tempo_espera} segundos para o próximo lead...")
                time.sleep(tempo_espera)
            
        cur.close()
        conn.close()
        print("\n--- FIM DO LOTE ---")
        
    except Exception as e:
        print(f"ERRO CRÍTICO NO BANCO DE DADOS: {e}")

if __name__ == "__main__":
    job()