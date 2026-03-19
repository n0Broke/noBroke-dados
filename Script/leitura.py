import pandas as pd
import time
import os

#Caminhos de Entrada
caminhoEntrada = './csv/capturaDados.csv'
caminhoSaida = './csv/dadosTratados.csv'

#Loop para continuamente gerar Relátorios de Leitura
while(True):
    #Checagem se Existe o caminho
    existeCSV = os.path.exists(caminhoSaida)

    #Lendo CSV e transformando Objeto Data em Data de fato para ser manipulada
    df = pd.read_csv(caminhoEntrada)
    df["horaCaptura"] = pd.to_datetime(df["horaCaptura"]) 

    #Pegando o registro mais Recente para gerar as médias
    agora = df["horaCaptura"].max()

    #Formula para pegar os registros que estão na ultima hora com base no registro mais Recente 
    # (Recente = 21 Ultimos Minutos = 21:05), porem no Dataframe inteiro utilizando o .TimeDelta e lógica.
    ultimos5 = df[df["horaCaptura"] >= agora - pd.Timedelta(minutes=5)]

    #Pegando o começo e o fim para gerar Intervalo, com base nos ultimos minutos.
    inicio = ultimos5["horaCaptura"].min()
    fim = ultimos5["horaCaptura"].max()
    intervaloHora = f"{inicio:%d/%m/%Y %H:%M} - {fim:%d/%m/%Y %H:%M}" #Gerando o intervalo de Tempo com data e horarios formatados
    mediaRAM = round(ultimos5["RAM"].mean(), 2) #Média da Ultima Hora de RAM
    mediaCPU = round(ultimos5["CPU"].mean(), 2) # Média da CPU nos ultimos 30 minutos
    picoCPU = round(ultimos5["CPU"].max(), 2) # Máximo de CPU que bateu
    mediaDisco = round(ultimos5["DISCO"].mean(), 2) # Média de Disco
    discoUsado = round(ultimos5["DISCO USADO"].mean() / 1024 **3, 2) # Disco Usado
    discoLivre = round(ultimos5["DISCO LIVRE"].mean() / 1024**3, 2) # Disco Livre

    #Colocando tudo em um JSON para exibir em um CSV
    relatorio = {
        "Intervalo de Tempo": [intervaloHora],
        "Media RAM": [mediaRAM],
        "Media CPU": [mediaCPU],
        "Pico CPU": [picoCPU],
        "Media Disco": [mediaDisco],
        "Disco Usado": [discoUsado],
        "Disco Livre": [discoLivre]
        }

    relatorioFinal = pd.DataFrame(relatorio)

    if existeCSV:
            relatorioFinal.to_csv(caminhoSaida, mode='a', encoding="utf-8", index=False, header=False)
    else:
            relatorioFinal.to_csv(caminhoSaida, encoding="utf-8", index=False)

    time.sleep(300)