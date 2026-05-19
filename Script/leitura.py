import pandas as pd # Tratar arquivos de Tabela 
import boto3 # SDK da aws que interage com o s3 (Serve pra falar com a AWS)
import requests # Serve pra fazer requisições GET, POST, PUT and DELETE
import json # Biblioteca de manipular JSON
import time # Biblioteca medir tempo
from io import StringIO # Ler arquivos em memória sem precisar criar arquivo no Disco
import mysql.connector # Conexão com MySQL
import credenciais # Importa os dados do arquivo python (coloca as credencias da sua aws LÁ IMEDIATAMENTE)
from botocore.exceptions import ClientError, EndpointConnectionError
from datetime import datetime, timedelta
import time
import numpy as np

# ANTEÇÃO: LINHA 174  É ONDE VOCÊ VAI COLOCAR OS ARQUIVOS SEPARADOS, MODIFIQUE LÁ

# Configurações pra se conectar com banco de Dados (credenciais aqui)
config = {
    'user':"root",
    'password':"pepe@2011",
    'host':"localhost",
    'database':"noBroke" 
}

NOME_BUCKET = 's3-bucket-projeto-unico1' # Nome do Bucket na sua S3
RAW_CAMINHO = 'RAW/' # Caminho dentro do Bucket até a pasta da Camada 1
TRUSTED_CAMINHO = 'TRUSTED/Trusted.csv' # Caminho pra criar o Arquivo Trusted (Camada 2)
CLIENT_CAMINHO = 'CLIENT/Client.csv' # Caminho para criar o Arquivo Client (Camada 3)
SITE_URL= '' #tem que subir na ec2 pra enviar o json, futuramente colocar a url do site aqui

