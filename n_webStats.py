import time
import datetime
import n_restClient

def multiline2Table(s):
  s = s.split('\n')
  res = "<table><tr><td>"
  x = '</td></tr><tr><td>'.join(s)
  res += x + "</tr></td></table>"
  return res

def img(nameli):
  res = ""
  mark = str(datetime.datetime.now().time())
  for i in nameli:
    res += f'<img src="{i}?{mark}" alt="{i}" style="width:100%">'
  return res

def normalize(arr):
  for i in range(1,len(arr)-1):
     avg = (arr[i-1]+arr[i+1])/2
     if abs(arr[i]-avg) > 3*abs(avg-arr[i-1]):
        arr[i] = avg

def getData(d,n):
	try:
		return d[n]
	except:
		return "N/A"

def show(h):
     x = n_restClient.restGetInv()
     pw = n_restClient.restGetVar("CurHeat")
     onoff = n_restClient.restGetVar("onoff") 
     ronoff = n_restClient.restGetVar("realonoff")
     ronoffm = n_restClient.restGetVar("offonminutes")
     temp = n_restClient.restGetTemps()
     temps = {}
     for i in temp:
     	  temps[i] = temp[i][0]
     sw1 = n_restClient.restGetVar("sw1_giver")     
     sw2 = n_restClient.restGetVar("sw2_radiant")
     sw3 = n_restClient.restGetVar("sw3_syncer")
     sw4 = n_restClient.restGetVar("sw4_cooler")
     tmax = n_restClient.restGetVar("tmax")     
     s  = "On  temp = " + str(onoff[0]) + "(" + str(ronoff[0]) + ")\n"
     s += "Off temp = " + str(onoff[1]) + "(" + str(ronoff[1]) + ")\n"
     s += f"fallback heating times ON minutes {ronoffm[1]} OFF minutes {ronoffm[0]}\n"
     v = getData(temps, '_ТеплаПідлога')
     s += f"Current temp   = {v}\n"
     s += f"Current giver status = {sw1}\n"
     s += f"Radiant status       = {sw2}\n"
     s += f"Syncer status        = {sw3}\n"
     s += f"Room cooler status   = {sw4}\n"
     v = getData(temps, '_Бак')
     s += f"Tank temp  = {v}"
     v = getData(temps, 'NewTank')
     s += f"/{v}\n"
     s += f"Tank max   = {tmax}\n"
     v = n_restClient.restGetVar("inner_reserve")
     s += f"L2 fail = {v}\n"
     v = n_restClient.restGetVar("outer_reserve")
     s += f"On battery = {v}\n"
     s += "Tank Heating = " + str(pw) + " W\n"
     x = n_restClient.solarConvert(x)
     res = ""
     for i in x:
         res += i + " = " + str(x[i]) + "\n"
     solarData = multiline2Table(res)
     getData = multiline2Table(s)
     res = ""
     for i in temp:
        res += str(i) + " : " + str(temp[i][0]) + " C"
        if temp[i][1]:
           res += " / "+str(temp[i][1]) + "%"
        res += "\n"
     tempData = multiline2Table(res)
     n_restClient.restPlot("static/lane4", ["в_Південь"])
     n_restClient.restPlot("static/lane1", ["Ванна", "Кабінет", "Вітальня", "_ТеплаПідлога"])
     #h.plotName(["Коридор"], "static/lane2")
     n_restClient.restPlot("static/lane3", ["Паливна", "_Бак", "ТрубаВерх", "NewTank"])
     tempGraph1 = img(["static/lane1.png","static/lane4.png", "static/lane3.png"])
     n_restClient.restPlot("static/solar", ["PV1 Power", "PV2 Power", "PV3 Power", "PV4 Power"])
     n_restClient.restPlot("static/Batt", ["Battery Voltage"])
     n_restClient.restPlot("static/usage", ["Total Load Power"])
     n_restClient.restPlot("static/Dis", ["Total Battery Discharge"])
     n_restClient.restPlot("static/Daily", ["Daily Production", "Daily Energy Bought", "Daily Load Consumption"])
     solGraph = img(["static/solar.png", "static/usage.png"])
     batt = img(["static/Batt.png", "static/Dis.png", "static/Daily.png"])
     style = '''
<style>
* {
  box-sizing: border-box;
}

body {
  margin: 0;
  font-family: Arial;
}

.header {
  text-align: center;
  padding: 32px;
}

.row {
  display: flex;
  flex-wrap: wrap;
  padding: 0 4px;
}

.column {
  flex: 33%;
  max-width: 33%;
  padding: 0 4px;
}

.column img {
  margin-top: 8px;
  vertical-align: left;
}

@media (max-width: 800px) {
  .column {
    flex: 50%;
    max-width: 50%;
  }
}

@media (max-width: 600px) {
  .column {
    flex: 100%;
    max-width: 100%;
  }
}
</style>
     '''
     v1 = '<!DOCTYPE html> <html>'+ style + '<body> <div class="header"> <h1>Smart Home stats</h1>  <a href="/config" target="_blank">Config</a>  </div><div class="row">'
     v2 = f'<div class="column"><h2>Temperature</h2> {tempData} {tempGraph1} </div>'
     v3 = f'<div class="column"><h2>Configuration</h2> {getData} {batt}</div>'
     v4 = f'<div class="column"><h2>Solar Stuff</h2> {solarData} {solGraph} </div>'
     v5 = '</div></body></html>'
     return v1+v2+v3+v4+v5

if __name__ == '__main__':
     while 1:
        html = smartWeb.show(self)
        with open("templates/show.html",'w') as f:
           f.write(html)
        time.sleep(0.2)