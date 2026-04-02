import pandas
import psutil
import json
import csv
import time
from datetime import datetime
import pytz
import pyfiglet
# import sys
import subprocess
import platform

fuso_brasil = pytz.timezone('America/Sao_Paulo')


resultados = {
    "timestamp": [],
    "home_broker":[],
    "cpu_percent":[], 
    "cpu_freq_current":[], 
    "cpu_time_idle": [],
    "ram_total_gb": [],
    "ram_available_gb":[],
    "ram_used_gb": [],
    "ram_free_gb":[],
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
}
# with open("banco.json", "r", encoding="utf-8") as file:
#     dados = json.load(file)

def conversao_gb(valor: float):
    return valor/ (1024 ** 3)
def conversao_mb(valor: float):
    return valor/ (1024 ** 2)

def coletar_cpu_percent():
    return round(psutil.cpu_percent(interval=1),2)

# def coletar_cpu_count_logical():
#     return round(psutil.cpu_count(),2)

# def coletar_cpu_count_physical():
#     return round(psutil.cpu_count(logical=False),2)

def coletar_cpu_freq_current():
    cpu = psutil.cpu_freq()
    return round(cpu.current,2)

# def coletar_cpu_freq_min():
#     cpu = psutil.cpu_freq()
#     return round(cpu.min,2)

# def coletar_cpu_freq_max():
#     cpu = psutil.cpu_freq()
#     return round(cpu.max,2)

# def coletar_cpu_ctx_switches():
#     stats = psutil.cpu_stats()
#     return round(stats.ctx_switches,2)

# def coletar_cpu_interrupts():
#     stats = psutil.cpu_stats()
#     return round(stats.interrupts,2)

# def coletar_cpu_soft_interrupts():
#     stats = psutil.cpu_stats()
#     return round(stats.soft_interrupts,2)

# def coletar_cpu_syscalls():
#     stats = psutil.cpu_stats()
#     return round(stats.syscalls,2)

# def coletar_cpu_time_user():
#     tempos = psutil.cpu_times()
#     return round(tempos.user,2)

# def coletar_cpu_time_system():
#     tempos = psutil.cpu_times()
#     return round(tempos.system,2)

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

def coletar_virtual_memory_free_gb(): #OK
    memoria = psutil.virtual_memory()
    return round(conversao_gb(memoria.free),2)

def coletar_virtual_memory_percent():
    memoria = psutil.virtual_memory()
    return round(memoria.percent,2)

# def coletar_virtual_memory_active_gb():
#     memoria = psutil.virtual_memory()
#     return round(conversao_gb(memoria.active),2)

# def coletar_virtual_memory_inactive_gb():
#     memoria = psutil.virtual_memory()
#     return round(conversao_gb(memoria.inactive),2)

# def coletar_virtual_memory_buffers_gb():
#     memoria = psutil.virtual_memory()
#     return round(conversao_gb(memoria.buffers),2)

# def coletar_virtual_memory_cached_gb():
#     memoria = psutil.virtual_memory()
#     return round(conversao_gb(memoria.cached),2)

# def coletar_swap_total_gb():
#     swap = psutil.swap_memory()
#     return round(conversao_gb(swap.total),2)

def coletar_swap_used_gb():
    swap = psutil.swap_memory()
    return round(conversao_gb(swap.used),2)

def coletar_swap_free_gb():
    swap = psutil.swap_memory()
    return round(conversao_gb(swap.free),2)

def coletar_swap_percent():
     swap = psutil.swap_memory()
     return round(swap.percent,2)

# def coletar_swap_sin_gb():
#     swap = psutil.swap_memory()
#     return round(conversao_gb(swap.sin),2)

# def coletar_swap_sout_gb():
#     swap = psutil.swap_memory()
#     return round(conversao_gb(swap.sout),2)

def coletar_disk_percent():
    disco = psutil.disk_usage('/')
    return round(disco.percent,2)

