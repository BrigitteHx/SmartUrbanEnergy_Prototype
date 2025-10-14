from flask import Flask
from flask_cors import CORS
import os
from config import Config 
from database import db, init_db 
from seed_data import seed_initial_data 
from routes.city_routes import city_bp 
from routes.energy_routes import energy_bp 

app = Flask(__name__)
CORS(app) 

# Configureer de app 
app.config.from_object(Config)

# Initialiseer de database 
init_db(app)

# Registreer Blueprints voor routes
app.register_blueprint(city_bp)
app.register_blueprint(energy_bp)

# Simpele test route voor backend
@app.route('/')
def hello_world():
    return 'Hello from Flask Backend (Modular Version)!'

if __name__ == '__main__':
    with app.app_context():
        print("Starting database operations...")
        # BELANGRIJK: UNCOMMENT db.drop_all() ALLEEN ALS JE DE DB WIL RESETTEN !!!
        # db.drop_all() 
        db.create_all() # Zorgt dat alle tabellen bestaan (geen migraties hier, alleen aanmaken)
        print("Database tables checked/created.")
        
        # Roep de seed functie aan om data te genereren
        seed_initial_data(app)
        print("Demo data seeding complete.")
        
    app.run(debug=True)