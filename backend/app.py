# backend/app.py

from flask import Flask
from flask_cors import CORS
import os
from config import Config # Importeer de Config class
from database import db, init_db # Importeer db en init_db functie
from seed_data import seed_initial_data # Importeer seed functie

app = Flask(__name__)
CORS(app) 

# Configureer de app met de instellingen uit config.py
app.config.from_object(Config)

# Initialiseer de database met de app
init_db(app)

# Registreer Blueprints voor routes
from routes.city_routes import city_bp # Importeer blueprint voor steden
from routes.energy_routes import energy_bp # Importeer blueprint voor energie

app.register_blueprint(city_bp)
app.register_blueprint(energy_bp)

# Simpele test route 
@app.route('/')
def hello_world():
    return 'Hello from Flask Backend (Modular Version)!'

if __name__ == '__main__':
    with app.app_context(): # Zorgt ervoor dat alle database operaties de context hebben
        print("Starting database operations...")
        # --- BELANGRIJK: ZORG DAT DEZE LIJN ALLEEN AANSTAAT ALS JE ECHT WIL RESETTEN! ---
        # db.drop_all() # UNCOMMENT DIT TIJDELIJK OM ALLE TABELLEN EN DATA TE WISSEN
        db.create_all() # Zorgt dat alle tabellen bestaan (geen migraties hier, alleen aanmaken)
        print("Database tables checked/created.")
        
        # Roep de seed functie aan om data te genereren
        # Deze functie beheert nu zelf of data verwijderd en/of aangevuld moet worden
        seed_initial_data() # Roep de seed functie aan, de 'app' context is al gezet
        print("Demo data seeding complete.")
        
    app.run(debug=True)