import csv
import subprocess
import socket
import os
import ftplib
import sys
import time
import threading
import tkinter
import tkinter.messagebox
from tkinter import *
from tkinter import ttk
import tkcalendar
import re
from datetime import datetime
import modbus_tk.defines as comfunc
import modbus_tk.modbus_tcp as modbus_tcp
import matplotlib.ticker
import matplotlib.dates
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import pandas

xLabelPos, xValuePos, yPos = 20, 190, 100
localIP, panelIP, panelDate, panelTime, currentTime, filename, picname = "", "", "", "", "", "", ""
fgComm, fgVal, bgGlob, bgLoc = "white", "yellow", "#2B0542", "#510D70"
status = ("НЕТ СВЯЗИ", "АВАРИЯ", "РАБОТА", "ОСТАНОВ")
mode = ("НЕТ СВЯЗИ", "НАСТРОЙКА", "ТЕРМО", "ВЛАГА")
statusIndex, modeIndex = 0, 0
temperatureCurrent, temperatureSet = -1.1, -1.1
humidityCurrent, humiditySet = 1.1, 1.1
rootFolder = f"C:\\Cont\\"
picFolder = f"{rootFolder}Graph\\"
converter = f"{rootFolder}Converter\\easyсonverter.exe"
dtlFolder = f"{rootFolder}Converter\\data\\"
csvFolder = f"{rootFolder}\\CSV\\"
xlsFolder = f"{rootFolder}\\XLS\\"
machineIP, machineName = "", ""


def ObjectsPlace():
    logoLabel.place(x=650, y=780)
    panelDateLabel.place(x=880, y=15, width=100)
    panelTimeLabel.place(x=880, y=35, width=100)
    armIPLabel.place(x=xLabelPos, y=10)
    panelIPLabel.place(x=xLabelPos, y=30)
    panelNameLabel.place(x=xLabelPos, y=50)
    statusLabel.place(x=xLabelPos, y=yPos, width=150)
    statusValue.place(x=xValuePos, y=yPos, width=100)
    modeLabel.place(x=xLabelPos, y=yPos + 20, width=150)
    modeValue.place(x=xValuePos, y=yPos + 20, width=100)
    tempCurLabel.place(x=xLabelPos, y=yPos + 50, width=150)
    tempCurValue.place(x=xValuePos, y=yPos + 50, width=100)
    tempSetLabel.place(x=xLabelPos, y=yPos + 70, width=150)
    tempSetValue.place(x=xValuePos, y=yPos + 70, width=100)
    humCurLabel.place(x=xLabelPos, y=yPos + 100, width=150)
    humCurValue.place(x=xValuePos, y=yPos + 100, width=100)
    humSetLabel.place(x=xLabelPos, y=yPos + 120, width=150)
    humSetValue.place(x=xValuePos, y=yPos + 120, width=100)
    labelPeriods.place(x=670, y=90)
    labelNotif.place(x=670, y=120)


def LabelsShow():
    logoLabel["text"] = f"© 'МИР ОБОРУДОВАНИЯ', Санкт-Петербург, 2024"
    armIPLabel["text"] = f"IP адрес рабочей станции: {localIP}"
    panelIPLabel["text"] = f'IP адрес климатической установки: {panelIP}'
    panelNameLabel["text"] = f'Наименование: {machineName}'
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
    labelNotif["text"] = "Ошибка чтения данных из указанного диапазона..."
    root.after(1000, LabelsShow)


def GraphControl():
    global graphLabels, graphPeriods, graphDefault
    graphLabels = ["1 минута", "5 минут", "15 минут", "30 минут", "1 час", "2 часа", "Настраиваемый..."]
    graphPeriods = ["00:01:00", "00:05:00", "00:15:00", "00:30:00", "01:00:00", "02:00:00", "08:00:00"]
    graphDefault = StringVar(value=graphLabels[0])
    graphPeriod = ttk.Combobox(values=graphLabels, textvariable=graphDefault, width=20, state="readonly",
                               background=bgLoc, foreground=bgLoc)
    graphPeriod.place(x=830, y=90)
    buttonSave.place(x=670, y=210, width=280)
    buttonName.place(x=400, y=10, width=200)


def GetLocalIP():
    global localIP
    hostname = socket.gethostname()
    localIP = socket.gethostbyname(hostname)


