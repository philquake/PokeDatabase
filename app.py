from flask import Flask, render_template
import pokebase as pb

app = Flask(__name__)

@app.route('/')
def index():
    charmander = pb.pokemon('charmander')  # Quick lookup.
    poke_name = charmander.height

    return render_template('index.html',poke_name=poke_name)


if __name__ =="__main__":
    app.run(debug=True)