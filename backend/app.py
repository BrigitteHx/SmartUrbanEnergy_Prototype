from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import os
from datetime import datetime, timedelta
import random

app = Flask(__name__)
CORS(app) 

# Database configuratie
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL') or \
                                        'postgresql://postgres:password@localhost:5432/smart_urban_energy_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Definieer databasemodellen 
class Area(db.Model):
    __tablename__ = 'areas'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text)
    
    lighting_units = db.relationship('LightingUnit', backref='area', lazy=True)

    def __repr__(self):
        return f"<Area {self.name}>"

class LightingUnit(db.Model):
    __tablename__ = 'lighting_units'
    id = db.Column(db.Integer, primary_key=True)
    area_id = db.Column(db.Integer, db.ForeignKey('areas.id'), nullable=False)
    unit_type = db.Column(db.String(50)) 
    location = db.Column(db.String(255)) 
    power_watt = db.Column(db.Integer) 
    
    consumption_data = db.relationship('EnergyConsumptionData', backref='lighting_unit', lazy=True)
    recommendations = db.relationship('Recommendation', backref='lighting_unit', lazy=True)

    def __repr__(self):
        return f"<LightingUnit {self.location} in Area {self.area.name}>"

class EnergyConsumptionData(db.Model):
    __tablename__ = 'energy_consumption_data'
    id = db.Column(db.Integer, primary_key=True)
    lighting_unit_id = db.Column(db.Integer, db.ForeignKey('lighting_units.id'), nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False)
    consumption_kwh = db.Column(db.Float, nullable=False) 
    status_recording = db.Column(db.String(50)) 

    def __repr__(self):
        return f"<Consumption {self.consumption_kwh}kWh at {self.timestamp} for LU_ID:{self.lighting_unit_id}>"

class Recommendation(db.Model):
    __tablename__ = 'recommendations'
    id = db.Column(db.Integer, primary_key=True)
    area_id = db.Column(db.Integer, db.ForeignKey('areas.id'), nullable=True)
    lighting_unit_id = db.Column(db.Integer, db.ForeignKey('lighting_units.id'), nullable=True)
    date_generated = db.Column(db.Date, nullable=False)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=False)
    potential_savings_kwh = db.Column(db.Float)
    potential_savings_euro = db.Column(db.Float)
    action_status = db.Column(db.String(50))

    def __repr__(self):
        return f"<Recommendation {self.title} for AreaID:{self.area_id} LU_ID:{self.lighting_unit_id}>"

# Simpele test route
@app.route('/')
def hello_world():
    return 'Hello from Flask Backend!'

# Route om alle gebieden op te halen
@app.route('/areas')
def get_areas():
    with app.app_context():
        areas = Area.query.all()
        return jsonify([{"id": area.id, "name": area.name, "description": area.description} for area in areas])

# Route om energieverbruik op te halen voor een specifieke periode
@app.route('/energy_data/<int:area_id>')
@app.route('/energy_data/<int:area_id>/<string:period>') 
def get_energy_data(area_id, period='day'): 
    with app.app_context():
        area = Area.query.get(area_id)
        if not area:
            return jsonify({"error": "Area not found"}), 404
        
        lighting_units_in_area = LightingUnit.query.filter_by(area_id=area_id).all()
        
        all_consumption_data = []
        for lu in lighting_units_in_area:
            data_for_unit = EnergyConsumptionData.query.filter_by(lighting_unit_id=lu.id)\
                                                .order_by(EnergyConsumptionData.timestamp.asc())\
                                                .all() 
            
            all_consumption_data.append({
                "unit_id": lu.id,
                "location": lu.location,
                "unit_type": lu.unit_type,
                "power_watt": lu.power_watt,
                "data": [{
                    "timestamp": d.timestamp.isoformat(), # ISO formaat voor makkelijke JS parsing
                    "consumption_kwh": d.consumption_kwh,
                    "status_recording": d.status_recording
                } for d in data_for_unit]
            })
        
        return jsonify(all_consumption_data)

