import pandas as pd # Tratar arquivos de Tabela 
import boto3 # SDK da aws que interage com o s3 (Serve pra falar com a AWS)
import requests # Serve pra fazer requisições GET, POST, PUT and DELETE
import json # Biblioteca de manipular JSON
import time # Biblioteca medir tempo
from io import StringIO # Ler arquivos em memória sem precisar criar arquivo no Disco
import mysql.connector # Conexão com MySQL
import credenciais # Importa os dados do arquivo python (coloca as credencias da sua aws LÁ IMEDIATAMENTE)
from botocore.exceptions import ClientError, EndpointConnectionError

# ANTEÇÃO: LINHA 174  É ONDE VOCÊ VAI COLOCAR OS ARQUIVOS SEPARADOS, MODIFIQUE LÁ

# Configurações pra se conectar com banco de Dados (credenciais aqui)
config = {
    'user':"root",
    'password':"#Rich130407",
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
    aws_access_key_id = credenciais.AWS_ACCESS_KEY,
    aws_secret_access_key = credenciais.AWS_SECRET_KEY,
    aws_session_token = credenciais.AWS_SESSION_TOKEN
)

# Função de Buscar medidas e Componentes no banco de dados, ela:
# 1. Quais os Componentes tem daquele servidor que fez a requisição
# 2. Quais as Unidades de medida ele colocou pra ser lá
def buscar_medidas(nome_servidor):
    try:
        print(f"Buscando Medidas do Banco de Dados para: {nome_servidor}")
        conn = mysql.connector.connect(**config) # Tenta fazer uma conexão com as "**config" (credenciais) que demos
        cursor = conn.cursor(dictionary=True) # Cria um "executor" de comandos SQL

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
    except Exception as e:
        # Se der erro na conexão mostra no terminal e retorna tabela vazia
        print(f"Erro ao consultar banco de dados: {e}")
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

        df_trusted = df_raw.copy()
        print("(TRANSFORM) Removendo cópias")
        df_trusted = df_trusted.drop_duplicates() # Remove dados Duplicados

        # Define colunas que NUNCA vão ser anuladas (identificação)
        colunas_preservar = ['id_servidor', 'home_broker', 'timestamp', 'processo_maior_consumo']

        print("(TRANSFORM) Removendo valores iguais a 0")
        colunas_numericas = df_trusted.select_dtypes(include=['number']).columns # Colunas apenas de números
        for i in colunas_numericas: # Loop nessa lista de cima
            if i in colunas_preservar:
                continue
            df_trusted[i] = df_trusted[i].replace(0, None) # Troca tudo que for 0 (tipo cpu 0) por None

        # Identifica todos os servidores únicos presentes no DataFrame para tratar um por um
        servidores_presentes = df_trusted['home_broker'].dropna().unique()

        print("(TRANSFORM) Aplicando regras de monitoramento individuais por servidor")
        for broker in servidores_presentes:
            # Busca as regras específicas deste servidor no Banco de Dados
            mudar_medidas = buscar_medidas(broker)
            componentes_solicitados = [medida['nome_componente'] for medida in mudar_medidas]
            
            # Cria um filtro para aplicar as mudanças apenas nas linhas deste servidor
            filtro_servidor = df_trusted['home_broker'] == broker

            # Anula métricas não solicitadas pelo Banco de Dados APENAS para este servidor
            for coluna in df_trusted.columns:
                if coluna not in componentes_solicitados and coluna not in colunas_preservar:
                    df_trusted.loc[filtro_servidor, coluna] = None

            # Converte as unidades de medida conforme solicitado pelo BD para este servidor
            for medida in mudar_medidas:
                nome_coluna = medida['nome_componente']
                unidade = medida['unidade_medida']

                if nome_coluna in df_trusted.columns:
                    # Garante que a coluna seja numérica
                    df_trusted[nome_coluna] = pd.to_numeric(df_trusted[nome_coluna], errors='coerce')

                    # Só processa a conversão se a coluna não estiver toda vazia para este servidor
                    if not df_trusted.loc[filtro_servidor, nome_coluna].isnull().all():
                        if unidade == 'MB' or unidade == 'MB/s':
                            df_trusted.loc[filtro_servidor, nome_coluna] = round(df_trusted.loc[filtro_servidor, nome_coluna] * 1024, 2)
                        elif unidade == 'GHz':
                            df_trusted.loc[filtro_servidor, nome_coluna] = round(df_trusted.loc[filtro_servidor, nome_coluna] / 1000, 2)

        # Garante que o id_servidor seja um número inteiro e não float/NaN
        df_trusted['id_servidor'] = df_trusted['id_servidor'].fillna(0).astype(int)

        # Salva no diretório trusted (Camada 2)
        pd.DataFrame(df_trusted).to_csv("trusted.csv", encoding="utf-8", sep=";", index=False)
        Salvar_s3(df_trusted, TRUSTED_CAMINHO)

        print("(LOADING) Mandando dados para o diretório 'client'")
        df_client = df_trusted.copy() # Pega os dados e copia da Camada 2 pra 3 (antes de tratar pra JSON)
        
        # Blindagem: Transforma qualquer NaN em None para o JSON exibir 'null' corretamente
        df_client = df_client.astype(object).where(pd.notnull(df_client), None)
        
        Salvar_s3(df_client, CLIENT_CAMINHO) # Salva os dados do Cliente na S3

        print("(LOADING) Convertendo Client para JSON e enviando para o site na EC2...")

        # Converte DataFrame para Dicionário e salva como JSON formatado
        dados_json = df_client.to_dict(orient='records')

        # Salva no Note local (para debug/backup ou revisão)
        with open('client.json', 'w') as f:
            json.dump(dados_json, f, indent=4, default=str)
            # indent=4: JSON formatado (bonito)
            # default=str: converte tipos especiais (datetime) para string

            # ===============================================================
            # Aqui você coloca o seu código que vai criar o arquivo separado
            # Arquivos do individuais no caso



            # ===============================================================


        print("(LOADING) Enviando o Json pro bucket")

        # Aqui envia o JSON para o S3
        with open('client.json', 'rb') as f:
            s3_client.put_object(Bucket=NOME_BUCKET,
                                 Key='CLIENT/client.json',
                                 Body=f,
                                 ContentType='application/json')
        print("JSON enviado para o bucket com sucesso.")


    # Tratativas de Erro caso a AWS não funfe
    except EndpointConnectionError:
        print("Erro de Conexão: Não foi possível alcançar a AWS. Verifique sua internet.")

    except ClientError as e:
        erro_code = e.response['Error']['Code']
        if erro_code == '403':
            print("Erro AWS [403]: Acesso Negado. Verificar suas credenciais.py ou a Policy do Bucket.")
        elif erro_code == '404':
            print("Erro AWS [404]: O Bucket ou o arquivo não foi encontrado. Verifique o nome do Bucket.")
        elif erro_code == 'ExpiredToken':
            print("Erro AWS: Token da AWS expirou! Tenta pegar um novo.")
        else:
            print(f"Erro Desconhecido da AWS: {e}")

    except pd.errors.EmptyDataError:
        print("Erro de Dados: Algum dos arquivos CSV no S3 está vazio.")

    except ValueError as e:
        print(f"Erro na Lógica: {e}")

    except Exception as e:
        print(f"Erro adverso: {e}")


# Função pra mandar o Objeto pra S3 Cliente
def Salvar_s3(df, Key): # nome do data frame/ dados e caminho no bucket
    csv_buffer = StringIO()
    df.to_csv(csv_buffer, index=False, sep=';')
    s3_client.put_object(Bucket=NOME_BUCKET, Key=Key, Body=csv_buffer.getvalue())
    print(f"Arquivo salvo no S3: {Key}")

# Agora vai iniciar a ETL
if __name__ == "__main__":
    print(f"Início do processo: {pd.Timestamp.now()}")
    ETL()
    print(f"Fim do processo: {pd.Timestamp.now()}")