# def coletar_disk_total_gb():
#     disco = psutil.disk_usage('/')
#     return round(conversao_gb(disco.total),2)

# def coletar_disk_used_gb():
#     disco = psutil.disk_usage('/')
#     return round(conversao_gb(disco.used),2)

def coletar_disk_free_gb():
    disco = psutil.disk_usage('/')
    return round(conversao_gb(disco.free),2)

# def coletar_disk_read_count():
#     disco = psutil.disk_io_counters()
#     return round(conversao_gb(disco.read_count),2) # adicionei a conversão pra manter o padrão

# def coletar_disk_write_count():
#     disco = psutil.disk_io_counters()
#     return round(disco.write_count,2)

def coletar_throughput():
    disco = []
    disco.append(psutil.disk_io_counters())
    time.sleep(1)
    disco.append(psutil.disk_io_counters())

    read_disco = disco[1].read_bytes - disco[0].read_bytes
    write_disco = disco[1].write_bytes - disco[0].write_bytes
    throughput = round(conversao_mb(read_disco+write_disco),2)
    return (throughput)


# def coletar_disk_read_bytes_gb(parametros):
#     disco = psutil.disk_io_counters()
#     return round(conversao_gb(disco.read_bytes),2)

# def coletar_disk_write_bytes_gb(parametros):
#     disco = psutil.disk_io_counters()
#     return round(conversao_gb(disco.write_bytes),2)

# def coletar_disk_read_time(parametros):
#     disco = psutil.disk_io_counters()
#     return round(disco.read_time,2)

# def coletar_disk_write_time(parametros):
#     disco = psutil.disk_io_counters()
#     return round(disco.write_time,2)

# def coletar_net_bytes_sent_gb(parametros):
#     rede = psutil.net_io_counters()
#     return round(conversao_gb(rede.bytes_sent),2)

# def coletar_net_bytes_recv_gb(parametros):
#     rede = psutil.net_io_counters()
#     return round(conversao_gb(rede.bytes_recv),2)

def coletar_net_packets_sent():
    rede = psutil.net_io_counters()
    return round(conversao_mb(rede.packets_sent),2)

def coletar_net_packets_recv():
    rede = psutil.net_io_counters()
    return round(conversao_mb(rede.packets_recv),2)

# def coletar_net_errin(parametros):
#     rede = psutil.net_io_counters()
#     return round(rede.errin,2)

# def coletar_net_errout(parametros):
#     rede = psutil.net_io_counters()
#     return round(rede.errout,2)

# def coletar_net_dropin(parametros):
#     rede = psutil.net_io_counters()
#     return round(rede.dropin,2)

# def coletar_net_dropout(parametros):
#     rede = psutil.net_io_counters()
#     return round(rede.dropout,2)

def coletar_total_processos():
    return round(len(psutil.pids()),2)

# def coletar_usuarios_logados(parametros):
#     return round(len(psutil.users()),2)

# def coletar_boot_time(parametros):
#     return round(psutil.boot_time(),2)

# def coletar_uptime_segundos(parametros):
#     return round(time.time() - psutil.boot_time(),2)

# def coletar_uptime_minutos(parametros):
#     return round((time.time() - psutil.boot_time())/60,2)

# def coletar_uptime_horas(parametros):
#     return round((time.time() - psutil.boot_time())/3600,2)

# def coletar_total_particoes(parametros):
#     particoes = psutil.disk_partitions()
#     return round(len(particoes),2)

# def coletar_total_conexoes(parametros):
#     conexoes = psutil.net_connections()
#     return round(len(conexoes),2)

# def coletar_bateria_percent(parametros):
#     bateria = psutil.sensors_battery()
#     return round(bateria.percent,2)

# def coletar_bateria_plugada(parametros):
#     bateria = psutil.sensors_battery()
#     return round(bateria.power_plugged,2)

# def coletar_bateria_segundos_restantes(parametros):
#     bateria = psutil.sensors_battery()
#     return round(bateria.secsleft,2)

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
            
