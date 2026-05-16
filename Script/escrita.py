import pandas
import psutil
import time
from datetime import datetime
import pytz
import pyfiglet
import boto3
import mysql.connector
# import sys
import subprocess
import platform
import credenciais # Importa os dados do arquivo python (coloca as credencias da sua aws LÁ IMEDIATAMENTE)
import random
import subprocess
import re

requisicoes = {

    "login": [
        {
            "metodo": "POST",
            "endpoint": "/api/auth/login",
            "status_code": random.choice([200, 500, 501, 502, 503, 504, 505]),
            "latencia_ms": random.choice([120, 800, 1200, 2500, 4000])
        },
        {
            "metodo": "POST",
            "endpoint": "/api/auth/logout",
            "status_code": random.choice([200, 500, 503, 504]),
            "latencia_ms": random.choice([80, 600, 1800, 3200])
        },
        {
            "metodo": "POST",
            "endpoint": "/api/auth/refresh-token",
            "status_code": random.choice([200, 500, 502, 504]),
            "latencia_ms": random.choice([60, 500, 2000, 3500])
        },
        {
            "metodo": "POST",
            "endpoint": "/api/auth/2fa/verify",
            "status_code": random.choice([200, 401, 500, 503]),
            "latencia_ms": random.choice([150, 900, 2200])
        }
    ],

    "mercado": [
        {
            "metodo": "GET",
            "endpoint": "/api/quotes/PETR4",
            "status_code": random.choice([200, 500, 502, 504]),
            "latencia_ms": random.choice([35, 400, 1400, 3000])
        },
        {
            "metodo": "GET",
            "endpoint": "/api/quotes/VALE3",
            "status_code": random.choice([200, 500, 503]),
            "latencia_ms": random.choice([32, 350, 2500])
        },
        {
            "metodo": "GET",
            "endpoint": "/api/market/orderbook/PETR4",
            "status_code": random.choice([200, 500, 502, 503, 504, 505]),
            "latencia_ms": random.choice([90, 1200, 3200, 5000])
        },
        {
            "metodo": "GET",
            "endpoint": "/api/market/news",
            "status_code": random.choice([200, 500, 503]),
            "latencia_ms": random.choice([90, 700, 2100])
        }
    ],

    "carteira": [
        {
            "metodo": "GET",
            "endpoint": "/api/portfolio",
            "status_code": random.choice([200, 500, 503, 504]),
            "latencia_ms": random.choice([50, 600, 1900, 3400])
        },
        {
            "metodo": "GET",
            "endpoint": "/api/portfolio/performance",
            "status_code": random.choice([200, 500, 504]),
            "latencia_ms": random.choice([70, 850, 2800])
        }
    ],

    "financeiro": [
        {
            "metodo": "GET",
            "endpoint": "/api/account/balance",
            "status_code": random.choice([200, 500, 503]),
            "latencia_ms": random.choice([45, 500, 2300])
        },
        {
            "metodo": "POST",
            "endpoint": "/api/deposits",
            "status_code": random.choice([201, 500, 502, 504]),
            "latencia_ms": random.choice([180, 1200, 2600, 4200])
        }
    ],

    "orders": [
        {
            "metodo": "POST",
            "endpoint": "/api/orders/buy",
            "status_code": random.choice([201, 500, 502, 503, 504]),
            "latencia_ms": random.choice([210, 1300, 2800, 4500])
        },
        {
            "metodo": "POST",
            "endpoint": "/api/orders/sell",
            "status_code": random.choice([201, 500, 501, 503, 504, 505]),
            "latencia_ms": random.choice([250, 1600, 3200, 5000])
        },
        {
            "metodo": "DELETE",
            "endpoint": "/api/orders/cancel",
            "status_code": random.choice([200, 500, 503, 504]),
            "latencia_ms": random.choice([160, 1000, 2600])
        }
    ],

    "trades": [
        {
            "metodo": "GET",
            "endpoint": "/api/trades",
            "status_code": random.choice([200, 500, 503]),
            "latencia_ms": random.choice([95, 700, 2400])
        },
        {
            "metodo": "GET",
            "endpoint": "/api/trades/summary",
            "status_code": random.choice([200, 500, 502, 504]),
            "latencia_ms": random.choice([110, 950, 3100])
        }
    ],

    "validacao_ordens": [
        {
            "metodo": "POST",
            "endpoint": "/api/order-preview",
            "status_code": random.choice([200, 422, 500, 503]),
            "latencia_ms": random.choice([140, 800, 2200])
        },
        {
            "metodo": "POST",
            "endpoint": "/api/orders/validate",
            "status_code": random.choice([200, 422, 500, 504]),
            "latencia_ms": random.choice([170, 1200, 3000])
        }
    ],

    "risk_check": [
        {
            "metodo": "POST",
            "endpoint": "/api/risk/check",
            "status_code": random.choice([200, 500, 503, 504]),
            "latencia_ms": random.choice([130, 700, 2600, 4100])
        }
    ],

    "b3": [
        {
            "metodo": "POST",
            "endpoint": "/api/b3/orders",
            "status_code": random.choice([200, 500, 501, 502, 503, 504, 505]),
            "latencia_ms": random.choice([400, 1800, 3500, 6000])
        },
        {
            "metodo": "GET",
            "endpoint": "/api/b3/session-status",
            "status_code": random.choice([200, 500, 503, 504]),
            "latencia_ms": random.choice([85, 600, 2400])
        }
    ]
}

