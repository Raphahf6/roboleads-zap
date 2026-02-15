import os
import time
import random
import requests
import psycopg2
from datetime import datetime

# --- CONFIGURAÇÕES ---
DATABASE_URL = os.environ.get("DATABASE_URL")
ZAP_ENGINE_URL = os.environ.get("ZAP_ENGINE_URL")
LIMITE_POR_EXECUCAO = 10 

def gerar_mensagem_customizada(empresa, cidade):
    """Gera variações aleatórias da mensagem para evitar o filtro de spam."""
    
    saudacoes = ["Olá", "Oi", "Tudo bem?"]
    intros = [
        f"vi que a *{empresa}* aqui em {cidade}",
        f"estava pesquisando empresas em {cidade} e notei que a *{empresa}*",
        f"percebi que o seu negócio (*{empresa}*)",
        f"notei que sua empresa em {cidade}"
    ]
    problemas = [
        "ainda não possui um site oficial no Google.",
        "não aparece com um site profissional nas buscas.",
        "está sem uma página na web para converter clientes.",
        "não tem um site otimizado para os novos clientes."
    ]
    ganchos = [
        "Isso faz você perder vendas todos os dias.",
        "Muitos clientes podem estar indo para a concorrência por causa disso.",
        "Um site te rankearia melhor para quem te procura."
    ]
    chamadas = [
        "Eu sou desenvolvedor web e posso criar seu site com preços a partir de R$ 50. Tem interesse?",
        "Trabalho com Web Design e consigo criar sua página profissional com um valor super acessível. Topa conversar?",
        "Sou o Raphael, designer web. Posso montar um site moderno para você hoje mesmo. Posso te mandar os detalhes?",
        "Faço sites profissionais e rápidos para empresas da região. Vamos colocar a *{empresa}* no topo do Google?"
    ]

    # Constrói a mensagem escolhendo partes aleatórias
    msg = (
        f"{random.choice(saudacoes)}! {random.choice(intros)} "
        f"{random.choice(problemas)} {random.choice(ganchos)} \n\n"
        f"{random.choice(chamadas)}"
    )
    return msg

def enviar_zap_humanizado(fone, msg):
    num = "".join(filter(str.isdigit, fone))
    if not num.startswith("55"): num = "55" + num
    
    # Simulação de digitação (humano)
    tempo_digitando = random.randint(4000, 9000) 
    
    params = {
        "num": num,
        "msg": msg,
        "delay": tempo_digitando
    }
    
    try:
        r = requests.get(f"{ZAP_ENGINE_URL}/send", params=params, timeout=30)
        return r.status_code == 200
    except Exception as e:
        print(f"   [ERRO CONEXÃO] {e}")
        return False

def job():
    print(f"--- 🚀 SNIPER SALES INICIADO: {datetime.now()} ---")
    
    if not DATABASE_URL or not ZAP_ENGINE_URL:
        print("ERRO: Variáveis de ambiente faltando.")
        return

    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        cur.execute(f"""
            SELECT id, empresa, telefone, cidade 
            FROM leads 
            WHERE (status_envio IS NULL OR status_envio = 'Pendente') 
            AND telefone != 'N/A' 
            LIMIT {LIMITE_POR_EXECUCAO}
        """)
        leads = cur.fetchall()
        
        if not leads:
            print("Fila vazia. O Sniper está descansando.")
            return

        for i, lead in enumerate(leads):
            lid, empresa, fone, cidade = lead
            
            # Gera a mensagem única para este lead
            pitch = gerar_mensagem_customizada(empresa, cidade)
            
            print(f"\n[{i+1}/{len(leads)}] Mirando em: {empresa} ({fone})...")

            if enviar_zap_humanizado(fone, pitch):
                cur.execute("UPDATE leads SET status_envio = 'Enviado', data_envio = NOW() WHERE id = %s", (lid,))
                conn.commit()
                print(f"   ✅ DISPARO CERTEIRO!")
            else:
                cur.execute("UPDATE leads SET status_envio = 'Erro' WHERE id = %s", (lid,))
                conn.commit()
                print(f"   ❌ TIRO FALHOU.")
            
            # Delay entre disparos (Longos e Aleatórios)
            if i < len(leads) - 1:
                tempo_espera = random.randint(60, 180) # 1 a 3 minutos
                print(f"   ⏳ Esfriando o cano por {tempo_espera}s...")
                time.sleep(tempo_espera)
            
        cur.close()
        conn.close()
        print("\n--- LOTE FINALIZADO COM SUCESSO ---")
        
    except Exception as e:
        print(f"ERRO: {e}")

if __name__ == "__main__":
    job()