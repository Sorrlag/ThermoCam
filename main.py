import subprocess
import socket
import os
import ftplib
import sys
import time
import threading
import re
from collections import deque as last
from datetime import datetime, timedelta
import modbus_tk.defines as communicate
import modbus_tk.modbus_tcp as modbus_tcp
import tkinter
import tkinter.messagebox
from tkinter import *
from tkinter import ttk
from tkinter_input_box.input_box import InputBox
import matplotlib.ticker
import matplotlib.dates
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import pandas
import logging


xLabelPos, xValuePos, yPos = 10, 180, 85
fgLab, fgVal, bgGlob, bgLoc = "white", "yellow", "#2B0542", "#510D70"
baseMode = "Temperature"
baseStatus = "Stop"
wait = 10

status = ("НЕТ СВЯЗИ", "АВАРИЯ", "РАБОТА", "ОСТАНОВ")
mode = ("НЕТ СВЯЗИ", "НАСТРОЙКА", "ТЕРМО", "ВЛАГА")
cycleTemp = ("НЕ АКТИВЕН", "ПОДДЕРЖАНИЕ", "НАГРЕВ", "ОХЛАЖДЕНИЕ")
cycleHum = ("НЕ АКТИВЕН", "ПОДДЕРЖАНИЕ", "НАСЫЩЕНИЕ", "ОСУШЕНИЕ")
cycleTech = ("НЕ АКТИВЕН", "ВЫХОД НА УСТАВКУ", "ПОДДЕРЖАНИЕ")

graphLabels = ["5 минут", "15 минут", "30 минут", "1 час", "2 часа", "4 часа", "<Настроить>"]
graphPeriods = ["00:05:00", "00:15:00", "00:30:00", "01:00:00", "02:00:00", "04:00:00", "00:05:00"]
frameColumns = ["Date", "Time", "TemperatureCurrent", "TemperatureSet", "HumidityCurrent", "HumiditySet"]
combColumns = ["Datetime", "TemperatureCurrent", "TemperatureSet", "HumidityCurrent", "HumiditySet"]
ipColumns = ["ip", "name"]

frameCurrent = frameData = frameDataFrom = frameDataTo = pandas.DataFrame(columns=frameColumns)
frameIP = pandas.DataFrame(columns=ipColumns)

runFolder = os.path.abspath(os.curdir)
rootFolder = runFolder if len(runFolder) < 4 else runFolder + "\\"
iconsFolder = getattr(sys, "_MEIPASS", os.getcwd()) + "\\icons\\"
picFolder = f"{rootFolder}graph\\"
converter = f"{rootFolder}support\\easyсonverter.exe"
sourceFolder = f"{rootFolder}support\\data\\"
csvFolder = f"{rootFolder}\\CSV\\"
xlsFolder = f"{rootFolder}\\XLS\\"

graphDefault = StringVar
currentMachine = StringVar
listIP = {}
historyFiles = []

dateNow: datetime
dateInitial: datetime
dateFinal: datetime
timeInitial: datetime
timeFinal: datetime

temperatureCurrent: float
temperatureSet: float
humidityCurrent: int
humiditySet: int
temperatureNew: int
humidityNew: int
statusNew: int
modeNew: int
version: int
tmin: int
tmax: int
statusIndex: int
modeIndex: int
cycleTempIndex: int
cycleHumIndex: int
cycleTechIndex: int
techTimer: int

localIP, panelIP, panelDate, currentDate, currentDateDot, panelTime, currentTime = "", "", "", "", "", "", ""
filename, picname, machineIP, machineName, lastlog = "", "", "", "", ""
sliceDateFrom, sliceDateTo, sliceTimeFrom, sliceTimeTo = "", "", "", ""

sliceActive = sliceChange = showSlice = showError = showButton = False
heat = cold = idleT = wet = dry = idleH = False
connection = exchange = run = draw = failConnection = failDevice = onlinePlot = humidity = actualData = xlsNeed = False
temperatureChange = humidityChange = statusChange = modeChange = False
updateData = True

master, ftp, machinesList, saved = None, None, None, None
buttonEdit, buttonOnline, sliceFrame, labelError = None, None, None, None
timeNow, timeDif, fileList, fileMain, timeBegin, graphTemp, graphHum = None, None, None, None, None, None, None
heatLabel, coldLabel, idleTempLabel, wetLabel, dryLabel, idleHumLabel = None, None, None, None, None, None

statusIndex = 0
modeIndex = 0
temperatureCurrent = 0
temperatureSet = 0
humidityCurrent = 0
humiditySet = 0
cycleTempIndex = 0
cycleHumIndex = 0
cycleTechIndex = 0
techTimer = 0
version = 0


def ObjectsPlace():
    logoLabel.place(x=650, y=720)
    panelDateLabel.place(x=880, y=15, width=100)
    panelTimeLabel.place(x=880, y=35, width=100)
    armIPLabel.place(x=350, y=15)
    panelIPLabel.place(x=350, y=35)
    statusLabel.place(x=xLabelPos, y=yPos + 0, width=150)
    statusValue.place(x=xValuePos, y=yPos + 0, width=120)
    modeLabel.place(x=xLabelPos, y=yPos + 15, width=150)
    modeValue.place(x=xValuePos, y=yPos + 15, width=120)
    tempCurLabel.place(x=xLabelPos, y=yPos + 45, width=150)
    tempCurValue.place(x=xValuePos, y=yPos + 45, width=120)
    tempSetLabel.place(x=xLabelPos, y=yPos + 60, width=150)
    tempSetValue.place(x=xValuePos, y=yPos + 60, width=120)
    humCurLabel.place(x=xLabelPos, y=yPos + 90, width=150)
    humCurValue.place(x=xValuePos, y=yPos + 90, width=120)
    humSetLabel.place(x=xLabelPos, y=yPos + 105, width=150)
    humSetValue.place(x=xValuePos, y=yPos + 105, width=120)
    labelPeriods.place(x=670, y=90)
    cycleTechLabel.place(x=xLabelPos, y=yPos + 135, width=150)
    cycleTechValue.place(x=xValuePos, y=yPos + 135, width=120)
    timerTechLabel.place(x=xLabelPos, y=yPos + 150, width=150)
    timerTechValue.place(x=xValuePos, y=yPos + 150, width=120)


