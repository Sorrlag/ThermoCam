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
from tkinter_input_box.input_box import InputBox
import re
from collections import deque as last
from functools import reduce
from datetime import datetime, timedelta
import modbus_tk.defines as communicate
import modbus_tk.modbus_tcp as modbus_tcp
import matplotlib.ticker
import matplotlib.dates
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import pandas


xLabelPos, xValuePos, yPos = 20, 190, 100
localIP, panelIP, panelDate, panelTime, currentTime, filename, picname = "", "", "", "", "", "", ""
fgComm, fgVal, bgGlob, bgLoc = "white", "yellow", "#2B0542", "#510D70"
status = ("НЕТ СВЯЗИ", "АВАРИЯ", "РАБОТА", "ОСТАНОВ")
mode = ("НЕТ СВЯЗИ", "НАСТРОЙКА", "ТЕРМО", "ВЛАГА")
statusIndex, modeIndex = 0, 0
listIP = {}
temperatureCurrent, temperatureSet = -1.1, -1.1
humidityCurrent, humiditySet = 1.1, 1.1
version, tmin, tmax = 0, 0, 0
rootFolder = f"C:\\Cont\\"
picFolder = f"{rootFolder}Graph\\"
converter = f"{rootFolder}Converter\\easyсonverter.exe"
dtlFolder = f"{rootFolder}Converter\\data\\"
csvFolder = f"{rootFolder}\\CSV\\"
xlsFolder = f"{rootFolder}\\XLS\\"
machineIP, machineName = "", ""
sliceActive = sliceChange = showSlice = showError = showButton = False
sliceDateFrom, sliceDateTo, sliceTimeFrom, sliceTimeTo = "", "", "", ""
baseMode, baseStatus = "Temperature", "Stop"
heat = cold = idleT = wet = dry = idleH = False
onlinePlot = True
humidity = False
connect = False


def ObjectsPlace():
    logoLabel.place(x=650, y=780)
    panelDateLabel.place(x=880, y=15, width=100)
    panelTimeLabel.place(x=880, y=35, width=100)
    armIPLabel.place(x=350, y=15)
    panelIPLabel.place(x=350, y=35)
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


def GlobalStatus():

    def ChangeTempStatus(climate, value):
        global heat, cold, idleT
        if value is True:
            match climate:
                case "heat":
                    heat = True
                    ShowGif("heat")
                case "cold":
                    cold = True
                    ShowGif("cold")
                case "idleT":
                    idleT = True
                    ShowGif("idleT")
        if value is False:
            match climate:
                case "heat":
                    heat = False
                    HideGif("heat")
                case "cold":
                    cold = False
                    HideGif("cold")
                case "idleT":
                    idleT = False
                    HideGif("idleT")

    def ChangeHumStatus(climate, value):
        global wet, dry, idleH
        if value is True:
            match climate:
                case "wet":
                    wet = True
                    ShowGif("wet")
                case "dry":
                    dry = True
                    ShowGif("dry")
                case "idleH":
                    idleH = True
                    ShowGif("idleH")
        if value is False:
            match climate:
                case "wet":
                    wet = False
                    HideGif("wet")
                case "dry":
                    dry = False
                    HideGif("dry")
                case "idleH":
                    idleH = False
                    HideGif("idleH")

    global baseStatus, baseMode, heat, cold, idleT, wet, dry, idleH, \
        temperatureCurrent, temperatureSet, humidityCurrent, humiditySet
    baseStatus = "Run" if statusIndex == 2 else "Stop"
    if modeIndex == 2:
        baseMode = "Temperature"
    if modeIndex == 3:
        baseMode = "Humidity"
    if (baseStatus == "Run") & (modeIndex >= 2):
        if temperatureCurrent <= (temperatureSet - 2):
            ChangeTempStatus("heat", True) if heat is False else None
        else:
            ChangeTempStatus("heat", False) if heat is True else None
        if temperatureCurrent >= (temperatureSet + 2):
            ChangeTempStatus("cold", True) if cold is False else None
        else:
            ChangeTempStatus("cold", False) if cold is True else None
        if (temperatureCurrent > (temperatureSet - 2)) & (temperatureCurrent < (temperatureSet + 2)):
            ChangeTempStatus("idleT", True) if idleT is False else None
        else:
            ChangeTempStatus("idleT", False) if idleT is True else None
    else:
        ChangeTempStatus("heat", False) if heat is True else None
        ChangeTempStatus("cold", False) if cold is True else None
        ChangeTempStatus("idleT", False) if idleT is True else None

    if (baseStatus == "Run") & (modeIndex == 3):
        if humidityCurrent <= (humiditySet - 2):
            ChangeHumStatus("wet", True) if wet is False else None
        else:
            ChangeHumStatus("wet", False) if wet is True else None
        if humidityCurrent >= (humiditySet + 2):
            ChangeHumStatus("dry", True) if dry is False else None
        else:
            ChangeHumStatus("dry", False) if dry is True else None
        if (humidityCurrent > (humiditySet - 2)) & (humidityCurrent < (humiditySet + 2)):
            ChangeHumStatus("idleH", True) if idleH is False else None
        else:
            ChangeHumStatus("idleH", False) if idleH is True else None
    else:
        ChangeHumStatus("wet", False) if wet is True else None
        ChangeHumStatus("dry", False) if dry is True else None
        ChangeHumStatus("idleH", False) if idleH is True else None

    root.after(1000, GlobalStatus)