def InputIP():
    def GetIP():
        global machineIP
        stringIP = entryIP.get()
        record = [stringIP, "Климатическая установка"]
        configPath = f"{rootFolder}config.ini"
        with open(configPath, mode="a", newline="") as configFile:
            writeIP = csv.writer(configFile)
            writeIP.writerow(record)
        machineIP = stringIP
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
    iconIP = PhotoImage(file="icons\\icon.png")
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
    global machineIP, machineName
    configPath = f"{rootFolder}config.ini"
    frameIP = pandas.read_csv(configPath, sep=",", encoding="cp1251")
    if frameIP.empty:
        InputIP()
    else:
        machineIP = frameIP.iloc[-1]["ip"]
        machineName = frameIP.iloc[-1]["name"]
        OpenConnection()


def DeleteButton():
    # buttonName.destroy()
    raise Exception("Abort")


def ShowGif():
    global heatLabel
    heatLabel = tkinter.Label(root)
    heatLabel.place(x=340, y=90)
    UpdateHeat()


def HideGif():
    global heatLabel
    heatLabel.destroy()


def OpenConnection():
    global machineIP, master, ftp, fileList, csvFolder, xlsFolder
    try:
        master = modbus_tcp.TcpMaster(host=machineIP, port=502, timeout_in_sec=5)
        master.set_timeout(5.0)
    except TimeoutError:
        ConnectionError()
        return
    try:
        ftp = ftplib.FTP(host=machineIP, timeout=5)
        ftp.login(user="uploadhis", passwd="111111")
        ftp.cwd("datalog/data")
        fileList = ftp.nlst()
        csvFolder = f"{rootFolder}{machineIP}\\CSV\\"
        xlsFolder = f"{rootFolder}{machineIP}\\XLS\\"
    except TimeoutError:
        ConnectionError()
        return
    except AttributeError:
        ConnectionError()
        return
    except ftplib.error_perm:
        print("Error open FTP")
    threadModbus.start()
    LabelsShow()
    GraphControl()
    FTPhistory()
    CSVhistory()
    threadFTP.start()
    Plot()


def ConnectionError():
    def Countdown():
        global wait
        if wait > 1:
            wait -= 1
            info["text"] = f"Ошибка соединения...\nПовтор через: {wait}"
            screenError.after(1000, Countdown)
        else:
            RetryConnection()
    def RetryConnection():
        screenError.grab_release()
        screenError.destroy()
        OpenConnection()
    def ResetIP():
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
    screenIcon = PhotoImage(file="icons\\icon.png")
    screenError.iconphoto(False, screenIcon)

    info = tkinter.Label(master=screenError, bg="yellow")
    info.place(x=10, y=10, width=280)
    buttonRetry = ttk.Button(master=screenError, text="Повторить", command=RetryConnection)
    buttonChange = ttk.Button(master=screenError, text="Изменить IP", command=ResetIP)
    buttonClose = ttk.Button(master=screenError, text="Завершить", command=sys.exit)
    buttonRetry.place(x=15, y=60, width=80)
    buttonChange.place(x=110, y=60, width=80)
    buttonClose.place(x=205, y=60, width=80)
    screenError.after(50, Countdown)


def ReadModbusTCP():
    global panelIP, panelDate, panelTime, currentTime, filename, picname, \
        temperatureCurrent, temperatureSet, humidityCurrent, humiditySet, modeIndex, statusIndex
    while True:
        try:
            getSys = master.execute(1, comfunc.READ_INPUT_REGISTERS, 10099, 10)
            getTempCur = master.execute(1, comfunc.READ_INPUT_REGISTERS, 10109, 1)
            getTempSet = master.execute(1, comfunc.READ_INPUT_REGISTERS, 10110, 1)
            getHumCur = master.execute(1, comfunc.READ_INPUT_REGISTERS, 10111, 1)
            getHumSet = master.execute(1, comfunc.READ_INPUT_REGISTERS, 10112, 1)
            getStatus = master.execute(1, comfunc.READ_INPUT_REGISTERS, 10115, 1)
            getMode = master.execute(1, comfunc.READ_INPUT_REGISTERS, 10114, 1)
            panelIP = f"{getSys[0]}.{getSys[1]}.{getSys[2]}.{getSys[3]}"
            panelDate = f"{getSys[4]:02} / {getSys[5]:02} / {getSys[6]}"
            panelTime = f"{getSys[7]:02} : {getSys[8]:02} : {getSys[9]:02}"
            currentTime = f"{getSys[7]:02}:{getSys[8]:02}:{getSys[9]:02}"
            filename = f"{getSys[6]:04}{getSys[5]:02}{getSys[4]:02}"
            picname = f"{getSys[6]}{getSys[5]:02}{getSys[4]:02}_{getSys[7]:02}{getSys[8]:02}{getSys[9]:02}"
            temperatureCurrent = (getTempCur[0] - 2 ** 16) / 10 if getTempCur[0] > 2 ** 15 else getTempCur[0] / 10
            temperatureSet = (getTempSet[0] - 2 ** 16) / 10 if getTempSet[0] > 2 ** 15 else getTempSet[0] / 10
            humidityCurrent = getHumCur[0] / 10
            humiditySet = getHumSet[0]
            statusIndex = int(getStatus[0])
            modeIndex = int(getMode[0])
        except UnboundLocalError:
            print("Modbus format error")
        except TimeoutError:
            ConnectionError()
            return
        except ConnectionRefusedError:
            print("Modbus read error")
        time.sleep(1)