def LabelsShow():
    logoLabel["text"] = "© 'МИР ОБОРУДОВАНИЯ', Санкт-Петербург, 2024"
    armIPLabel["text"] = f"IP адрес рабочей станции: {localIP}"
    panelIPLabel["text"] = f"IP адрес климатической камеры: {panelIP}"
    panelDateLabel["text"] = panelDate
    panelTimeLabel["text"] = panelTime
    statusLabel["text"] = "Статус камеры:"
    statusValue["text"] = status[statusIndex]
    modeLabel["text"] = "Режим работы:"
    modeValue["text"] = mode[modeIndex]
    tempCurLabel["text"] = "Текущая температура:"
    tempCurValue["text"] = f"{temperatureCurrent} °C"
    tempSetLabel["text"] = "Уставка по температуре:"
    tempSetValue["text"] = f"{temperatureSet} °C"
    humCurLabel["text"] = "Текущая влажность:"
    humCurValue["text"] = f"{humidityCurrent} %" if version == 2 else "Н/Д"
    humSetLabel["text"] = "Уставка по влажности:"
    humSetValue["text"] = f"{humiditySet} %" if version == 2 else "Н/Д"
    labelPeriods["text"] = "Диапазон отображения:"
    cycleTechLabel["text"] = "Технологический цикл:"
    cycleTechValue["text"] = cycleTech[cycleTechIndex]
    timerTechLabel["text"] = "Время на режиме:"
    timerTechLabel["fg"] = fgLab if techTimer > 0 else bgLoc
    timerTechValue["text"] = f"{techTimer//100} час : {techTimer%100} мин"
    timerTechValue["fg"] = fgVal if techTimer > 0 else bgLoc

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

    global baseStatus, baseMode, heat, cold, idleT, wet, dry, idleH, cycleTempIndex, cycleHumIndex, \
        temperatureCurrent, temperatureSet, humidityCurrent, humiditySet, techTimer, cycleTechIndex

    baseStatus = "Run" if statusIndex == 2 else "Stop"

    if techTimer > 0:
        cycleTechIndex = 2
    elif baseStatus == "Run":
        cycleTechIndex = 1
    else:
        cycleTechIndex = 0

    if modeIndex == 2:
        baseMode = "Temperature"
        humCurLabel["fg"] = humSetLabel["fg"] = "dim gray"
        humCurValue["fg"] = humSetValue["fg"] = "dim gray"
        buttonSetHum["state"] = "disabled"
    if modeIndex == 3:
        baseMode = "Humidity"
        humCurLabel["fg"] = humSetLabel["fg"] = fgLab
        humCurValue["fg"] = humSetValue["fg"] = fgVal
        buttonSetHum["state"] = "normal"
    if (baseStatus == "Run") & (modeIndex >= 2):
        if temperatureCurrent <= (temperatureSet - 2):
            cycleTempIndex = 2
            ChangeTempStatus("heat", True) if heat is False else None
        else:
            ChangeTempStatus("heat", False) if heat is True else None
        if temperatureCurrent >= (temperatureSet + 2):
            cycleTempIndex = 3
            ChangeTempStatus("cold", True) if cold is False else None
        else:
            ChangeTempStatus("cold", False) if cold is True else None
        if (temperatureCurrent > (temperatureSet - 2)) & (temperatureCurrent < (temperatureSet + 2)):
            cycleTempIndex = 1
            ChangeTempStatus("idleT", True) if idleT is False else None
        else:
            ChangeTempStatus("idleT", False) if idleT is True else None
    else:
        cycleTempIndex = 0
        ChangeTempStatus("heat", False) if heat is True else None
        ChangeTempStatus("cold", False) if cold is True else None
        ChangeTempStatus("idleT", False) if idleT is True else None

    if (baseStatus == "Run") & (modeIndex == 3):
        if humidityCurrent <= (humiditySet - 2):
            cycleHumIndex = 2
            ChangeHumStatus("wet", True) if wet is False else None
        else:
            ChangeHumStatus("wet", False) if wet is True else None
        if humidityCurrent >= (humiditySet + 2):
            cycleHumIndex = 3
            ChangeHumStatus("dry", True) if dry is False else None
        else:
            ChangeHumStatus("dry", False) if dry is True else None
        if (humidityCurrent > (humiditySet - 2)) & (humidityCurrent < (humiditySet + 2)):
            cycleHumIndex = 1
            ChangeHumStatus("idleH", True) if idleH is False else None
        else:
            ChangeHumStatus("idleH", False) if idleH is True else None
    else:
        cycleHumIndex = 0
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
            heatLabel.destroy() if isinstance(heatLabel, Label) else None
        case "cold":
            coldLabel.destroy() if isinstance(coldLabel, Label) else None
        case "idleT":
            idleTempLabel.destroy() if isinstance(idleTempLabel, Label) else None
        case "wet":
            wetLabel.destroy() if isinstance(wetLabel, Label) else None
        case "dry":
            dryLabel.destroy() if isinstance(dryLabel, Label) else None
        case "idleH":
            idleHumLabel.destroy() if isinstance(idleHumLabel, Label) else None


def UpdateGif(ani, index=0):
    try:
        match ani:
            case "heat":
                framePic = framesHeat[index]
                index += 1
                if index == 14:
                    index = 0
                heatLabel.configure(image=framePic, borderwidth=0) if isinstance(heatLabel, Label) else None
            case "cold":
                framePic = framesCold[index]
                index += 1
                if index == 10:
                    index = 0
                coldLabel.configure(image=framePic, borderwidth=0) if isinstance(coldLabel, Label) else None
            case "idleT":
                framePic = framesIdleT[index]
                index += 1
                if index == 11:
                    index = 0
                idleTempLabel.configure(image=framePic, borderwidth=0) if isinstance(idleTempLabel, Label) else None
            case "wet":
                framePic = framesWet[index]
                index += 1
                if index == 12:
                    index = 0
                wetLabel.configure(image=framePic, borderwidth=0) if isinstance(wetLabel, Label) else None
            case "dry":
                framePic = framesDry[index]
                index += 1
                if index == 10:
                    index = 0
                dryLabel.configure(image=framePic, borderwidth=0) if isinstance(dryLabel, Label) else None
            case "idleH":
                framePic = framesIdleH[index]
                index += 1
                if index == 11:
                    index = 0
                idleHumLabel.configure(image=framePic, borderwidth=0) if isinstance(idleHumLabel, Label) else None
        root.after(100, UpdateGif, ani, index)
    except Exception:
        return


def ChangeName():

    def Accept():
        global machineIP, machineName, listIP, frameIP, machinesList, currentMachine
        machineName = newName.get()
        listIP[machineIP] = machineName
        if isinstance(machinesList, ttk.Combobox):
            machinesList["values"] = [f"{k} :: {v}" for k, v in listIP.items()]
        if isinstance(currentMachine, StringVar):
            currentMachine.set(value=f"{machineIP} :: {machineName}")
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


def GetLocalIP():
    global localIP
    hostname = socket.gethostname()
    localIP = socket.gethostbyname(hostname)


def CheckIP(init):
    global machineIP, machineName, frameIP, listIP, exchange
    configPath = f"{rootFolder}config.ini"
    frameIP = pandas.read_csv(configPath, sep=",")
    exchange = False
    if frameIP.empty:
        if init:
            InputIP(empty=True)
        else:
            machineName = "Климатическая камера"
            listIP = {machineIP: machineName}
            frameIP = pandas.DataFrame(list(listIP.items()), columns=ipColumns)
    else:
        listIP = dict(zip(frameIP["ip"], frameIP["name"]))
        if init:
            [machineIP] = last(listIP, maxlen=1)
            machineName = listIP[machineIP]
        else:
            if machineIP in listIP:
                machineName = listIP[machineIP]
            else:
                machineName = "Климатическая камера"
                listIP[machineIP] = machineName
            frameIP = pandas.DataFrame(list(listIP.items()), columns=ipColumns)
    OpenConnection() if not (frameIP.empty & init) else None


