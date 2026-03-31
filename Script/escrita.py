import psutil
import json
import csv
import time
from datetime import datetime
import subprocess
import platform

with open("banco.json", "r", encoding="utf-8") as file:
    dados = json.load(file)

def conversao_gb(valor: float):
    return valor/ (1024 ** 3)

def coletar_cpu_percent(parametros):
    return round(psutil.cpu_percent(interval=1),2)

def coletar_cpu_count_logical(parametros):
    return round(psutil.cpu_count(),2)

def coletar_cpu_count_physical(parametros):
    return round(psutil.cpu_count(logical=False),2)

def coletar_cpu_freq_current(parametros):
    cpu = psutil.cpu_freq()
    return round(cpu.current,2)

def coletar_cpu_freq_min(parametros):
    cpu = psutil.cpu_freq()
    return round(cpu.min,2)

def coletar_cpu_freq_max(parametros):
    cpu = psutil.cpu_freq()
    return round(cpu.max,2)

def coletar_cpu_ctx_switches(parametros):
    stats = psutil.cpu_stats()
    return round(stats.ctx_switches,2)

def coletar_cpu_interrupts(parametros):
    stats = psutil.cpu_stats()
    return round(stats.interrupts,2)

def coletar_cpu_soft_interrupts(parametros):
    stats = psutil.cpu_stats()
    return round(stats.soft_interrupts,2)

def coletar_cpu_syscalls(parametros):
    stats = psutil.cpu_stats()
    return round(stats.syscalls,2)

def coletar_cpu_time_user(parametros):
    tempos = psutil.cpu_times()
    return round(tempos.user,2)

def coletar_cpu_time_system(parametros):
    tempos = psutil.cpu_times()
    return round(tempos.system,2)

def coletar_cpu_time_idle(parametros):
    tempos = psutil.cpu_times()
    return round(tempos.idle,2)

def coletar_virtual_memory_total_gb(parametros):
    memoria = psutil.virtual_memory()
    return round(conversao_gb(memoria.total),2)

def coletar_virtual_memory_available_gb(parametros):
    memoria = psutil.virtual_memory()
    return round(conversao_gb(memoria.available),2)

def coletar_virtual_memory_used_gb(parametros):
    memoria = psutil.virtual_memory()
    return round(conversao_gb(memoria.used),2)

def coletar_virtual_memory_free_gb(parametros):
    memoria = psutil.virtual_memory()
    return round(conversao_gb(memoria.free),2)

def coletar_virtual_memory_percent(parametros):
    memoria = psutil.virtual_memory()
    return round(memoria.percent,2)

def coletar_virtual_memory_active_gb(parametros):
    memoria = psutil.virtual_memory()
    return round(conversao_gb(memoria.active),2)

def coletar_virtual_memory_inactive_gb(parametros):
    memoria = psutil.virtual_memory()
    return round(conversao_gb(memoria.inactive),2)

def coletar_virtual_memory_buffers_gb(parametros):
    memoria = psutil.virtual_memory()
    return round(conversao_gb(memoria.buffers),2)

def coletar_virtual_memory_cached_gb(parametros):
    memoria = psutil.virtual_memory()
    return round(conversao_gb(memoria.cached),2)

def coletar_swap_total_gb(parametros):
    swap = psutil.swap_memory()
    return round(conversao_gb(swap.total),2)

def coletar_swap_used_gb(parametros):
    swap = psutil.swap_memory()
    return round(conversao_gb(swap.used),2)

def coletar_swap_free_gb(parametros):
    swap = psutil.swap_memory()
    return round(conversao_gb(swap.free),2)

def coletar_swap_percent(parametros):
    swap = psutil.swap_memory()
    return round(swap.percent,2)

def coletar_swap_sin_gb(parametros):
    swap = psutil.swap_memory()
    return round(conversao_gb(swap.sin),2)

def coletar_swap_sout_gb(parametros):
    swap = psutil.swap_memory()
    return round(conversao_gb(swap.sout),2)

def coletar_disk_percent(parametros):
    disco = psutil.disk_usage('/')
    return round(disco.percent,2)

def coletar_disk_total_gb(parametros):
    disco = psutil.disk_usage('/')
    return round(conversao_gb(disco.total),2)

def coletar_disk_used_gb(parametros):
    disco = psutil.disk_usage('/')
    return round(conversao_gb(disco.used),2)

def coletar_disk_free_gb(parametros):
    disco = psutil.disk_usage('/')
    return round(conversao_gb(disco.free),2)

def coletar_disk_read_count(parametros):
    disco = psutil.disk_io_counters()
    return round(conversao_gb(disco.read_count),2) # adicionei a conversão pra manter o padrão