def ShowGif(ani):
    global heatLabel, coldLabel, idleTempLabel, wetLabel, dryLabel, idleHumLabel
    match ani:
        case "heat":
            heatLabel = tkinter.Label(root)
            heatLabel.place(x=50, y=10)
            UpdateGif("heat")
        case "cold":
            coldLabel = tkinter.Label(root)
            coldLabel.place(x=50, y=10)
            UpdateGif("cold")
        case "idleT":
            idleTempLabel = tkinter.Label(root)
            idleTempLabel.place(x=50, y=10)
            UpdateGif("idleT")
        case "wet":
            wetLabel = tkinter.Label(root)
            wetLabel.place(x=190, y=10)
            UpdateGif("wet")
        case "dry":
            dryLabel = tkinter.Label(root)
            dryLabel.place(x=190, y=10)
            UpdateGif("dry")
        case "idleH":
            idleHumLabel = tkinter.Label(root)
            idleHumLabel.place(x=190, y=10)
            UpdateGif("idleH")


def HideGif(ani):
    global heatLabel, coldLabel, idleTempLabel, wetLabel, dryLabel, idleHumLabel
    match ani:
        case "heat":
            heatLabel.destroy()
        case "cold":
            coldLabel.destroy()
        case "idleT":
            idleTempLabel.destroy()
        case "wet":
            wetLabel.destroy()
        case "dry":
            dryLabel.destroy()
        case "idleH":
            idleHumLabel.destroy()


def UpdateGif(ani, index=0):
    try:
        match ani:
            case "heat":
                framePic = framesHeat[index]
                index += 1
                if index == 14:
                    index = 0
                heatLabel.configure(image=framePic, borderwidth=0)
            case "cold":
                framePic = framesCold[index]
                index += 1
                if index == 10:
                    index = 0
                coldLabel.configure(image=framePic, borderwidth=0)
            case "idleT":
                framePic = framesIdleT[index]
                index += 1
                if index == 11:
                    index = 0
                idleTempLabel.configure(image=framePic, borderwidth=0)
            case "wet":
                framePic = framesWet[index]
                index += 1
                if index == 12:
                    index = 0
                wetLabel.configure(image=framePic, borderwidth=0)
            case "dry":
                framePic = framesDry[index]
                index += 1
                if index == 10:
                    index = 0
                dryLabel.configure(image=framePic, borderwidth=0)
            case "idleH":
                framePic = framesIdleH[index]
                index += 1
                if index == 11:
                    index = 0
                idleHumLabel.configure(image=framePic, borderwidth=0)
        root.after(100, UpdateGif, ani, index)
    except Exception:
        return


def ChangeName():

    def Accept():
        global machineName, listIP, frameIP, machinesList, machineDefault
        machineName = newName.get()
        listIP[machineIP] = machineName
        machinesList["values"] = [f"{k} :: {v}" for k, v in listIP.items()]
        machineDefault.set(value=f"{machineIP} :: {machineName}")
        frameIP = pandas.DataFrame(list(listIP.items()), columns=["ip", "name"])
        frameIP.to_csv(f"{rootFolder}config.ini", index=False)
        frameName.destroy()

    def Decline():
        frameName.destroy()

    frameName = tkinter.Frame(master=root, borderwidth=1, width=240, height=25, bg=bgLoc)
    frameName.place(x=360, y=114)
    newName = InputBox(container=frameName, placeholder="Введите наименование", placeholder_color="dim gray",
                       input_type="text", justify="center")
    newName.place(x=30, y=1, width=180, height=22)
    ttk.Button(master=frameName, style="TButton", image=acceptImage, compound=TOP, command=Accept)\
        .place(x=0, y=0, width=24, height=24)
    ttk.Button(master=frameName, style="TButton", image=declineImage, command=Decline)\
        .place(x=216, y=0, width=24, height=24)