config = {
    'user': "root",
    'password': "Mywtty135790",
    'host': "localhost",
    'database': "noBroke" 
}

fuso_brasil = pytz.timezone('America/Sao_Paulo')


NAME_BUCKET = 's3-bucket-projeto-unico'#Vamos mudar pra um nome do projeto

s3_client = boto3.client(
    's3',
    aws_access_key_id = credenciais.AWS_ACCESS_KEY,
    aws_secret_access_key = credenciais.AWS_SECRET_KEY,
    aws_session_token = credenciais.AWS_SESSION_TOKEN
)

resultados = {
    "id_servidor":[],
    "home_broker":[],
    "timestamp": [],
    "cpu_percent":[], 
    "cpu_freq_current":[], 
    "cpu_time_idle": [],
    "ram_total_gb": [],
    "ram_available_gb":[],
    "ram_used_gb": [],
    "ram_percent": [],
    "swap_percent": [],
    "swap_used_gb": [],
    "swap_free_gb": [],
    "disk_percent": [],
    "disco_taxa_transferencia": [], #quantidade de dados transferidos por segundo
    "latencia_resposta_ms":[],
    "net_bytes_sent_gb":[],
    "net_bytes_recv_gb":[],
    "total_processos":[],
    "processo_maior_consumo":[],
    "metodo": [],
    "endpoint": [],
    "status_code": [],
    "latencia_ms": []
}

def GerarRequisicao():
    lista_requisicoes_feitas = []

    for i in range(10):
        categoria = random.choice(list(requisicoes.keys()))
        requisicao = random.choice(requisicoes[categoria])
        lista_requisicoes_feitas.append(requisicao)

    return lista_requisicoes_feitas

def buscar_idServidor(nome_servidor):
    try:
        conn = mysql.connector.connect(**config) # Tenta fazer uma conexão com as "**config" (credenciais) que demos
        cursor = conn.cursor(dictionary=True) # Cria um "executor" de comandos SQL
        # dictionary=True faz retornar dados como dicionário: {'coluna': 'valor'}
        # Sem isso, retornaria tupla: ('valor1', 'valor2')


        # Aqui está o comando que irá fazer quando se conectar
        query = """
            SELECT id_servidor FROM servidor WHERE nome = %s;
        """

        # Realiza a função de conexão passando a query (oque é pra buscar) e o nome do servidor que fica no %s
        cursor.execute(query, (nome_servidor,))
        resultado = cursor.fetchone() # Pega todos os resultados que achar
        
        # Fecha a conexão e retorna o que achou de maneira bruta
        cursor.close()
        conn.close()

        if resultado:
            return resultado['id_servidor']
        else:
            print(f"Servidor '{nome_servidor}' não foi encontrado no Banco de Dados!")
            return None
        
    except mysql.connector.Error as erro:
        print(f"Erro MySQL: {erro}")
        return None
    except Exception as erro:
        print(f"Erro: {erro}")
        return None

def conversao_gb(valor: float):
    return valor/ (1024 ** 3)