def coletar_disk_write_count(parametros):
    disco = psutil.disk_io_counters()
    return round(disco.write_count,2)

def coletar_disk_read_bytes_gb(parametros):
    disco = psutil.disk_io_counters()
    return round(conversao_gb(disco.read_bytes),2)

def coletar_disk_write_bytes_gb(parametros):
    disco = psutil.disk_io_counters()
    return round(conversao_gb(disco.write_bytes),2)

def coletar_disk_read_time(parametros):
    disco = psutil.disk_io_counters()
    return round(disco.read_time,2)

def coletar_disk_write_time(parametros):
    disco = psutil.disk_io_counters()
    return round(disco.write_time,2)

def coletar_net_bytes_sent_gb(parametros):
    rede = psutil.net_io_counters()
    return round(conversao_gb(rede.bytes_sent),2)

def coletar_net_bytes_recv_gb(parametros):
    rede = psutil.net_io_counters()
    return round(conversao_gb(rede.bytes_recv),2)

def coletar_net_packets_sent(parametros):
    rede = psutil.net_io_counters()
    return round(rede.packets_sent,2)

def coletar_net_packets_recv(parametros):
    rede = psutil.net_io_counters()
    return round(rede.packets_recv,2)

def coletar_net_errin(parametros):
    rede = psutil.net_io_counters()
    return round(rede.errin,2)

def coletar_net_errout(parametros):
    rede = psutil.net_io_counters()
    return round(rede.errout,2)

def coletar_net_dropin(parametros):
    rede = psutil.net_io_counters()
    return round(rede.dropin,2)

def coletar_net_dropout(parametros):
    rede = psutil.net_io_counters()
    return round(rede.dropout,2)

def coletar_total_processos(parametros):
    return round(len(psutil.pids()),2)

def coletar_usuarios_logados(parametros):
    return round(len(psutil.users()),2)

def coletar_boot_time(parametros):
    return round(psutil.boot_time(),2)

def coletar_uptime_segundos(parametros):
    return round(time.time() - psutil.boot_time(),2)

def coletar_uptime_minutos(parametros):
    return round((time.time() - psutil.boot_time())/60,2)

def coletar_uptime_horas(parametros):
    return round((time.time() - psutil.boot_time())/3600,2)

def coletar_total_particoes(parametros):
    particoes = psutil.disk_partitions()
    return round(len(particoes),2)

def coletar_total_conexoes(parametros):
    conexoes = psutil.net_connections()
    return round(len(conexoes),2)

def coletar_bateria_percent(parametros):
    bateria = psutil.sensors_battery()
    return round(bateria.percent,2)

def coletar_bateria_plugada(parametros):
    bateria = psutil.sensors_battery()
    return round(bateria.power_plugged,2)

def coletar_bateria_segundos_restantes(parametros):
    bateria = psutil.sensors_battery()
    return round(bateria.secsleft,2)

def coletar_latencia_resposta_ms(parametros):
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

coletores = {
"cpu_percent": coletar_cpu_percent,
"cpu_count_logical": coletar_cpu_count_logical,
"cpu_count_physical": coletar_cpu_count_physical,
"cpu_freq_current": coletar_cpu_freq_current,
"cpu_freq_min": coletar_cpu_freq_min,
"cpu_freq_max": coletar_cpu_freq_max,
"cpu_ctx_switches": coletar_cpu_ctx_switches,
"cpu_interrupts": coletar_cpu_interrupts,
"cpu_soft_interrupts": coletar_cpu_soft_interrupts,
"cpu_syscalls": coletar_cpu_syscalls,
"cpu_time_user": coletar_cpu_time_user,
"cpu_time_system": coletar_cpu_time_system,
"cpu_time_idle": coletar_cpu_time_idle,
"virtual_memory_total_gb": coletar_virtual_memory_total_gb,
"virtual_memory_available_gb": coletar_virtual_memory_available_gb,
"virtual_memory_used_gb": coletar_virtual_memory_used_gb,
"virtual_memory_free_gb": coletar_virtual_memory_free_gb,
"virtual_memory_percent": coletar_virtual_memory_percent,
"virtual_memory_active_gb": coletar_virtual_memory_active_gb,
"virtual_memory_inactive_gb": coletar_virtual_memory_inactive_gb,
"virtual_memory_buffers_gb": coletar_virtual_memory_buffers_gb,
"virtual_memory_cached_gb": coletar_virtual_memory_cached_gb,
"swap_total_gb": coletar_swap_total_gb,
"swap_used_gb": coletar_swap_used_gb,
"swap_free_gb": coletar_swap_free_gb,
"swap_percent": coletar_swap_percent,
"swap_sin_gb": coletar_swap_sin_gb,
"swap_sout_gb": coletar_swap_sout_gb,
"disk_percent": coletar_disk_percent,
"disk_total_gb": coletar_disk_total_gb,
"disk_used_gb": coletar_disk_used_gb,
"disk_free_gb": coletar_disk_free_gb,
"disk_read_count": coletar_disk_read_count,
"disk_write_count": coletar_disk_write_count,
"disk_read_bytes_gb": coletar_disk_read_bytes_gb,
"disk_write_bytes_gb": coletar_disk_write_bytes_gb,
"disk_read_time": coletar_disk_read_time,
"disk_write_time": coletar_disk_write_time,
"net_bytes_sent_gb": coletar_net_bytes_sent_gb,
"net_bytes_recv_gb": coletar_net_bytes_recv_gb,
"net_packets_sent": coletar_net_packets_sent,
"net_packets_recv": coletar_net_packets_recv,
"net_errin": coletar_net_errin,
"net_errout": coletar_net_errout,
"net_dropin": coletar_net_dropin,
"net_dropout": coletar_net_dropout,
"total_processos": coletar_total_processos,
"usuarios_logados": coletar_usuarios_logados,
"boot_time": coletar_boot_time,
"uptime_segundos": coletar_uptime_segundos,
"uptime_minutos": coletar_uptime_minutos,
"uptime_horas": coletar_uptime_horas,
"total_particoes": coletar_total_particoes,
"total_conexoes": coletar_total_conexoes,
"bateria_percent": coletar_bateria_percent,
"bateria_plugada": coletar_bateria_plugada,
"bateria_segundos_restantes": coletar_bateria_segundos_restantes,
"latencia_resposta_ms": coletar_latencia_resposta_ms

}

