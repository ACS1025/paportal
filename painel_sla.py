import pandas as pd
from playwright.sync_api import sync_playwright
import time
import threading
import os
from flask import Flask, jsonify, make_response
from flask_cors import CORS

app = Flask(__name__)
# Configuração robusta de CORS
CORS(app, resources={r"/*": {"origins": "*"}})

# --- MEMÓRIA PERSISTENTE ---
cache_real = {
    "monitorados": 0, "em_transito": 0, "nova_solicitacao": 0, 
    "aguardando_inicio": 0, "inicio_atraso": 0
}

@app.route('/dados')
def get_dados():
    global cache_real
    # Adicionando headers manuais para garantir que o torre.html acesse
    response = make_response(jsonify(cache_real))
    response.headers["Access-Control-Allow-Origin"] = "*"
    return response

def processar_dados(df):
    global cache_real
    if df is not None and not df.empty and len(df) > 0:
        total = len(df)
        df_transito = df[df['Status'].str.contains('INICIADO', na=False)]
        df_nova = df[df['Status'].str.contains('NOVA SOLICITAÇÃO', na=False)]
        df_aguardando = df[df['Status'].str.contains('AGUARDANDO INÍCIO', na=False)]
        df_atraso = df[df['Status'].str.contains('ATRASADO|ATRASO PRÓXIMO', na=False)]
        
        cache_real = {
            "monitorados": total,
            "nova_solicitacao": len(df_nova),
            "em_transito": len(df_transito),
            "aguardando_inicio": len(df_aguardando),
            "inicio_atraso": len(df_atraso)
        }
        print(f"✅ Cache Atualizado: {total} Monitorados | {len(df_transito)} Em Trânsito")
    else:
        print("⚠️ Tabela vazia ou não encontrada. Mantendo dados anteriores.")

def extrair_tabela(page):
    """ Captura a tabela de dentro dos frames da VSoftware """
    alvo = page
    # Tenta encontrar o frame que contém a tabela
    for frame in page.frames:
        try:
            if frame.query_selector("table"):
                alvo = frame
                break
        except: continue
    
    try:
        alvo.wait_for_selector("table tbody tr", timeout=8000)
        rows = alvo.query_selector_all("table tbody tr")
        lista = []
        for row in rows:
            cols = row.query_selector_all("td")
            if len(cols) < 11: continue
            
            # Captura o texto do status dentro do ícone/span
            status_td = cols[2] 
            icon = status_td.query_selector("i, img, span")
            status_texto = icon.get_attribute("title") if icon else "SEM STATUS"
            
            lista.append({
                "Código": cols[1].text_content().strip(),
                "Status": status_texto.upper().strip()
            })
        return pd.DataFrame(lista)
    except Exception as e:
        print(f"❌ Erro na extração: {e}")
        return pd.DataFrame()

def iniciar_painel():
    with sync_playwright() as p:
        # headless=False para você poder logar
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        page.goto("http://vstrack.ddns.net/komando/", timeout=120000)
        
        print("\n--- AGUARDANDO LOGIN (30 SEGUNDOS) ---")
        time.sleep(30) 

        while True:
            try:
                print("🔍 Extraindo dados...")
                df = extrair_tabela(page)
                processar_dados(df)
                
                print("🔄 Atualizando página para próxima leitura...")
                page.reload(wait_until="domcontentloaded")
                time.sleep(8)
                
                # Garante as 100 linhas para o dashboard ficar completo
                for f in page.frames:
                    try:
                        selector = "select[name*='length']"
                        if f.query_selector(selector):
                            f.select_option(selector, "100")
                            print("📏 Ajustado para 100 linhas.")
                            time.sleep(5)
                            break
                    except: continue
                
                print("💤 Dormindo 60s...")
                time.sleep(60)
            except Exception as e:
                print(f"❌ Erro no Loop: {e}")
                time.sleep(15)

if __name__ == "__main__":
    print("🚀 Servidor Local rodando em http://127.0.0.1:8080/dados")
    # Mudamos para 127.0.0.1 para evitar bloqueio de rede externa
    threading.Thread(target=lambda: app.run(host='127.0.0.1', port=8080, debug=False, use_reloader=False), daemon=True).start()
    iniciar_painel()