def InputIP(empty):

    def Get():
        global machineIP
        machineIP = entryIP.get()
        screenIP.grab_release()
        screenIP.destroy()
        CheckIP(init=False)

    def Close():
        screenIP.grab_release()
        screenIP.destroy()

    def Mask(ip):
        validIP = re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", ip)
        buttonStart["state"] = "normal" if validIP is not None else "disabled"
        if (validIP is not None) & (len(listIP) > 1) & (ip in listIP.keys()) & (ip != machineIP):
            buttonDel["state"] = "normal"
        else:
            buttonDel["state"] = "disabled"
        return True

    def Shift(event):
        global saved
        chosenIP = saved.get().split(sep=" :: ")[0] if isinstance(saved, ttk.Combobox) else None
        entryIP.delete(0, END)
        entryIP.insert(index=0, string=chosenIP)

    def Delete():
        del listIP[entryIP.get()]
        entryIP.delete(0, END)
        saved["values"] = [f"{k} :: {v}" for k, v in listIP.items()]
        saved["textvariable"] = StringVar(value="<EMPTY>")
        UpdateList()

    global listIP, saved
    screenIP = Toplevel(root)
    screenIP.title("Введите IP")
    screenIP.geometry("300x150")
    rootPosX = root.winfo_rootx() + 250
    rootPosY = root.winfo_rooty() + 350
    screenIP.wm_geometry("+%d+%d" % (rootPosX, rootPosY))
    screenIP.resizable(False, False)
    screenIP.grab_set()
    screenIP.protocol("WM_DELETE_WINDOW", Close)
    iconIP = PhotoImage(file=f"{iconsFolder}icon.png")
    screenIP.iconphoto(False, iconIP)
    labelIP = tkinter.Label(master=screenIP, text="Введите IP адрес климатической камеры:")
    labelIP.place(x=10, y=10, width=280)
    isvalid = (screenIP.register(Mask), "%P")
    entryIP = tkinter.Entry(master=screenIP, relief="solid", justify="center",
                            validate="key", validatecommand=isvalid)
    entryIP.place(x=10, y=40, width=280)
    buttonStart = ttk.Button(master=screenIP, style="TButton", text="Начать опрос", command=Get, state="disabled")
    buttonStart.place(x=10, y=110, width=130)
    buttonDel = ttk.Button(master=screenIP, style="TButton", text="Удалить камеру", command=Delete, state="disabled")
    buttonDel.place(x=160, y=110, width=130)
    saved = ttk.Combobox(master=screenIP, values=[f"{k} :: {v}" for k, v in listIP.items()],
                         state="readonly", background=bgLoc, foreground=bgLoc)
    saved.bind("<<ComboboxSelected>>", Shift)
    saved.place(x=10, y=70, width=280)


def OpenConnection():
    global machineIP, panelIP, master, ftp, historyFiles, sourceFolder, csvFolder, xlsFolder, \
        failConnection, failDevice, run, exchange
    try:
        master = modbus_tcp.TcpMaster(host=machineIP, port=502, timeout_in_sec=8)
        master.set_timeout(8.0)

        ftp = ftplib.FTP(host=machineIP, timeout=8)
        ftp.login(user="uploadhis", passwd="111111")
        ftp.cwd("datalog/data")
        historyFiles = ftp.nlst()
        time.sleep(1)
        sourceFolder = f"{rootFolder}support\\{machineIP}\\"
        csvFolder = f"{rootFolder}{machineIP}\\CSV\\"
        xlsFolder = f"{rootFolder}{machineIP}\\XLS\\"
        os.mkdir(sourceFolder) if os.path.exists(sourceFolder) is False else None
    except TimeoutError:
        logging.error("Connection timed out:", exc_info=True)
        ConnectionErrorWindow() if failConnection is False else None
    except Exception as excConnect:
        logging.error("Open connection error:", excConnect, exc_info=True)
        ConnectionErrorWindow() if failConnection is False else None
        return
    else:
        Single() if run is False else None
        run = True
        exchange = True


def Single():
    try:
        threadModbus.start()
        threadPlot.start()
        threadHistory.start()
        threadRuntime.start()
    except RuntimeError:
        pass
    LabelsShow()
    UserControl()
    GetPeriod()
    GlobalStatus()
    UpdateList()


def UpdateList():

    def CurrentMachine(event):
        global machineIP, machineName, exchange
        currentList = currentMachine.get().split(sep=" :: ") if isinstance(currentMachine, StringVar) else None
        chosenIP = currentList[0]
        if chosenIP != machineIP:
            machineIP = currentList[0]
            machineName = currentList[1]
            exchange = False
            OpenConnection()

    global frameIP, currentMachine, machinesList, machineIP, machineName, onlinePlot
    currentMachine.set(value=f"{machineIP} :: {machineName}") if isinstance(currentMachine, StringVar) else None
    if isinstance(machinesList, ttk.Combobox):
        machinesList["values"] = [f"{k} :: {v}" for k, v in listIP.items()]
        machinesList.bind("<<ComboboxSelected>>", CurrentMachine)
    frameIP = pandas.DataFrame(list(listIP.items()), columns=ipColumns)
    frameIP.to_csv(f"{rootFolder}config.ini", index=False)
    onlinePlot = True


def ModbusTCP():

    def Read(address, quantity):
        global master
        if isinstance(master, modbus_tcp.TcpMaster):
            output = master.execute(1, communicate.READ_INPUT_REGISTERS,
                                    starting_address=address, quantity_of_x=quantity)
            return output

    def Write(address, value):
        global master
        if isinstance(master, modbus_tcp.TcpMaster):
            master.execute(1, communicate.WRITE_SINGLE_REGISTER,
                           starting_address=address, output_value=value)

    global panelIP, panelDate, currentDate, currentDateDot, panelTime, currentTime, filename, picname, \
        failConnection, failDevice, machineIP, connection, exchange, temperatureCurrent, temperatureSet, \
        humidityCurrent, humiditySet, modeIndex, statusIndex, version, tmin, tmax, master, run, techTimer, \
        temperatureChange, humidityChange, statusChange, modeChange, temperatureNew, humidityNew, statusNew, modeNew
    while True:
        if exchange:
            try:
                master = modbus_tcp.TcpMaster(host=machineIP, port=502, timeout_in_sec=8)
                master.set_timeout(8.0)

                getSys = Read(10099, 10)
                getTempCur = Read(10109, 1)
                getTempSet = Read(10110, 1)
                getHumCur = Read(10111, 1)
                getHumSet = Read(10112, 1)
                getStatus = Read(10115, 1)
                getMode = Read(10114, 1)
                getVersion = Read(10116, 1)
                getTmin = Read(10117, 1)
                getTmax = Read(10118, 1)
                getTimer = Read(10113, 1)

                panelIP = f"{getSys[0]}.{getSys[1]}.{getSys[2]}.{getSys[3]}"
                connection = panelIP == machineIP
                panelDate = f"{getSys[4]:02} / {getSys[5]:02} / {getSys[6]}"
                panelTime = f"{getSys[7]:02} : {getSys[8]:02} : {getSys[9]:02}"
                currentDate = f"{getSys[4]:02}/{getSys[5]:02}/{getSys[6]}"
                currentDateDot = f"{getSys[4]:02}.{getSys[5]:02}.{getSys[6]}"
                currentTime = f"{getSys[7]:02}:{getSys[8]:02}:{getSys[9]:02}"
                filename = f"{getSys[6]:04}{getSys[5]:02}{getSys[4]:02}"
                picname = f"{getSys[6]}{getSys[5]:02}{getSys[4]:02}_{getSys[7]:02}{getSys[8]:02}{getSys[9]:02}"
                temperatureCurrent = (getTempCur[0] - 2**16) / 10 if getTempCur[0] > 2**15 else getTempCur[0] / 10
                temperatureSet = (getTempSet[0] - 2**16) / 10 if getTempSet[0] > 2**15 else getTempSet[0] / 10
                humidityCurrent = int(getHumCur[0] / 10)
                humiditySet = int(getHumSet[0])
                statusIndex = int(getStatus[0])
                modeIndex = int(getMode[0])
                version = int(getVersion[0])
                tmin = int(getTmin[0]) - 2**16 if getTmin[0] > 2**15 else int(getTmin[0])
                tmax = int(getTmax[0]) - 2**16 if getTmax[0] > 2**15 else int(getTmax[0])
                techTimer = int(getTimer[0])

                if temperatureChange:
                    Write(10120, value=temperatureNew)
                    Write(10119, 3)
                    temperatureChange = False

                if humidityChange:
                    Write(10121, value=humidityNew)
                    Write(10119, 5)
                    humidityChange = False

                if statusChange:
                    Write(10122, value=statusNew)
                    Write(10119, 9)
                    statusChange = False

                if modeChange:
                    Write(10123, value=modeNew)
                    Write(10119, 17)
                    modeChange = False

            except TimeoutError:
                ConnectionErrorWindow() if failConnection else None
            except Exception as excModbus:
                logging.error("Modbus error:", excModbus, exc_info=True)
                ConnectionErrorWindow() if failConnection else None
        time.sleep(1)


