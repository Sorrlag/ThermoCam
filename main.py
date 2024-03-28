import csv
import subprocess
import socket
import os
import ftplib
import sys
import time
import tkinter
import tkinter.messagebox
from tkinter import *
from tkinter import ttk
import tkcalendar
import re
import warnings
from datetime import datetime
import modbus_tk.defines as comfunc
import modbus_tk.modbus_tcp as modbus_tcp
import matplotlib.ticker
import matplotlib.dates
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import pandas

xLpos, xVpos, yPos = 20, 220, 100
localIP, panelIP, panelDate, panelTime, currentTime, filename = "", "", "", "", "", ""
fg, fgv, bg = "white", "yellow", "black"
status = ("НЕТ СВЯЗИ", "АВАРИЯ", "РАБОТА", "ОСТАНОВ")
mode = ("НЕТ СВЯЗИ", "НАСТРОЙКА", "ТЕРМО", "ВЛАГА")
statusIndex, modeIndex = 0, 0
temperatureCurrent, temperatureSet = -1.1, -1.1
humidityCurrent, humiditySet = 1.1, 1.1
rootFolder = f"C:\\Cont\\"
converter = f"{rootFolder}Converter\\easyсonverter.exe"
dtlFolder = f"{rootFolder}Converter\\data\\"
csvFolder = f"{rootFolder}_Data\\CSV\\"
xlsFolder = f"{rootFolder}_Data\\XLS\\"
mainIP = ""


def ObjectsPlace():
    logoLabel.place(x=450, y=780)
    armIPLabel.place(x=xLpos, y=15)
    panelIPLabel.place(x=xLpos, y=35)
    panelDateLabel.place(x=650, y=15, width=100)
    panelTimeLabel.place(x=650, y=35, width=100)
    statusLabel.place(x=xLpos, y=yPos, width=200)
    statusValue.place(x=xVpos, y=yPos, width=150)
    modeLabel.place(x=xLpos, y=yPos + 20, width=200)
    modeValue.place(x=xVpos, y=yPos + 20, width=150)
    tempCurLabel.place(x=xLpos, y=yPos + 40, width=200)
    tempCurValue.place(x=xVpos, y=yPos + 40, width=150)
    tempSetLabel.place(x=xLpos, y=yPos + 60, width=200)
    tempSetValue.place(x=xVpos, y=yPos + 60, width=150)
    humCurLabel.place(x=xLpos, y=yPos + 80, width=200)
    humCurValue.place(x=xVpos, y=yPos + 80, width=150)
    humSetLabel.place(x=xLpos, y=yPos + 100, width=200)
    humSetValue.place(x=xVpos, y=yPos + 100, width=150)
    labelPeriods.place(x=410, y=90)


def LabelsShow():
    logoLabel["text"] = f"© 'МИР ОБОРУДОВАНИЯ', Санкт-Петербург, 2024"
    armIPLabel["text"] = f"IP адрес рабочей станции: {localIP}"
    panelIPLabel["text"] = f'IP адрес климатической установки: {panelIP}'
    panelDateLabel["text"] = panelDate
    panelTimeLabel["text"] = panelTime
    statusLabel["text"] = f"Статус установки:"
    statusValue["text"] = status[statusIndex]
    modeLabel["text"] = f"Режим работы:"
    modeValue["text"] = mode[modeIndex]
    tempCurLabel["text"] = f"Текущая температура:"
    tempCurValue["text"] = f"{temperatureCurrent} °C"
    tempSetLabel["text"] = f"Уставка по температуре:"
    tempSetValue["text"] = f"{temperatureSet} °C"
    humCurLabel["text"] = f"Текущая влажность:"
    humCurValue["text"] = f"{humidityCurrent} °C"
    humSetLabel["text"] = f"Уставка по влажности:"
    humSetValue["text"] = f"{humiditySet} °C"
    labelPeriods["text"] = "Диапазон отображения:"
    root.after(1000, LabelsShow)


def ComboboxShow():
    global graphLabels, graphPeriods, graphDefault
    graphLabels = ["1 минута", "5 минут", "15 минут", "30 минут", "1 час", "2 часа", "Настраиваемый..."]
    graphPeriods = ["00:01:00", "00:05:00", "00:15:00", "00:30:00", "01:00:00", "02:00:00", "00:01:00"]
    graphDefault = StringVar(value=graphLabels[0])
    graphPeriod = ttk.Combobox(values=graphLabels, textvariable=graphDefault, width=20, state="readonly")
    graphPeriod.place(x=570, y=90)


def GetLocalIP():
    global localIP
    hostname = socket.gethostname()
    localIP = socket.gethostbyname(hostname)


