import pandas as pd # Tratar arquivos de Tabela 
import boto3 # SDK da aws que interage com o s3 (Serve pra falar com a AWS)
import requests # Serve pra fazer requisições GET, POST, PUT and DELETE
import json # Biblioteca de manipular JSON
import time # Biblioteca medir tempo
from io import StringIO # Ler arquivos em memória sem precisar criar arquivo no Disco
import mysql.connector # Conexão com MySQL

# Configurações pra se conectar com banco de Dados (credenciais aqui)
config = {
    'user':"root",
    'password':"",
    'host':"localhost",
    'database':"noBroke" 
}

NOME_BUCKET = 's3-bucket-projeto-unico' # Nome do Bucket na sua S3
RAW_CAMINHO = 'RAW/' # Caminho dentro do Bucket até a pasta da Camada 1
TRUSTED_CAMINHO = 'TRUSTED/Trusted.csv' # Caminho pra criar o Arquivo Trusted (Camada 2)
CLIENT_CAMINHO = 'CLIENT/Client.csv' # Caminho para criar o Arquivo Client (Camada 3)
SITE_URL= '' #tem que subir na ec2 pra enviar o json, futuramente colocar a url do site aqui

# Credenciais da AWS (Só pegar na página quando tu liga a AWS)
s3_client = boto3.client(
    's3',
     #COLOCAR AS CREDENCIAIS AQUI, 
    #!!!!!!!!!!!!!ATENÇÃO!!!!!!!!!!!!!!
    # NÃO COMITE AS CREDENDIACIS DA AWS
)
# Função de Buscar medidas e Componentes no banco de dados, ela:
# 1. Quais os Componentes tem daquele servidor que fez a requisição
# 2. Quais as Unidades de medida ele colocou pra ser lá

def buscar_medidas(nome_servidor):
    try:
        conn = mysql.connector.connect(**config) # Tenta fazer uma conexão com as "**config" (credenciais) que demos
        cursor = conn.cursor(dictionary=True) # Cria um "executor" de comandos SQL
        # dictionary=True faz retornar dados como dicionário: {'coluna': 'valor'}
        # Sem isso, retornaria tupla: ('valor1', 'valor2')


        # Aqui está o comando que irá fazer quando se conectar
        query = """
            SELECT 
                tipo.nome_componente, 
                formato.unidade_medida 
            FROM tipo_componente tipo
            JOIN servidor ON tipo.fk_servidor = servidor.id_servidor
            JOIN formato ON tipo.fk_formato = formato.id_formato
            WHERE servidor.nome = %s;
        """

        # Realiza a função de conexão passando a query (oque é pra buscar) e o nome do servidor que fica no %s
        cursor.execute(query, (nome_servidor,))
        resultados = cursor.fetchall() # Pega todos os resultados que achar
        
        # Fecha a conexão e retorna o que achou de maneira bruta
        cursor.close()
        conn.close()
        return resultados
    except:
        # Se der erro na conexão mostra no terminal e retorna tabela vazia
        print("Erro ao consultar banco de dados")
        return []

