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
            "status_codes": [200, 500, 501, 502, 503, 504, 505]
        },
        {
            "metodo": "POST",
            "endpoint": "/api/auth/logout",
            "status_codes": [200, 500, 503, 504]
        }
    ],

    "orders": [
        {
            "metodo": "POST",
            "endpoint": "/api/orders/buy",
            "status_codes": [201, 500, 502, 503, 504]
        },
        {
            "metodo": "POST",
            "endpoint": "/api/orders/sell",
            "status_codes": [201, 500, 501, 503, 504, 505]
        },
        {
            "metodo": "DELETE",
            "endpoint": "/api/orders/cancel",
            "status_codes": [200, 500, 503, 504]
        }
    ]
}

config = {
    'user': "root",
    'password':"",
    'host': "localhost",
    'database': "noBroke" 
}

fuso_brasil = pytz.timezone('America/Sao_Paulo')


NAME_BUCKET = 'buckettestenobroke' #Vamos mudar pra um nome do projeto

s3_client = boto3.client(
    's3',
    aws_access_key_id = "",
    aws_secret_access_key = "",
    aws_session_token = ""
    )

resultados = {
    "fk_empresa": [],
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
    "latencia_ms": [],
    "jitter_ms": [],
    "packet_loss_percent": [],
    "upload_mbps": [],
    "download_mbps": []
}

def GerarRequisicao():
    todas_requisicoes = []

    for categoria in requisicoes:
        for req in requisicoes[categoria]:

            requisicao = {
                "metodo": req["metodo"],
                "endpoint": req["endpoint"],
                "status_code": random.choice(req["status_codes"])
            }

            todas_requisicoes.append(requisicao)

    quantidade = random.randint(5, 15)

    lista_requisicoes = random.choices(
        todas_requisicoes,
        k=quantidade
    )

    return lista_requisicoes

def buscar_fkEmpresa(nome_servidor):
    try:
        conn = mysql.connector.connect(**config) # Tenta fazer uma conexão com as "**config" (credenciais) que demos
        cursor = conn.cursor(dictionary=True) # Cria um "executor" de comandos SQL
        # dictionary=True faz retornar dados como dicionário: {'coluna': 'valor'}
        # Sem isso, retornaria tupla: ('valor1', 'valor2')


        # Aqui está o comando que irá fazer quando se conectar
        query = """
            SELECT fk_empresa FROM servidor WHERE nome = %s;
        """

        # Realiza a função de conexão passando a query (oque é pra buscar) e o nome do servidor que fica no %s
        cursor.execute(query, (nome_servidor,))
        resultado = cursor.fetchone() # Pega todos os resultados que achar
        
        # Fecha a conexão e retorna o que achou de maneira bruta
        cursor.close()
        conn.close()

        if resultado:
            return resultado['fk_empresa']
        else:
            print(f"Servidor '{nome_servidor}' não foi encontrado no Banco de Dados!")
            return None
        
    except mysql.connector.Error as erro:
        print(f"Erro MySQL: {erro}")
        return None
    except Exception as erro:
        print(f"Erro: {erro}")
        return None

def buscar_idServidor(nome_servidor,):
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

def coletar_net_bytes_sent():
    rede = psutil.net_io_counters()
    return round(conversao_mb(rede.bytes_sent),2)

def coletar_net_bytes_recv():
    rede = psutil.net_io_counters()
    return round(conversao_mb(rede.bytes_recv),2)

def coletar_total_processos():
    return round(len(psutil.pids()),2)