def AddMachine():

    def Accept():
        newlist = listIP
        print(newlist)
        newIP = newAddress.get()
        newlist[newIP] = "new machine"
        print(newlist)
        frameAdd.destroy()

    def Decline():
        frameAdd.destroy()

    frameAdd = tkinter.Frame(master=root, borderwidth=1, width=240, height=25, bg=bgLoc)
    frameAdd.place(x=360, y=114)
    newAddress = InputBox(container=frameAdd, placeholder="Введите IP адрес", placeholder_color="dim gray",
                          input_type="text", justify="center")
    newAddress.place(x=30, y=1, width=180, height=22)
    ttk.Button(master=frameAdd, style="TButton", image=acceptImage, compound=TOP, command=Accept)\
        .place(x=0, y=0, width=24, height=24)
    ttk.Button(master=frameAdd, style="TButton", image=declineImage, compound=TOP, command=Decline)\
        .place(x=216, y=0, width=24, height=24)


def GetLocalIP():
    global localIP
    hostname = socket.gethostname()
    localIP = socket.gethostbyname(hostname)


def CheckIP():
    global machineIP, machineName, frameIP, listIP
    configPath = f"{rootFolder}config.ini"
    frameIP = pandas.read_csv(configPath, sep=",")
    if frameIP.empty:
        if machineIP == "":
            InputIP()
        else:
            machineName = "Климатическая установка"
            listIP = {machineIP: machineName}
            frameIP = pandas.DataFrame(list(listIP.items()), columns=["ip", "name"])
            OpenConnection()
    else:
        listIP = dict(zip(frameIP["ip"], frameIP["name"]))
        [machineIP] = last(listIP, maxlen=1)
        machineName = listIP[machineIP]
        OpenConnection()


def InputIP():
    def GetIP():
        global machineIP
        machineIP = entryIP.get()
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


def UpdateList():
    global frameIP
    frameIP.to_csv(f"{rootFolder}config.ini", index=False)


def OpenConnection():
    global machineIP, master, ftp, fileList, csvFolder, xlsFolder, connect
    try:
        master = modbus_tcp.TcpMaster(host=machineIP, port=502, timeout_in_sec=8)
        master.set_timeout(8.0)
    except TimeoutError:
        print("4")
        ConnectionErrorWindow()
        return
    try:
        ftp = ftplib.FTP(host=machineIP, timeout=8)
        ftp.login(user="uploadhis", passwd="111111")
        ftp.cwd("datalog/data")
        fileList = ftp.nlst()
        csvFolder = f"{rootFolder}{machineIP}\\CSV\\"
        xlsFolder = f"{rootFolder}{machineIP}\\XLS\\"
    except TimeoutError:
        print("5")
        ConnectionErrorWindow()
        return
    except AttributeError:
        print("6")
        ConnectionErrorWindow()
        return
    except ftplib.error_perm:
        DeviceErrorWindow()
        return
    threadModbus.start() if not threadModbus.is_alive() else None
    LabelsShow()
    UserControl()
    HistoryFTP()
    HistoryCSV()
    threadFTP.start() if not threadFTP.is_alive() else None
    UpdateList()
    GetPeriod()
    GlobalStatus()
    time.sleep(3)
    Plot()


def ConnectionErrorWindow():

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


def DeviceErrorWindow():
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

    info = tkinter.Label(master=screenError, bg="yellow", text="Невозможно установить связь!")
    info.place(x=10, y=10, width=280)
    buttonClose = ttk.Button(master=screenError, text="Завершить", command=sys.exit)
    buttonClose.place(x=20, y=60, width=260)