TRUSTED_RICHARD_CAMINHO = 'TRUSTED/richard.csv'
CLIENT_RICHARD_CAMINHO = 'CLIENT/richard.json'

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
        
        # Cria uma lista que vai armazenar os csv
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
                    df_trusted[nome_coluna] = pd.to_numeric(df_trusted[nome_coluna], errors='coerce').astype(float)

                    # Só processa a conversão se a coluna não estiver toda vazia para este servidor
                    if not df_trusted.loc[filtro_servidor, nome_coluna].isnull().all():
                        if unidade == 'MB' or unidade == 'MB/s':
                            df_trusted.loc[filtro_servidor, nome_coluna] = round(df_trusted.loc[filtro_servidor, nome_coluna] * 1024, 2)
                        elif unidade == 'GHz':
                            df_trusted.loc[filtro_servidor, nome_coluna] = round(df_trusted.loc[filtro_servidor, nome_coluna] / 1000, 2)

        # Garante que o id_servidor seja um número inteiro e não float/NaN
        
        if df_trusted['id_servidor'].dtype == 'object':
            df_trusted['id_servidor'] = df_trusted['id_servidor'].replace('[]', '0')
            
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

        print("(LOADING) Enviando o Json pro bucket")

        # Aqui envia o JSON para o S3
        with open('client.json', 'rb') as f:
            s3_client.put_object(Bucket=NOME_BUCKET,
                                 Key='CLIENT/client.json',
                                 Body=f,
                                 ContentType='application/json')
        print("JSON enviado para o bucket com sucesso.")

            # ===============================================================
            # Aqui você coloca o seu código que vai criar o arquivo separado
            # Arquivos do individuais no caso

            #isa_individual

        print("Entregavel da Isa")
        df_trusted_isabela = df_raw.copy()

        colunas_remover = [
                'cpu_percent', 'cpu_freq_current', 'cpu_time_idle', 
                'ram_total_gb', 'ram_available_gb', 'ram_used_gb', 'ram_percent', 
                'swap_percent', 'swap_used_gb', 'swap_free_gb', 'disk_percent', 'latencia_resposta_ms',
                'disco_taxa_transferencia','net_bytes_sent_gb', 'net_bytes_recv_gb', 'total_processos','processo_maior_consumo'
            ]
        
        df_trusted_isabela = df_trusted_isabela.drop(columns=colunas_remover, errors='ignore')

        df_trusted_isabela["categoria"] = df_trusted_isabela["endpoint"].fillna("").apply(classificar_categoria)

        pd.DataFrame(df_trusted_isabela).to_csv("isa_trusted.csv", encoding="utf-8", sep=";", index=False)
        print("Consegui acessar o classifica_categoria")


        df_trusted_isabela["tipo_status"] = df_trusted_isabela["status_code"].fillna(0).astype(int).apply(classificar_status)

        Salvar_s3(df_trusted_isabela, "TRUSTED/isa.csv")
        print("Enviado para o bucket o trusted da isabela")

        df_client_isabela = df_trusted_isabela.copy()
        df_client_isabela["timestamp"] = pd.to_datetime(df_client_isabela["timestamp"], dayfirst=True, errors="coerce")
        
        agora = datetime.now()
        inicio_atual = agora - timedelta(minutes=15)
        inicio_anterior = agora - timedelta(minutes=30)


        df_atual = df_client_isabela[df_client_isabela["timestamp"] >= inicio_atual]
        df_anterior = df_client_isabela[(df_client_isabela["timestamp"] >= inicio_anterior) &(df_client_isabela["timestamp"] < inicio_atual)]


        contador_ordens = (df_client_isabela["categoria"] == "ordens").sum()

        contador_volume = len(df_client_isabela)
        contador_atual = len(df_atual)
        contador_anterior = len(df_anterior)

        contador_sucesso_atual = len(df_atual[(df_atual["categoria"] == "ordens") & (df_atual["tipo_status"] == "sucesso")])
        contador_sucesso_anterior = len(df_anterior[df_anterior["tipo_status"] == "sucesso"])
        
        contador_5xx = len(df_client_isabela[(df_client_isabela["status_code"] >= 500) & (df_client_isabela["status_code"] <= 507)])

        contador_5xx_atual = len(df_atual[(df_atual["status_code"] >= 500) & (df_atual["status_code"] <= 507)])
        contador_5xx_anterior = len(df_anterior[(df_anterior["status_code"] >= 500) & (df_anterior["status_code"] <= 507)])

        porcentagem_volume = variacao_percentual(contador_atual, contador_anterior)

        porcentagem_sucesso_atual = porcentagem(contador_sucesso_atual, contador_atual)
        porcentagem_sucesso_anterior = porcentagem(contador_sucesso_anterior, contador_anterior)
        variacao_sucesso = variacao_percentual(porcentagem_sucesso_atual, porcentagem_sucesso_anterior)

        porcentagem_5xx_atual = porcentagem(contador_5xx_atual, contador_atual)
        porcentagem_5xx_anterior = porcentagem(contador_5xx_anterior, contador_anterior)
        variacao_5xx = variacao_percentual(porcentagem_5xx_atual, porcentagem_5xx_anterior)

        latencias_atuais = df_atual[df_atual["categoria"] == "ordens"]["latencia_ms"].dropna().tolist()

        latencias_anteriores = df_anterior[df_anterior["categoria"] == "ordens"]["latencia_ms"].dropna().tolist()

        if len(latencias_atuais) > 0:
            p95_atual = np.percentile(latencias_atuais, 95)
        else:
            p95_atual = 0

        if len(latencias_anteriores) > 0:
            p95_anterior = np.percentile(latencias_anteriores, 95)
        else:
            p95_anterior = 0

        variacao_p95 = variacao_percentual(
        p95_atual,
        p95_anterior)
        
        porcentagem_ordens = porcentagem(contador_ordens, contador_volume)

        total_sucesso_ordens = len(
        df_client_isabela[(df_client_isabela["categoria"] == "ordens") & (df_client_isabela["tipo_status"] == "sucesso")])

        porcentagem_sucesso_ordens = porcentagem(total_sucesso_ordens,contador_ordens)

        latencias_ordens = df_client_isabela[df_client_isabela["categoria"] == "ordens"]["latencia_ms"].dropna().tolist()

        if len(latencias_ordens) > 0:
            latencia_p95_ordens = round(np.percentile(latencias_ordens, 95), 2)
        else:
            latencia_p95_ordens = 0

        df_client_isabela["total_ordens"] = contador_ordens
        df_client_isabela["total_sucesso_ordens"] = total_sucesso_ordens
        df_client_isabela["porcentagem_sucesso_ordens"] = porcentagem_sucesso_ordens
        df_client_isabela["latencia_p95_ordens"] = latencia_p95_ordens
        df_client_isabela["variacao_latencia_p95"] = variacao_p95
        df_client_isabela["porcentagem_ordens"] = porcentagem_ordens
        df_client_isabela["total_volume"] = contador_volume
        df_client_isabela["variacao_volume"] = porcentagem_volume
        df_client_isabela["variacao_sucesso"] = variacao_sucesso
        df_client_isabela["contador_5xx"] = contador_5xx
        df_client_isabela["variacao_5xx"] = variacao_5xx

        df_client_isabela = df_client_isabela.astype(object).where(pd.notnull(df_client_isabela), None)
        
        dados_isabela_json = df_client_isabela.to_dict(orient="records")

        
        with open("isa.json", "w", encoding="utf-8") as f:
                json.dump(dados_isabela_json, f, indent=4, default=str)

        with open("isa.json", "rb") as f:
                s3_client.put_object(
                Bucket=NOME_BUCKET,
                Key="CLIENT/isa.json",
                Body=f,
                ContentType="application/json"
            )
        
            #Fim isa individual
            # ======================================================
            # Começo Luiz Individual
        print('Individual Luiz')

        df_trusted_luiz = df_raw.copy()

        colunas_remover_2 = [
                'cpu_percent', 'cpu_freq_current', 'cpu_time_idle', 'ram_total_gb', 'ram_available_gb', 
                'ram_used_gb','swap_used_gb', 'swap_free_gb', 'disk_percent', 'latencia_resposta_ms',
                'disco_taxa_transferencia','net_bytes_sent_gb', 'net_bytes_recv_gb', 'total_processos','processo_maior_consumo', 
                'metodo', 'endpoint', 'status_code','latencia_ms'
            ]
        
        df_trusted_luiz = df_trusted_luiz.drop(columns=colunas_remover_2, errors='ignore')

        # transformar tudo em float para conseguir fazer as operações matemáticas.

        print('Transformando os valores do csv em numerais')

        df_trusted_luiz['timestamp'] = pd.to_datetime(df_trusted_luiz['timestamp'], dayfirst=True, errors='coerce')
        df_trusted_luiz = df_trusted_luiz.sort_values(by=['home_broker', 'timestamp']).reset_index(drop=True)
        df_trusted_luiz['ram_percent'] = pd.to_numeric(df_trusted_luiz['ram_percent'], errors='coerce')
        df_trusted_luiz['swap_percent'] = pd.to_numeric(df_trusted_luiz['swap_percent'], errors='coerce')

        correlacoes = []
        tendencias_minuto = []
        horas_registro = []
        etas = []
        projeções_futuras = []

        janela_previsao = 24

        for i in range(len(df_trusted_luiz)):
             servidor_atual = df_trusted_luiz.loc[i, 'home_broker']
             horario_registro = df_trusted_luiz.loc[i, 'timestamp']
             ram_registro = df_trusted_luiz.loc[i, 'ram_percent']

             df_luiz = df_trusted_luiz [
                  (df_trusted_luiz['home_broker'] == servidor_atual) &
                  (df_trusted_luiz['timestamp'] <= horario_registro)
             ].tail(janela_previsao)
             
             horas_registro.append(horario_registro.strftime('%H:%M:%S')if pd.notnull(horario_registro) else None)
             
             correlacao = calcular_correcao_movel(df_luiz)
             taxa_minuto = calcular_tendencia_ram(df_luiz)
             eta = calcular_eta_ram(ram_registro, taxa_minuto)
             predicoes = calcular_projeções_futuras(ram_registro, taxa_minuto, df_luiz)

             correlacoes.append(correlacao)
             tendencias_minuto.append(taxa_minuto)
             etas.append(eta)
             projeções_futuras.append(predicoes)

        df_trusted_luiz['correlacao_ram_swap'] = correlacoes
        df_trusted_luiz['tendencia_ram_por_minuto'] = tendencias_minuto
        df_trusted_luiz['hora_registro'] = horas_registro
        df_trusted_luiz['ETA'] = etas

        df_projeções = pd.DataFrame(projeções_futuras, columns=['proj1', 'proj2', 'proj3', 'proj4', 'proj5'])
        df_trusted_luiz = pd.concat([df_trusted_luiz, df_projeções], axis=1)


        print("(LOADING) Enviando o luiz_trusted csv pro bucket")
        Salvar_s3(df_trusted_isabela, "TRUSTED/luiz_trusted.csv")
        pd.DataFrame(df_trusted_luiz).to_csv("luiz_trusted.csv", encoding="utf-8", sep=";", index=False)
        
        df_client_luiz = df_trusted_luiz.copy()

        df_client_luiz = df_client_luiz.astype(object).where(pd.notnull(df_client_luiz), None)
        
        df_client_luiz = df_client_luiz.to_dict(orient="records")

        with open("luiz.json", "w", encoding="utf-8") as f:
                json.dump(df_client_luiz, f, indent=4, default=str)

        with open("luiz.json", "rb") as f:
                s3_client.put_object(
                Bucket=NOME_BUCKET,
                Key="CLIENT/luiz.json",
                Body=f,
                ContentType="application/json"
            )

        # ===============================================================
        # Começo richard individual

        print("(LOADING) Iniciando tratamento de rede...")

        # 1. Fazendo Trusted (Camada 2)
        # Filtrando somente as colunas que eu quero pegar
        df_trusted_richard = df_trusted[['id_servidor', 'home_broker', 'timestamp', 'latencia_resposta_ms', 'net_bytes_sent_gb', 'net_bytes_recv_gb']].copy()

        # Salva o CSV na Camada do trusted localmente e no S3 (Sempre salvando o Trusted para registro)
        pd.DataFrame(df_trusted_richard).to_csv("richard.csv", encoding="utf-8", sep=";", index=False)
        Salvar_s3(df_trusted_richard, TRUSTED_RICHARD_CAMINHO)

        # 2. Fazendo Client (Camada 3 - arquivo JSON)
        # Se latencia, bytes_sent e bytes_recv forem todos nulos, o código pula o bloco abaixo
        cols_rede = ['latencia_resposta_ms', 'net_bytes_sent_gb', 'net_bytes_recv_gb']

        nome_do_servidor = 'SRV-Argos-isa-BD'
        # Verifica se as colunas declaradas são nulas (todas no caso)
        if df_trusted_richard[cols_rede].isnull().all().all():
            print(f"TRATAMENTO: O servidor {nome_do_servidor} não quer coletar dados de Rede ou deu algum erro. Pulando script de JSON.")
        else:
            print(f"(LOADING) Gerando arquivo JSON de Latência para: {nome_do_servidor}")
            df_client_richard = df_trusted_richard.copy()

            # Transforma qualquer NaN em 0 para o JSON não quebrar no site
            df_client_richard = df_client_richard.astype(object).where(pd.notnull(df_client_richard), 0)

            # Converte para lista de dicionários (formato JSON)
            dados_richard_json = df_client_richard.to_dict(orient='records')

            # Salva o JSON localmente
            with open('latencia_richard.json', 'w') as f:
                json.dump(dados_richard_json, f, indent=4, default=str)

            # Envia o JSON para a pasta client no S3
            print("[LOADING] Enviando JSON de Rede e Latêncai para o bucket...")
            with open('latencia_richard.json', 'rb') as f:
                s3_client.put_object(Bucket=NOME_BUCKET,
                                     Key=CLIENT_RICHARD_CAMINHO,
                                     Body=f,
                                     ContentType='application/json')

            print("[LOADING] Arquivo JSON de Rede e Latência enviado com sucesso!")

        # Fim richard individual
        # ===============================================================

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