def print_barra(Componente, nomeComponente, metrica, limite_barra, numDivisao):
    calculo_total_barras = int(limite_barra * (Componente/numDivisao))
    return f"{nomeComponente} [{'■'* calculo_total_barras}{" "*(limite_barra - calculo_total_barras)}] {Componente}{metrica}"

# coletores = {
# "cpu_percent": coletar_cpu_percent,
# # "cpu_count_logical": coletar_cpu_count_logical,
# # "cpu_count_physical": coletar_cpu_count_physical,
# "cpu_freq_current": coletar_cpu_freq_current,
# # "cpu_freq_min": coletar_cpu_freq_min,
# # "cpu_freq_max": coletar_cpu_freq_max,
# # "cpu_ctx_switches": coletar_cpu_ctx_switches,
# # "cpu_interrupts": coletar_cpu_interrupts,
# # "cpu_soft_interrupts": coletar_cpu_soft_interrupts,
# # "cpu_syscalls": coletar_cpu_syscalls,
# # "cpu_time_user": coletar_cpu_time_user,
# # "cpu_time_system": coletar_cpu_time_system,
# "cpu_time_idle": coletar_cpu_time_idle,
# "virtual_memory_total_gb": coletar_virtual_memory_total_gb,
# "virtual_memory_available_gb": coletar_virtual_memory_available_gb,
# "virtual_memory_used_gb": coletar_virtual_memory_used_gb,
# "virtual_memory_free_gb": coletar_virtual_memory_free_gb,
# "virtual_memory_percent": coletar_virtual_memory_percent,
# # "virtual_memory_active_gb": coletar_virtual_memory_active_gb,
# # "virtual_memory_inactive_gb": coletar_virtual_memory_inactive_gb,
# # "virtual_memory_buffers_gb": coletar_virtual_memory_buffers_gb,
# # "virtual_memory_cached_gb": coletar_virtual_memory_cached_gb,
# # "swap_total_gb": coletar_swap_total_gb,
# "swap_used_gb": coletar_swap_used_gb,# ok 
# "swap_free_gb": coletar_swap_free_gb,# ok
# # "swap_percent": coletar_swap_percent,
# # "swap_sin_gb": coletar_swap_sin_gb,
# # "swap_sout_gb": coletar_swap_sout_gb,
# "disk_percent": coletar_disk_percent,
# # "disk_total_gb": coletar_disk_total_gb,
# # "disk_used_gb": coletar_disk_used_gb,
# "disk_free_gb": coletar_disk_free_gb,
# # "disk_read_count": coletar_disk_read_count,
# # "disk_write_count": coletar_disk_write_count,
# "disco_throughput": coletar_throughput,
# # "disk_read_bytes_gb": coletar_disk_read_bytes_gb,
# # "disk_write_bytes_gb": coletar_disk_write_bytes_gb,
# # "disk_read_time": coletar_disk_read_time,
# # "disk_write_time": coletar_disk_write_time,
# # "net_bytes_sent_gb": coletar_net_bytes_sent_gb,
# # "net_bytes_recv_gb": coletar_net_bytes_recv_gb,
# "net_packets_sent": coletar_net_packets_sent,
# "net_packets_recv": coletar_net_packets_recv,
# # "net_errin": coletar_net_errin,
# # "net_errout": coletar_net_errout,
# # "net_dropin": coletar_net_dropin,
# # "net_dropout": coletar_net_dropout,
# "total_processos": coletar_total_processos,
# # "usuarios_logados": coletar_usuarios_logados,
# # "boot_time": coletar_boot_time,
# # "uptime_segundos": coletar_uptime_segundos,
# # "uptime_minutos": coletar_uptime_minutos,
# # "uptime_horas": coletar_uptime_horas,
# # "total_particoes": coletar_total_particoes,
# # "total_conexoes": coletar_total_conexoes,
# # "bateria_percent": coletar_bateria_percent,
# # "bateria_plugada": coletar_bateria_plugada,
# # "bateria_segundos_restantes": coletar_bateria_segundos_restantes,
# "latencia_resposta_ms": coletar_latencia_resposta_ms