def ReadModbusTCP():
    global panelIP, panelDate, panelTime, currentTime, filename, picname, \
        temperatureCurrent, temperatureSet, humidityCurrent, humiditySet, modeIndex, statusIndex, version, tmin, tmax
    while True:
        try:
            getSys = master.execute(1, communicate.READ_INPUT_REGISTERS, 10099, 10)
            getTempCur = master.execute(1, communicate.READ_INPUT_REGISTERS, 10109, 1)
            getTempSet = master.execute(1, communicate.READ_INPUT_REGISTERS, 10110, 1)
            getHumCur = master.execute(1, communicate.READ_INPUT_REGISTERS, 10111, 1)
            getHumSet = master.execute(1, communicate.READ_INPUT_REGISTERS, 10112, 1)
            getStatus = master.execute(1, communicate.READ_INPUT_REGISTERS, 10115, 1)
            getMode = master.execute(1, communicate.READ_INPUT_REGISTERS, 10114, 1)
            getVersion = master.execute(1, communicate.READ_INPUT_REGISTERS, 10116, 1)
            getTmin = master.execute(1, communicate.READ_INPUT_REGISTERS, 10117, 1)
            getTmax = master.execute(1, communicate.READ_INPUT_REGISTERS, 10118, 1)

            panelIP = f"{getSys[0]}.{getSys[1]}.{getSys[2]}.{getSys[3]}"
            panelDate = f"{getSys[4]:02} / {getSys[5]:02} / {getSys[6]}"
            panelTime = f"{getSys[7]:02} : {getSys[8]:02} : {getSys[9]:02}"
            currentTime = f"{getSys[7]:02}:{getSys[8]:02}:{getSys[9]:02}"
            filename = f"{getSys[6]:04}{getSys[5]:02}{getSys[4]:02}"
            picname = f"{getSys[6]}{getSys[5]:02}{getSys[4]:02}_{getSys[7]:02}{getSys[8]:02}{getSys[9]:02}"
            temperatureCurrent = (getTempCur[0] - 2**16) / 10 if getTempCur[0] > 2**15 else getTempCur[0] / 10
            temperatureSet = (getTempSet[0] - 2**16) / 10 if getTempSet[0] > 2**15 else getTempSet[0] / 10
            humidityCurrent = getHumCur[0] / 10
            humiditySet = getHumSet[0]
            statusIndex = int(getStatus[0])
            modeIndex = int(getMode[0])
            version = int(getVersion[0])
            tmin = int(getTmin[0]) - 2**16 if getTmin[0] > 2**15 else int(getTmin[0])
            tmax = int(getTmax[0]) - 2**16 if getTmax[0] > 2**15 else int(getTmax[0])
        except UnboundLocalError:
            print("Modbus format error")
            DeviceErrorWindow()
            return
        except TimeoutError:
            print("1")
            ConnectionErrorWindow()
            return
        except ConnectionRefusedError:
            print("Modbus read error")
            DeviceErrorWindow()
            return
        time.sleep(1)


def HistoryFTP():
    try:
        for fileNum in fileList:
            remoteFile = fileNum
            localFile = f"{dtlFolder}{remoteFile}"
            os.mkdir(dtlFolder) if not os.path.exists(dtlFolder) else None
            with open(localFile, "wb") as file:
                ftp.retrbinary("RETR %s" % remoteFile, file.write)
    except NameError:
        DeviceErrorWindow()
        return
    except TimeoutError:
        print("2")
        ConnectionErrorWindow()
        return
    except FileNotFoundError:
        DeviceErrorWindow()
        return


def HistoryCSV():
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
            print("3")
            ConnectionErrorWindow()
            return
        except NameError:
            DeviceErrorWindow()
            return
        except FileNotFoundError:
            print("Current day file not found")
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
    # root.after(1000, WriteFile)


def UserControl():
    global graphLabels, graphPeriods, graphDefault, machineDefault, listIP, machinesList
    graphLabels = ["5 минут", "15 минут", "30 минут", "1 час", "2 часа", "4 часа", "<Настроить>"]
    graphPeriods = ["00:05:00", "00:15:00", "00:30:00", "01:00:00", "02:00:00", "04:00:00", "00:01:00"]
    graphDefault = StringVar(value=graphLabels[0])
    graphPeriod = ttk.Combobox(values=graphLabels, textvariable=graphDefault, width=21, state="readonly",
                               background=bgLoc, foreground=bgLoc)
    graphPeriod.place(x=820, y=90)
    buttonSave.place(x=830, y=225, width=140, height=30)
    buttonRename.place(x=360, y=115, width=115)
    buttonAdd.place(x=485, y=115, width=115)
    buttonStatus.place(x=360, y=155, width=240)
    buttonSpeed.place(x=360, y=180, width=240)
    buttonSetTemp.place(x=360, y=205, width=240)
    buttonSetHum.place(x=360, y=230, width=240)
    machineDefault = StringVar(value=f"{machineIP} :: {machineName}")
    machinesList = ttk.Combobox(values=[f"{k} :: {v}" for k, v in listIP.items()], textvariable=machineDefault,
                                state="readonly", background=bgLoc, foreground=bgLoc)
    machinesList.place(x=360, y=90, width=240)
    navi = NavigationToolbar2Tk(canvasGraph)
    navi.configure(background=bgLoc)
    navi.place(x=670, y=220, width=155, height=40)


