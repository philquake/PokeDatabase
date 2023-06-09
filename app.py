from flask import Flask, render_template, request, redirect, url_for
import pokebase as pb
import logging, pprint

app = Flask(__name__)

class PokeObj:
    def __init__(self,name,id,height):
        self.name = name
        self.id = id
        self.height = height

class GenObj:
    def __init__(self, gen, name):
        self.gen = gen
        self.name = name
        
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
    error = None
    try:
        poke = pb.pokemon(poke_name)
        app.logger.info(poke)   #Concsole log for pokemon name entered    
        id = poke.id
        height = poke.height
        pname = poke.name
        # app.logger.info('Type',(poke.type_))
        # types = poke.types
        obj = PokeObj(pname,id,height)
        return render_template('poke_detail.html', obj=obj)
    except: #Will handle Attribute Error if an incorrect pokemon name is entered
        error = "Please check your spelling, no such pokemon."
        return render_template('index.html',error=error)
    
@app.route('/gen', methods=['POST'])
def gen():
    if request.method == "POST":
        gen = request.form['gen']
        return redirect(url_for('generation', gen = gen))
    return render_template('index.html')

@app.route('/generation/<gen>', methods=['GET', 'POST'])
def generation(gen):
    error = None
    genlist = []
    try:
        match gen:
            case "1":
                GENERATION = 1
            case "2":
                GENERATION = 2
            case "3":
                GENERATION = 3
            case "4":
                GENERATION = 4
            case "5":
                GENERATION = 5
            case "6":
                GENERATION = 6
            case "7":
                GENERATION = 7
            case "8":
                GENERATION = 8
            case "9":
                GENERATION = 9
            case other:
                error = "No such generation."
        gen_resource = pb.generation(GENERATION)     # Get API data associated with that particular generation.
        for pokemon in gen_resource.pokemon_species:     # Iterate through the list of Pokemon introduced in that generation.
            genlist.append(GenObj(GENERATION,pokemon.name.title()))
        return render_template('generation.html', genlist = genlist, len = len(genlist))
    except:
        return render_template('index.html',error=error)

if __name__ =="__main__":
    app.run(debug=True)