def AccessToFile(file):
    global sourceFolder
    try:
        with open(os.path.join(sourceFolder, file), "r") as ff:
            return True
    except Exception as excFile:
        logging.error("File is inaccessible", excFile, exc_info=True)
        return False


def DownloadFile(remotefile):
    global sourceFolder
    try:
        with open(os.path.join(sourceFolder, remotefile), "wb") as file:
            ftp.retrbinary("RETR %s" % remotefile, file.write) if isinstance(ftp, ftplib.FTP) else None
    except Exception as excDownload:
        logging.error("File download error:", excDownload, exc_info=True)
        return False
    else:
        return True


def ConvertFile(command):
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startupinfo.wShowWindow = subprocess.SW_HIDE
    creationflags = subprocess.CREATE_NO_WINDOW
    try:
        process = subprocess.Popen(command, shell=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                   creationflags=creationflags, startupinfo=startupinfo)
        process.wait()
        if process.returncode != 0:
            pass
    except Exception as excConvert:
        logging.error("File convertion error:", excConvert, exc_info=True)
        return False
    else:
        return True


def History():
    global historyFiles, sourceFolder, csvFolder, xlsFolder, failConnection, failDevice
    history = False
    while True:
        if (history is False) & (len(historyFiles) > 1):
            try:
                for sourceFile in historyFiles[:-1]:
                    if not os.path.isfile(os.path.join(sourceFolder, sourceFile)):
                        while True:
                            if DownloadFile(sourceFile):
                                break
                            time.sleep(1)

                for sourceFile in historyFiles[:-1]:
                    csvFile = f"{sourceFile[:8]}.csv"
                    xlsFile = f"{sourceFile[:8]}.xls"
                    csvconvert = [converter, '/b0', '/t0', os.path.join(sourceFolder, sourceFile),
                                  os.path.join(csvFolder, csvFile)]
                    xlsconvert = [converter, '/b0', '/t0', os.path.join(sourceFolder, sourceFile),
                                  os.path.join(xlsFolder, xlsFile)]
                    if AccessToFile(sourceFile):
                        if not os.path.isfile(os.path.join(csvFolder, csvFile)):
                            while True:
                                if ConvertFile(csvconvert):
                                    break
                                time.sleep(1)
                        if not os.path.isfile(os.path.join(xlsFolder, xlsFile)):
                            while True:
                                if ConvertFile(xlsconvert):
                                    break
                                time.sleep(1)
            except Exception as excHistory:
                logging.error("History synchronize error:", excHistory, exc_info=True)
                ConnectionErrorWindow() if failConnection is False else None
            else:
                history = True
            time.sleep(10)
        time.sleep(1)


def Runtime():
    global filename, updateData, actualData, xlsNeed
    while True:
        if filename:
            if updateData:
                currentFile = f"{filename}.dtl"
                csvFile = f"{filename}.csv"
                xlsFile = f"{filename}.xls"
                try:
                    csvconvert = [converter, '/b0', '/t0', os.path.join(sourceFolder, currentFile),
                                  os.path.join(csvFolder, csvFile)]
                    xlsconvert = [converter, '/b0', '/t0', os.path.join(sourceFolder, currentFile),
                                  os.path.join(xlsFolder, xlsFile)]
                    while True:
                        if DownloadFile(currentFile):
                            break
                        time.sleep(1)
                    if AccessToFile(currentFile):
                        while True:
                            with semaphore:
                                if ConvertFile(csvconvert):
                                    break
                            time.sleep(1)
                        if xlsNeed:
                            while True:
                                if ConvertFile(xlsconvert):
                                    xlsNeed = False
                                    break
                                time.sleep(1)
                except Exception as excRuntime:
                    logging.error("Runtime failed:", excRuntime, exc_info=True)
                else:
                    updateData = False
                    actualData = False
        time.sleep(1)


def UserControl():

    def PeriodIsChanged(event):
        global updateData
        updateData = True

    global graphLabels, graphPeriods, graphDefault, currentMachine, listIP, machinesList, machineIP, machineName
    graphDefault = StringVar(value=graphLabels[0])
    graphPeriod = ttk.Combobox(values=graphLabels, textvariable=graphDefault, width=21, state="readonly",
                               background=bgLoc, foreground=bgLoc)
    graphPeriod.bind("<<ComboboxSelected>>", PeriodIsChanged)
    graphPeriod.place(x=820, y=90)
    buttonOpenHistory.place(x=670, y=170, width=300)
    buttonSaveFig.place(x=840, y=199, width=130)
    buttonOpenFig.place(x=840, y=227, width=130)
    buttonRename.place(x=360, y=115, width=115)
    buttonAdd.place(x=485, y=115, width=115)
    buttonStatus.place(x=360, y=155, width=115)
    buttonMode.place(x=485, y=155, width=115)
    buttonSpeed.place(x=360, y=180, width=240)
    buttonSetTemp.place(x=360, y=205, width=240)
    buttonSetHum.place(x=360, y=230, width=240)
    currentMachine = StringVar(value=f"{machineIP} :: {machineName}")
    machinesList = ttk.Combobox(values=[f"{k} :: {v}" for k, v in listIP.items()], textvariable=currentMachine,
                                state="readonly", background=bgLoc, foreground=bgLoc)
    machinesList.place(x=360, y=90, width=240)
    navi = NavigationToolbar2Tk(canvasGraph)
    navi.place(x=671, y=200, width=155, height=50)