def GetPeriod():

    def StartStopPlot():
        global onlinePlot
        onlinePlot = not onlinePlot
        Plot() if onlinePlot else None

    global showSlice, sliceActive, buttonEdit, buttonOnline, onlinePlot, showButton
    choice = graphLabels.index(graphDefault.get())
    if (choice == 6) & (showSlice is False):
        showSlice = True
        buttonEdit = ttk.Button(command=ShowSlice, style="TButton", text="Изменить диапазон")
        buttonEdit.place(x=670, y=130, width=300)
        ShowSlice()
    if (choice != 6) & (showSlice is True):
        showSlice = False
        sliceActive = False
        buttonEdit.destroy()
        HideSlice()
        print("This one 1")
        Plot()
    if choice != 6:
        if showButton is False:
            buttonOnline = ttk.Button(root, style="TButton", command=StartStopPlot)
            buttonOnline.place(x=670, y=180, width=300)
            showButton = True
        buttonOnline["text"] = "Остановить выборку в реальном времени" if onlinePlot \
            else "Возобновить выборку в реальном времени"
    if (choice == 6) & showButton is True:
        buttonOnline.destroy()
        showButton = False

    root.after(1000, GetPeriod)


def ShowSlice():

    def GetSlice(climate):
        global sliceActive, sliceDateFrom, sliceDateTo, sliceTimeFrom, sliceTimeTo, onlinePlot, humidity
        sliceDateFrom = "2024"+monthFrom.get()+dayFrom.get()
        sliceTimeFrom = f"{hourFrom.get()}:{minutesFrom.get()}:00"
        sliceDateTo = "2024"+monthTo.get()+dayTo.get()
        sliceTimeTo = f"{hourTo.get()}:{minutesTo.get()}:00"
        sliceActive = True
        onlinePlot = True
        humidity = climate
        print(climate)
        print("This one 2")
        Plot()
        HideSlice()

    def TimeValidControl():
        dateInitialSet = datetime.strptime(f"{dayInitial.get()}/{monthInitial.get()}/{yearNow}", "%d/%m/%Y")
        dateFinalSet = datetime.strptime(f"{dayFinal.get()}/{monthFinal.get()}/{yearNow}", "%d/%m/%Y")
        if dateInitialSet == dateFinalSet:
            if dateInitialSet == datetime.strptime(panelDate, "%d / %m / %Y"):
                if hourFinal.get() > panelTime[0:2]:
                    hourFinal.set(value=panelTime[0:2])
                if (hourFinal.get() == panelTime[0:2]) & (minutesFinal.get() > panelTime[5:7]):
                    minutesFinal.set(value=panelTime[5:7])
            else:
                if (hourFinal.get() == "00") & (minutesFinal.get() == "00"):
                    minutesFinal.set(value="01")
                if hourInitial.get() > hourFinal.get():
                    hourInitial.set(value=str(hourFinal.get()))
                if (hourInitial.get() == hourFinal.get()) & (minutesInitial.get() >= minutesFinal.get()):
                    if minutesFinal.get() == "00":
                        hourInitial.set(value=f"{(int(hourFinal.get())-1):02.0f}")
                        minutesInitial.set(value="59")
                    else:
                        minutesInitial.set(value=f"{(int(minutesFinal.get())-1):02.0f}")

    def DateValidControl(direction):
        global dateInitial
        try:
            dateInitial = datetime.strptime(f"{dayInitial.get()}/{monthInitial.get()}/{yearNow}",
                                            "%d/%m/%Y")
        except ValueError:
            if direction == "down":
                dateInitial = datetime.strptime(f"{int(dayInitial.get())+1}/{monthInitial.get()}/{yearNow}",
                                                "%d/%m/%Y")
                dateInitial = dateInitial - timedelta(days=1)
            if direction == "up":
                dateInitial = datetime.strptime(f"{int(dayInitial.get())-1}/{monthInitial.get()}/{yearNow}",
                                                "%d/%m/%Y")
                dateInitial = dateInitial + timedelta(days=1)
        dayInitial.set(value=datetime.strftime(dateInitial, "%d/%m/%Y")[0:2])
        monthInitial.set(value=datetime.strftime(dateInitial, "%d/%m/%Y")[3:5])
        hourInitial.set(value="00")
        minutesInitial.set(value="00")
        dateFinal = datetime.strptime(f"{dayFinal.get()}/{monthFinal.get()}/{yearNow}", "%d/%m/%Y")
        if (dateFinal - dateInitial) > timedelta(days=1):
            dayFinal.set(value=datetime.strftime(dateInitial + timedelta(days=1), "%d/%m/%Y")[0:2])
            monthFinal.set(value=datetime.strftime(dateInitial + timedelta(days=1), "%d/%m/%Y")[3:5])
            hourFinal.set(value="23")
            minutesFinal.set(value="59")
        if dateFinal < dateInitial:
            dayFinal.set(value=datetime.strftime(dateInitial, "%d/%m/%Y")[0:2])
            monthFinal.set(value=datetime.strftime(dateInitial, "%d/%m/%Y")[3:5])
            hourFinal.set(value="23")
            minutesFinal.set(value="59")
        if dateInitial == datetime.strptime(panelDate, "%d / %m / %Y"):
            dayInitial.set(value=panelDate[0:2])
            monthInitial.set(value=panelDate[5:7])
            dayFinal.set(value=panelDate[0:2])
            monthFinal.set(value=panelDate[5:7])
            hourFinal.set(value=panelTime[0:2])
            minutesFinal.set(value=panelTime[5:7])

    global sliceFrame
    dayValidControl = root.register(DateValidControl)
    dayInitial = StringVar(value=panelDate[0:2])
    dayFinal = StringVar(value=panelDate[0:2])
    monthInitial = StringVar(value=panelDate[5:7])
    monthFinal = StringVar(value=panelDate[5:7])
    yearNow = StringVar(value=panelDate[10:14]).get()
    hourInitial = StringVar(value="00")
    minutesInitial = StringVar(value="00")
    hourFinal = StringVar(value=panelTime[0:2])
    minutesFinal = StringVar(value=panelTime[5:7])

    sliceFrame = tkinter.Frame(master=root, borderwidth=1, width=300, height=140, bg=bgLoc)
    sliceFrame.place(x=670, y=120)
    ttk.Button(master=sliceFrame, text="< °C >", command=lambda: GetSlice(False), style="TButton")\
        .place(x=0, y=110, width=150, height=25)
    ttk.Button(master=sliceFrame, text="< °C > + < %RH >", command=lambda: GetSlice(True), style="TButton") \
        .place(x=160, y=110, width=150, height=25)

    tkinter.Label(master=sliceFrame, text="Начало выборки", anchor="w", bg=bgLoc, fg="white").place(x=0, y=10, height=20)
    tkinter.Label(master=sliceFrame, text="Дата:", anchor="e", bg=bgLoc, fg="white").place(x=120, y=0, width=50, height=20)
    dayFrom = tkinter.Spinbox(master=sliceFrame, from_=0, to=32, state="readonly", format="%02.0f",
                              textvariable=dayInitial, command=(dayValidControl, "%d"),
                              buttonbackground=bgLoc, foreground=bgLoc)
    dayFrom.place(x=180, y=0, width=30, height=20)
    tkinter.Label(master=sliceFrame, text=".", bg=bgLoc, fg="white").place(x=215, y=0, width=5, height=20)
    monthFrom = tkinter.Spinbox(master=sliceFrame, from_=1, to=12, state="disabled", format="%02.0f",
                                textvariable=monthInitial, buttonbackground="dim gray", foreground=bgLoc)
    monthFrom.place(x=225, y=0, width=30, height=20)
    tkinter.Label(master=sliceFrame, text=f" .  {yearNow}", anchor="w", bg=bgLoc, fg="white").place(x=255, y=0, width=40, height=20)
    tkinter.Label(master=sliceFrame, text="Время:", anchor="e", bg=bgLoc, fg="white").place(x=120, y=25, width=50, height=20)
    hourFrom = tkinter.Spinbox(master=sliceFrame, from_=0, to=23, state="readonly", format="%02.0f",
                               textvariable=hourInitial, command=TimeValidControl,
                               buttonbackground=bgLoc, foreground=bgLoc)
    hourFrom.place(x=180, y=25, width=30, height=20)
    tkinter.Label(master=sliceFrame, text=":", bg=bgLoc, fg="white").place(x=215, y=25, width=5, height=20)
    minutesFrom = tkinter.Spinbox(master=sliceFrame, from_=0, to=55, state="readonly", format="%02.0f",
                                  textvariable=minutesInitial, command=TimeValidControl,
                                  buttonbackground=bgLoc, foreground=bgLoc)
    minutesFrom.place(x=225, y=25, width=30, height=20)
    tkinter.Label(master=sliceFrame, text=" :  00", anchor="w", bg=bgLoc, fg="white").place(x=255, y=25, width=40, height=20)

    tkinter.Label(master=sliceFrame, text="Конец выборки", anchor="w", bg=bgLoc, fg="white").place(x=0, y=65, height=20)
    tkinter.Label(master=sliceFrame, text="Дата:", anchor="e", bg=bgLoc, fg="white").place(x=120, y=55, width=50, height=20)
    dayTo = tkinter.Spinbox(master=sliceFrame, from_=0, to=32, state="readonly", format="%02.0f",
                            textvariable=dayFinal, command=(dayValidControl, "%d"),
                            buttonbackground="dim gray", foreground=bgLoc)
    dayTo.place(x=180, y=55, width=30, height=20)
    tkinter.Label(master=sliceFrame, text=".", bg=bgLoc, fg="white").place(x=215, y=55, width=5, height=20)
    monthTo = tkinter.Spinbox(master=sliceFrame, from_=1, to=12, state="disabled", format="%02.0f",
                              textvariable=monthFinal, buttonbackground="dim gray", foreground=bgLoc)
    monthTo.place(x=225, y=55, width=30, height=20)
    tkinter.Label(master=sliceFrame, text=f" .  {yearNow}", anchor="w", bg=bgLoc, fg="white").place(x=255, y=55, width=40, height=20)
    tkinter.Label(master=sliceFrame, text="Время:", anchor="e", bg=bgLoc, fg="white").place(x=120, y=80, width=50, height=20)
    hourTo = tkinter.Spinbox(master=sliceFrame, from_=0, to=23, state="readonly", format="%02.0f",
                             textvariable=hourFinal, command=TimeValidControl,
                             buttonbackground=bgLoc, foreground=bgLoc)
    hourTo.place(x=180, y=80, width=30, height=20)
    tkinter.Label(master=sliceFrame, text=":", bg=bgLoc, fg="white").place(x=215, y=80, width=5, height=20)
    minutesTo = tkinter.Spinbox(master=sliceFrame, from_=0, to=59, state="readonly", format="%02.0f",
                                textvariable=minutesFinal, command=TimeValidControl,
                                buttonbackground=bgLoc, foreground=bgLoc, buttonuprelief="sunken")
    minutesTo.place(x=225, y=80, width=30, height=20)
    tkinter.Label(master=sliceFrame, text=" :  00", anchor="w", bg=bgLoc, fg="white").place(x=255, y=80, width=40, height=20)