resultados = {
"cpu_percent":"",
"cpu_count_logical":"",
"cpu_count_physical":"",
"cpu_freq_current":"",
"cpu_freq_min":"",
"cpu_freq_max":"",
"cpu_ctx_switches":"",
"cpu_interrupts":"",
"cpu_soft_interrupts":"",
"cpu_syscalls":"",
"cpu_time_user":"",
"cpu_time_system":"",
"cpu_time_idle":"",
"virtual_memory_total_gb":"",
"virtual_memory_available_gb":"",
"virtual_memory_used_gb":"",
"virtual_memory_free_gb":"",
"virtual_memory_percent":"",
"virtual_memory_active_gb":"",
"virtual_memory_inactive_gb":"",
"virtual_memory_buffers_gb":"",
"virtual_memory_cached_gb":"",
"swap_total_gb":"",
"swap_used_gb":"",
"swap_free_gb":"",
"swap_percent":"",
"swap_sin_gb":"",
"swap_sout_gb":"",
"disk_percent":"",
"disk_total_gb":"",
"disk_used_gb":"",
"disk_free_gb":"",
"disk_read_count":"",
"disk_write_count":"",
"disk_read_bytes_gb":"",
"disk_write_bytes_gb":"",
"disk_read_time":"",
"disk_write_time":"",
"net_bytes_sent_gb":"",
"net_bytes_recv_gb":"",
"net_packets_sent":"",
"net_packets_recv":"",
"net_errin":"",
"net_errout":"",
"net_dropin":"",
"net_dropout":"",
"total_processos":"",
"usuarios_logados":"",
"boot_time":"",
"uptime_segundos":"",
"uptime_minutos":"",
"uptime_horas":"",
"total_particoes":"",
"total_conexoes":"",
"bateria_percent":"",
"bateria_plugada":"",
"bateria_segundos_restantes":"",
"latencia_resposta_ms":""

}

nome_servidor = psutil.users()[0].name

arquivo_csv = "escalavel.csv"


with open(arquivo_csv, mode="w",  newline='', encoding="utf-8") as file:
        writer = csv.writer(file, delimiter=";")
        writer.writerow(["Nome", " Data", " CPU(%)", " Mémoria-total", " Mémoria-livre", " Mémoria-used", " Mémoria-free", " Mémoria(%)", " Disco-total", " Disco-used","Disco-latencia"," Disco-free", " Disco(%)", " Latencia(ms)","Processos-ativos"])

for i in range(1, 41):

    lista_componentes = []

    for componentes in dados["componentes"]:
        nome = componentes["nome"]
        parametros = componentes["parametros"]
        funcao = coletores.get(nome)
        valor = funcao(parametros)
        resultados[nome] = valor
        lista_componentes.append(resultados[nome])

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with open(arquivo_csv, mode="a",  newline='', encoding="utf-8") as file:
        writer = csv.writer(file, delimiter=";")
        writer.writerow([nome_servidor, timestamp ,lista_componentes])

    print(lista_componentes)
    time.sleep(5)