def conversao_mb(valor: float):
    return valor/ (1024 ** 2)

def coletar_cpu_percent():
    return round(psutil.cpu_percent(interval=1),2)


def coletar_cpu_freq_current():
    cpu = psutil.cpu_freq()
    return round(cpu.current,2)

def coletar_cpu_time_idle():
    tempos = psutil.cpu_times_percent()
    return round(tempos.idle,2)

def coletar_virtual_memory_total_gb(): #ok
    memoria = psutil.virtual_memory()
    return round(conversao_gb(memoria.total),2)

def coletar_virtual_memory_available_gb():#OK
    memoria = psutil.virtual_memory()
    return round(conversao_gb(memoria.available),2)

def coletar_virtual_memory_used_gb():# OK
    memoria = psutil.virtual_memory()
    return round(conversao_gb(memoria.used),2)

def coletar_virtual_memory_percent():
    memoria = psutil.virtual_memory()
    return round(memoria.percent,2)

def coletar_swap_used_gb():
    swap = psutil.swap_memory()
    return round(conversao_gb(swap.used),2)

def coletar_swap_free_gb():
    swap = psutil.swap_memory()
    return round(conversao_gb(swap.free),2)

def coletar_swap_percent():
     swap = psutil.swap_memory()
     return round(swap.percent,2)

def coletar_disk_percent():
    part = psutil.disk_partitions()[0].mountpoint
    disco = psutil.disk_usage(part)
    return round(disco.percent,2)

def coletar_disk_free_gb():
    part = psutil.disk_partitions()[0].mountpoint
    disco = psutil.disk_usage(part)
    return round(conversao_gb(disco.free),2)

def coletar_taxa_transferencia():
    disco = []
    disco.append(psutil.disk_io_counters())
    time.sleep(1)
    disco.append(psutil.disk_io_counters())

    read_disco = disco[1].read_bytes - disco[0].read_bytes
    write_disco = disco[1].write_bytes - disco[0].write_bytes
    taxa_transferencia = round(conversao_mb(read_disco+write_disco),2)
    return (taxa_transferencia)

def coletar_net_packets_sent():
    rede = psutil.net_io_counters()
    return round(conversao_mb(rede.packets_sent),2)

def coletar_net_packets_recv():
    rede = psutil.net_io_counters()
    return round(conversao_mb(rede.packets_recv),2)

def coletar_total_processos():
    return round(len(psutil.pids()),2)

def coletar_latencia_resposta_ms():
    try:
        param = "-n" if platform.system().lower() == "windows" else "-c" # Verifica o sistema operacional do
        resultado = subprocess.run(
            ["ping", param, "1", "104.18.43.121"],
            capture_output=True, # faz o resultado ser capturado no .stdout da linha 243
            text=True, # transforma em String ao invés de byte
            timeout=2 # Timeout de 2s
            )
        if resultado.returncode != 0:
            return 0.0

        linhas = resultado.stdout.lower().replace("<", "=")
        linhas = linhas.split("\n")
        for linha in linhas:
               if "tempo=" in linha or "time=" in linha:
                    chave = "tempo=" if "tempo=" in linha else "time="
                    parte_valor = linha.split(chave)[1]
                    valor_final = parte_valor.split("ms")[0].strip().split(" ")[0].replace(",", ".")
                    return round(float(valor_final), 2)
    except FileNotFoundError:
        print("Comando 'Ping' não tem no Sistema. Baixar os pacotes")
        return 0.0
    except Exception as e:
        print(f"Erro ao pegar a Latência: {e}")
        return 0.0

    return 0.0

