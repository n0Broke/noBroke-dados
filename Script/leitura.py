import pandas as pd
import boto3 #sdk da aws que interage com o s3
import requests
import json
import time
from io import StringIO
import mysql.connector

config = {
    'user':"root",
    'password':"",
    'host':"localhost",
    'database':"noBroke" 
}

NOME_BUCKET = 's3-bucket-projeto-unico' #Vamos mudar pra um nome do projeto
RAW_CAMINHO = 'RAW/'#caminho do raw.csv
TRUSTED_CAMINHO = 'TRUSTED/Trusted.csv'# caminho do Trusted.csv
CLIENT_CAMINHO = 'CLIENT/Client.csv' #caminho do client.csv
SITE_URL= '' #tem que subir na ec2 pra enviar o json, futuramente colocar a url do site aqui


s3_client = boto3.client(
    's3',
     #COLOCAR AS CREDENCIAIS AQUI, 
    #!!!!!!!!!!!!!ATENÇÃO!!!!!!!!!!!!!!
    # NÃO COMITE AS CREDENDIACIS DA AWS
)
def buscar_medidas(nome_servidor):
    try:
        conn = mysql.connector.connect(**config)
        cursor = conn.cursor(dictionary=True)

        query = """
            SELECT 
                tipo.nome_componente, 
                formato.unidade_medida 
            FROM tipo_componente tipo
            JOIN servidor ON tipo.fk_servidor = servidor.id_servidor
            JOIN formato ON tipo.fk_formato = formato.id_formato
            WHERE servidor.nome = %s;
        """
        cursor.execute(query, (nome_servidor,))
        resultados = cursor.fetchall()
        
        cursor.close()
        conn.close()
        return resultados
    except:
        print("Erro ao consultar banco de dados")
        return []

def ETL():
    try:
        print("(EXTRACT) Coletando dados brutos do diretório 'raw'")
        listar_csv_raw = s3_client.list_objects_v2(Bucket=NOME_BUCKET, Prefix=RAW_CAMINHO)

        csv = [obj['Key'] for obj in listar_csv_raw.get('Contents', []) if obj['Key'].endswith('.csv')]
        
        lista_csv = []
        for i in csv:
            pegar_raw = s3_client.get_object(Bucket=NOME_BUCKET, Key=i)
            ler_csv = pd.read_csv(pegar_raw['Body'], sep=';')
            lista_csv.append(ler_csv)
        
        df_raw = pd.concat(lista_csv, ignore_index=True)

        nome_do_servidor = df_raw['home_broker'].iloc[0]

        df_trusted = df_raw.copy()
        print("(TRANSFORM) Removendo cópias")
        df_trusted = df_trusted.drop_duplicates()

        print("(TRANSFORM) Removendo valores iguais a 0")
        colunas_numericas = df_trusted.select_dtypes(include=['number']).columns
        for i in colunas_numericas:
            df_trusted[i] = df_trusted[i].replace(0, None)
        
        mudar_medidas = buscar_medidas(nome_do_servidor)

        
        for medida in mudar_medidas:
            nome_coluna = medida['nome_componente']
            unidade = medida['unidade_medida']

            if nome_coluna in df_trusted.columns:
                df_trusted[nome_coluna] = pd.to_numeric(df_trusted[nome_coluna], errors='coerce')
                df_trusted[nome_coluna] = df_trusted[nome_coluna].fillna(0)

                if unidade == 'MB' or unidade == 'MB/s':
                    df_trusted[nome_coluna] = round(df_trusted[nome_coluna] * 1024, 2)
                elif unidade == 'GHz':
                    df_trusted[nome_coluna] = round(df_trusted[nome_coluna] / 1000, 2)

        # Salva no diretório trusted
        pd.DataFrame(df_trusted).to_csv("trusted.csv", encoding="utf-8", sep=";", index=False)
        Salvar_s3(df_trusted, TRUSTED_CAMINHO)

        print("(LOADING) Mandando dados para o diretório 'client'")
        df_client = df_trusted.copy() 
        
        Salvar_s3(df_client, CLIENT_CAMINHO)

        print("(LOADING) Convertendo Client para JSON e enviando para o site na EC2...")

        df_client.to_json('client.json', orient='records', lines=False,)
        dados_json = df_client.to_dict(orient='records')
        with open('client.json', 'w') as f:
            json.dump(dados_json, f, indent=4, default=str)
            print("(LOADING) Enviando o Json pro bucket")
        with open('client.json', 'rb') as f:
            s3_client.put_object(Bucket=NOME_BUCKET,Key='CLIENT/client.json',Body=f,ContentType='application/json')
        print("(LOADING) JSON enviado para o bucket com sucesso.")


    
    
    except:
        print(f"Erro no envio de dados")

def Salvar_s3(df, Key): # nome do data frame/ dados e caminho no bucket
    csv_buffer = StringIO()
    df.to_csv(csv_buffer, index=False, sep=';')
    s3_client.put_object(Bucket=NOME_BUCKET, Key=Key, Body=csv_buffer.getvalue())
    print(f"Arquivo salvo: {Key}")

if __name__ == "__main__":
    ETL()