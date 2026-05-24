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
    'password':"5",
    'host':"localhost",
    'database':"noBroke" 
}

NOME_BUCKET = 'bucket.06-04-2026' # Nome do Bucket na sua S3
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


a = None
def buscar_medidas(nome_servidor,):
    try:
        a = nome_servidor
        print(f"Buscando Medidas do Banco de Dados para: {nome_servidor}")
        conn = mysql.connector.connect(**config) # Tenta fazer uma conexão com as "**config" (credenciais) que demos
        cursor = conn.cursor(dictionary=True) # Cria um "executor" de comandos SQL

        # Aqui está o comando que irá fazer quando se conectar
        query = """
            SELECT 
                tipo.nome_componente, 
                formato.unidade_medida,
                tipo.valor_max_critico 
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
        print(f"O componente {componente} tem o valor crítico de: {valor_critico}")
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
        print("+------------------------------------------------------------------------------+")
        print("Iniciando o tratamento das métricas dos servidores")
        print("Coletando dados brutos do diretório 'raw'")
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
        df_trusted = df_trusted.drop_duplicates() # Remove dados Duplicados

        # Define colunas que NUNCA vão ser anuladas (identificação)
        colunas_preservar = ['fk_empresa','id_servidor', 'home_broker', 'timestamp', 'processo_maior_consumo']

        colunas_numericas = df_trusted.select_dtypes(include=['number']).columns # Colunas apenas de números
        for i in colunas_numericas: # Loop nessa lista de cima
            if i in colunas_preservar:
                continue
            df_trusted[i] = df_trusted[i].replace(0, None) # Troca tudo que for 0 (tipo cpu 0) por None

        # Identifica todos os servidores únicos presentes no DataFrame para tratar um por um
        servidores_presentes = df_trusted['home_broker'].dropna().unique()

        print("Aplicando regras de monitoramento individuais por servidor")
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

        print("Enviando os dados parametrizados ao diretório 'client'")
        print("+------------------------------------------------------------------------------+")

        df_dados_feio = df_trusted.copy() # Pega os dados e copia da Camada 2 pra 3 (antes de tratar pra JSON)
        
        # Blindagem: Transforma qualquer NaN em None para o JSON exibir 'null' corretamente
        df_trusted_matheus = df_dados_feio.astype(object).where(pd.notnull(df_dados_feio), None)
        
        Salvar_s3(df_trusted_matheus, CLIENT_CAMINHO) # Salva os dados do Cliente na S3

        print("Limpando dados que serão exibidos nas dashboards")

            # === ADICIONE ESTE BLOCO AQUI PARA CRIAR OS LIMITES DIRETO NA FUNÇÃO ===
        resultados = buscar_medidas("NB1-luiz") # Busca direto do banco usando o nome correto do servidor
        limites = {}
        for linha in resultados:
            limites[linha['nome_componente']] = float(linha['valor_max_critico'])
        # ======================================================================
        # Garante o formato de data e remove repetições dentro do mesmo minuto
        # 1. Garante que a coluna de timestamp está no formato datetime do pandas
        df_trusted_matheus['timestamp_dt'] = pd.to_datetime(df_trusted_matheus['timestamp'], format='%d-%m-%Y %H:%M:%S')

        # 2. Cria uma coluna de texto temporária apenas com Ano-Mês-Dia Hora:Minuto
        df_trusted_matheus['timestamp'] = df_trusted_matheus['timestamp_dt'].dt.strftime('%Y-%m-%d %H:%M')

        # 3. Remove duplicatas baseando-se nessa nova coluna de minutos
        df_filtrado = df_trusted_matheus.drop_duplicates(subset=['timestamp'])

        df_client_matheus = []

        # Mudamos aqui para ler do 'df_filtrado'
        for _, linha in df_filtrado.iterrows():
            registro = linha.to_dict()
            
            # Removemos a coluna auxiliar de datetime do json final para manter limpo
            registro.pop('timestamp_dt', None)
            
            # 2. Injeta os limites dinamicamente para cada componente ativo
            for componente, limite_critico in limites.items():
                if componente in registro:
                    registro[f"limite_{componente}"] = limite_critico
                    
            # 3. Filtra os nulos do registro atual e remove as chaves indesejadas
            registro_limpo = {
                chave: valor for chave, valor in registro.items()
                if pd.notnull(valor) and chave != "processo_maior_consumo"
            }
            
            # 4. Adiciona na lista final
            df_client_matheus.append(registro_limpo)

        # Salva no Note local (para debug/backup ou revisão)
        with open('matheus.json', 'w') as f:
            json.dump(df_client_matheus, f, indent=4, default=str)
            # indent=4: JSON formatado (bonito)
            # default=str: converte tipos especiais (datetime) para string

        # Aqui envia o JSON para o S3
        with open('matheus.json', 'rb') as f:
            s3_client.put_object(Bucket=NOME_BUCKET,
                                 Key='CLIENT/matheus.json',
                                 Body=f,
                                 ContentType='application/json')
        print("Dados limpos enviados ao bucket.")

            # ===============================================================
            # Aqui você coloca o seu código que vai criar o arquivo separado
            # Arquivos do individuais no caso
        print("+------------------------------------------------------------------------------+")
        #isa_individual

        print("Iniciando tratamento das requisições")
        df_trusted_isabela = df_raw.copy()

        df_trusted_isabela = df_trusted_isabela[
            [
                'fk_empresa',
                'id_servidor',
                'home_broker',
                'timestamp',
                'metodo',
                'endpoint',
                'status_code',
                'latencia_ms'
            ]
        ]
        print("Classificando as requisições devidamente")
        df_trusted_isabela["categoria"] = (
            df_trusted_isabela["endpoint"]
            .fillna("")
            .apply(classificar_categoria)
        )

        df_trusted_isabela["tipo_status"] = (
            df_trusted_isabela["status_code"]
            .fillna(0)
            .astype(int)
            .apply(classificar_status)
        )

        pd.DataFrame(df_trusted_isabela).to_csv(
            "isa_trusted.csv",
            encoding="utf-8",
            sep=";",
            index=False
        )

        Salvar_s3(df_trusted_isabela, "TRUSTED/isa.csv")

        print("Trusted da Isabela enviado")
        df_client_isabela = df_trusted_isabela.copy()

        df_client_isabela["timestamp"] = pd.to_datetime(
            df_client_isabela["timestamp"],
            dayfirst=True,
            errors="coerce"
        )

        df_client_isabela = df_client_isabela.sort_values("timestamp")

        df_client_isabela["janela_15min"] = df_client_isabela["timestamp"].dt.floor("15min")

        janelas = sorted(df_client_isabela["janela_15min"].dropna().unique())

        dados_dashboard = []

        for i in range(len(janelas)):

            janela_atual = janelas[i]

            df_atual = df_client_isabela[
                df_client_isabela["janela_15min"] == janela_atual
            ]

            if i > 0:
                janela_anterior = janelas[i - 1]

                df_anterior = df_client_isabela[
                    df_client_isabela["janela_15min"] == janela_anterior
                ]
            else:
                df_anterior = df_client_isabela.iloc[0:0]

            total_volume = len(df_atual)
            total_volume_anterior = len(df_anterior)

            variacao_volume = variacao_percentual(
                total_volume,
                total_volume_anterior
            )

            ordens_atual = df_atual[
                df_atual["categoria"] == "ordens"
            ]

            ordens_anterior = df_anterior[
                df_anterior["categoria"] == "ordens"
            ]

            total_ordens = len(ordens_atual)

            total_sucesso_ordens = len(
                ordens_atual[ordens_atual["tipo_status"] == "sucesso"]
            )

            total_sucesso_ordens_anterior = len(
                ordens_anterior[ordens_anterior["tipo_status"] == "sucesso"]
            )

            porcentagem_sucesso_ordens = porcentagem(
                total_sucesso_ordens,
                total_ordens
            )

            porcentagem_sucesso_ordens_anterior = porcentagem(
                total_sucesso_ordens_anterior,
                len(ordens_anterior)
            )

            variacao_sucesso = variacao_percentual(
                porcentagem_sucesso_ordens,
                porcentagem_sucesso_ordens_anterior
            )

            latencias_ordens = ordens_atual["latencia_ms"].dropna().tolist()
            latencias_ordens_anterior = ordens_anterior["latencia_ms"].dropna().tolist()

            if len(latencias_ordens) > 0:
                latencia_p95_ordens = round(np.percentile(latencias_ordens, 95), 2)
            else:
                latencia_p95_ordens = 0

            if len(latencias_ordens_anterior) > 0:
                latencia_p95_ordens_anterior = round(np.percentile(latencias_ordens_anterior, 95), 2)
            else:
                latencia_p95_ordens_anterior = 0

            variacao_latencia_p95 = variacao_percentual(
                latencia_p95_ordens,
                latencia_p95_ordens_anterior
            )

            contador_5xx = len(
                df_atual[
                    (df_atual["status_code"] >= 500) &
                    (df_atual["status_code"] <= 507)
                ]
            )

            contador_5xx_anterior = len(
                df_anterior[
                    (df_anterior["status_code"] >= 500) &
                    (df_anterior["status_code"] <= 507)
                ]
            )

            porcentagem_5xx_atual = porcentagem(
                contador_5xx,
                total_volume
            )

            porcentagem_5xx_anterior = porcentagem(
                contador_5xx_anterior,
                total_volume_anterior
            )

            variacao_5xx = variacao_percentual(
                porcentagem_5xx_atual,
                porcentagem_5xx_anterior
            )

            porcentagem_ordens = porcentagem(
                total_ordens,
                total_volume
            )

            qtd_sucesso = len(df_atual[df_atual["tipo_status"] == "sucesso"])
            qtd_erro_cliente = len(df_atual[df_atual["tipo_status"] == "erro_cliente"])
            qtd_erro_servidor = len(df_atual[df_atual["tipo_status"] == "erro_servidor"])
            qtd_sucesso = len(ordens_atual[ordens_atual["tipo_status"] == "sucesso"])
            qtd_erro_cliente = len(ordens_atual[ordens_atual["tipo_status"] == "erro_cliente"])
            qtd_erro_servidor = len(ordens_atual[ordens_atual["tipo_status"] == "erro_servidor"])

            erro_500 = len(df_atual[df_atual["status_code"] == 500])
            erro_501 = len(df_atual[df_atual["status_code"] == 501])
            erro_502 = len(df_atual[df_atual["status_code"] == 502])
            erro_503 = len(df_atual[df_atual["status_code"] == 503])
            erro_504 = len(df_atual[df_atual["status_code"] == 504])
            erro_505 = len(df_atual[df_atual["status_code"] == 505])

            dados_dashboard.append({
                "fk_empresa": 2,
                "id_servidor": 3,
                "home_broker": "SRV-DTIC-PROD",
                "timestamp": str(janela_atual),

                "total_volume": total_volume,
                "variacao_volume": variacao_volume,

                "total_ordens": total_ordens,
                "total_sucesso_ordens": total_sucesso_ordens,
                "porcentagem_sucesso_ordens": porcentagem_sucesso_ordens,
                "variacao_sucesso": variacao_sucesso,

                "latencia_p95_ordens": latencia_p95_ordens,
                "variacao_latencia_p95": variacao_latencia_p95,

                "porcentagem_ordens": porcentagem_ordens,

                "contador_5xx": contador_5xx,
                "variacao_5xx": variacao_5xx,

                "qtd_sucesso": qtd_sucesso,
                "qtd_erro_cliente": qtd_erro_cliente,
                "qtd_erro_servidor": qtd_erro_servidor,

                "erro_500": erro_500,
                "erro_501": erro_501,
                "erro_502": erro_502,
                "erro_503": erro_503,
                "erro_504": erro_504,
                "erro_505": erro_505,
                # Adicionei linha de tipo_status, onde ela pega 
                # o valor mais frequente (moda) da coluna tipo_status para aquela janela de 15 minutos, e se tiver vazia coloca None
                "tipo_status": str(df_atual["tipo_status"].mode()[0]) if not df_atual["tipo_status"].empty else None,
            })


        with open("isa.json", "w", encoding="utf-8") as f:
            json.dump(dados_dashboard, f, indent=4, default=str)

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


        print('+------------------------------------------------------------------------------+')
        print('Apurando dados para a previsão da RAM')

        df_trusted_luiz = df_raw.copy()
        df_trusted_luiz = df_trusted_luiz[['id_servidor','fk_empresa','home_broker','timestamp','ram_percent','swap_percent']]

        df_trusted_luiz['timestamp'] = pd.to_datetime(df_trusted_luiz['timestamp'], dayfirst=True, errors='coerce')
        
        # CORREÇÃO 1: Remover duplicidades temporais exatas que travam o desvio padrão em zero
        df_trusted_luiz = df_trusted_luiz.drop_duplicates(subset=['home_broker', 'timestamp'])
        df_trusted_luiz = df_trusted_luiz.sort_values(by=['home_broker', 'timestamp']).reset_index(drop=True)
        
        df_trusted_luiz['ram_percent'] = pd.to_numeric(df_trusted_luiz['ram_percent'], errors='coerce')
        df_trusted_luiz['swap_percent'] = pd.to_numeric(df_trusted_luiz['swap_percent'], errors='coerce')

        correlacoes = []
        tendencias_minuto = []
        tendencia_hora = []
        horas_registro = []
        etas = []
        projeções_futuras = []

        # Listas para guardar as contagens das faixas
        faixas_nomes = ['ram_10_20', 'ram_20_30', 'ram_30_40', 'ram_40_50', 'ram_50_60', 'ram_60_70', 'ram_70_80', 'ram_80_90', 'ram_90_100']
        historico_faixas = {nome: [] for nome in faixas_nomes}

        janela_previsao = 24

        print("Efetuando os cálculos de correlação e temporizadores")
        for i in range(len(df_trusted_luiz)):
             servidor_atual = df_trusted_luiz.loc[i, 'home_broker']
             horario_registro = df_trusted_luiz.loc[i, 'timestamp']
             ram_registro = df_trusted_luiz.loc[i, 'ram_percent']

             df_luiz = df_trusted_luiz [
                  (df_trusted_luiz['home_broker'] == servidor_atual) &
                  (df_trusted_luiz['timestamp'] <= horario_registro)
             ].tail(janela_previsao)
             
             horas_registro.append(horario_registro.strftime('%H:%M:%S') if pd.notnull(horario_registro) else None)
             
             # Cálculos estatísticos
             correlacao = calcular_correcao_movel(df_luiz)
             taxa_minuto = calcular_tendencia_ram(df_luiz)
             taxa_hora = calcular_tendencia_ram_hora(taxa_minuto)
             eta = calcular_eta_ram(ram_registro, taxa_minuto)
             predicoes = calcular_projeções_futuras(ram_registro, taxa_minuto, df_luiz)

             correlacoes.append(correlacao)
             tendencias_minuto.append(taxa_minuto)
             tendencia_hora.append(taxa_hora)
             etas.append(eta)
             projeções_futuras.append(predicoes)

             # SOLUÇÃO 2: Contagem de ocorrências por intervalo na janela móvel (últimos 24)
             # Definindo os limites (bins) e labels das faixas de 10% em 10%
             bins = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
             
             # Conta as ocorrências de RAM na janela atual usando pd.cut
             contagem_janela = pd.cut(df_luiz['ram_percent'], bins=bins, labels=faixas_nomes, right=True).value_counts()
             
             # Armazena os resultados para cada coluna correspondente
             for faixa in faixas_nomes:
                 historico_faixas[faixa].append(int(contagem_janela.get(faixa, 0)))

        # Inserindo os vetores calculados de volta ao dataframe 
        df_trusted_luiz['correlacao_ram_swap'] = correlacoes
        df_trusted_luiz['tendencia_ram_por_minuto'] = tendencias_minuto
        df_trusted_luiz['tendencia_ram_por_hora'] = tendencia_hora
        df_trusted_luiz['hora_registro'] = horas_registro
        df_trusted_luiz['ETA'] = etas

        # Adicionando as colunas de contagem ao dataframe
        for faixa in faixas_nomes:
            df_trusted_luiz[faixa] = historico_faixas[faixa]

        df_projeções = pd.DataFrame(projeções_futuras, columns=['proj1', 'proj2', 'proj3', 'proj4', 'proj5'])
        df_trusted_luiz = pd.concat([df_trusted_luiz, df_projeções], axis=1)

        print("Enviando os dados de previsão ao bucket")
        # Mantendo as suas funções originais de envio
        Salvar_s3(df_trusted_luiz, "TRUSTED/luiz_trusted.csv")
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
                # ======================================================
                # Começo Gabriel Individual
        print('+------------------------------------------------------------------------------+')
        print('Classificando Criticidade dos valores coletados')


        df_trusted_gabriel = df_raw.copy()

        df_trusted_gabriel = df_trusted_gabriel[['id_servidor','fk_empresa','home_broker','cpu_percent', 'ram_total_gb', 'ram_used_gb', 'disk_percent', 'ram_percent', 'timestamp']]

        df_trusted_gabriel['timestamp'] = pd.to_datetime(df_trusted_gabriel['timestamp'], dayfirst=True, errors='coerce')
        df_trusted_gabriel = df_trusted_gabriel.sort_values(by=['home_broker', 'timestamp']).reset_index(drop=True)
        df_trusted_gabriel['ram_total_gb'] = pd.to_numeric(df_trusted_gabriel['ram_total_gb'], errors='coerce')
        df_trusted_gabriel['ram_percent'] = pd.to_numeric(df_trusted_gabriel['ram_percent'], errors='coerce')
        df_trusted_gabriel['ram_used_gb'] = pd.to_numeric(df_trusted_gabriel['ram_used_gb'], errors='coerce')
        df_trusted_gabriel['disk_percent'] = pd.to_numeric(df_trusted_gabriel['disk_percent'], errors='coerce')
        df_trusted_gabriel['cpu_percent'] = pd.to_numeric(df_trusted_gabriel['cpu_percent'], errors='coerce')

        horas_registro = []
        cpu = []
        ram_used = []
        ram_total = []
        disk = []
        ram_percent = []
        servidor_atual = []
        status = []

        for i in range(len(df_trusted_gabriel)):
                    servidor_atual.append(df_trusted_gabriel.loc[i, 'home_broker'])
                    horas_registro.append(df_trusted_gabriel.loc[i, 'timestamp'])
                    ram_percent.append(df_trusted_gabriel.loc[i, 'ram_percent'])
                    cpu.append(df_trusted_gabriel.loc[i,'cpu_percent'])
                    ram_used.append(df_trusted_gabriel.loc[i, 'ram_used_gb'])
                    disk.append(df_trusted_gabriel.loc[i,'disk_percent'])
                    ram_total.append(df_trusted_gabriel.loc[i,'ram_total_gb'])
        resultados = buscar_medidas(a)
        print("Chamou com o nome certo ", a)
        limites = {}
        for linha in resultados:
                limites[linha['nome_componente']] = double(linha['valor_max_critico'])


        for i in range(len(df_trusted_gabriel)):
                    status_linha = "Normal"
                    if 'cpu_percent' in limites:
                        if limites['cpu_percent'] < cpu[i]:
                            status_linha = "Crítico"
                    if 'ram_percent' in limites:
                     if limites['ram_percent'] < ram_percent[i]:
                            status_linha = "Crítico"
                    if 'ram_used_gb' in limites:
                        if limites['ram_used_gb'] < (ram_total[i] - ram_used[i]):
                            status_linha = "Crítico"
                    if 'disk_percent' in limites:
                        if limites['disk_percent'] < disk[i]:
                            status_linha = "Crítico"
                    status.append(status_linha)
        df_trusted_gabriel['status'] = status

        Salvar_s3(df_trusted_gabriel, "TRUSTED/gabriel_trusted.csv")
        pd.DataFrame(df_trusted_gabriel).to_csv("gabriel_trusted.csv", encoding="utf-8", sep=";", index=False)
        df_client_gabriel = df_trusted_gabriel.copy()
        # # Garante o formato de data e remove repetições dentro do mesmo minuto

        # 1. Garante que a coluna de timestamp está no formato datetime do pandas
        df_client_gabriel['timestamp_dt'] = pd.to_datetime(df_client_gabriel['timestamp'], format='%d-%m-%Y %H:%M:%S')

        # 2. Cria uma coluna temporária APENAS para o critério do filtro (sem segundos)
        df_client_gabriel['minuto_filtro'] = df_client_gabriel['timestamp_dt'].dt.strftime('%Y-%m-%d %H:%M')

        # 3. Remove duplicatas baseando-se na coluna de minutos e gera o df_filtrado
        df_filtrado = df_client_gabriel.drop_duplicates(subset=['minuto_filtro'])

        # 3.5. Altera o formato para remover os segundos antes de apagar a coluna de apoio
        df_filtrado['timestamp'] = df_filtrado['timestamp_dt'].dt.strftime('%d-%m-%Y %H:%M')

        # 4. Remove as colunas auxiliares do df_filtrado para não irem para o JSON final
        df_filtrado = df_filtrado.drop(columns=['timestamp_dt', 'minuto_filtro'], errors='ignore')

        # 5. Converte o DF FILTRADO para dicionário (Garantindo que use o df_filtrado aqui)
        dados_gabriel = df_filtrado.astype(object).where(pd.notnull(df_filtrado), None)
        df_client_gabriel_dict = dados_gabriel.to_dict(orient="records")

        with open("gabriel.json", "w", encoding="utf-8") as f:
                json.dump(df_client_gabriel_dict, f, indent=4, default=str)

        with open("gabriel.json", "rb") as f:
                s3_client.put_object(
                Bucket=NOME_BUCKET,
                Key="CLIENT/gabriel.json",
                Body=f,
                ContentType="application/json"
                )

        print("Os dados de criticidade foram enviados ao bucket")
        print("+------------------------------------------------------------------------------+")
        # 1. Fazendo Trusted (Camada 2)

        
                # ===============================================================

         # individual gabrielly

#         print("Coletando os dados de produtividade do Jira")
#         # Busca os dados do Jira
#         print("Calculando taxa de SLA")
#         try:
#             resposta_mttr = requests.get("http://localhost:8080/api/mttr")
#             dados_mttr = resposta_mttr.json()
#             mttr_rapido = dados_mttr["maisRapido"]
#             mttr_lento  = dados_mttr["maisLento"]
#             print(f"MTTR mais rápido: {mttr_rapido}min | mais lento: {mttr_lento}min")
#         except:
#             mttr_rapido = 0
#             mttr_lento  = 0
#             print("Não foi possível buscar dados do Jira")

#         try:
#             resposta_kpis = requests.get("http://localhost:8080/api/kpis")
#             dados_kpis = resposta_kpis.json()
#             incidentes_resolvidos = dados_kpis["incidentesResolvidos"]
#         except:
#             incidentes_resolvidos = 0

#         try:
#             resposta_alertas = requests.get("http://localhost:8080/api/alertas-abertos")
#             dados_alertas = resposta_alertas.json()
#             alertas_abertos = dados_alertas["alertasAbertos"]
#         except:
#             alertas_abertos = 0

#         try:
#             resposta_sla = requests.get("http://localhost:8080/api/sla")
#             dados_sla = resposta_sla.json()
#             taxa_sla = dados_sla["taxaSla"]
#         except:
#             taxa_sla = 0

#         try:
#             resposta_membros = requests.get("http://localhost:8080/api/membros")
#             dados_membros = resposta_membros.json()
#             membros = dados_membros["membros"]
#         except:
#             membros = []

#         dados_gabrielly = {
#             "timestamp": datetime.now().strftime("%d-%m-%Y %H:%M:%S"),
#             "incidentes_resolvidos": incidentes_resolvidos,
#             "alertas_abertos": alertas_abertos,
#             "taxa_sla": taxa_sla,
#             "mttr_mais_rapido_min": mttr_rapido,
#             "mttr_mais_lento_min": mttr_lento,
#             "membros": membros
#         }

#         with open("gabrielly.json", "w", encoding="utf-8") as f:
#             json.dump(dados_gabrielly, f, indent=4, default=str)

#         with open("gabrielly.json", "rb") as f:
#             s3_client.put_object(
#                 Bucket=NOME_BUCKET,
#                 Key="CLIENT/gabrielly.json",
#                 Body=f,
#                 ContentType="application/json"
#             )
#        print("Dados de produtividade enviados ao bucket")


# # Fim Gabrielly Individual
# # ======================================================

        # Filtrando somente as colunas que eu quero pegar
        
        print("+------------------------------------------------------------------------------+")
        print("Iniciando tratamento de rede...")

        df_trusted_richard = df_raw[['id_servidor', 'home_broker', 'timestamp', 'latencia_resposta_ms', 'net_bytes_sent_gb', 'net_bytes_recv_gb', 'jitter_ms', 'packet_loss_percent', 'upload_mbps', 'download_mbps']].copy()

        # Salva o CSV na Camada do trusted localmente e no S3 (Sempre salvando o Trusted para registro)
        pd.DataFrame(df_trusted_richard).to_csv("richard.csv", encoding="utf-8", sep=";", index=False)
        Salvar_s3(df_trusted_richard, TRUSTED_RICHARD_CAMINHO)

        # 2. Fazendo Client (Camada 3 - arquivo JSON)
        # Se latencia, bytes_sent e bytes_recv forem todos nulos, o código pula o bloco abaixo
        cols_rede = ['latencia_resposta_ms', 'net_bytes_sent_gb', 'net_bytes_recv_gb', 'jitter_ms', 'packet_loss_percent', 'upload_mbps', 'download_mbps']

        nome_do_servidor = ', '.join(df_trusted_richard['home_broker'].dropna().unique().tolist())
        # Verifica se as colunas declaradas são nulas (todas no caso)
        if df_trusted_richard[cols_rede].isnull().all(axis=None):
            print(f"TRATAMENTO: O servidor {nome_do_servidor} não quer coletar dados de Rede ou deu algum erro. Pulando script de JSON.")
        else:
            print(f"Gerando arquivo JSON de Latência para: {nome_do_servidor}")
            df_client_richard = df_trusted_richard.copy()

            # Transforma qualquer NaN em 0 para o JSON não quebrar no site
            df_client_richard = df_client_richard.astype(object).where(pd.notnull(df_client_richard), 0)

            # Converte para lista de dicionários (formato JSON)
            dados_richard_json = df_client_richard.to_dict(orient='records')

            # Salva o JSON localmente
            with open('latencia_richard.json', 'w') as f:
                json.dump(dados_richard_json, f, indent=4, default=str)

            # Envia o JSON para a pasta client no S3
            print("Enviando JSON de Rede e Latêncai para o bucket...")
            with open('latencia_richard.json', 'rb') as f:
                s3_client.put_object(Bucket=NOME_BUCKET,
                                     Key=CLIENT_RICHARD_CAMINHO,
                                     Body=f,
                                     ContentType='application/json')

            print("Arquivo JSON de Rede e Latência enviado com sucesso!")
            print("+------------------------------------------------------------------------------+")
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

def calcular_tendencia_ram_hora(taxa_minuto):
     taxa_hora = taxa_minuto*60

     return round(taxa_hora, 4)

def variacao_percentual(atual, anterior):
    if anterior == 0:
        return 0

    return round(((atual - anterior) / anterior) * 100, 2)

# Agora vai iniciar a ETL
if __name__ == "__main__":
    print(f"Início do processo: {pd.Timestamp.now()}")
    ETL()
    print(f"Fim do processo: {pd.Timestamp.now()}")