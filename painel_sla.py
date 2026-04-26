import pandas as pd
from playwright.sync_api import sync_playwright
import time
import threading
import os
from flask import Flask, jsonify
from flask_cors import CORS
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from supabase import create_client 

app = Flask(__name__)
CORS(app) 

# --- CONFIGURAÇÕES SUPABASE ---
# Dados extraídos das suas configurações de API
URL_SUPABASE = "https://vhebojltcxsfohmmever.supabase.co"
KEY_SUPABASE = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZoZWJvamx0Y3hzZm9maG1ldmVyIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzcxODEwMzIsImV4cCI6MjA5Mjc1NzAzMn0.jOep5EfDwK3lj4jlaCe8AgYBz_yYkCBiHMm8dTcAR28"

supabase = create_client(URL_SUPABASE, KEY_SUPABASE)

# --- MEMÓRIA PERSISTENTE ---
cache_real = {
    "monitorados": 0, "em_transito": 0, "nova_solicitacao": 0, 
    "aguardando_inicio": 0, "inicio_atraso": 0
}

NOME_ARQUIVO_JSON = 'credenciais.json' 
PLANILHA_ID = "1zBXe00PPK4B0BsOha5Jo4WUPnJ7EBuLS5dl7_5F0jYI"

def enviar_para_supabase(dados):
    """ Envia os dados para a tabela status_operacao no Supabase """
    try:
        dados_supa = {
            "id": 1,
            "monitorados": dados["monitorados"],
            "em_transito": dados["em_transito"],
            "nova_solicitacao": dados["nova_solicitacao"],
            "aguardando_inicio": dados["aguardando_inicio"],
            "inicio_atraso": dados["inicio_atraso"]
        }
        supabase.table("status_operacao").upsert(dados_supa).execute()
        print("☁️ Sincronizado com Supabase (Nuvem).")
    except Exception as e:
        print(f"❌ Erro Supabase: {e}")

def enviar_para_gsheet(dados):
    try:
        if not os.path.exists(NOME_ARQUIVO_JSON):
            return
        if dados["monitorados"] <= 0: return
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name(NOME_ARQUIVO_JSON, scope)
        client = gspread.authorize(creds)
        ss = client.open_by_key(PLANILHA_ID)
        sheet = ss.worksheet("Dashboard_Dados2")
        
        valores = [
            [dados["monitorados"]], [dados["em_transito"]],
            [dados["nova_solicitacao"]], [dados["aguardando_inicio"]],
            [dados["inicio_atraso"]], [time.strftime('%H:%M:%S')]
        ]
        sheet.update('B2:B7', valores)
        print("📊 Dados sincronizados com Google Sheets.")
    except Exception as e:
        print(f"❌ Erro Sheets: {e}")

@app.route('/dados')
def get_dados():
    global cache_real
    return jsonify(cache_real)

def processar_dados(df):
    global cache_real
    if df is not None and not df.empty and len(df) > 5:
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
        print(f"✅ Cache Atualizado: {total} Monitorados")
        enviar_para_gsheet(cache_real)
        enviar_para_supabase(cache_real)
    else:
        print("⚠️ Leitura inválida ou página em branco. Mantendo cache anterior.")

def extrair_tabela(page):
    alvo = page
    for frame in page.frames:
        try:
            if frame.query_selector("table"):
                alvo = frame
                break
        except: continue
    try:
        alvo.wait_for_selector("table tbody tr", timeout=5000)
        rows = alvo.query_selector_all("table tbody tr")
        lista = []
        for row in rows:
            cols = row.query_selector_all("td")
            if len(cols) < 11: continue
            status_td = cols[2] 
            icon = status_td.query_selector("i, img, span")
            status_texto = icon.get_attribute("title") if icon else "SEM STATUS"
            lista.append({
                "Código": cols[1].text_content().strip(),
                "Status": status_texto.upper().strip()
            })
        return pd.DataFrame(lista)
    except:
        return pd.DataFrame()

def iniciar_painel():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        page.goto("http://vstrack.ddns.net/komando/", timeout=120000)

        # Isso substitui o "Enter" que não estava funcionando
        print("\n--- VOCÊ TEM 30 SEGUNDOS PARA LOGAR NO NAVEGADOR ---")
        time.sleep(30) 

        while True:
            try:
                df = extrair_tabela(page)
                processar_dados(df)

                print("🔄 Recarregando página...")
                page.reload(wait_until="domcontentloaded")
                time.sleep(10)
                
                for f in page.frames:
                    if f.query_selector("select[name*='length']"):
                        f.select_option("select[name*='length']", "100")
                        time.sleep(6)
                        break
                
                print("💤 Aguardando 60s...")
                time.sleep(60)

            except Exception as e:
                print(f"❌ Erro no loop: {e}")
                time.sleep(10)

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=8080), daemon=True).start()
    iniciar_painel()