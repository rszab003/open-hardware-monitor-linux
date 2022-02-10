import os, json, concurrent.futures, time


def refreshUsageData(currUsages: list) -> None:
    mapsFi = open("/tmp/openhwmon_linux/maps.json", "r+")
    maps = json.load(mapsFi)
    maps["prevUsageData"] = currUsages
    # print("MAPS NOW!!!", maps)
    mapsFi.seek(0); mapsFi.truncate()
    json.dump(maps, mapsFi, indent=3)
    mapsFi.close()


def calcUsage(prevUsages: list, currUsages: list) -> list:
    currSums = []; prevSums = []
    currDeltas = []; idles = []
    for usage in currUsages:
        cpuSum = 0
        for i in range(1, len(usage)):
            cpuSum += int(usage[i])
            if i == 4:
                idles.append(int(usage[i]))
        currSums.append(cpuSum)
    icount = 0 #index for current core of idle list
    for usage in prevUsages:
        prevCpuSum = 0
        for i in range(1, len(usage)):
            prevCpuSum += int(usage[i])
            if i == 4:
                idles[icount] = idles[icount] - int(usage[i])
                icount += 1
        prevSums.append(prevCpuSum)

    for i in range(0, len(currSums)):
        currDeltas.append(currSums[i] - prevSums[i])
    cpuUsed = []; totUsage = []
    for i in range(0, len(currDeltas)):
        cpuUsed.append((currDeltas[i] - idles[i]) / currDeltas[i])
    
    return cpuUsed



def getUsage() -> tuple:
    currUsageFile = "/proc/stat"; prevUsageFile = "/tmp/openhwmon_linux/maps.json"
    currUsages = []
    try:
        f = open(prevUsageFile, "r")
        prevUsages = json.load(f)
        prevUsages = prevUsages["prevUsageData"]
        f.close()
    except FileNotFoundError as ex:
        print("ERROR GETTING PREV USAGE DATA")
        print(ex)
    # print("PREV USAGES!!!\n", prevUsages)
    try:
        with open(currUsageFile, "r") as fi:
            for i in range(0, os.cpu_count() + 1):
                currUsages.append(fi.readline()[:-1].split())
        # print(currUsages)
    except FileNotFoundError as ex:
        print("ERROR GETTING CURRENT USAGE DATA")
        print(ex)
    return (prevUsages, currUsages)



def getCpuTemp() -> dict:
    master = {}
    tempDir =""
    try:
        with open("/tmp/openhwmon_linux/maps.json", "r") as fi:
            tempDir = json.load(fi)
            tempDir = tempDir["cpuTempDir"]
    except FileNotFoundError as ex:
        print("ERROR! FILE WAS NOT MADE IN init.py.\nCHECK init.determineCpuTempDirectory()")
        print(ex)
    #core count starts at 1 here for some reason
    coreID = 0
    for i in range(1, os.cpu_count() + 2):
        cpuTempLoc = tempDir + "/temp{}_input".format(str(i))
        try:
            with open(cpuTempLoc, "r") as fi:
                temp = fi.read()[:-1]
                if i == 1:
                    master["CPU TEMP"] = temp
                else:
                    master[coreID] = temp
                    coreID += 1
        except FileNotFoundError as ex:
            print("ERROR: could not find: {}".format(cpuTempLoc))
            print(ex)
    return master



# GET CPU MODEL, CACHE SIZE & CURR CLOCK SPEEDS
def cpuInfo() -> dict:
    parsedData = {}
    try:
        cpuInfoFile = open("/proc/cpuinfo", "r")
        cpuDump = cpuInfoFile.readlines()
        #GET MODEL AND CACHE SIZE
        model = cpuDump[4][13:]
        cacheSize = cpuDump[8][13:]
        parsedData["CPU Model"] = model[:-1] #removes \n character
        parsedData["CPU Cache Size"] = cacheSize[:-1]
        parsedData["Cores"] = []
        #GET CLOCK SPEED
        coreID = 0
        for line in cpuDump:
            if "cpu MHz" in line:
                parsedData["Cores"].append(
                    {
                        "id" : coreID,
                        "Clock MHz" : float(line[11:-1]),
                    }
                )
                coreID += 1
        cpuInfoFile.close()
        return parsedData
    except Exception as ex:
        print("ERROR GETTING CPU DATA!")
        print(ex)


def fetch() -> dict:
    master = cpuInfo()
    tempData = getCpuTemp()
    prevCurrUsage = getUsage()
    refreshUsageData(prevCurrUsage[1]) #Stores current usage data for next calculation
    usageData = calcUsage(prevCurrUsage[0], prevCurrUsage[1])
    master["CPU Temp"] = tempData["CPU TEMP"]
    master["Total Usage"] = usageData[0]
    i = 0; j = 1
    for coreData in master["Cores"]:
        coreData["Temp"] = tempData[i]
        coreData["Usage"] = usageData[j]
        i += 1; j += 1

    return master

if __name__ == "__main__":
    fetch()