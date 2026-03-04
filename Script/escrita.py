import psutil
import csv
import time
import datetime
import os


#Verificar se Arquivo Existe
existeCSV = os.path.exists('./csv/capturaDados.csv')

#Obtenção dos dados via psutil
horaAtual = datetime.datetime.now()
ram = psutil.virtual_memory().percent
cpu = psutil.cpu_percent(interval=1)
disk = psutil.disk_usage('/').percent
diskUsed = psutil.disk_usage("/").used
diskFree = psutil.disk_usage("/").free

#Criação das Arrays para exibição dentro do CSV
dadosCapturados = [[horaAtual, cpu, ram, disk, diskUsed, diskFree]]
Header = ['horaCaptura', 'CPU', 'RAM', 'DISCO', 'DISCO USADO', 'DISCO LIVRE']

#Criação do CSV
with open('./csv/capturaDados.csv', 'a', newline ='') as csvfile:
   writer = csv.writer(csvfile)
   if not existeCSV:
      writer.writerow(Header)
   while True:
    writer.writerows(dadosCapturados)
    time.sleep(10)