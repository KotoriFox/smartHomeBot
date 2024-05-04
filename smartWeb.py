import datetime

def bash(cmd):
  #li = cmd.split(' ')
  import subprocess
  return subprocess.check_output(cmd, shell=True, text=True)
  #result = subprocess.run([cmd], stdout=subprocess.PIPE)
  #return result.stdout.decode('UTF-8')

def readWifiDht():
  try:
    #s = bash("nmap -n -Pn 192.168.1.0/24 -p80 -oG - | grep '/open/' | awk '/Host:/{print $2}' | xargs -n 1 curl --max-time 1 -L --silent | grep WIFI-DHT")
    s = bash("echo 192.168.131.123 192.168.131.31 192.168.131.104 | xargs -P0 -n1 curl --max-time 3 --retry 5 --retry-delay 0 --retry-max-time 15 -L --silent | grep WIFI-DHT")
  except:
    return []
  li = s.strip().split('\n')
  db = []
  for i in li:
    x = i.split(';')
    db.append(x[1] + ' : ' + x[2]+ ' C / ' + x[3] + ' %')
  return db

def full_stack():
    import traceback, sys
    exc = sys.exc_info()[0]
    stack = traceback.extract_stack()[:-1]  # last one would be full_stack()
    if exc is not None:  # i.e. an exception is present
        del stack[-1]       # remove call of full_stack, the printed exception
                            # will contain the caught exception caller instead
    trc = 'Traceback (most recent call last):\n'
    stackstr = trc + ''.join(traceback.format_list(stack))
    if exc is not None:
         stackstr += '  ' + traceback.format_exc().lstrip(trc)
    return stackstr

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

def show(h):
     x = h.coll.getData()
     try:
          import smartSolar
          import importlib
          importlib.reload(smartSolar)
          pw = smartSolar.getPwStr(h.r.i2c)
          s  = "On  temp = " + str(h._conf["onoff"][0]) + "(" + str(h.ronoff[0]) + ")\n"
          s += "Off temp = " + str(h._conf["onoff"][1]) + "(" + str(h.ronoff[1]) + ")\n"
          s += "Current temp   = " + str(h.temp[h.heaterKey]) + "\n"
          s += "Current status = " + str(h.r.status('sw1')) + "\n"
          s += "Radiant status = " + str(h.r.status('sw2')) + "\n"
          s += "Heating status = " + str(h.r.status('sw3')) + "\n"
          s += "Tank temp  = " + str(h.temp[h.tankKey]) + "/"+str(h.temp[h.tank2Key]) + "\n"
          s += "Tank max   = " + str(h._conf["tmax"]) + '\n'
          s += "On battery = " + str(h.reserve) + "\n"
          s += "Tank Heating = " + str(pw) + " W\n"
          x = smartSolar.convert(x)
          res = ""
          for i in x:
              res += i + " = " + str(x[i]) + "\n"
     except:
          s = full_stack()
          print(s)
          for i in s.split('\n'):
            h.log.error(i)
          res = s
     solarData = multiline2Table(res)
     getData = multiline2Table(s)
     h1,s = h.getTemp()
     wfs = readWifiDht()
     s = s+wfs
     tempData = multiline2Table('\n'.join(s))
     h.plotName(["в_Південь", "в_Північ"], "static/lane4")
     h.plotName(["Ванна", "Кабінет", "Вітальня", "_ТеплаПідлога"], "static/lane1")
     #h.plotName(["Коридор"], "static/lane2")
     h.plotName(["Паливна", "_Бак", "ТрубаВерх", "NewTank"], "static/lane3")
     tempGraph1 = img(["static/lane1.png","static/lane4.png"])
     tempGraph2 = img(["static/lane3.png"])
     normalize(h.history["Сонце"][1]);
     normalize(h.history["Акум"][1]);
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