def GetPeriod():

    def StartStopPlot():
        global onlinePlot, updateData
        updateData = True if onlinePlot is False else None
        onlinePlot ^= True

    global showSlice, sliceActive, buttonEdit, buttonOnline, onlinePlot, showButton
    choice = graphLabels.index(graphDefault.get()) if isinstance(graphDefault, StringVar) else None
    if (choice == 6) & (showSlice is False):
        showSlice = True
        buttonEdit = ttk.Button(command=ShowSlice, style="TButton", text="Изменить диапазон")
        buttonEdit.place(x=670, y=130, width=300)
        ShowSlice()
    if (choice != 6) & (showSlice is True):
        showSlice = False
        sliceActive = False
        onlinePlot = True
        buttonEdit.destroy()
        HideSlice()
    if choice != 6:
        if showButton is False:
            buttonOnline = ttk.Button(root, style="TButton", command=StartStopPlot)
            buttonOnline.place(x=670, y=120, width=300)
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
        logging.info("Slice started")
        HideSlice()

    def DatetimeValidControl():
        global currentDate, dateNow, dateInitial, dateFinal, currentTime, timeNow, timeInitial, timeFinal
        dateNow = datetime.strptime(currentDate, "%d/%m/%Y")

        try:
            dateInitial = datetime.strptime(f"{dayInitial.get()}/{monthInitial.get()}/{yearNow}", "%d/%m/%Y")
        except ValueError:
            if int(dayInitial.get()) == 0:
                dateInitial = datetime.strptime(f"{int(dayInitial.get()) + 1}/{monthInitial.get()}/{yearNow}",
                                                "%d/%m/%Y")
                dateInitial = dateInitial - timedelta(days=1)
            else:
                dateInitial = datetime.strptime(f"{int(dayInitial.get()) - 1}/{monthInitial.get()}/{yearNow}",
                                                "%d/%m/%Y")
                dateInitial = dateInitial + timedelta(days=1)

        try:
            dateFinal = datetime.strptime(f"{dayFinal.get()}/{monthFinal.get()}/{yearNow}", "%d/%m/%Y")
        except ValueError:
            if int(dayFinal.get()) == 0:
                dateFinal = datetime.strptime(f"{int(dayFinal.get()) + 1}/{monthFinal.get()}/{yearNow}",
                                              "%d/%m/%Y")
                dateFinal = dateFinal - timedelta(days=1)
            else:
                dateFinal = datetime.strptime(f"{int(dayFinal.get()) - 1}/{monthFinal.get()}/{yearNow}",
                                              "%d/%m/%Y")
                dateFinal = dateFinal + timedelta(days=1)

        timeNow = datetime.strptime(currentTime, "%H:%M:%S")
        timeInitial = datetime.strptime(f"{hourInitial.get()}:{minutesInitial.get()}:00", "%H:%M:%S")
        timeFinal = datetime.strptime(f"{hourFinal.get()}:{minutesFinal.get()}:00", "%H:%M:%S")

        if dateInitial > dateNow:
            dateInitial = dateNow
        if dateFinal > dateNow:
            dateFinal = dateNow
        if dateFinal < dateInitial:
            dateFinal = dateInitial
        if dateFinal == dateNow:
            if timeFinal > timeNow:
                timeFinal = timeNow
        if dateInitial == dateFinal:
            if timeInitial >= timeFinal:
                timeInitial = timeFinal - timedelta(minutes=1)

        dayInitial.set(value=datetime.strftime(dateInitial, "%d/%m/%Y")[0:2])
        monthInitial.set(value=datetime.strftime(dateInitial, "%d/%m/%Y")[3:5])
        dayFinal.set(value=datetime.strftime(dateFinal, "%d/%m/%Y")[0:2])
        monthFinal.set(value=datetime.strftime(dateFinal, "%d/%m/%Y")[3:5])
        hourInitial.set(value=datetime.strftime(timeInitial, "%H:%M:%S")[0:2])
        minutesInitial.set(value=datetime.strftime(timeInitial, "%H:%M:%S")[3:5])
        hourFinal.set(value=datetime.strftime(timeFinal, "%H:%M:%S")[0:2])
        minutesFinal.set(value=datetime.strftime(timeFinal, "%H:%M:%S")[3:5])

    global sliceFrame, version, currentDate, currentTime
    dayInitial = StringVar(value=currentDate[0:2])
    dayFinal = StringVar(value=currentDate[0:2])
    monthInitial = StringVar(value=currentDate[3:5])
    monthFinal = StringVar(value=currentDate[3:5])
    yearNow = StringVar(value=currentDate[6:10]).get()
    hourInitial = StringVar(value="00")
    minutesInitial = StringVar(value="00")
    hourFinal = StringVar(value=currentTime[0:2])
    minutesFinal = StringVar(value=currentTime[3:5])

    sliceFrame = tkinter.Frame(master=root, borderwidth=1, width=300, height=140, bg=bgLoc)
    sliceFrame.place(x=670, y=120)
    ttk.Button(master=sliceFrame, text="<°C>", command=lambda: GetSlice(False), style="TButton")\
        .place(x=0, y=110, width=150, height=25)
    humstate = "normal" if version==2 else "disabled"
    ttk.Button(master=sliceFrame, text="<°C> & <%RH>", command=lambda: GetSlice(True), style="TButton", state=humstate) \
        .place(x=160, y=110, width=150, height=25)

    tkinter.Label(master=sliceFrame, text="Начало выборки", anchor="w", bg=bgLoc, fg="white") \
        .place(x=0, y=10, height=20)
    tkinter.Label(master=sliceFrame, text="Дата:", anchor="e", bg=bgLoc, fg="white") \
        .place(x=120, y=0, width=50, height=20)
    dayFrom = tkinter.Spinbox(master=sliceFrame, from_=0, to=32, state="readonly", format="%02.0f",
                              textvariable=dayInitial, command=DatetimeValidControl,
                              buttonbackground=bgLoc, foreground=bgLoc)
    dayFrom.place(x=180, y=0, width=30, height=20)
    tkinter.Label(master=sliceFrame, text=".", bg=bgLoc, fg="white").place(x=215, y=0, width=5, height=20)
    monthFrom = tkinter.Spinbox(master=sliceFrame, from_=1, to=12, state="disabled", format="%02.0f",
                                textvariable=monthInitial, buttonbackground="dim gray", foreground=bgLoc)
    monthFrom.place(x=225, y=0, width=30, height=20)
    tkinter.Label(master=sliceFrame, text=f" .  {yearNow}", anchor="w", bg=bgLoc, fg="white") \
        .place(x=255, y=0, width=40, height=20)
    tkinter.Label(master=sliceFrame, text="Время:", anchor="e", bg=bgLoc, fg="white") \
        .place(x=120, y=25, width=50, height=20)
    hourFrom = tkinter.Spinbox(master=sliceFrame, from_=0, to=23, state="readonly", format="%02.0f",
                               textvariable=hourInitial, command=DatetimeValidControl,
                               buttonbackground=bgLoc, foreground=bgLoc)
    hourFrom.place(x=180, y=25, width=30, height=20)
    tkinter.Label(master=sliceFrame, text=":", bg=bgLoc, fg="white").place(x=215, y=25, width=5, height=20)
    minutesFrom = tkinter.Spinbox(master=sliceFrame, from_=0, to=59, state="readonly", format="%02.0f",
                                  textvariable=minutesInitial, command=DatetimeValidControl,
                                  buttonbackground=bgLoc, foreground=bgLoc)
    minutesFrom.place(x=225, y=25, width=30, height=20)
    tkinter.Label(master=sliceFrame, text=" :  00", anchor="w", bg=bgLoc, fg="white") \
        .place(x=255, y=25, width=40, height=20)

    tkinter.Label(master=sliceFrame, text="Конец выборки", anchor="w", bg=bgLoc, fg="white") \
        .place(x=0, y=65, height=20)
    tkinter.Label(master=sliceFrame, text="Дата:", anchor="e", bg=bgLoc, fg="white") \
        .place(x=120, y=55, width=50, height=20)
    dayTo = tkinter.Spinbox(master=sliceFrame, from_=0, to=32, state="readonly", format="%02.0f",
                            textvariable=dayFinal, command=DatetimeValidControl,
                            buttonbackground=bgLoc, foreground=bgLoc)
    dayTo.place(x=180, y=55, width=30, height=20)
    tkinter.Label(master=sliceFrame, text=".", bg=bgLoc, fg="white").place(x=215, y=55, width=5, height=20)
    monthTo = tkinter.Spinbox(master=sliceFrame, from_=1, to=12, state="disabled", format="%02.0f",
                              textvariable=monthFinal, buttonbackground="dim gray", foreground=bgLoc)
    monthTo.place(x=225, y=55, width=30, height=20)
    tkinter.Label(master=sliceFrame, text=f" .  {yearNow}", anchor="w", bg=bgLoc, fg="white") \
        .place(x=255, y=55, width=40, height=20)
    tkinter.Label(master=sliceFrame, text="Время:", anchor="e", bg=bgLoc, fg="white") \
        .place(x=120, y=80, width=50, height=20)
    hourTo = tkinter.Spinbox(master=sliceFrame, from_=0, to=23, state="readonly", format="%02.0f",
                             textvariable=hourFinal, command=DatetimeValidControl,
                             buttonbackground=bgLoc, foreground=bgLoc)
    hourTo.place(x=180, y=80, width=30, height=20)
    tkinter.Label(master=sliceFrame, text=":", bg=bgLoc, fg="white").place(x=215, y=80, width=5, height=20)
    minutesTo = tkinter.Spinbox(master=sliceFrame, from_=0, to=59, state="readonly", format="%02.0f",
                                textvariable=minutesFinal, command=DatetimeValidControl,
                                buttonbackground=bgLoc, foreground=bgLoc, buttonuprelief="sunken")
    minutesTo.place(x=225, y=80, width=30, height=20)
    tkinter.Label(master=sliceFrame, text=" :  00", anchor="w", bg=bgLoc, fg="white") \
        .place(x=255, y=80, width=40, height=20)


