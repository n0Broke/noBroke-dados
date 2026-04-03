import pandas as pd
import boto3
import requests
import json
from io import StringIO
# por favor richard, coloca o nome dos diretórios como está  no código python, pelo amor de Jesus Cristo
# https://www.instagram.com/reel/DWo5DB8DTk1/?igsh=MXZ3bnRiZ3RvYjJvaA==
# Richard por favor, pesquise como funfa a lambida vamo precisar disso pra alguma coisa -> Fui, vou jogar re9 

BUCKET_NOME = 'nome do bucket burro'
RAW_CAMINHO     = 'raw/Raw.csv'#caminho do raw.csv
TRUSTED_CAMINHO = 'trusted/Trusted.csv'# caminho do Trusted.csv
CLIENT_CAMINHO  = 'client/Client.csv' #caminho do client.csv
SITE_URL = 'coloca a url do site aq' #tem que subir na ec2 pra enviar o json

s3_client = boto3.client('s3')

def ETL():
    try:
        print("(EXTRACT) Coletando dados brutos do diretório 'raw'")
        response_raw = s3_client.get_object(Bucket=BUCKET_NOME, Key=RAW_CAMINHO)
        df_raw = pd.read_csv(response_raw['Body'], sep=';')
        
        print("(TRANSFORM) Removendo cópias")
        df_trusted = df_raw.drop_duplicates()
        
        # Salva no diretório trusted
        Salvar_s3(df_trusted, TRUSTED_CAMINHO)

        print("Mandando dados para o diretório 'client'")
        df_client = df_trusted.copy() 
        
        df_client['timestamp'] = pd.to_datetime(df_client['timestamp'])
        
        # Salva no client
        Salvar_s3(df_client, CLIENT_CAMINHO)

        print("3. Convertendo Client para JSON e enviando para API no EC2...")
        # Transforma os dados em JSON
        dados_json = df_client.to_dict(orient='records')
        
        headers = {'Content-Type': 'application/json'}
        response_api = requests.post(SITE_URL, json=dados_json, headers=headers)

        if response_api.status_code == 200:
            print("Sucesso: Dados integrados ao site no EC2!")
        else:
            print(f"Aviso: API retornou status {response_api.status_code}")
    except Exception:
        print(f"Erro no fluxo ETL: {Exception}")

def Salvar_s3(df, key):
    csv_buffer = StringIO()
    df.to_csv(csv_buffer, index=False, sep=';')
    s3_client.put_object(Bucket=BUCKET_NOME, Key=key, Body=csv_buffer.getvalue())
    print(f"Arquivo salvo: {key}")

if __name__ == "__main__":
    ETL()