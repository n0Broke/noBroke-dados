import pandas as pd
import boto3 #sdk da aws que interage com o s3
import requests
import json
from io import StringIO

NAME_BUCKET = 's3-bucket-projeto-unico' #Vamos mudar pra um nome do projeto
RAW_WAY = 'RAW/Raw.csv'#caminho do raw.csv
TRUSTED_WAY = 'TRUSTED/Trusted.csv'# caminho do Trusted.csv
CLIENT_WAY = 'CLIENT/Client.csv' #caminho do client.csv
SITE_URL= '' #tem que subir na ec2 pra enviar o json, futuramente colocar a url do site aqui


s3_client = boto3.client(
    's3'
    #COLOCAR AS CREDENCIAIS AQUI, 
    #!!!!!!!!!!!!!ATENÇÃO!!!!!!!!!!!!!!
    # NÃO COMITE AS CREDENDIACIS DA AWS
    )


def ETL():
    try:
        print("(EXTRACT) Coletando dados brutos do diretório 'raw'")
        read_raw = s3_client.get_object(Bucket=NAME_BUCKET, Key=RAW_WAY)
        df_raw = pd.read_csv(read_raw['Body'], sep=';')
         
        print("(TRANSFORM) Removendo cópias")
        df_trusted = df_raw.drop_duplicates()

        # Salva no diretório trusted
        Salvar_s3(df_trusted, TRUSTED_WAY)

        print("Mandando dados para o diretório 'client'")
        df_client = df_trusted.copy() 
        
        df_client['timestamp'] = pd.to_datetime(df_client['timestamp']) # transforma a string da data em formato data e hora
        
        # Salva no client
        Salvar_s3(df_client, CLIENT_WAY)

        print("Convertendo Client para JSON e enviando para o site na EC2...")
        # Transforma os dados em JSON em formata de dicionário 
        dados_json = df_client.to_dict(orient='records')
        
        headers = {'Content-Type': 'application/json'} # pra avisar a API da EC2 que é um Json (ainda não está funcionando)
        response_api = requests.post(SITE_URL, json=dados_json, headers=headers)

        if response_api.status_code == 200:
            print("Sucesso: Dados integrados ao site na EC2!")
        else:
            print(f"Aviso: API retornou status {response_api.status_code}")
    except Exception:
        print(f"Erro no fluxo da ETL: {Exception}")

def Salvar_s3(df, key):
    csv_buffer = StringIO()
    df.to_csv(csv_buffer, index=False, sep=';')
    s3_client.put_object(Bucket=NAME_BUCKET, Key=key, Body=csv_buffer.getvalue())
    print(f"Arquivo salvo: {key}")

if __name__ == "__main__":
    ETL()