def HideSlice():
    global sliceFrame
    sliceFrame.destroy() if isinstance(sliceFrame, Frame) else None


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

    def ValidCheck(frame):
        correct = True
        frameCheck = pandas.DataFrame(columns=frameColumns)
        try:
            frameCheck["Time"] = pandas.to_datetime(frame["Time"], format="%H:%M:%S")
        except Exception as excFrame:
            logging.error("Frame is not valid", excFrame, exc_info=True)
            correct = False
        if frame.isnull().values.any():
            correct = False
        if frame.duplicated().any():
            correct = False
        if list(frame) != frameColumns:
            correct = False
        for column in frame.columns:
            if (column != "Time") & (column != "Date"):
                if pandas.api.types.is_numeric_dtype(frame[column]) is False:
                    correct = False
        return correct

    def NotSlice():

        def Filling():
            global frameData, temperatureCurrent, temperatureSet, humidityCurrent, humiditySet
            record = {"Date": [currentDateDot], "Time": [currentTime],
                      "TemperatureCurrent": [temperatureCurrent], "TemperatureSet": [temperatureSet],
                      "HumidityCurrent": [humidityCurrent], "HumiditySet": [humiditySet]}
            frameRecord = pandas.DataFrame(record)
            frameData = pandas.concat([frameData, frameRecord], ignore_index=True)

        global csvFolder, frameData, frameCurrent, frameColumns, timeNow, timeDif, fileList, fileMain, \
            frameDataFrom, frameDataTo, actualData, timeBegin
        chosenTime = graphPeriods[graphLabels.index(graphDefault.get())] if isinstance(graphDefault, StringVar) else None
        try:
            fileList = sorted(os.listdir(csvFolder))
            fileMain = os.path.join(csvFolder, fileList[-1])
        except Exception as excFilelist:
            logging.error("File not found:", excFilelist, exc_info=True)
            PlotError(True)
        else:
            if currentTime and chosenTime:
                try:
                    timeNow = datetime.strptime(currentTime, "%H:%M:%S")
                    timeDif = datetime.strptime(chosenTime, "%H:%M:%S")
                except Exception as excTime:
                    logging.error("1-day time read error:", excTime, exc_info=True)
                    PlotError(True)
                else:
                    # ONLINE - IF THE SAME DAY DIFFERENCE
                    if (timeNow - timeDif).days == 0:
                        if updateData is False:
                            # IF CONVERTING FINISHED
                            timeBegin = str(datetime.strptime(str(timeNow - timeDif), "%H:%M:%S").time())
                            try:
                                if actualData is False:
                                    # IF ONLINE SLICE IS CHANGED
                                    with semaphore:
                                        frameData = pandas.read_csv(fileMain, sep=",", header=0)
                                    actualData = True
                                else:
                                    Filling()
                            except Exception as excCSV:
                                logging.error("Error reading CSV file:", excCSV, exc_info=True)
                                PlotError(True)
                            else:
                                frameData = pandas.DataFrame(frameData.loc[frameData["Time"] >= timeBegin, frameColumns])
                                if ValidCheck(frameData) & frameData.empty is False:
                                    frameCurrent = frameData
                    else:
                        # ONLINE - IF TWO DAYS DIFFERENCE
                        if updateData is False:
                            # IF CONVERTING FINISHED
                            fileFrom = os.path.join(csvFolder, fileList[-2])
                            fileTo = os.path.join(csvFolder, fileList[-1])
                            timeBegin = str(((timeNow - timeDif) +
                                            datetime.strptime("23:59:59", "%H:%M:%S")).time())
                            try:
                                if actualData is False:
                                    # IF ONLINE SLICE IS CHANGED
                                    with semaphore:
                                        frameDataFrom = pandas.read_csv(fileFrom, sep=",", header=0)
                                        frameDataTo = pandas.read_csv(fileTo, sep=",", header=0)
                                    actualData = True
                                else:
                                    Filling()
                            except Exception as excCSVs:
                                logging.error("Error reading two CSV files:", excCSVs, exc_info=True)
                                PlotError(True)
                            else:
                                frameDataFrom = pandas.DataFrame(frameDataFrom.loc
                                                                 [(frameDataFrom["Time"] >= timeBegin), frameColumns])
                                frameDataTo = pandas.DataFrame(frameDataTo)
                                if (ValidCheck(frameDataFrom) & ValidCheck(frameDataTo) &
                                        frameDataFrom.empty is False & frameDataTo.empty is False):
                                    frameCurrent = pandas.concat([frameDataFrom, frameDataTo], ignore_index=True)
            else:
                logging.error("Bad time data")
                PlotError(True)

    def IsSlice():
        global csvFolder, frameData, frameCurrent, frameColumns, fileMain, frameDataFrom, frameDataTo
        if sliceDateFrom == sliceDateTo:
            fileMain = os.path.join(csvFolder, f"{sliceDateFrom}.csv")
            frameData = pandas.read_csv(fileMain, sep=",", header=0)
            frameData = frameData.loc[(frameData["Time"] >= sliceTimeFrom) &
                                      (frameData["Time"] <= sliceTimeTo), frameColumns]
            frameCurrent = pandas.DataFrame(frameData)
        else:
            dateFrom = datetime.strptime(sliceDateFrom, "%Y%m%d")
            dateTo = datetime.strptime(sliceDateTo, "%Y%m%d")
            fileFrom = os.path.join(csvFolder, f"{sliceDateFrom}.csv")
            frameDataFrom = pandas.read_csv(fileFrom, sep=",", header=0)
            frameData = pandas.DataFrame(frameDataFrom.loc[(frameDataFrom["Time"] >= sliceTimeFrom) &
                                                           (frameDataFrom.index % 10 == 0), frameColumns])
            for i in range(1, (dateTo - dateFrom).days + 1):
                sliceDateNext = datetime.strftime(dateFrom + timedelta(days=i), "%Y%m%d")
                fileTo = os.path.join(csvFolder, f"{sliceDateNext}.csv")
                frameDataTo = pandas.read_csv(fileTo, sep=",", header=0)
                if sliceDateNext == sliceDateTo:
                    frameDataTo = pandas.DataFrame(frameDataTo.loc[(frameDataTo["Time"] <= sliceTimeTo), frameColumns])
                else:
                    frameDataTo = pandas.DataFrame(frameDataTo)
                frameTo = frameDataTo.loc[(frameDataTo.index % 10 == 0), frameColumns]
                frameData = pandas.concat([frameData, frameTo], ignore_index=True)
            frameCurrent = pandas.DataFrame(frameData)

    def DatetimeConvert():
        global frameCurrent
        if ValidCheck(frameCurrent):
            try:
                frameCurrent["Datetime"] = pandas.to_datetime(frameCurrent["Date"] + " " + frameCurrent["Time"],
                                                              dayfirst=True)
                frameCurrent = pandas.DataFrame(frameCurrent[combColumns])
            except Exception as excDatetime:
                logging.error("Datetime convert failed:", excDatetime, exc_info=True)

    global sliceActive, baseMode, onlinePlot, humidity, frameCurrent, draw, graphTemp, graphHum
    while True:
        if onlinePlot:
            try:
                if not sliceActive:
                    NotSlice()
                else:
                    IsSlice()
                DatetimeConvert()
            except Exception as excFrame:
                PlotError(True)
                logging.error("Data block error:", excFrame, exc_info=True)
            try:
                figure.clear()
                locX = matplotlib.ticker.LinearLocator(18)
                formX = matplotlib.dates.DateFormatter("%d.%m\n%H:%M:%S")
                graphTemp = figure.add_subplot(111)
                graphTemp.xaxis.set_major_locator(locX)
                graphTemp.xaxis.set_major_formatter(formX)
                graphTemp.set_facecolor(bgLoc)
                graphTemp.set_title(machineName, color="yellow")
            except Exception as excSubplot:
                logging.error("Subplot error:", excSubplot, exc_info=True)
            try:
                graphTemp.plot(frameCurrent["Datetime"], frameCurrent["TemperatureCurrent"], "-w",
                               frameCurrent["Datetime"], frameCurrent["TemperatureSet"], "--c")
                graphTemp.set_ylabel("Температура, °C", color="white")
                graphTemp.grid(alpha=0.5, linestyle="-", color="cyan", linewidth=0.3)
                graphTemp.tick_params(labelsize=8, colors="yellow")
                if ((baseMode == "Temperature") & (sliceActive is False)) | ((humidity is False) & (sliceActive is True)):
                    graphTemp.fill_between(x=frameCurrent["Datetime"], y1=frameCurrent["TemperatureCurrent"],
                                           y2=frameCurrent["TemperatureSet"], alpha=0.2)
                if ((baseMode == "Humidity") & (sliceActive is False)) | ((humidity is True) & (sliceActive is True)):
                    graphHum = graphTemp.twinx()
                    graphHum.set_ylabel("Влажность, %", color="red")
                    graphHum.plot(frameCurrent["Datetime"], frameCurrent["HumidityCurrent"], "-r",
                                  frameCurrent["Datetime"], frameCurrent["HumiditySet"], "--m")
                    graphHum.fill_between(x=frameCurrent["Datetime"], y1=frameCurrent["HumidityCurrent"],
                                          y2=frameCurrent["HumiditySet"], alpha=0.2)
                    graphHum.grid(alpha=0.6, linestyle=":", color="red")
                    graphHum.tick_params(labelsize=8, colors="yellow")
                figure.autofmt_xdate(rotation=45)
                canvasGraph.draw()
            except Exception as excPlot:
                PlotError(True)
                logging.error("Plot error:", excPlot, exc_info=True)
            else:
                PlotError(False)
            if draw is False:
                canvasGraph.get_tk_widget().place(x=20, y=290)
                draw = True
            if sliceActive:
                humidity = False
                onlinePlot = False
        time.sleep(5)


