from flask import Flask, render_template
from flask import request
from time import sleep

def bash(cmd):
  #li = cmd.split(' ')
   try:
      import subprocess
      return subprocess.check_output(cmd, shell=True, text=True)
   except:
      return ""
  #result = subprocess.run([cmd], stdout=subprocess.PIPE)
  #return result.stdout.decode('UTF-8')

def loadIp(ip):
   cmd = F"curl {ip} | grep WIFI-DHT"
   s = bash(cmd)
   if s=="":
      return None
   x = s.strip().split(';')
   if len(x) > 4:
      res = F"<a href=\"/{ip}\">"+x[1]+"</a> : " + x[2]+ ' C / ' + x[3] + ' %'
   else:
      res = x[1] + ' : ' + x[2]+ ' C / ' + x[3] + ' %'
   return res


app = Flask("monitoring")

@app.route('/')
def index():
   return render_template("show.html")

@app.route('/<int:i1>.<int:i2>.<int:i3>.<int:i4>', methods = ['GET', 'POST'])
def dht(i1,i2,i3,i4):
   ip = F"{i1}.{i2}.{i3}.{i4}"
   if request.method == 'POST':
      data = request.form
      onT = data['onTemp']
      offT = data['offTemp']
      cmd = F"curl \"{ip}/ON={onT};OFF={offT};\""
      bash(cmd)
      sleep(2)
   cmd = F"curl {ip} | grep WIFI-DHT"
   s = bash(cmd)
   x = s.strip().split(';')
   loc = x[1]
   temp = x[2]
   hum = x[3]
   onT = x[4]
   offT = x[5]
   st = x[6]
   templ = F'''
<html>
<div><big> {loc} </big></div>
<div> Temperature {temp} C</div>
<div> Humidity {hum} %</div>
<div> Heating is now {st}</div> <br>
<form method="POST">
  <div>
    <label for="onTemp">On temperature</label>
    <input name="onTemp" id="onTemp" value="{onT}" />
  </div>
  <div>
    <label for="offTemp">Off temperature</label>
    <input name="offTemp" id="offTemp" value="{offT}" />
  </div>
  <div>
    <button>Commit change</button>
  </div>
</form>
</html>
'''
   return templ

app.run(debug=True,host='0.0.0.0',port=8080)