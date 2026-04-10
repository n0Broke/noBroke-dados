import pandas as pd
import boto3 #sdk da aws que interage com o s3
import requests
import json
import time
from io import StringIO

NAME_BUCKET = 's3-bucket-projeto-unico' #Vamos mudar pra um nome do projeto
RAW_WAY = 'RAW/Raw.csv'#caminho do raw.csv
TRUSTED_WAY = 'TRUSTED/Trusted.csv'# caminho do Trusted.csv
CLIENT_WAY = 'CLIENT/Client.csv' #caminho do client.csv
SITE_URL= '' #tem que subir na ec2 pra enviar o json, futuramente colocar a url do site aqui


s3_client = boto3.client(
    's3',
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
        print("(TRANSFORM) Removendo valores iguais a 0")
        df_trusted = df_trusted.replace(0, '')
        print("(TRANSFORM) Removendo valores nulos")
        df_trusted = df_trusted.dropna()


        # Salva no diretório trusted
        Salvar_s3(df_trusted, TRUSTED_WAY)
        pd.DataFrame(df_trusted).to_csv("trusted.csv", encoding="utf-8", sep=";", index=False)

        print("(LOADING) Mandando dados para o diretório 'client'")
        df_client = df_trusted.copy() 
        
        # df_client['timestamp'] = pd.to_datetime(df_client['timestamp'])
        # transforma a string da data em formato data e hora
        
        # Salva no client
        Salvar_s3(df_client, CLIENT_WAY)

        print("(LOADING) Convertendo Client para JSON e enviando para o site na EC2...")

        df_client.to_json('client.json', orient='records', lines=False,)
        dados_json = df_client.to_dict(orient='records')
        with open('client.json', 'w') as f:
            json.dump(dados_json, f, indent=4, default=str)
            print("(LOADING) Enviando o Json pro bucket")
            s3_client.put_object(Body='client.json',Bucket=NAME_BUCKET, Key='CLIENT/client.json')


        # Transforma os dados em JSON em formata de dicionário 
        
        # headers = {'Content-Type': 'application/json'} # pra avisar a API da EC2 que é um Json (ainda não está funcionando)

        # response_api = requests.post(SITE_URL, json=dados_json, headers=headers)

        # if response_api.status_code == 200:
        #     print("Sucesso: Dados integrados ao site na EC2!")
        # else:
        #     print(f"Aviso: API retornou status {response_api.status_code}")
    
    
    
    except:
        print(f"Erro no envio de dados")

def Salvar_s3(df, Key): # nome do data frame/ dados e caminho no bucket
    csv_buffer = StringIO()
    df.to_csv(csv_buffer, index=False, sep=';')
    s3_client.put_object(Bucket=NAME_BUCKET, Key=Key, Body=csv_buffer.getvalue())
    print(f"Arquivo salvo: {Key}")

if __name__ == "__main__":

    while True:
        ETL()
        time.sleep(15)