def SaveFigure():
    os.mkdir(picFolder) if not os.path.isdir(picFolder) else None
    figure.savefig(f"{picFolder}{picname}")
    buttonOpenFig["state"] = "normal"


def OpenFigure():
    if os.path.exists(picFolder) & bool(os.listdir(picFolder)):
        buttonOpenFig["state"] = "normal"
        os.system(f"explorer.exe {picFolder}")
    else:
        buttonOpenFig["state"] = "disabled"


def OpenHistory():
    global updateData, xlsNeed
    os.mkdir(xlsFolder) if not os.path.exists(xlsFolder) else None
    updateData = True
    xlsNeed = True
    os.system(f"explorer.exe {xlsFolder}")


def ChangeTemperature():

    def Accept():
        global temperatureNew, temperatureChange
        try:
            value = int(setTemp.get())
            if (value >= tmin) & (value <= tmax):
                temperatureNew = value
                temperatureChange = True
                frameTemp.destroy()
        except ValueError:
            pass

    def Decline():
        frameTemp.destroy()

    frameTemp = tkinter.Frame(master=root, borderwidth=1, width=240, height=25, bg=bgLoc)
    frameTemp.place(x=360, y=204)
    setTemp = InputBox(container=frameTemp, placeholder=f"Уставка от {tmin} до +{tmax} °C", placeholder_color="dim gray",
                       input_type="number", justify="center")
    setTemp.place(x=30, y=1, width=180, height=22)
    ttk.Button(master=frameTemp, style="TButton", image=acceptImage, compound=TOP, command=Accept)\
        .place(x=0, y=0, width=24, height=24)
    ttk.Button(master=frameTemp, style="TButton", image=declineImage, compound=TOP, command=Decline)\
        .place(x=216, y=0, width=24, height=24)


def ChangeHumidity():

    def Accept():
        global humidityNew, humidityChange
        try:
            value = int(setHum.get())
            if (value >= 20) & (value <= 98):
                humidityNew = value
                humidityChange = True
                frameHum.destroy()
        except ValueError:
            pass

    def Decline():
        frameHum.destroy()

    frameHum = tkinter.Frame(master=root, borderwidth=1, width=240, height=25, bg=bgLoc)
    frameHum.place(x=360, y=229)
    setHum = InputBox(container=frameHum, placeholder="Уставка от 20 до 98 %", placeholder_color="dim gray",
                      input_type="number", justify="center")
    setHum.place(x=30, y=1, width=180, height=22)
    ttk.Button(master=frameHum, style="TButton", image=acceptImage, compound=TOP, command=Accept)\
        .place(x=0, y=0, width=24, height=24)
    ttk.Button(master=frameHum, style="TButton", image=declineImage, compound=TOP, command=Decline)\
        .place(x=216, y=0, width=24, height=24)


def ChangeStatus():
    global statusIndex, statusChange, statusNew
    if statusIndex == 2:
        statusNew = 0
        statusChange = True
    if statusIndex == 3:
        statusNew = 1
        statusChange = True


