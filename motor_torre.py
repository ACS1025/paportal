import pandas as pd
from playwright.sync_api import sync_playwright
import time
import threading
import os
import requests  # Para o Firebase
from flask import Flask, jsonify, make_response
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# --- MEMORIA PERSISTENTE ---
cache_real = {
    "monitorados": 0, "em_transito": 0, "nova_solicitacao": 0, 
    "aguardando_inicio": 0, "inicio_atraso": 0
}

# --- FUNCAO FIREBASE ---
def atualizar_firebase(dados):
    url_firebase = "https://torre-acs-default-rtdb.firebaseio.com/dashboard.json"
    try:
        # Enviando os dados para a nuvem
        response = requests.put(url_firebase, json=dados, timeout=10)
        
        if response.status_code == 200:
            print(f"✅ SINCRONIZADO COM FIREBASE! (Monitorados: {dados['monitorados']})")
        else:
            print(f"❌ ERRO NO FIREBASE: Status {response.status_code}")
            print(f"Motivo: {response.text}")
    except Exception as e:
        print(f"⚠️ FALHA DE CONEXÃO COM INTERNET: {e}")

@app.route('/dados')
def get_dados():
    global cache_real
    response = make_response(jsonify(cache_real))
    response.headers["Access-Control-Allow-Origin"] = "*"
    return response

def processar_dados(df):
    global cache_real
    if df is not None and not df.empty:
        total = len(df)
        df_transito = df[df['Status'].str.contains('INICIADO', na=False)]
        df_nova = df[df['Status'].str.contains('NOVA SOLICITACAO', na=False)]
        df_aguardando = df[df['Status'].str.contains('AGUARDANDO INICIO', na=False)]
        df_atraso = df[df['Status'].str.contains('ATRASADO|ATRASO PROXIMO', na=False)]
        
        cache_real = {
            "monitorados": total,
            "nova_solicitacao": len(df_nova),
            "em_transito": len(df_transito),
            "aguardando_inicio": len(df_aguardando),
            "inicio_atraso": len(df_atraso)
        }
        
        print(f"\n📊 RESUMO LOCAL: {total} Monitorados")
        # ENVIA PARA A NUVEM LOGO APÓS CALCULAR
        atualizar_firebase(cache_real)
    else:
        print("--- Tabela vazia ou nao encontrada.")

def extrair_tabela(page):
    alvo = page
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
            
            status_td = cols[2] 
            icon = status_td.query_selector("i, img, span")
            status_texto = icon.get_attribute("title") if icon else "SEM STATUS"
            
            lista.append({
                "Codigo": cols[1].text_content().strip(),
                "Status": status_texto.upper().strip()
            })
        return pd.DataFrame(lista)
    except Exception as e:
        print(f"Erro na extracao: {e}")
        return pd.DataFrame()

def iniciar_painel():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        page.goto("http://vstrack.ddns.net/komando/", timeout=120000)
        
        print("\n--- AGUARDANDO LOGIN (30 SEGUNDOS) ---")
        time.sleep(30) 

        while True:
            try:
                time.sleep(10) 
                for f in page.frames:
                    try:
                        selector = "select[name*='length']"
                        element = f.query_selector(selector)
                        if element and element.input_value() != "100":
                            f.select_option(selector, "100")
                            print("Ajustando para 100 linhas...")
                            time.sleep(15) 
                            break
                    except: continue

                print("\n🔍 Lendo dados da Torre...")
                df = extrair_tabela(page)
                
                if not df.empty:
                    processar_dados(df)
                else:
                    print("Atenção: Tabela não capturada.")

                print("⏳ Aguardando 60s para próxima atualização...")
                time.sleep(60)
                
                print("🔄 Atualizando página do rastreador...")
                page.reload(wait_until="domcontentloaded", timeout=90000)

            except Exception as e:
                print(f"❌ Erro no Loop: {e}")
                time.sleep(20)

if __name__ == "__main__":
    print("🚀 Servidor Local rodando em http://127.0.0.1:8080/dados")
    
    # Inicia o Flask em uma thread separada
    threading.Thread(target=lambda: app.run(host='127.0.0.1', port=8080, debug=False, use_reloader=False), daemon=True).start()
    
    # Inicia a automação do Playwright
    iniciar_painel()