# }

# resultados = {
#     "timestamp": [],
#     "home_broker":[],
#     "cpu_percent":[], 
#     "cpu_freq_current":[], 
#     "cpu_time_idle": [],
#     "virtual_memory_total_gb": [],
#     "virtual_memory_available_gb":[],
#     "virtual_memory_free_gb":[],
#     "virtual_memory_percent": [],
#     "swap_percent": [],
#     "swap_used_gb": [],
#     "swap_free_gb": [],
#     "disk_percent": [],
#     "disco_throughput": [], #quantidade de dados transferidos por segundo
#     "latencia_resposta_ms":[],
#     "net_bytes_sent_gb":[],
#     "net_bytes_recv_gb":[],
#     "total_processos":[],
# }

nome_servidor = psutil.users()[0].name
memoria_total = round(conversao_gb(psutil.virtual_memory().total),2)
arquivo_csv = "escalavel.csv"

# def carregamento():
#     for i in range(1,101):
#         sys.stdout.write("\r"+f"Carregando:  {i}%") 
#         sys.stdout.flush() 
#         time.sleep(0.05)
#     sys.stdout.write("\n")

print(f"HORÁRIO AGORA = {datetime.now().strftime("%d/%m/%Y %H:%M")}")
print(pyfiglet.figlet_format("n0Broke-Script"))
# print(carregamento())

# with open(arquivo_csv, mode="w",  newline='', encoding="utf-8") as file:
#         writer = csv.writer(file, delimiter=";")
#         writer.writerow(["Nome", " Data", " CPU(%)", "Freq-CPU(hz)", "Ociosidade-CPU", " Mémoria-total", " Mémoria-disponivel", " Mémoria-used", " Memoria-free", "Memoria-percent(%)","Swap-used"," Swap-free", "Bytes-sent","Bytes-recv"," Latencia(ms)","Processos-ativos"])

for i in range(1, 41):

    horario_atual = datetime.now()
    horario_tratado = datetime.strftime(horario_atual, "%d-%m-%Y %H:%M:%S")
    cpu_porcentagem = coletar_cpu_percent()
    cpu_frequencia_atual = coletar_cpu_freq_current()
    cpu_tempo_ocioso = coletar_cpu_time_idle()
    ram_total = coletar_virtual_memory_total_gb()
    ram_available = coletar_virtual_memory_available_gb()
    ram_used = coletar_virtual_memory_used_gb()
    ram_free = coletar_virtual_memory_free_gb()
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


    resultados["timestamp"].append(horario_tratado)
    resultados["home_broker"].append(nome_servidor)
    resultados["cpu_percent"].append(cpu_porcentagem)
    resultados["cpu_freq_current"].append(cpu_frequencia_atual)
    resultados["cpu_time_idle"].append(cpu_tempo_ocioso)
    resultados["ram_total_gb"].append(ram_total)
    resultados["ram_available_gb"].append(ram_available)
    resultados["ram_used_gb"].append(ram_used)
    resultados["ram_free_gb"].append(ram_free)
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


    # for componentes in dados["componentes"]:
    #     nome = componentes["nome"]
    #     parametros = componentes["parametros"]
    #     funcao = coletores.get(nome)
    #     valor = funcao(parametros)
    #     resultados[nome] = valor
    #     lista_componentes.append(resultados[nome])

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
                {print_barra(resultados['ram_free_gb'][len(resultados['ram_free_gb'])-1], "Memória Livre", "GB", 10, memoria_total)}
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

         +------------------------------------------------------------------------------+
          """)
    pandas.DataFrame(resultados).to_csv("escalavel.csv", encoding="utf-8", sep=";", index=False)
    time.sleep(5)