def classificar_categoria(endpoint):
                if "account" in endpoint:
                    return "financeiro"
                elif "orders" in endpoint:
                    return "ordens"
                elif "market" in endpoint:
                    return "mercado"
                elif "b3" in endpoint:
                    return "b3"
                else:
                    return "trades"


def classificar_status(status_code):
                if status_code < 200 or status_code > 599:
                    return "status_code_invalido"
                elif status_code <= 299:
                    return "sucesso"
                elif status_code <= 499:
                    return "erro_cliente"
                else:
                    return "erro_servidor"

def porcentagem(parte, total):
                if total == 0:
                    return 0
                return round((parte / total) * 100, 2)

def calcular_correcao_movel(df_luiz):
    if len(df_luiz) < 5:
        return 0.0
        
    df_limpo = df_luiz.dropna(subset=['ram_percent', 'swap_percent'])
    
    if df_limpo['ram_percent'].std() == 0 or df_limpo['swap_percent'].std() == 0:
        return 0.0
        
    corr_val = df_limpo['ram_percent'].corr(df_limpo['swap_percent'])
    
    return round(corr_val, 4) if pd.notnull(corr_val) else 0.0

def calcular_tendencia_ram(df_luiz):
    if len(df_luiz) < 3 or df_luiz['ram_percent'].isnull().any():
        return 0.0
    
    tempo_delta = (df_luiz['timestamp'] - df_luiz['timestamp'].min()).dt.total_seconds()
    
    if tempo_delta.max() == 0:
        return 0.0
        
    tempos_minutos = tempo_delta / 60.0
    valores_ram = df_luiz['ram_percent'].values
    
    try:
        coeficientes = np.polyfit(tempos_minutos, valores_ram, 1)
        return round(coeficientes[0], 4)
    except Exception:
        return 0.0