def FTPhistory():
    try:
        for fileNum in fileList:
            remoteFile = fileNum
            localFile = f"{dtlFolder}{remoteFile}"
            with open(localFile, "wb") as file:
                ftp.retrbinary("RETR %s" % remoteFile, file.write)
    except NameError:
        print("Error read file list")
        time.sleep(1)
        FTPhistory()
    except TimeoutError:
        ConnectionError()
        return


def CSVhistory():
    fileList = os.listdir(dtlFolder)
    for fileNum in fileList:
        dtlFile = fileNum
        csvFile = f"{fileNum[:8]}.csv"
        xlsFile = f"{fileNum[:8]}.xls"
        subprocess.run(f'{converter} /b0 /t0 "{dtlFolder}{dtlFile}" "{csvFolder}{csvFile}"', shell=True)
        subprocess.run(f'{converter} /b0 /t0 "{dtlFolder}{dtlFile}" "{xlsFolder}{xlsFile}"', shell=True)


def CurrentUpdate():
    while True:
        try:
            remoteFile = ''.join(fileList[-1:])
            localFile = f"{dtlFolder}{remoteFile}"
            with open(localFile, "wb") as file:
                ftp.retrbinary("RETR %s" % remoteFile, file.write)
        except TimeoutError:
            ConnectionError()
            return
        except NameError:
            print("Error open FTP document")
            return
        dtlList = os.listdir(dtlFolder)
        dtlFile = ''.join(dtlList[-1:])
        csvFile = f"{dtlFile[:8]}.csv"
        xlsFile = f"{dtlFile[:8]}.xls"
        subprocess.run(f'{converter} /b0 /t0 "{dtlFolder}{dtlFile}" "{csvFolder}{csvFile}"', shell=True)
        subprocess.run(f'{converter} /b0 /t0 "{dtlFolder}{dtlFile}" "{xlsFolder}{xlsFile}"', shell=True)
        time.sleep(5)


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
    filePath = csvFolder + ''.join(fileList[-1])
    choice = graphDefault.get()
    choiceTime = graphPeriods[graphLabels.index(choice)]
    try:
        timeNow = datetime.strptime(currentTime, "%H:%M:%S")
        timeDif = datetime.strptime(choiceTime, "%H:%M:%S")
        timeBegin = str(timeNow - timeDif)
        frameData = pandas.read_csv(filePath, sep=",", header=0, usecols=[1, 2, 3, 4, 5])
        frameColumns = ["Time", "TemperatureCurrent", "TemperatureSet", "HumidityCurrent", "HumiditySet"]
        frameCurrent = frameData.loc[frameData["Time"] >= timeBegin, frameColumns]
        print("Normal reading data")
        print(timeBegin)
    except ValueError:
        print("Time read error")
        filePathPrev = csvFolder + ''.join(fileList[-2])
        frameDataPrev = pandas.read_csv(filePathPrev, sep=",", header=0, usecols=[1, 2, 3, 4, 5])
        frameColumns = ["Time", "TemperatureCurrent", "TemperatureSet", "HumidityCurrent", "HumiditySet"]
        frameCurrentPrev = frameDataPrev.loc[((frameDataPrev["Time"] >= "23:00:00") & (frameDataPrev["Time"] <= "23:59:59")), frameColumns]
        frameDataNow = pandas.read_csv(filePath, sep=",", header=0, usecols=[1, 2, 3, 4, 5])
        frameCurrentNow = frameDataPrev.loc[((frameDataNow["Time"] >= "00:00:00") & (frameDataNow["Time"] <= "02:00:00")), frameColumns]
        frameCurrent = pandas.concat([frameCurrentPrev, frameCurrentNow], ignore_index=True)
        print(filePathPrev)
    except FileNotFoundError:
        print("File not found")
        return
    except UnboundLocalError:
        print("Time format error")
    figure.clear()
    lox = matplotlib.ticker.LinearLocator(24)
    graphTemp = figure.add_subplot(111)
    graphTemp.xaxis.set_major_locator(lox)
    graphTemp.set_facecolor(bgLoc)
    graphTemp.set_title(machineName, color="yellow")
    try:
        graphTemp.plot(frameCurrent["Time"], frameCurrent["TemperatureCurrent"], "-w",
                            frameCurrent["Time"], frameCurrent["TemperatureSet"], "--c")
        graphTemp.set_ylabel("Температура, °C", color="white")
        graphTemp.grid(alpha=0.5, linestyle="-", color="cyan", linewidth=0.3)
        graphTemp.tick_params(labelsize=8, colors="yellow")
        if modeIndex == 2:
            graphTemp.fill_between(x=frameCurrent["Time"], y1=frameCurrent["TemperatureCurrent"],
                               y2=frameCurrent["TemperatureSet"], alpha=0.2)
        if modeIndex == 3:
            graphHum = graphTemp.twinx()
            graphHum.set_ylabel("Влажность, %", color="red")
            graphHum.plot(frameCurrent["Time"], frameCurrent["HumidityCurrent"], "-r",
                      frameCurrent["Time"], frameCurrent["HumiditySet"], "--m")
            graphHum.fill_between(x=frameCurrent["Time"], y1=frameCurrent["HumidityCurrent"],
                              y2=frameCurrent["HumiditySet"], alpha=0.2)
            graphHum.grid(alpha=0.6, linestyle=":", color="red")
            graphHum.tick_params(labelsize=8, colors="yellow")
    except UnboundLocalError:
        print("Plot error")
    except TypeError:
        print("Error read data. Need to restart")
        labelNotif["fg"] = "red"
    else:
        labelNotif["fg"] = bgLoc
    figure.autofmt_xdate()
    canvasGraph.draw()
    canvasGraph.get_tk_widget().place(x=20, y=290)

    root.after(5000, Plot)


