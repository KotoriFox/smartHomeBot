import datetime

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

def show(h):
     x = h.coll.getData()
     try:
          import smartSolar
          import importlib
          importlib.reload(smartSolar)
          pw = smartSolar.getPwNow(h.r.i2c)
          s  = "On  temp = " + str(h._conf["onoff"][0]) + "(" + str(h.ronoff[0]) + ")\n"
          s += "Off temp = " + str(h._conf["onoff"][1]) + "(" + str(h.ronoff[1]) + ")\n"
          s += "Current temp   = " + str(h.temp[h.heaterKey]) + "\n"
          s += "Current status = " + str(h.r.status('sw1')) + "\n"
          s += "Tank temp  = " + str(h.temp[h.tankKey]) + "\n"
          s += "Tank max   = " + str(h._conf["tmax"]) + '\n'
          s += "On battery = " + str(h.r.isReserve()) + "\n"
          s += "Tank Heating = " + str(pw) + " W\n"
          x = smartSolar.convert(x)
          res = ""
          for i in x:
              res += i + " = " + str(x[i]) + "\n"          
     except:
          s = full_stack()
          print(s)
          for i in s.split('\n'):
            self.log.error(i)
          res = s
     solarData = multiline2Table(res)
     getData = multiline2Table(s)
     h1,s = h.getTemp()
     tempData = multiline2Table('\n'.join(s))
     h.plotName(["в_Південь", "в_Земля", "в_Північ", "в_ПідБудинком"], "static/lane4")
     h.plotName(["Ванна", "Кабінет", "Вітальня"], "static/lane1")
     h.plotName(["Тамбур", "Коридор"], "static/lane2")
     h.plotName(["Паливна", "_Бак", "ТрубаВерх"], "static/lane3")
     tempGraph1 = img(["static/lane1.png","static/lane2.png"])
     tempGraph2 = img(["static/lane3.png","static/lane4.png"])
     h.plotName(["Сонце"], "static/solar")
     h.plotName(["Споживання"], "static/usage")
     h.plotName(["Акум"], "static/Batt")
     h.plotName(["Розряд"], "static/Dis")
     solGraph = img(["static/solar.png", "static/usage.png"])
     batt = img(["static/Batt.png", "static/Dis.png"])
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
     v1 = '<!DOCTYPE html> <html>'+ style + '<body> <div class="header"> <h1>Smart Home stats</h1></div><div class="row">'
     v2 = f'<div class="column"><h2>Temperature</h2> {tempData} {tempGraph1} </div>'
     v3 = f'<div class="column"><h2>Configuration</h2> {getData} {tempGraph2} {batt}</div>'
     v4 = f'<div class="column"><h2>Solar Stuff</h2> {solarData} {solGraph} </div>'
     v5 = '</div></body></html>'
     return v1+v2+v3+v4+v5