def HideSlice():
    global sliceFrame
    sliceFrame.destroy()


def Plot():

    def PlotError(activate):
        global canvasError, labelError, showError
        if showError is False:
            if activate is True:
                canvasError = tkinter.Canvas(master=root, bg="yellow", width=100, height=100)
                labelError = tkinter.Label(master=canvasError, bg="yellow", fg="red", text="Ошибка чтения данных...")
                labelError.pack(fill=BOTH, expand=True)
                canvasError.place(x=430, y=500)
                showError = True
        else:
            if activate is False:
                canvasError.destroy()
                showError = False

    global sliceActive, baseMode, onlinePlot, humidity
    if onlinePlot is False:
        return
    chosenTime = graphPeriods[graphLabels.index(graphDefault.get())]
    try:
        if not sliceActive:
            fileList = os.listdir(csvFolder)
            fileMain = csvFolder + "".join(fileList[-1])
            timeNow = datetime.strptime(currentTime, "%H:%M:%S")
            timeDif = datetime.strptime(chosenTime, "%H:%M:%S")
            timeBegin = str(datetime.strptime(str(timeNow-timeDif), "%H:%M:%S").time())
            frameData = pandas.read_csv(fileMain, sep=",", header=0, usecols=[1, 2, 3, 4, 5])
            frameColumns = ["Time", "TemperatureCurrent", "TemperatureSet", "HumidityCurrent", "HumiditySet"]
            frameCurrent = frameData.loc[frameData["Time"] >= timeBegin, frameColumns]
            print("Normal reading data >>>", timeNow.time())
        else:
            if sliceDateFrom == sliceDateTo:
                fileMain = csvFolder + sliceDateFrom + ".csv"
                frameData = pandas.read_csv(fileMain, sep=",", header=0, usecols=[1, 2, 3, 4, 5])
                frameColumns = ["Time", "TemperatureCurrent", "TemperatureSet", "HumidityCurrent", "HumiditySet"]
                frameCurrent = frameData.loc[(frameData["Time"] >= sliceTimeFrom) &
                                             (frameData["Time"] <= sliceTimeTo), frameColumns]
                print("Normal reading 1-day slice data")
            else:
                fileFrom = csvFolder + sliceDateFrom + ".csv"
                fileTo = csvFolder + sliceDateTo + ".csv"
                frameDataFrom = pandas.read_csv(fileFrom, sep=",", header=0)
                frameDataTo = pandas.read_csv(fileTo, sep=",", header=0)
                frameColumns = ["Date", "Time", "TemperatureCurrent", "TemperatureSet", "HumidityCurrent", "HumiditySet"]
                frameLocalFrom = pandas.DataFrame(frameDataFrom.loc[((frameDataFrom["Time"] >= sliceTimeFrom) &
                                                                     (frameDataFrom["Time"] <= "23:59:59")), frameColumns])
                frameLocalTo = pandas.DataFrame(frameDataTo.loc[((frameDataTo["Time"] >= "00:00:00") &
                                                                 (frameDataTo["Time"] <= sliceTimeTo)), frameColumns])
                frameFrom = frameLocalFrom.loc[(frameLocalFrom.index % 2 == 0), frameColumns]
                frameTo = frameLocalTo.loc[(frameLocalTo.index % 2 == 0), frameColumns]
                frameCurrent = pandas.concat([frameFrom, frameTo], ignore_index=True)
                print("Normal reading 2-days slice data")
    except ValueError:
        print("Time read error")
        PlotError(True)
    except FileNotFoundError:
        print("File not found")
        PlotError(True)
    except UnboundLocalError:
        print("Time format error")
        PlotError(True)
    except IndexError:
        DeviceErrorWindow()
        return
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
        if ((baseMode == "Temperature") & (sliceActive is False)) | ((humidity is False) & (sliceActive is True)):
            graphTemp.fill_between(x=frameCurrent["Time"], y1=frameCurrent["TemperatureCurrent"],
                                   y2=frameCurrent["TemperatureSet"], alpha=0.2)
        if ((baseMode == "Humidity") & (sliceActive is False)) | ((humidity is True) & (sliceActive is True)):
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
        PlotError(True)
    except TypeError:
        print("Error read data")
        PlotError(True)
    else:
        PlotError(False)
    figure.autofmt_xdate()
    canvasGraph.draw()
    canvasGraph.get_tk_widget().place(x=20, y=290)
    if sliceActive:
        humidity = False
        return

    root.after(5000, Plot)


