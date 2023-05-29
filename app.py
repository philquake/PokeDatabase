from flask import Flask, render_template, request, redirect, url_for
import pokebase as pb

app = Flask(__name__)

class PokeObj:
    def __init__(self,name,id,height):
        self.name = name
        self.id = id
        self.height = height

@app.route('/')
def index():

    return render_template('index.html')

@app.route('/poke', methods=['POST'])
def poke():
    if request.method == "POST":
        poke_name = request.form['poke_name']
        return redirect(url_for('poke_detail', poke_name = poke_name))
    return render_template('index.html')

@app.route('/poke_detail/<poke_name>', methods=['GET', 'POST'])
def poke_detail(poke_name):
    name = pb.pokemon(poke_name)
    id = name.id
    height = name.height
    pname = name.name
    obj = PokeObj(pname,id,height)
    return render_template('poke_detail.html', obj=obj)

if __name__ =="__main__":
    app.run(debug=True)