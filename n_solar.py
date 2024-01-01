import numpy
import n_restClient
import time

class solarLogic:
    def __init__(self):
        self.TEHpw = n_restClient.restGetVar("TEHpw")
        self.pw2bm = {}
        for i in range(1 << len(self.TEHpw)):
            bm = [int(x) for x in format(i, '#07b')[2:]]
            p = sum(list(numpy.multiply(self.TEHpw,bm)))
            self.pw2bm[p] = bm   
        self.cur2pw = [*self.pw2bm]
        self.cur2pw.sort()
        self.pw2cur = {x:i for i,x in enumerate(self.cur2pw)}
        for i in self.pw2bm:
            li = self.pw2bm[i]
            self.pw2bm[i] = [int(not i) for i in li]
        self.pwMaxCharge = 6000
        self.pwMaxTEH = 5500
        self._lastHeat = 0
        self.historyPow=[0,0,0]
    def applypw(self, pw):
        bm = self.pw2bm[pw]
        n_restClient.restSetVar("TEHs", bm)
        temps = n_restClient.restGetTemps()
        t2 = temps["NewTank"]
        t1 = temps["_Бак"]
        print(f"NewTank {t2}, Tank {t1}")
        if (pw == 0) and (t2-t1 <= 4):
            n_restClient.restSetVar("sw3_syncer", 0)
        else:
            n_restClient.restSetVar("sw3_syncer", 1)            
    def bm2pw(self,st):
        st = [not i for i in st]
        return sum([i[0]*i[1] for i in zip(st,self.TEHpw)])
    def getPwSt(self):
        return n_restClient.restGetVar("TEHs")
    def getPwStr(self):
        st = self.getPwSt()
        return str(self.bm2pw(st))
    def getPwNow(self):
        st = self.getPwSt()
        return self.bm2pw(st)

    def reservCalc(self, bV, bVmax):
        x = 500*bV/bVmax-400
        bRes = self.pwMaxCharge
        if x > 80:
            d = x-80
            bRes -= self.pwMaxCharge*(pow(d+3,3)/20)/100
        if bRes<-100:
            return -100
        return bRes

    # decrease pwCur by ndiff
    def minusCalc(self, pwCur, grid, ndiff):
        cur = self.pw2cur[pwCur]
        if ndiff >= pwCur:
            return 0
        while ndiff>0:
            if cur==0:
                return 0
            m = self.cur2pw[cur]-self.cur2pw[cur-1]
            pwCur -= m
            ndiff -= m
            cur -=1
        return pwCur

    # add pwCur by one step
    def plusCalc(self, pwCur, grid, pLoad, pBuy, pwMax):
        if pBuy > 200:
            return self.minusCalc(pwCur, grid, pBuy)
        if pLoad >= 7000:
            ndiff = pLoad-7000
            return self.minusCalc(pwCur, grid, ndiff)
        if pwCur >= 5500:
            return 5500
        cur = self.pw2cur[pwCur]
        npow = self.cur2pw[cur+1]
        if pLoad+npow-pwCur > pwMax-800:
            print(f"overflow {pLoad}+{npow}-{pwCur} > {pwMax}-1300")
            return pwCur # overflow if add
        return npow

    # return - heating power in W
    def calcHeat(self, pwCur, pwMax, bV, bVmax, pBuy, pBatt, pLoad, tCur, tMax, grid):
        import datetime
        hnow = datetime.datetime.now().hour
        if tCur>= tMax:
            print("return 1")
            return 0
        bres = self.reservCalc(bV, bVmax)      
        #calc minus
        ndiff = bres+pBatt
        if ndiff >=0:
            print(f"{bres}+{pBatt} >= 0")
            return self.minusCalc(pwCur, grid, ndiff)
        #plus calc
        if (pBatt > 400) and (hnow >= 17):
            print("return 3")
            return 0
        plu = self.plusCalc(pwCur, grid, pLoad, pBuy, pwMax)
        battPercent = 500*bV/bVmax-400
        print(f"battPercent = {battPercent}")
        if battPercent > 90:
            print("return 4")
            return plu
        #if not 90% - check not to disturb charging
        print(f"{pBatt} + {plu} - {pwCur} > {-bres}")
        if (pBatt+plu-pwCur) > (-bres):
            print("return 5")
            return pwCur
        return plu

#===============================================
    def stopHeat(self):
        self.applypw(0)
    def heatLogic(self):
        import datetime
        lhp = self._lastHeat
        tmax = n_restClient.restGetVar("tmax")
        temps = n_restClient.restGetTemps()
        tb = temps["_Бак"]
        oldPw = self.getPwNow()
        currr = oldPw
        cur = self.pw2cur[oldPw]
        d = n_restClient.restGetInv()
        grid = d["Grid-connected Status"] == "On-Grid"
        batV = d["Battery Voltage"]
        buy = d["Total Grid Power"]
        solar = d["PV1 Power"]+d["PV2 Power"]+d["PV3 Power"]+d["PV4 Power"]
        batt = d["Battery Current"] * d["Battery Voltage"]
        load = d["Total Load Power"]
        xxxx = n_restClient.restInvGetLastN(["PV1 Power","PV2 Power","PV3 Power","PV4 Power"],4)
        lastSol = []
        for i in xxxx:
        	  sp = sum(list(xxxx[i].values()))
        	  lastSol.append(sp)
        lastSol = lastSol[:-1] #remove current one
	     lastSol = [abs(i-solar) for i in lastSol]
 	     lastSol = sum(lastSol)/len(lastSol)
        wasOn = sum(self.historyPow) != 0
        hnow = datetime.datetime.now().hour
        print(f'{hnow}:: {lastSol} : cur {cur}({oldPw}) buy {buy} solar {solar} batt {batt} {batV} soc {soc} temp {tb}')
        grid = d["Grid-connected Status"] != "Off-Grid"
        p = self.calcHeat(oldPw, 9000, batV, 57.3, buy, batt, load, tb, tmax, grid)
        print(f"{historyPow}, {xxxx}")
        if (hnow>=17)and(p == 1000)and(lastSol<400)and(wasOn):
           p = 0
        t2t = temps["NewTank"]
        buy -= lhp
        if (p == 0) and (t2t < 42) and grid:
          if buy < 5000:
            p+=1000
            buy+=1000
          if buy < 5000:
            p+=1000
        self.applypw(p)
        self.historyPow = self.historyPow[1:]
        self.historyPow.append(p)
        print("Set pw %d" % p)
        self._lastHeat = p

if __name__ == '__main__':
    x = solarLogic()
    while 1:
    	x.heatLogic()
    	time.sleep(1)
