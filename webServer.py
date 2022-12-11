from flask import Flask, render_template

app = Flask("monitoring")

@app.route('/')
def index():
   return render_template("show.html")

app.run(debug=True,host='0.0.0.0',port=8080)