def coletar_metricas_rede(host="104.18.43.121", qtd_pings=5):
    # Utiliza o Ping definido como do HomeBreaker
    # Faz múltiplos pings e retorna latência média, jitter e perda de pacotes.
    
    # Tenta acessar o tipo de SO para usar o comando ping correto (Windows usa -n, Linux/Mac usa -c)
    try:
        sistema = platform.system().lower()
        param_count = "-n" if sistema == "windows" else "-c"
        
        # Executa o comando de Ping e vê a saída em ms, exemplo: "time=23ms" ou "tempo=23ms"
        resultado = subprocess.run(
            ["ping", param_count, str(qtd_pings), host],
            capture_output=True,
            text=True,
            timeout=qtd_pings + 5
        )
        
        # Deixa a saída minúscula e substitui "<" por "=" (afinal o ms n é exato mas tratamos como exato)
        output = resultado.stdout.lower().replace("<", "=")
        
        # Extrai todos os tempos de resposta (regex pega "time=XX" ou "tempo=XX")
        # Resumindo: Ele procura na saída do ping por qualquer coisa que seja "time=23ms" ou "tempo=23ms" e pega o número 23 (pode ser decimal também)
        tempos = re.findall(r"(?:time|tempo)=([\d,\.]+)", output)
        tempos = [float(t.replace(",", ".")) for t in tempos]
        
        # Se não tiver pego tempo, retorna 000 em tudo e 100% de perda de pacote
        if not tempos:
            return {"latencia": 0.0, "jitter": 0.0, "packet_loss": 100.0}
        
        # Cálculo Latência Média
        latencia_media = round(sum(tempos) / len(tempos), 2)
        
        # Cálculo do jitter (média das diferenças absolutas entre pings consecutivos)
        # Como é calculado: Ele pega a diferença entre cada ping e o anterior, tira o valor absoluto (pra não ter número negativo) 
        # e depois faz a média dessas diferenças. Isso mostra o quanto os tempos de resposta variam entre si. (verifica se o tempo é maior que 1)
        if len(tempos) > 1:
            diferencas = [abs(tempos[i] - tempos[i-1]) for i in range(1, len(tempos))]
            jitter = round(sum(diferencas) / len(diferencas), 2)
        else:
            jitter = 0.0
        
        # Cálculo de Perda de Pacotes
        # Cálculo: (quantidade de pings enviados - quantidade de pings recebidos) / quantidade de pings enviados * 100 arredondado em 2 casa decimal
        pacotes_recebidos = len(tempos)
        packet_loss = round(((qtd_pings - pacotes_recebidos) / qtd_pings) * 100, 2)
        
        # Retorna todos os resultados
        return {
            "latencia": latencia_media,
            "jitter": jitter,
            "packet_loss": packet_loss
        }
        
        # Se não, retorna tudo zerado
    except Exception as e:
        print(f"Erro ao coletar métricas de rede: {e}")
        return {"latencia": 0.0, "jitter": 0.0, "packet_loss": 0.0}
    
def coletar_banda_rede():
    # Mede a banda usada em MB/s (download e upload separados).
    
    rede_antes = psutil.net_io_counters()
    time.sleep(1)
    rede_depois = psutil.net_io_counters()
    
    # Diferença em bytes durante 1 segundo = bytes por segundo
    bytes_enviados = rede_depois.bytes_sent - rede_antes.bytes_sent
    bytes_recebidos = rede_depois.bytes_recv - rede_antes.bytes_recv
    
    # Converte para MB/s
    upload_mbps = round(conversao_mb(bytes_enviados), 4)
    download_mbps = round(conversao_mb(bytes_recebidos), 4)
    banda_total = round(upload_mbps + download_mbps, 4)
    
    return {
        "upload_mbps": upload_mbps,
        "download_mbps": download_mbps,
        "banda_total": banda_total
    }

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




nome_servidor = "NB1-luiz"
fk_empresa = buscar_fkEmpresa(nome_servidor)
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
    # Minhas coletas de rede
    metricas_rede = coletar_metricas_rede(qtd_pings=5)
    latencia_resposta = metricas_rede["latencia"]
    jitter_atual = metricas_rede["jitter"]
    packet_loss_atual = metricas_rede["packet_loss"]
    banda = coletar_banda_rede()
    upload_atual = banda["upload_mbps"]
    download_atual = banda["download_mbps"]
    net_bytes_sent = coletar_net_bytes_sent()
    net_bytes_recv = coletar_net_bytes_recv()
    # _________________________________________
    total_processos = coletar_total_processos()
    pid_mais_consumista = pid_consumindo_mais()
    requisicoes_geradas = GerarRequisicao()


    for requisicao in requisicoes_geradas:
        resultados["fk_empresa"].append(fk_empresa)
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
        resultados["latencia_ms"].append(latencia_resposta)
        resultados["jitter_ms"].append(jitter_atual)
        resultados["packet_loss_percent"].append(packet_loss_atual)
        resultados["upload_mbps"].append(upload_atual)
        resultados["download_mbps"].append(download_atual)

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

                !--------DADOS DE REDE---------!
                {print_barra(latencia_resposta, "Latência", "ms", 10, 1000)}
                {print_barra(jitter_atual, "Jitter", "ms", 10, 100)}
                {print_barra(packet_loss_atual, "Perda Pacotes", "%", 10, 100)}
                {print_barra(upload_atual, "Upload", "MB/s", 10, 100)}
                {print_barra(download_atual, "Download", "MB/s", 10, 100)}



         +------------------------------------------------------------------------------+
          """)
    pandas.DataFrame(resultados).to_csv(NAME_CSV, encoding="utf-8", sep=";", index=False)

    try:
        s3_client.upload_file(NAME_CSV, NAME_BUCKET,f'RAW/{NAME_CSV}')
        print(f'Dados enviados ao bucket')
    except:
           print(f'Problema no envio dos dados para o bucket')
    time.sleep(5)