def SaveFigure():
    os.mkdir(picFolder) if not os.path.isdir(picFolder) else None
    figure.savefig(f"{picFolder}{picname}")


root = Tk()
root.title("Модуль удалённого контроля климатической камеры  |  Climcontrol v1.0a")
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
framesIdleT = [PhotoImage(file="icons\\idleT.gif", format="gif -index %i" %(i)) for i in range(11)]
framesWet = [PhotoImage(file="icons\\wet.gif", format="gif -index %i" %(i)) for i in range(12)]
framesDry = [PhotoImage(file="icons\\dry.gif", format="gif -index %i" %(i)) for i in range(10)]
framesIdleH = [PhotoImage(file="icons\\idleH.gif", format="gif -index %i" %(i)) for i in range(11)]

acceptImage = PhotoImage(file="icons\\accept.png")
declineImage = PhotoImage(file="icons\\decline.png")

threadModbus = threading.Thread(target=ReadModbusTCP, daemon=True, name="modbus")
threadFTP = threading.Thread(target=CurrentUpdate, daemon=True, name='ftp')

logoLabel = Label(font=("Arial", 10, "bold"), fg=fgComm, bg=bgGlob)
armIPLabel = Label(fg=fgComm, bg=bgGlob)
panelIPLabel = Label(fg=fgComm, bg=bgGlob)
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

figure = Figure(figsize=(9.5, 4.7), dpi=100, facecolor=bgLoc)
canvasGraph = FigureCanvasTkAgg(figure=figure, master=root)

canvasError = tkinter.Canvas(master=root, bg="red", width=100, height=100)

ttk.Style().configure("TButton", font="helvetica 8", background=bgGlob, relief="sunken", border=0, foreground="blue")
buttonSave = ttk.Button(command=SaveFigure, style="TButton", text="Сохранить график")
buttonRename = ttk.Button(command=ChangeName, style="TButton", text="Переименовать")
buttonAdd = ttk.Button(command=AddMachine, style="TButton", text="Добавить")
buttonStatus = ttk.Button(style="TButton", text="ПУСК / СТОП", state="disabled")
buttonSpeed = ttk.Button(style="TButton", text="Активировать контроль скорости", state="disabled")
buttonSetTemp = ttk.Button(style="TButton", text="Сменить уставку по температуре", state="disabled")
buttonSetHum = ttk.Button(style="TButton", text="Сменить уставку по влажности", state="disabled")

ObjectsPlace()
GetLocalIP()
CheckIP()

root.mainloop()