# Função pra achar o programa que tá usando mais CPU agora.
# Resolve o problema de pegar 0% ou pegar o processo fantasma do sistema (Idle)
def pid_consumindo_mais():
    processo_maisConsome = "Nenhum"
    cpu_max = -1

    # Lista de Todos os Processos
    processos = []
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            # No psutil, a primeira vez que tu pede a CPU de um processo ele SEMPRE devolve 0.0
            # Ele precisa dessa primeira chamada pra criar um ponto de partida (baseline)
            proc.cpu_percent(None)
            processos.append(proc)  # Add na lista pra verificar jajá
        except:
            # Se o processo fechar do nada ou der acesso negado, ignora e segue a vida
            continue

    # Tempo (100 milissegundos) pro PC rodar as coisas
    # Sem essa pausa, a diferença de tempo seria zero e ia dar 0% de novo
    time.sleep(0.1)

    # PASSO 3: Passa na lista de novo pegando a porcentagem VERDADEIRA agora que passou um tempo
    for proc in processos:
        try:
            # Segunda chamada: agora sim ele calcula o quanto consumiu naqueles 0.1 segundos
            cpu = proc.cpu_percent(None)

            # proc.pid == 0: Ignora a Ociosidade do Sistema.
            # No Windows/Linux, o PID 0 representa a CPU que NÃO tá sendo usada.
            # Se tu não pular ele, o sistema ocioso sempre ganha como "maior consumidor".
            # cpu <= 0: Pula também quem não tá consumindo nada.
            if proc.pid == 0 or cpu <= 0:
                continue

            # Se esse cara consumiu mais que o antigo vencedor, toma o trono
            if cpu > cpu_max:
                cpu_max = cpu
                processo_maisConsome = (
                    f"{proc.info['name']} (PID: {proc.pid}) - {cpu}%"
                )
        except:
            continue

    # Retorna a string bonita pronta pra ir pro Banco/S3
    return processo_maisConsome

def print_barra(Componente, nomeComponente, metrica, limite_barra, numDivisao):
    calculo_total_barras = int(limite_barra * (Componente/numDivisao))
    return f"{nomeComponente} [{'■'* calculo_total_barras}{" "*(limite_barra - calculo_total_barras)}] {Componente}{metrica}"





nome_servidor = "luiz"
id_servidor = buscar_idServidor(nome_servidor)

# Verificar se o id_Servidor existe
if id_servidor is None:
    print(f"Erro ao capturar o id_servidor que retornou Nulo/Nenhum do Banco")
    print("Cadastre o Servidor com mesmo nome da máquina para a Coleta")
    exit()



memoria_total = round(conversao_gb(psutil.virtual_memory().total),2)
data_arquivo = datetime.now().strftime("%d-%m-%Y")

print(f"HORÁRIO AGORA = {datetime.now().strftime("%d/%m/%Y %H:%M")}")
print(pyfiglet.figlet_format("n0Broke-Script")) 

NAME_CSV = f"Raw_{nome_servidor}-{data_arquivo}.csv"

