import pandas as pd
from playwright.sync_api import sync_playwright
import time
import threading
import requests
from flask import Flask, jsonify, make_response
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

cache_real = {
    "monitorados": 0, "em_transito": 0, "nova_solicitacao": 0, 
    "aguardando_inicio": 0, "inicio_atraso": 0
}

def atualizar_firebase(dados):
    url_firebase = "https://torre-acs-default-rtdb.firebaseio.com/dashboard.json"
    try:
        response = requests.put(url_firebase, json=dados, timeout=10)
        if response.status_code == 200:
            print(f"✅ SINCRONIZADO COM FIREBASE! (Monitorados: {dados['monitorados']})")
        else:
            print(f"❌ ERRO NO FIREBASE: Status {response.status_code}")
    except Exception as e:
        print(f"⚠️ FALHA DE CONEXÃO: {e}")

@app.route('/dados')
def get_dados():
    return make_response(jsonify(cache_real))

def extrair_tabela(page):
    # Procura a tabela nos frames
    alvo = page
    for frame in page.frames:
        try:
            if frame.query_selector("table"):
                alvo = frame
                break
        except: continue
    
    try:
        alvo.wait_for_selector("table tbody tr", timeout=10000)
        rows = alvo.query_selector_all("table tbody tr")
        lista = []
        for row in rows:
            cols = row.query_selector_all("td")
            if len(cols) < 11: continue
            
            status_td = cols[2] 
            icon = status_td.query_selector("i, img, span")
            status_texto = icon.get_attribute("title") if icon else "SEM STATUS"
            
            lista.append({
                "Codigo": cols[1].text_content().strip(),
                "Status": status_texto.upper().strip()
            })
        return pd.DataFrame(lista)
    except:
        return pd.DataFrame()

def processar_dados(df):
    global cache_real
    if df is not None and len(df) > 0:
        total = len(df)
        df_transito = df[df['Status'].str.contains('INICIADO', na=False)]
        df_nova = df[df['Status'].str.contains('NOVA SOLICITACAO', na=False)]
        df_aguardando = df[df['Status'].str.contains('AGUARDANDO INICIO', na=False)]
        df_atraso = df[df['Status'].str.contains('ATRASADO|ATRASO PROXIMO', na=False)]
        
        novos_dados = {
            "monitorados": total,
            "nova_solicitacao": len(df_nova),
            "em_transito": len(df_transito),
            "aguardando_inicio": len(df_aguardando),
            "inicio_atraso": len(df_atraso)
        }
        cache_real = novos_dados
        print(f"\n📊 RESUMO LOCAL: {total} Monitorados")
        atualizar_firebase(novos_dados)
    else:
        print("⚠️ Tabela vazia. Mantendo dados anteriores no Firebase.")

def iniciar_painel():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        page.goto("http://vstrack.ddns.net/komando/", timeout=120000)
        
        print("\n--- AGUARDANDO LOGIN (30 SEGUNDOS) ---")
        time.sleep(30) 

        # O LOOP PRECISA FICAR DENTRO DA FUNÇÃO ONDE 'page' EXISTE
        while True:
            try:
                print("🔄 Atualizando página do rastreador...")
                page.reload(wait_until="networkidle", timeout=90000)
                time.sleep(15) 

                for f in page.frames:
                    try:
                        selector = "select[name*='length']"
                        element = f.query_selector(selector)
                        if element:
                            f.select_option(selector, "100")
                            time.sleep(5)
                            break
                    except: continue

                print("🔍 Lendo dados...")
                df = extrair_tabela(page)
                processar_dados(df)

                print("⏳ Aguardando 60s...")
                time.sleep(60)

            except Exception as e:
                print(f"❌ Erro no Loop: {e}")
                time.sleep(20)

if __name__ == "__main__":
    # Flask em thread separada
    threading.Thread(target=lambda: app.run(host='127.0.0.1', port=8080, debug=False, use_reloader=False), daemon=True).start()
    iniciar_painel()