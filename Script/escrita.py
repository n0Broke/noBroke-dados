import psutil
import csv
import time
import datetime
import os

#Verificar se o Arquivo Existe
existeCSV = os.path.exists('./csv/capturaDados.csv')

#Criando o Header
header = ['horaCaptura', 'CPU', 'RAM', 'DISCO', 'DISCO USADO', 'DISCO LIVRE']

#Criando o arquivo CSV utilizando a biblioteca CSV
with open('./csv/capturaDados.csv', 'a', newline='') as csvfile:
    writer = csv.writer(csvfile)

#Vendo se precisa ou não precisa sobreescrevar o CSV
    if not existeCSV:
        writer.writerow(header)

#Capturando os dados em looping
    while True:
        horaAtual = datetime.datetime.now()
        ram = psutil.virtual_memory().percent
        cpu = psutil.cpu_percent(interval=1)
        disk = psutil.disk_usage('/').percent
        diskUsed = psutil.disk_usage('/').used
        diskFree = psutil.disk_usage('/').free

        dadosCapturados = [horaAtual, cpu, ram, disk, diskUsed, diskFree]

        writer.writerow(dadosCapturados)

        time.sleep(60)