def SaveFigure():
    os.mkdir(picFolder) if not os.path.isdir(picFolder) else None
    figure.savefig(f"{picFolder}{picname}")


def UpdateHeat(index=0):
    try:
        framePic = framesHeat[index]
        index += 1
        if index == 14:
            index = 0
        heatLabel.configure(image=framePic, borderwidth=0)
        root.after(50, UpdateHeat, index)
    except Exception:
        print("error")
        return


def UpdateCold(index=0):
    framePic = framesCold[index]
    index += 1
    if index == 10:
        index = 0
    coldLabel.configure(image=framePic, borderwidth=0)
    root.after(100, UpdateCold, index)


def UpdateWet(index=0):
    framePic = framesWet[index]
    index += 1
    if index == 12:
        index = 0
    wetLabel.configure(image=framePic, borderwidth=0)
    root.after(100, UpdateWet, index)


def UpdateDry(index=0):
    framePic = framesDry[index]
    index += 1
    if index == 10:
        index = 0
    dryLabel.configure(image=framePic, borderwidth=0)
    root.after(100, UpdateDry, index)


def UpdateIdleTemp(index=0):
    framePic = framesIdle[index]
    index += 1
    if index == 12:
        index = 0
    idleTempLabel.configure(image=framePic, borderwidth=0)
    root.after(100, UpdateIdleTemp, index)


def UpdateIdleHum(index=0):
    framePic = framesIdle[index]
    index += 1
    if index == 12:
        index = 0
    idleHumLabel.configure(image=framePic, borderwidth=0)
    root.after(100, UpdateIdleHum, index)


root = Tk()
root.title("Модуль удалённого контроля климатической камеры")
root.geometry("1000x800")
root.wm_geometry("+%d+%d" % (100, 100))
root["bg"] = bgGlob
root.resizable(False, False)
icon = PhotoImage(file="icons\\icon.png")
root.iconphoto(False, icon)