# Função da ETL pra agora tratar eles pras Camadas 2 e 3
# Camada 2. 
# - Remove dados duplicados do CSV apenas (que já tinham na camada 2 e 3 no caso)
# - Deixa dados de Valor 0 como Null
# - Converte as Unidades que recebeu pra seus valores respectivos que o cliente pediu pra passar pro Banco de Dados
# - Salva CSV, envia pra S3 e BD
# Camada 3.
# - Salva JSON e envia pra S3
def ETL():
    try:
        # Tenta ir nos dados do caminho que vc passsou, criando um item com uma lista
        print("(EXTRACT) Coletando dados brutos do diretório 'raw'")
        listar_csv_raw = s3_client.list_objects_v2(Bucket=NOME_BUCKET, Prefix=RAW_CAMINHO)

        # Trata essa lista, criando outra com agora só arquivos que terminam com .csv
        csv = [obj['Key'] for obj in listar_csv_raw.get('Contents', []) if obj['Key'].endswith('.csv')]
        
        # Cria uma lista que vai armaazenar os csv
        lista_csv = []
        # Verifica agora cada arquivos csv
        for i in csv:
            # Baixa o arquivo CSV do S3
            pegar_raw = s3_client.get_object(Bucket=NOME_BUCKET, Key=i) # Key = caminho completo, exemplo: 'RAW/coleta_2024_01_15.csv'
            # Pegar e separar por ';' em cada linha
            ler_csv = pd.read_csv(pegar_raw['Body'], sep=';')
            # Agora naquela lista que fizemos, add o que foi pego no ler_csv
            lista_csv.append(ler_csv)
        
        # Quando acabar o loop entre os arquivos, concatena tudo da lista em um arquivo só

        # Junta todos os CSVs em uma única tabela
        # ignore_index=True renumera as linhas (evita índices duplicados)
        df_raw = pd.concat(lista_csv, ignore_index=True)

        # Nome do Servidor  escolhido
        nome_do_servidor = df_raw['home_broker'].iloc[0]

        df_trusted = df_raw.copy()
        print("(TRANSFORM) Removendo cópias")
        df_trusted = df_trusted.drop_duplicates() # Remove dados Duplicados

        print("(TRANSFORM) Removendo valores iguais a 0")
        colunas_numericas = df_trusted.select_dtypes(include=['number']).columns # Colunas apenas de números
        for i in colunas_numericas: # Loop nessa lista de cima
            df_trusted[i] = df_trusted[i].replace(0, None) # Troca tudo que for 0 (tipo cpu 0) por None, como se n fosse pra ter pego os dados
        
        mudar_medidas = buscar_medidas(nome_do_servidor)

        # Loop
        # Converte unidades para o padrão solicitado
        for medida in mudar_medidas:
            nome_coluna = medida['nome_componente']
            unidade = medida['unidade_medida']

            if nome_coluna in df_trusted.columns:
                # Garante que a coluna seja numérica (converte texto para número)
                df_trusted[nome_coluna] = pd.to_numeric(df_trusted[nome_coluna], errors='coerce')
                # Preenche valores inválidos com 0
                df_trusted[nome_coluna] = df_trusted[nome_coluna].fillna(0)

                if unidade == 'MB' or unidade == 'MB/s':
                    df_trusted[nome_coluna] = round(df_trusted[nome_coluna] * 1024, 2)
                elif unidade == 'GHz':
                    df_trusted[nome_coluna] = round(df_trusted[nome_coluna] / 1000, 2)

        # Salva no diretório trusted (Camada 2)
        pd.DataFrame(df_trusted).to_csv("trusted.csv", encoding="utf-8", sep=";", index=False)
        Salvar_s3(df_trusted, TRUSTED_CAMINHO)

        print("(LOADING) Mandando dados para o diretório 'client'")
        df_client = df_trusted.copy() # Pega os dados e copia da Camada 2 pra 3 (antes de tratar pra JSON)
        
        Salvar_s3(df_client, CLIENT_CAMINHO) # Salva os dados do Cliente na S3

        print("(LOADING) Convertendo Client para JSON e enviando para o site na EC2...")

        # Converte DataFrame para JSON
        df_client.to_json('client.json', orient='records', lines=False,)
        # orient='records' = formato: [{"col1": "val1"}, {"col2": "val2"}]
        # lines=False: JSON normal (não JSONL)

        dados_json = df_client.to_dict(orient='records')

        # Salva no Note local (para debug/backup ou revisão)
        with open('client.json', 'w') as f:
            json.dump(dados_json, f, indent=4, default=str)
                # indent=4: JSON formatado (bonito)
                # default=str: converte tipos especiais (datetime) para string

            print("(LOADING) Enviando o Json pro bucket")

        # Aqui envia pra S3
        with open('client.json', 'rb') as f:
            s3_client.put_object(Bucket=NOME_BUCKET,
                                 Key='CLIENT/client.json',
                                 Body=f,
                                 ContentType='application/json')
        print("(LOADING) JSON enviado para o bucket com sucesso.")


    
    
    except:
        print(f"Erro no envio de dados")

# Função pra mandar o Objeto pra S3 Cliente
def Salvar_s3(df, Key): # nome do data frame/ dados e caminho no bucket
    csv_buffer = StringIO()
    df.to_csv(csv_buffer, index=False, sep=';')
    s3_client.put_object(Bucket=NOME_BUCKET, Key=Key, Body=csv_buffer.getvalue())
    print(f"Arquivo salvo: {Key}")

if __name__ == "__main__":
    ETL()