for i in range(1, 41):

    horario_atual = datetime.now()
    horario_tratado = datetime.strftime(horario_atual, "%d-%m-%Y %H:%M:%S")
    cpu_porcentagem = coletar_cpu_percent()
    cpu_frequencia_atual = coletar_cpu_freq_current()
    cpu_tempo_ocioso = coletar_cpu_time_idle()
    ram_total = coletar_virtual_memory_total_gb()
    ram_available = coletar_virtual_memory_available_gb()
    ram_used = coletar_virtual_memory_used_gb()
    ram_percent = coletar_virtual_memory_percent()
    swap_percent = coletar_swap_percent()
    swap_used = coletar_swap_used_gb()
    swap_free = coletar_swap_free_gb()
    disk_percent = coletar_disk_percent()
    disco_taxa_transferencia = coletar_taxa_transferencia()
    latencia_resposta = coletar_latencia_resposta_ms()
    net_bytes_sent = coletar_net_packets_sent()
    net_bytes_recv = coletar_net_packets_recv()
    total_processos = coletar_total_processos()
    pid_mais_consumista = pid_consumindo_mais()
    requisicoes_geradas = GerarRequisicao()

    for requisicao in requisicoes_geradas:

        resultados["id_servidor"].append(id_servidor)
        resultados["home_broker"].append(nome_servidor)
        resultados["timestamp"].append(horario_tratado)
        resultados["cpu_percent"].append(cpu_porcentagem)
        resultados["cpu_freq_current"].append(cpu_frequencia_atual)
        resultados["cpu_time_idle"].append(cpu_tempo_ocioso)
        resultados["ram_total_gb"].append(ram_total)
        resultados["ram_available_gb"].append(ram_available)
        resultados["ram_used_gb"].append(ram_used)
        resultados["ram_percent"].append(ram_percent)
        resultados["swap_percent"].append(swap_percent)
        resultados["swap_used_gb"].append(swap_used)
        resultados["swap_free_gb"].append(swap_free)
        resultados["disk_percent"].append(disk_percent)
        resultados["disco_taxa_transferencia"].append(disco_taxa_transferencia)
        resultados["latencia_resposta_ms"].append(latencia_resposta)
        resultados["net_bytes_sent_gb"].append(net_bytes_sent)
        resultados["net_bytes_recv_gb"].append(net_bytes_recv)
        resultados["total_processos"].append(total_processos)
        resultados["processo_maior_consumo"].append(pid_mais_consumista)
        resultados["metodo"].append(requisicao["metodo"])
        resultados["endpoint"].append(requisicao["endpoint"])
        resultados["status_code"].append(requisicao["status_code"])
        resultados["latencia_ms"].append(requisicao["latencia_ms"])

    print(f"""
          +------------------------------------------------------------------------------+
                !--------IDENTIFICAÇÃO DO HOME BROKER---------!
                                 {nome_servidor}
                !--------DADOS DA CPU---------!
                {print_barra(resultados['cpu_percent'][len(resultados['cpu_percent'])-1], "Uso CPU Total", "%", 20, 100)}
                {print_barra(resultados['cpu_freq_current'][len(resultados['cpu_freq_current'])-1], "Frequência CPU", "MHz", 20, 5000)}
                {print_barra(resultados['cpu_time_idle'][len(resultados['cpu_freq_current'])-1], "Tempo CPU Ociosa", "s", 10, 100)}
                !--------DADOS DA RAM---------!
                {print_barra(resultados['ram_total_gb'][len(resultados['ram_total_gb'])-1], "Uso Memória Total", "%", 10, 100)}
                {print_barra(resultados['ram_available_gb'][len(resultados['ram_available_gb'])-1], "Memória Disponível", "GB", 10, memoria_total)}
                {print_barra(resultados['ram_used_gb'][len(resultados['ram_used_gb'])-1], "Memória Usada", "GB", 10, memoria_total)}
                {print_barra(resultados['ram_percent'][len(resultados['ram_percent'])-1], "Uso Memória Total", "%", 10, 100)}
                {print_barra(resultados['swap_percent'][len(resultados['swap_percent'])-1], "Uso Swap Total", "%", 10, 100)}
                {print_barra(resultados['swap_used_gb'][len(resultados['swap_used_gb'])-1], "Swap Usada", "GB", 10, memoria_total)}
                {print_barra(resultados['swap_free_gb'][len(resultados['swap_free_gb'])-1], "Swap Livre", "GB", 10, memoria_total)}

                !--------DADOS DO DISCO---------!
                {print_barra(resultados['disk_percent'][len(resultados['disk_percent'])-1], "Uso Disco Total", "%", 10, 100)}
                {print_barra(resultados['disco_taxa_transferencia'][len(resultados['disco_taxa_transferencia'])-1], "taxa_transferencia do Disco", "MB/s", 10, 500)}   
                {print_barra(resultados['latencia_resposta_ms'][len(resultados['latencia_resposta_ms'])-1], "Latência de Resposta", "ms", 10, 1000)}
                {print_barra(resultados['net_bytes_sent_gb'][len(resultados['net_bytes_sent_gb'])-1], "Bytes Enviados", "GB", 10, 100)}
                {print_barra(resultados['net_bytes_recv_gb'][len(resultados['net_bytes_recv_gb'])-1], "Bytes Recebidos", "GB", 10, 100)}

                !--------PROCESSOS ATIVOS ---------!
                {print_barra(resultados["total_processos"][len(resultados['total_processos'])-1], "Processos Ativos", "qtd", 10, 200)}
                Processo de maior consumo - { resultados["processo_maior_consumo"][len(resultados['processo_maior_consumo'])-1]}



         +------------------------------------------------------------------------------+
          """)
    pandas.DataFrame(resultados).to_csv(NAME_CSV, encoding="utf-8", sep=";", index=False)

    try:
        s3_client.upload_file(NAME_CSV, NAME_BUCKET,f'RAW/{NAME_CSV}')
        print(f'Dados enviados ao bucket')
    except:
           print(f'Problema no envio dos dados para o bucket')
    time.sleep(5)