# Route om de meest relevante aanbeveling op te halen 
@app.route('/recommendation/<int:area_id>')
def get_recommendation(area_id):
    with app.app_context():
        area = Area.query.get(area_id)
        if not area:
            return jsonify({"error": "Area not found"}), 404
        existing_rec = Recommendation.query.filter_by(area_id=area_id, title='Dimmen overdag / LED-upgrade').first()
        
        if existing_rec:
            rec_data = {
                "title": existing_rec.title,
                "description": existing_rec.description,
                "potential_savings_kwh": existing_rec.potential_savings_kwh,
                "potential_savings_euro": existing_rec.potential_savings_euro
            }
        else:
            # Simpele aanbeveling voor de 'Daylight_Inefficiency'
            # Bereken potentieel: stel, 2 inefficiënte lampen verbruiken 0.1 kWh/uur * 11 uur overdag = 1.1 kWh/dag per lamp
            # * 30 dagen = 33 kWh per maand. €0.40/kWh = ~€13.20
            potential_kwh = (2 * 0.1 * 11) * 30 # Voor 2 lampen, 11 uur, 30 dagen
            potential_euro = round(potential_kwh * 0.40, 2) # Stel 0.40 per kWh

            new_rec = Recommendation(
                area_id=area_id,
                date_generated=datetime.now().date(),
                title='Dimmen overdag / LED-upgrade',
                description='Er is onnodig energieverbruik gedetecteerd door straatverlichting die overdag aanstaat, met name bij oudere types lampen. Door de schakeltijden aan te passen of te upgraden naar energiezuinige LED-verlichting kan aanzienlijk bespaard worden.',
                potential_savings_kwh=potential_kwh,
                potential_savings_euro=potential_euro,
                action_status='Nieuw'
            )
            db.session.add(new_rec)
            db.session.commit()
            rec_data = {
                "title": new_rec.title,
                "description": new_rec.description,
                "potential_savings_kwh": new_rec.potential_savings_kwh,
                "potential_savings_euro": new_rec.potential_savings_euro
            }

        return jsonify(rec_data)


if __name__ == '__main__':
    with app.app_context():
        print("Checking/Creating database tables...")
        db.create_all()
        print("Tables checked/created.")

        # Voeg initiële demo Area data toe als de tabel leeg is
        if not Area.query.first(): 
            print("Adding demo Area data...")
            demo_area = Area(name='De Groene Kreek', description='Fictieve wijk voor energie-analyse')
            db.session.add(demo_area)
            db.session.commit()
            print("Demo Area added.")
        else:
            print("Area data already exists, skipping demo data insertion.")
        
        # Gesimuleerde LightingUnit en EnergyConsumptionData toevoegen
        if not LightingUnit.query.first(): # Kijkt of er al een LightingUnit is
            print("Adding demo LightingUnit and EnergyConsumptionData...")
            groene_kreek_area = Area.query.filter_by(name='De Groene Kreek').first()
            if groene_kreek_area:
                # 3 lantaarnpalen voor 'De Groene Kreek'
                lu1 = LightingUnit(area=groene_kreek_area, unit_type='LED', location='Hoofdstraat 1', power_watt=50)
                lu2 = LightingUnit(area=groene_kreek_area, unit_type='LED', location='Kerklaan 2', power_watt=50)
                lu3 = LightingUnit(area=groene_kreek_area, unit_type='Hogedruk Natrium', location='Marktplein 3', power_watt=100)
                db.session.add_all([lu1, lu2, lu3])
                db.session.commit()

                # Simuleer 24 uur data voor elke lantaarnpaal vanaf vandaag
                start_time = datetime(datetime.now().year, datetime.now().month, datetime.now().day, 0, 0, 0)
                for lu in [lu1, lu2, lu3]:
                    for i in range(24): 
                        current_time = start_time + timedelta(hours=i)
                        consumption = 0.0
                        status = 'Normal'

                        # Simulatie Logica voor Inefficiëntie:
                        # Lampen zijn aan van 18:00 tot 07:00 (normaal)
                        # Hoge Druk Natrium lampen (lu3) zijn ALTIJD aan, zelfs overdag, wat inefficiënt is.
                        if (current_time.hour >= 18 or current_time.hour < 7) or lu.unit_type == 'Hogedruk Natrium':
                            consumption = (lu.power_watt / 1000) * 1 # kWh voor 1 uur
                            if lu.unit_type == 'Hogedruk Natrium' and (current_time.hour >= 7 and current_time.hour < 18):
                                status = 'Daylight_Inefficiency' # Specifiek deze status voor overdag aan van inefficiënte lampen
                            elif current_time.hour >= 7 and current_time.hour < 18:
                                status = 'Daylight_Off' # Status voor LED lampen die uit zijn overdag

                        # Voeg wat lichte random ruis toe
                        consumption += random.uniform(-0.005, 0.005)
                        if consumption < 0: consumption = 0 # Verbruik kan niet negatief zijn

                        data_entry = EnergyConsumptionData(
                            lighting_unit=lu,
                            timestamp=current_time,
                            consumption_kwh=consumption,
                            status_recording=status
                        )
                        db.session.add(data_entry)
                db.session.commit()
                print("Demo LightingUnits and ConsumptionData added.")
            else:
                print("Area 'De Groene Kreek' not found, cannot add LightingUnits.")
        else:
            print("LightingUnit data already exists, skipping demo data insertion.")
            
    app.run(debug=True)