def calcular_eta_ram(ram_atual, taxa_minuto):
    if taxa_minuto > 0:
        ram_restante = 100.0 - ram_atual
        if ram_restante <= 0:
            return "Ja atingiu 100%"
        return f"{round(ram_restante / taxa_minuto, 2)} min"
    elif taxa_minuto < 0:
        return "Tendencia de Queda (Estavel)"
    else:
        return "Estacionario / Sem Variacao"


def calcular_projeções_futuras(ram_atual, taxa_minuto, df_luiz):
    if len(df_luiz) < 3:
        return [None, None, None, None, None]
        
    tempo_delta = (df_luiz['timestamp'] - df_luiz['timestamp'].min()).dt.total_seconds()
    
    if tempo_delta.max() == 0:
        intervalo_medio = 5 / 60.0
    else:
        tempos_minutos = tempo_delta / 60.0
        intervalo_medio = np.diff(tempos_minutos).mean() if len(tempos_minutos) > 1 else 5 / 60.0

    proximos_passos = []
    for passo in range(1, 6):
        predicao = ram_atual + (taxa_minuto * (intervalo_medio * passo))
        predicao = max(0.0, min(100.0, round(predicao, 2)))  
        proximos_passos.append(predicao)
        
    return proximos_passos

def variacao_percentual(atual, anterior):
                if anterior == 0:
                    return 0
                return round(((atual - anterior) / anterior) * 100, 2)

# Agora vai iniciar a ETL
if __name__ == "__main__":
    print(f"Início do processo: {pd.Timestamp.now()}")
    ETL()
    print(f"Fim do processo: {pd.Timestamp.now()}")