def InputIP():
    def GetIP():
        global mainIP
        stringIP = entryIP.get()
        record = [stringIP, "N"]
        configPath = f"{rootFolder}config.ini"
        with open(configPath, mode="a", newline="") as configFile:
            writeIP = csv.writer(configFile)
            writeIP.writerow(record)
        mainIP = stringIP
        screenIP.grab_release()
        screenIP.destroy()
        CheckIP()
    def Mask(ip):
        validIP = re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", ip)
        buttonStart["state"] = "normal" if validIP is not None else "disabled"
        return True
    screenIP = Toplevel(root)
    screenIP.title("Введите IP")
    screenIP.geometry("300x150")
    rootPosX = root.winfo_rootx() + 250
    rootPosY = root.winfo_rooty() + 350
    screenIP.wm_geometry("+%d+%d" % (rootPosX, rootPosY))
    screenIP.resizable(False, False)
    screenIP.grab_set()
    screenIP.protocol("WM_DELETE_WINDOW", sys.exit)
    iconIP = PhotoImage(file=f"{rootFolder}icon.png")
    screenIP.iconphoto(False, iconIP)
    labelIP = tkinter.Label(master=screenIP, text="Введите IP адрес климатической установки:")
    labelIP.place(x=10, y=30, width=280)
    isvalid = (screenIP.register(Mask), "%P")
    entryIP = tkinter.Entry(master=screenIP, relief="solid", justify="center",
                            validate="key", validatecommand=isvalid)
    entryIP.place(x=10, y=50, width=280)
    buttonStart = tkinter.Button(master=screenIP, text="Начать опрос", command=GetIP, state="disabled")
    buttonStart.place(x=10, y=80, width=280)
    buttonClose = tkinter.Button(master=screenIP, text="Закрыть программу", command=sys.exit)
    buttonClose.place(x=10, y=110, width=280)


def CheckIP():
    global mainIP
    configPath = f"{rootFolder}config.ini"
    frameIP = pandas.read_csv(configPath, sep=",")
    if frameIP.empty:
        InputIP()
    else:
        mainIP = frameIP.iloc[-1]["ip"]
        OpenConnection()


def OpenConnection():
    global mainIP, master, ftp, fileList
    try:
        master = modbus_tcp.TcpMaster(host=mainIP, port=502, timeout_in_sec=5)
        master.set_timeout(5.0)
    except TimeoutError:
        print("Error open TCP port")
        ConnectionError()
        return
    try:
        ftp = ftplib.FTP(host=mainIP, timeout=5)
        ftp.login(user="uploadhis", passwd="111111")
        ftp.cwd("datalog/data")
        fileList = ftp.nlst()
    except TimeoutError:
        print("FTP connection failure")
        ConnectionError()
        return
    except AttributeError:
        print("Wrong host")
        ConnectionError()
        return
    ReadModbusTCP()
    LabelsShow()
    ComboboxShow()
    FTPhistory()
    CSVhistory()
    CurrentUpdate()
    Plot()


def ConnectionError():
    def Countdown():
        global wait
        if wait > 1:
            wait -= 1
            info["text"] = f"Ошибка соединения...\nПовтор через: {wait}"
            print(wait)
            screenError.after(1000, Countdown)
        else:
            RetryConnection()
    def RetryConnection():
        print("Retry connection...")
        screenError.grab_release()
        screenError.destroy()
        OpenConnection()
    def ResetIP():
        print("IP is changing...")
        screenError.grab_release()
        screenError.destroy()
        InputIP()
    global wait
    wait = 10
    screenError = Toplevel(root)
    screenError.title("ВНИМАНИЕ")
    screenError.geometry("300x100")
    rootPosX = root.winfo_rootx() + 250
    rootPosY = root.winfo_rooty() + 350
    screenError.wm_geometry("+%d+%d" % (rootPosX, rootPosY))
    screenError.resizable(False, False)
    screenError.grab_set()
    screenError["bg"] = "yellow"
    screenError.protocol("WM_DELETE_WINDOW", sys.exit)
    screenIcon = PhotoImage(file=f"{rootFolder}icon.png")
    screenError.iconphoto(False, screenIcon)

    info = tkinter.Label(master=screenError, bg="yellow")
    info.place(x=10, y=10, width=280)
    buttonRetry = tkinter.Button(master=screenError, text="Повторить", command=RetryConnection)
    buttonChange = tkinter.Button(master=screenError, text="Изменить IP", command=ResetIP)
    buttonClose = tkinter.Button(master=screenError, text="Завершить", command=sys.exit)
    buttonRetry.place(x=15, y=60, width=80)
    buttonChange.place(x=110, y=60, width=80)
    buttonClose.place(x=205, y=60, width=80)
    screenError.after(50, Countdown)


