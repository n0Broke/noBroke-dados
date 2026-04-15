import pandas
import psutil
import time
from datetime import datetime
import pytz
import pyfiglet
import boto3
# import sys
import subprocess
import platform

fuso_brasil = pytz.timezone('America/Sao_Paulo')


NAME_BUCKET = 's3-bucket-projeto-unico'#Vamos mudar pra um nome do projeto

s3_client = boto3.client(
    's3',
    #COLOCAR AS CREDENCIAIS AQUI, 
    #!!!!!!!!!!!!!ATENÇÃO!!!!!!!!!!!!!!
    # NÃO COMITE AS CREDENDIACIS DA AWS
)

resultados = {
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
    "disco_throughput": [], #quantidade de dados transferidos por segundo
    "latencia_resposta_ms":[],
    "net_bytes_sent_gb":[],
    "net_bytes_recv_gb":[],
    "total_processos":[],
    "processo_maior_consumo":[]
}

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
    disco = psutil.disk_usage('/')
    return round(disco.percent,2)

def coletar_disk_free_gb():
    disco = psutil.disk_usage('/')
    return round(conversao_gb(disco.free),2)

def coletar_throughput():
    disco = []
    disco.append(psutil.disk_io_counters())
    time.sleep(1)
    disco.append(psutil.disk_io_counters())

    read_disco = disco[1].read_bytes - disco[0].read_bytes
    write_disco = disco[1].write_bytes - disco[0].write_bytes
    throughput = round(conversao_mb(read_disco+write_disco),2)
    return (throughput)

def coletar_net_packets_sent():
    rede = psutil.net_io_counters()
    return round(conversao_mb(rede.packets_sent),2)

def coletar_net_packets_recv():
    rede = psutil.net_io_counters()
    return round(conversao_mb(rede.packets_recv),2)

def coletar_total_processos():
    return round(len(psutil.pids()),2)

def coletar_latencia_resposta_ms():
        #https://www.fromdev.com/2024/10/how-to-use-python-subprocess-ping-with-ip-addresses-and-servers.html
        # como usar a biblioteca "subprocess" e pegar o ping em ms
        param = "-n" if platform.system().lower() == "windows" else "-c" # Verifica o sistema operacional do computador
        resultado = subprocess.run(
            ["ping", param, "1", "127.0.0.1"],
            capture_output=True, # faz o resultado ser capturado no .stdout da linha 243
            text=True, # transforma em String ao invés de byte
        )
        linhas = resultado.stdout.split("\n")
        for linha in linhas:
            if "time=" in linha:
                tempo_str = linha.split("time=")[1].split(" ")[0]
                return round(float(tempo_str), 2)
            elif "tempo=" in linha:
                tempo_str = linha.split("tempo=")[1].split("ms")[0].strip()
                return round(float(tempo_str), 2)
        return 0.0

def pid_consumindo_mais():
    processo_daVez = "Nenhum"
    cpu_max = -1
    
 
    for processo in psutil.process_iter(['pid', 'name', 'cpu_percent']):
        try:
            cpu_percent = processo.info['cpu_percent']
            
            if cpu_percent is not None and cpu_percent > cpu_max:
                cpu_max = cpu_percent
                processo_daVez = f"{processo.info['name']} (PID: {processo.info['pid']}) - {cpu_percent}%"
        
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
            
    return processo_daVez

def print_barra(Componente, nomeComponente, metrica, limite_barra, numDivisao):
    calculo_total_barras = int(limite_barra * (Componente/numDivisao))
    return f"{nomeComponente} [{'■'* calculo_total_barras}{" "*(limite_barra - calculo_total_barras)}] {Componente}{metrica}"



nome_servidor = psutil.users()[0].name
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
    disco_throughput = coletar_throughput()
    latencia_resposta = coletar_latencia_resposta_ms()
    net_bytes_sent = coletar_net_packets_sent()
    net_bytes_recv = coletar_net_packets_recv()
    total_processos = coletar_total_processos()
    pid_mais_consumista = pid_consumindo_mais()


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
    resultados["disco_throughput"].append(disco_throughput)
    resultados["latencia_resposta_ms"].append(latencia_resposta)
    resultados["net_bytes_sent_gb"].append(net_bytes_sent)
    resultados["net_bytes_recv_gb"].append(net_bytes_recv)
    resultados["total_processos"].append(total_processos)
    resultados["processo_maior_consumo"].append(pid_mais_consumista)

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
                {print_barra(resultados['disco_throughput'][len(resultados['disco_throughput'])-1], "Throughput do Disco", "MB/s", 10, 500)}   
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