def ChangeMode():
    global modeChange, modeNew, statusIndex, modeIndex
    if statusIndex == 3:
        if modeIndex == 2:
            modeNew = 2
        else:
            modeNew = 1
        modeChange = True


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
        global failConnection
        screenError.grab_release()
        screenError.destroy()
        failConnection = False
        OpenConnection()

    def ResetIP():
        global failConnection
        screenError.grab_release()
        screenError.destroy()
        failConnection = False
        InputIP(False)

    global wait, failConnection
    failConnection = True
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
    screenIcon = PhotoImage(file=f"{iconsFolder}icon.png")
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

    def CloseWindow():
        global failDevice
        failDevice = False
        screenError.grab_release()
        screenError.destroy()

    global failDevice
    failDevice = True
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
    screenIcon = PhotoImage(file=f"{iconsFolder}icon.png")
    screenError.iconphoto(False, screenIcon)
    tkinter.Label(master=screenError, bg="yellow", text="Невозможно установить связь!").place(x=10, y=10, width=280)
    ttk.Button(master=screenError, style="TButton", text="Подождать", command=CloseWindow).place(x=20, y=60, width=120)
    ttk.Button(master=screenError, style="TButton", text="Завершить", command=sys.exit).place(x=160, y=60, width=120)


logfile = os.path.join(rootFolder, "sys.log")
os.remove(logfile) if os.path.isfile(logfile) else None
logging.basicConfig(filename=logfile, level=logging.ERROR)

root = Tk()
root.title("Модуль удалённого контроля климатической камеры  |  Climcontrol v1.7.6")
root.geometry("1000x740")
root.wm_geometry("+%d+%d" % (100, 100))
root["bg"] = bgGlob
root.resizable(False, False)
icon = PhotoImage(file=os.path.join(iconsFolder, "icon.png"))
root.iconphoto(False, icon)
root.option_add("*Font", "Helvetica 8")
ttk.Style().configure(style=".", font="Helvetica 8")

canvas = Canvas(width=998, height=698, bg=bgGlob, highlightthickness=1, highlightbackground=bgGlob)
canvas.place(x=0, y=80)
canvas.create_rectangle(18, 8, 308, 188, fill="#352642", outline="#241C2B")
canvas.create_rectangle(10, 0, 300, 180, fill="#510D70", outline="#510D70")
canvas.create_rectangle(338, 8, 638, 188, fill="#352642", outline="#241C2B")
canvas.create_rectangle(330, 0, 630, 180, fill="#510D70", outline="#510D70")
canvas.create_rectangle(668, 8, 988, 188, fill="#352642", outline="#241C2B")
canvas.create_rectangle(660, 0, 980, 180, fill="#510D70", outline="#510D70")
canvas.create_rectangle(18, 208, 988, 638, fill="#352642", outline="#241C2B")
canvas.create_rectangle(10, 200, 980, 630, fill="#510D70", outline="#510D70")

framesHeat = [PhotoImage(file=f"{iconsFolder}heat.gif", format="gif -index %i" %i) for i in range(15)]
framesCold = [PhotoImage(file=f"{iconsFolder}cold.gif", format="gif -index %i" %i) for i in range(10)]
framesIdleT = [PhotoImage(file=f"{iconsFolder}idleT.gif", format="gif -index %i" %i) for i in range(11)]
framesWet = [PhotoImage(file=f"{iconsFolder}wet.gif", format="gif -index %i" %i) for i in range(12)]
framesDry = [PhotoImage(file=f"{iconsFolder}dry.gif", format="gif -index %i" %i) for i in range(10)]
framesIdleH = [PhotoImage(file=f"{iconsFolder}idleH.gif", format="gif -index %i" %i) for i in range(11)]

acceptImage = PhotoImage(file=f"{iconsFolder}accept.png")
declineImage = PhotoImage(file=f"{iconsFolder}decline.png")

threadModbus = threading.Thread(target=ModbusTCP, daemon=True, name="modbus")
threadPlot = threading.Thread(target=Plot, daemon=True, name="plot")
threadHistory = threading.Thread(target=History, daemon=True, name="history")
threadRuntime = threading.Thread(target=Runtime, daemon=True, name="runtime")
semaphore = threading.Semaphore(1)

logoLabel = Label(font=("Arial", 10, "bold"), fg=fgLab, bg=bgGlob)
armIPLabel = Label(fg=fgLab, bg=bgGlob)
panelIPLabel = Label(fg=fgLab, bg=bgGlob)
panelDateLabel = Label(fg=fgLab, bg=bgGlob, anchor="e")
panelTimeLabel = Label(fg=fgLab, bg=bgGlob, anchor="e")
statusLabel = Label(anchor="e", fg=fgLab, bg=bgLoc)
statusValue = Label(fg=fgVal, bg=bgLoc)
modeLabel = Label(anchor="e", fg=fgLab, bg=bgLoc)
modeValue = Label(fg=fgVal, bg=bgLoc)
tempCurLabel = Label(anchor="e", fg=fgLab, bg=bgLoc)
tempCurValue = Label(fg=fgVal, bg=bgLoc)
tempSetLabel = Label(anchor="e", fg=fgLab, bg=bgLoc)
tempSetValue = Label(fg=fgVal, bg=bgLoc)
humCurLabel = Label(anchor="e", fg=fgLab, bg=bgLoc)
humCurValue = Label(fg=fgVal, bg=bgLoc)
humSetLabel = Label(anchor="e", fg=fgLab, bg=bgLoc)
humSetValue = Label(fg=fgVal, bg=bgLoc)
labelPeriods = Label(anchor="w", fg=fgLab, bg=bgLoc)
cycleTechLabel = Label(anchor="e", fg=fgLab, bg=bgLoc)
cycleTechValue = Label(fg=fgVal, bg=bgLoc)
timerTechLabel = Label(anchor="e", fg=fgLab, bg=bgLoc)
timerTechValue = Label(fg=fgVal, bg=bgLoc)

figure = Figure(figsize=(9.5, 4.2), dpi=100, facecolor=bgLoc)
canvasGraph = FigureCanvasTkAgg(figure=figure, master=root)
canvasError = tkinter.Canvas(master=root, bg="red", width=100, height=100)

ttk.Style().configure("TButton", font="Helvetica 8", background=bgGlob, relief="sunken", border=0, foreground="blue")
buttonSaveFig = ttk.Button(command=SaveFigure, style="TButton", text="Сохранить график")
buttonOpenFig = ttk.Button(command=OpenFigure, style="TButton", text="Открыть график")
buttonOpenHistory = ttk.Button(command=OpenHistory, style="TButton", text="Открыть папку с суточными архивами")
buttonRename = ttk.Button(command=ChangeName, style="TButton", text="Переименовать")
buttonAdd = ttk.Button(command=lambda: InputIP(empty=False), style="TButton", text="Добавить / Удалить")
buttonStatus = ttk.Button(command=ChangeStatus, style="TButton", text="ПУСК / СТОП")
buttonMode = ttk.Button(command=ChangeMode, style="TButton", text="Термо / Влага")
buttonSpeed = ttk.Button(style="TButton", text="Активировать контроль скорости", state="disabled")
buttonSetTemp = ttk.Button(command=ChangeTemperature, style="TButton", text="Сменить уставку по температуре")
buttonSetHum = ttk.Button(command=ChangeHumidity, style="TButton", text="Сменить уставку по влажности")

ObjectsPlace()
GetLocalIP()
CheckIP(init=True)

root.mainloop()