def ReadModbusTCP():
    global panelIP, panelDate, panelTime, currentTime, filename, \
        temperatureCurrent, temperatureSet, humidityCurrent, humiditySet, modeIndex, statusIndex
    try:
        getSys = master.execute(1, comfunc.READ_INPUT_REGISTERS, 10099, 10)
        getTempCur = master.execute(1, comfunc.READ_INPUT_REGISTERS, 10109, 1)
        getTempSet = master.execute(1, comfunc.READ_INPUT_REGISTERS, 10110, 1)
        getHumCur = master.execute(1, comfunc.READ_INPUT_REGISTERS, 10111, 1)
        getHumSet = master.execute(1, comfunc.READ_INPUT_REGISTERS, 10112, 1)
        getStatus = master.execute(1, comfunc.READ_INPUT_REGISTERS, 10115, 1)
        getMode = master.execute(1, comfunc.READ_INPUT_REGISTERS, 10114, 1)
    except TimeoutError:
        print("TCP connection failure")
        ConnectionError()
        return
    panelIP = f"{getSys[0]}.{getSys[1]}.{getSys[2]}.{getSys[3]}"
    panelDate = f"{getSys[4]:02} / {getSys[5]:02} / {getSys[6]}"
    panelTime = f"{getSys[7]:02} : {getSys[8]:02} : {getSys[9]:02}"
    currentTime = f"{getSys[7]:02}:{getSys[8]:02}:{getSys[9]:02}"
    filename = f"{getSys[6]:04}{getSys[5]:02}{getSys[4]:02}"
    temperatureCurrent = (getTempCur[0] - 2 ** 16) / 10 if getTempCur[0] > 2 ** 15 else getTempCur[0] / 10
    temperatureSet = (getTempSet[0] - 2 ** 16) / 10 if getTempSet[0] > 2 ** 15 else getTempSet[0] / 10
    humidityCurrent = getHumCur[0] / 10
    humiditySet = getHumSet[0]
    statusIndex = int(getStatus[0])
    modeIndex = int(getMode[0])

    root.after(1000, ReadModbusTCP)


def FTPhistory():
    for fileNum in fileList:
        remoteFile = fileNum
        localFile = f"{dtlFolder}{remoteFile}"
        with open(localFile, "wb") as file:
            ftp.retrbinary("RETR %s" % remoteFile, file.write)


def CSVhistory():
    fileList = os.listdir(dtlFolder)
    for fileNum in fileList:
        dtlFile = fileNum
        csvFile = f"{fileNum[:8]}.csv"
        xlsFile = f"{fileNum[:8]}.xls"
        subprocess.run(f'{converter} /b0 /t0 "{dtlFolder}{dtlFile}" "{csvFolder}{csvFile}"', shell=True)
        subprocess.run(f'{converter} /b0 /t0 "{dtlFolder}{dtlFile}" "{xlsFolder}{xlsFile}"', shell=True)


def CurrentUpdate():
    try:
        remoteFile = ''.join(fileList[-1:])
        localFile = f"{dtlFolder}{remoteFile}"
        with open(localFile, "wb") as file:
            ftp.retrbinary("RETR %s" % remoteFile, file.write)
    except TimeoutError:
        print("FTP failure")
        return
    dtlList = os.listdir(dtlFolder)
    dtlFile = ''.join(dtlList[-1:])
    csvFile = f"{dtlFile[:8]}.csv"
    xlsFile = f"{dtlFile[:8]}.xls"
    subprocess.run(f'{converter} /b0 /t0 "{dtlFolder}{dtlFile}" "{csvFolder}{csvFile}"', shell=True)
    subprocess.run(f'{converter} /b0 /t0 "{dtlFolder}{dtlFile}" "{xlsFolder}{xlsFile}"', shell=True)

    root.after(5000, CurrentUpdate)


def WriteFile():
    os.chdir(f"{rootFolder}_DATA\\")
    filepath = f"{rootFolder}_DATA/test.csv"
    with open(filepath, mode="a", encoding="utf-8", newline="") as file:
        update = csv.writer(file)
        time = datetime.strptime(panelTime, "%H : %M : %S").time()
        record = [time, temperatureCurrent]
        if time.second % 5 == 0:
            update.writerow(record)
    root.after(1000, WriteFile)