canvas = Canvas(width=998, height=698, bg=bgGlob, highlightthickness=1, highlightbackground=bgGlob)
canvas.place(x=0, y=80)
canvas.create_rectangle(18, 8, 308, 188, fill="#352642", outline="#241C2B")
canvas.create_rectangle(10, 0, 300, 180, fill="#510D70", outline="#510D70")
canvas.create_rectangle(338, 8, 638, 188, fill="#352642", outline="#241C2B")
canvas.create_rectangle(330, 0, 630, 180, fill="#510D70", outline="#510D70")
canvas.create_rectangle(668, 8, 988, 188, fill="#352642", outline="#241C2B")
canvas.create_rectangle(660, 0, 980, 180, fill="#510D70", outline="#510D70")
canvas.create_rectangle(18, 208, 988, 698, fill="#352642", outline="#241C2B")
canvas.create_rectangle(10, 200, 980, 690, fill="#510D70", outline="#510D70")

framesHeat = [PhotoImage(file="icons\\heat.gif", format="gif -index %i" %(i)) for i in range(15)]
framesCold = [PhotoImage(file="icons\\cold.gif", format="gif -index %i" %(i)) for i in range(10)]
framesWet = [PhotoImage(file="icons\\wet.gif", format="gif -index %i" %(i)) for i in range(12)]
framesDry = [PhotoImage(file="icons\\dry.gif", format="gif -index %i" %(i)) for i in range(10)]
framesIdle = [PhotoImage(file="icons\\idle.gif", format="gif -index %i" %(i)) for i in range(12)]
# heatLabel = tkinter.Label(root)
coldLabel = tkinter.Label(root)
wetLabel = tkinter.Label(root)
dryLabel = tkinter.Label(root)
idleTempLabel = tkinter.Label(root)
idleHumLabel = tkinter.Label(root)
# heatLabel.place(x=340, y=90)
# coldLabel.place(x=440, y=90)
# idleTempLabel.place(x=540, y=90)
# wetLabel.place(x=340, y=180)
# dryLabel.place(x=440, y=180)
# idleHumLabel.place(x=540, y=180)

threadModbus = threading.Thread(target=ReadModbusTCP, daemon=True, name="modbus")
threadFTP = threading.Thread(target=CurrentUpdate, daemon=True, name='ftp')

# root.after(0, UpdateHeat)
# root.after(0, UpdateCold)
# root.after(0, UpdateIdleTemp)
# root.after(0, UpdateWet)
# root.after(0, UpdateDry)
# root.after(0, UpdateIdleHum)

logoLabel = Label(font=("Arial", 10, "bold"), fg=fgComm, bg=bgGlob)
armIPLabel = Label(fg=fgComm, bg=bgGlob)
panelIPLabel = Label(fg=fgComm, bg=bgGlob)
panelNameLabel = Label(fg=fgComm, bg=bgGlob)
panelDateLabel = Label(fg=fgComm, bg=bgGlob, anchor="e")
panelTimeLabel = Label(fg=fgComm, bg=bgGlob, anchor="e")
statusLabel = Label(anchor="e", fg=fgComm, bg=bgLoc)
statusValue = Label(fg=fgVal, bg=bgLoc)
modeLabel = Label(anchor="e", fg=fgComm, bg=bgLoc)
modeValue = Label(fg=fgVal, bg=bgLoc)
tempCurLabel = Label(anchor="e", fg=fgComm, bg=bgLoc)
tempCurValue = Label(fg=fgVal, bg=bgLoc)
tempSetLabel = Label(anchor="e", fg=fgComm, bg=bgLoc)
tempSetValue = Label(fg=fgVal, bg=bgLoc)
humCurLabel = Label(anchor="e", fg=fgComm, bg=bgLoc)
humCurValue = Label(fg=fgVal, bg=bgLoc)
humSetLabel = Label(anchor="e", fg=fgComm, bg=bgLoc)
humSetValue = Label(fg=fgVal, bg=bgLoc)
labelPeriods = Label(anchor="w", fg=fgComm, bg=bgLoc)
labelNotif = Label(anchor="w", fg=bgLoc, bg=bgLoc)

figure = Figure(figsize=(9.5, 4.7), dpi=100, facecolor=bgLoc)
canvasGraph = FigureCanvasTkAgg(figure=figure, master=root)

# view = ttk.Style().configure("TButton", background="red", foreground="red", color="red", relief="flat")

ttk.Style().configure("TButton", font="helvetica 8", background="red", relief="sunken")
buttonSave = ttk.Button(command=SaveFigure, style="TButton", text="Сохранить график")
buttonName = ttk.Button(command=DeleteButton, style="TButton", text="Задать наименование установки")

b1 = ttk.Button(command=ShowGif).place(x=700, y=10, width=50)
b2 = ttk.Button(command=HideGif).place(x=700, y=30, width=50)

ObjectsPlace()
GetLocalIP()
# CheckIP()

root.mainloop()