def Plot():
    fileList = os.listdir(csvFolder)
    filePath = csvFolder + ''.join(fileList[-1:])
    choice = graphDefault.get()
    choiceTime = graphPeriods[graphLabels.index(choice)]
    timeNow = datetime.strptime(currentTime, "%H:%M:%S")
    timeDif = datetime.strptime(choiceTime, "%H:%M:%S")
    timeBegin = str(timeNow - timeDif)
    frameData = pandas.read_csv(filePath, sep=",", header=0, usecols=[1, 2, 3, 4, 5])
    frameColumns = ["Time", "TemperatureCurrent", "TemperatureSet", "HumidityCurrent", "HumiditySet"]
    frameCurrent = frameData.loc[frameData["Time"] >= timeBegin, frameColumns]

    figure.clear()
    lox = matplotlib.ticker.LinearLocator(18)
    graphTemp = figure.add_subplot(111)
    graphTemp.xaxis.set_major_locator(lox)
    graphTemp.set_facecolor("black")
    graphTemp.plot(frameCurrent["Time"], frameCurrent["TemperatureCurrent"], "-b",
                   frameCurrent["Time"], frameCurrent["TemperatureSet"], "--c")
    graphHum = graphTemp.twinx()
    graphHum.plot(frameCurrent["Time"], frameCurrent["HumidityCurrent"], "-r",
                  frameCurrent["Time"], frameCurrent["HumiditySet"], "--m")
    graphHum.set_ylabel("Влажность, %", color="red")
    if modeIndex == 2:
        graphTemp.fill_between(x=frameCurrent["Time"], y1=frameCurrent["TemperatureCurrent"],
                               y2=frameCurrent["TemperatureSet"], alpha=0.2)
    if modeIndex == 3:
        graphHum.fill_between(x=frameCurrent["Time"], y1=frameCurrent["HumidityCurrent"],
                              y2=frameCurrent["HumiditySet"], alpha=0.2)
    graphTemp.set_ylabel("Температура, °C", color="blue")
    graphTemp.grid(alpha=0.5, linestyle="-", color="cyan", linewidth=0.3)
    graphHum.grid(alpha=0.6, linestyle=":", color="red")
    graphTemp.tick_params(labelsize=8, colors="yellow")
    graphHum.tick_params(labelsize=8, colors="yellow")
    figure.autofmt_xdate()
    canvasGraph.draw()
    canvasGraph.get_tk_widget().place(x=10, y=250)

    root.after(5000, Plot)


root = Tk()
root.title("Модуль удалённого контроля климатической камеры")
root.geometry("800x800")
root.wm_geometry("+%d+%d" % (100, 100))
root["bg"] = bg
root.resizable(False, False)
icon = PhotoImage(file=f"{rootFolder}icon.png")
root.iconphoto(False, icon)

canvasStat = Canvas(width=390, height=150, bg="yellow", relief="raised")
canvasStat.place(x=0, y=80)
canvasStat.create_rectangle(10, 10, 390, 150, fill=bg)
canvasBut = Canvas(width=396, height=160, bg=bg)
canvasBut.place(x=400, y=80)
canvasBut.create_rectangle(10, 10, 396, 160, fill=bg)
canvasPlot = Canvas(width=796, height=500, bg=bg)
canvasPlot.place(x=0, y=240)
canvasPlot.create_rectangle(10, 10, 780, 300, fill=bg)

logoLabel = Label(font=("Arial", 10, "bold"), fg=fg, bg=bg)
armIPLabel = Label(fg=fg, bg=bg)
panelIPLabel = Label(fg=fg, bg=bg)
panelDateLabel = Label(fg=fg, bg=bg, anchor="e")
panelTimeLabel = Label(fg=fg, bg=bg, anchor="e")
statusLabel = Label(anchor="e", fg=fg, bg=bg)
statusValue = Label(fg=fgv, bg=bg)
modeLabel = Label(anchor="e", fg=fg, bg=bg)
modeValue = Label(fg=fgv, bg=bg)
tempCurLabel = Label(anchor="e", fg=fg, bg=bg)
tempCurValue = Label(fg=fgv, bg=bg)
tempSetLabel = Label(anchor="e", fg=fg, bg=bg)
tempSetValue = Label(fg=fgv, bg=bg)
humCurLabel = Label(anchor="e", fg=fg, bg=bg)
humCurValue = Label(fg=fgv, bg=bg)
humSetLabel = Label(anchor="e", fg=fg, bg=bg)
humSetValue = Label(fg=fgv, bg=bg)
labelPeriods = Label(anchor="w", fg=fg, bg=bg)

figure = Figure(figsize=(7.8, 4.9), dpi=100, facecolor="black")
canvasGraph = FigureCanvasTkAgg(figure=figure, master=root)

ObjectsPlace()
GetLocalIP()
CheckIP()

root.mainloop()


