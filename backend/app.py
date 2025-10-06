from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import os
from datetime import datetime, timedelta
import random
from sqlalchemy import func, extract, and_ # Voor database aggregatie functies

app = Flask(__name__)
CORS(app) 

# Database configuratie
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL') or \
                                        'postgresql://postgres:password@localhost:5432/smart_urban_energy_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Definieer je databasemodellen
class City(db.Model):
    __tablename__ = 'cities'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    # Een stad kan meerdere gebieden/wijken hebben, maar voor nu simplificeren we
    # dat elke stad een uniek 'gebied' is, of we koppelen Areas direct aan City
    # Laten we voor nu Area direct aan City koppelen
    areas = db.relationship('Area', backref='city', lazy=True) 

    def __repr__(self):
        return f"<City {self.name}>"

class Area(db.Model):
    __tablename__ = 'areas'
    id = db.Column(db.Integer, primary_key=True)
    city_id = db.Column(db.Integer, db.ForeignKey('cities.id'), nullable=False) # Nieuwe Foreign Key naar City
    name = db.Column(db.String(100), unique=True, nullable=False) # Nu is dit de wijknaam
    description = db.Column(db.Text)
    
    lighting_units = db.relationship('LightingUnit', backref='area', lazy=True)

    def __repr__(self):
        return f"<Area {self.name} in City {self.city.name}>"

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


# --- API ROUTES ---

@app.route('/')
def hello_world():
    return 'Hello from Flask Backend!'

# Haal alle steden op
@app.route('/cities')
def get_cities():
    with app.app_context():
        cities = City.query.all()
        # In dit prototype gebruiken we Area.name als de 'stad'
        # dus we sturen een lijst van unieke Area namen terug voor de dropdowns
        # Dit simuleert dat elke Area een 'stad' is voor de dropdown
        return jsonify([{"id": city.id, "name": city.name} for city in cities])

# Haal gebieden op per stad (voor dit prototype 1-op-1)
@app.route('/city_area/<int:city_id>')
def get_city_area(city_id):
    with app.app_context():
        area = Area.query.filter_by(city_id=city_id).first()
        if not area:
            return jsonify({"error": "Area not found for this city"}), 404
        return jsonify({"id": area.id, "name": area.name, "description": area.description})


# Haal energieverbruik op voor een stad/gebied en periode
@app.route('/energy_data/<int:area_id>')
def get_energy_data(area_id):
    period_str = request.args.get('period', 'week') # Default naar 'week'

    with app.app_context():
        area = Area.query.get(area_id)
        if not area:
            return jsonify({"error": "Area not found"}), 404
        
        # Bereken de starttijd op basis van de periode
        end_time = datetime.now()
        if period_str == 'day':
            start_time = end_time - timedelta(hours=24)
            # Voor dagdata willen we uurlijkse aggregatie
            aggregation_interval = extract('hour', EnergyConsumptionData.timestamp)
            date_format = '%Y-%m-%dT%H:00:00'
        elif period_str == 'month':
            start_time = end_time - timedelta(days=30)
            # Voor maanddata willen we dagelijkse aggregatie
            aggregation_interval = func.date_trunc('day', EnergyConsumptionData.timestamp)
            date_format = '%Y-%m-%dT00:00:00'
        else: # Default is 'week'
            start_time = end_time - timedelta(days=7)
            # Voor weekdata willen we dagelijkse aggregatie
            aggregation_interval = func.date_trunc('day', EnergyConsumptionData.timestamp)
            date_format = '%Y-%m-%dT00:00:00'

        # Query voor geaggregeerd verbruik over de geselecteerde periode
        # We negeren individuele lighting units voor de geaggregeerde grafiek (vereenvoudiging)
        aggregated_consumption = db.session.query(
            aggregation_interval.label('interval_start'),
            func.sum(EnergyConsumptionData.consumption_kwh).label('total_consumption')
        ).join(LightingUnit).filter(
            LightingUnit.area_id == area_id,
            EnergyConsumptionData.timestamp >= start_time,
            EnergyConsumptionData.timestamp <= end_time
        ).group_by(
            'interval_start'
        ).order_by(
            'interval_start'
        ).all()
        
        # Resultaten formatteren
        formatted_data = []
        for row in aggregated_consumption:
            # Zorg dat de datetime objecten correct naar string worden geconverteerd
            interval_key = row.interval_start.isoformat() if isinstance(row.interval_start, datetime) else row.interval_start
            formatted_data.append({
                "timestamp": interval_key,
                "consumption_kwh": row.total_consumption,
            })
        
        # Voeg hier simulatie voor baseline en inefficiëntie markering toe
        # Voor dit prototype, simuleren we een verwachte baseline en een 'daglicht piek'
        
        # Eenvoudige baseline: gemiddelde consumptie over de gehele periode
        avg_consumption_per_interval = sum([d['consumption_kwh'] for d in formatted_data]) / len(formatted_data) if formatted_data else 0

        # Simuleer een inefficiëntie (bijv. 10% extra verbruik overdag)
        inefficiency_data = []
        for row in formatted_data:
            ts = datetime.fromisoformat(row['timestamp']) if isinstance(row['timestamp'], str) else row['timestamp']
            
            # Daglicht uren zijn hier de inefficiëntie die we willen spotten
            is_daytime = ts.hour >= 7 and ts.hour < 18 if period_str == 'day' else False # Check alleen bij dagdata voor uur

            if is_daytime and row['consumption_kwh'] > 0.05: # Als er verbruik is overdag
                 # Voeg een extra 'inefficiëntie' entry toe voor de visualisatie
                inefficiency_data.append({
                    "timestamp": row['timestamp'],
                    "consumption_kwh": row['consumption_kwh'], # Toon de actuele consumptie die inefficiënt is
                })
        
        total_consumption_kwh = sum([d['consumption_kwh'] for d in formatted_data])

        return jsonify({
            "area_id": area_id,
            "area_name": area.name,
            "total_consumption_kwh": total_consumption_kwh,
            "chart_data": formatted_data,
            "inefficiency_markers": inefficiency_data # Voor de rode lijn/markering
        })

# --- Haal aanbeveling op voor een stad/gebied ---
@app.route('/recommendation/<int:area_id>')
def get_recommendation(area_id):
    with app.app_context():
        area = Area.query.get(area_id)
        if not area:
            return jsonify({"error": "Area not found"}), 404

        # Voor dit prototype, laten we een simpele aanbeveling genereren/ophalen
        existing_rec = Recommendation.query.filter_by(area_id=area_id, title='Optimaliseer Schakeltijden Openbare Verlichting').first()
        
        if existing_rec:
            rec_data = {
                "title": existing_rec.title,
                "description": existing_rec.description,
                "potential_savings_kwh": existing_rec.potential_savings_kwh,
                "potential_savings_euro": existing_rec.potential_savings_euro,
                "percentage_savings": existing_rec.potential_savings_kwh / 50 * 100 # Simpele berekening voor demo
            }
        else:
            # Simpele aanbeveling voor de 'Daylight_Inefficiency' die we simuleren
            potential_kwh_per_month = random.uniform(25.0, 75.0) # Willekeurige besparing per maand in kWh
            potential_euro_per_month = round(potential_kwh_per_month * 0.40, 2) # Stel 0.40 per kWh

            new_rec = Recommendation(
                area_id=area_id,
                date_generated=datetime.now().date(),
                title='Optimaliseer Schakeltijden Openbare Verlichting',
                description='Onnodig energieverbruik gedetecteerd door straatverlichting die onnodig lang aanstaat of niet meeschaalt met de daglichturen. Door schakeltijden aan te passen of te dimmen tussen 07:00 en 18:00 uur kan significant bespaard worden.',
                potential_savings_kwh=potential_kwh_per_month,
                potential_savings_euro=potential_euro_per_month,
                action_status='Nieuw'
            )
            db.session.add(new_rec)
            db.session.commit()
            rec_data = {
                "title": new_rec.title,
                "description": new_rec.description,
                "potential_savings_kwh": new_rec.potential_savings_kwh,
                "potential_savings_euro": new_rec.potential_savings_euro,
                "percentage_savings": new_rec.potential_savings_kwh / 50 * 100 # Simpele berekening voor demo
            }

        return jsonify(rec_data)


# --- ROUTE voor het simuleren van een besparingsscenario ---
@app.route('/savings_scenario/<int:area_id>')
def get_savings_scenario(area_id):
    period_str = request.args.get('period', 'week')
    
    with app.app_context():
        area = Area.query.get(area_id)
        if not area:
            return jsonify({"error": "Area not found"}), 404
        
        # Hier kun je een meer geavanceerde simulatie doen
        # Voor dit prototype: pak de eerder berekende aanbeveling
        recommendation = Recommendation.query.filter_by(area_id=area_id, title='Optimaliseer Schakeltijden Openbare Verlichting').first()
        
        if not recommendation:
            return jsonify({"error": "No recommendation found to simulate savings"}), 404

        # Bereken de start- en eindtijd zoals in get_energy_data
        end_time = datetime.now()
        if period_str == 'day':
            start_time = end_time - timedelta(hours=24)
            date_format = '%Y-%m-%dT%H:00:00'
            interval_delta = timedelta(hours=1)
        elif period_str == 'month':
            start_time = end_time - timedelta(days=30)
            date_format = '%Y-%m-%dT00:00:00'
            interval_delta = timedelta(days=1)
        else: # Default is 'week'
            start_time = end_time - timedelta(days=7)
            date_format = '%Y-%m-%dT00:00:00'
            interval_delta = timedelta(days=1)
            
        # Haal de actuele chart data op (simpelweg de basisdata zonder aggregatie)
        # Voor een echte simulatie zou je de data eerst aggregeren
        actual_consumption_query = db.session.query(
            func.date_trunc(
                'hour' if period_str == 'day' else 'day',
                EnergyConsumptionData.timestamp
            ).label('interval_start'),
            func.sum(EnergyConsumptionData.consumption_kwh).label('total_consumption')
        ).join(LightingUnit).filter(
            LightingUnit.area_id == area_id,
            EnergyConsumptionData.timestamp >= start_time,
            EnergyConsumptionData.timestamp <= end_time
        ).group_by(
            'interval_start'
        ).order_by(
            'interval_start'
        ).all()
        
        actual_consumption_map = {row.interval_start: row.total_consumption for row in actual_consumption_query}

        # Simuleer de besparing per interval
        savings_scenario_data = []
        current_interval_time = start_time
        while current_interval_time <= end_time:
            actual_kwh = actual_consumption_map.get(current_interval_time, 0.0)
            
            # Hier de logica van de aanbeveling toepassen
            # Voor ons prototype: als er overdag verbruik was (inefficiëntie), verwijderen we dat
            # We hadden Hogedruk Natrium lampen die overdag aan stonden
            # Simuleer dat we 1/3 van het totale verbruik (door 1 op 3 inefficiënte lampen) overdag kunnen elimineren
            # Dit is een GROVE SIMULATIE!

            # Zoek echte LightingUnits die de 'Daylight_Inefficiency' status hadden
            daylight_ineff_consumption_for_interval = db.session.query(
                func.sum(EnergyConsumptionData.consumption_kwh)
            ).join(LightingUnit).filter(
                LightingUnit.area_id == area_id,
                EnergyConsumptionData.timestamp == current_interval_time,
                EnergyConsumptionData.status_recording == 'Daylight_Inefficiency'
            ).scalar() or 0.0 # Sum of consumption from inefficient units at this hour
            
            # De bespaarde hoeveelheid voor dit interval
            saved_kwh_this_interval = daylight_ineff_consumption_for_interval # Simuleer dat we dit deel elimineren
            
            new_kwh = actual_kwh - saved_kwh_this_interval
            if new_kwh < 0: new_kwh = 0 # Verbruik kan niet negatief zijn

            savings_scenario_data.append({
                "timestamp": current_interval_time.isoformat(),
                "consumption_kwh": new_kwh,
            })
            current_interval_time += interval_delta

        return jsonify(savings_scenario_data)



if __name__ == '__main__':
    with app.app_context():
        print("Checking/Creating database tables...")
        # db.drop_all() # UNCOMMENT DIT ALLEEN ALS JE ALLE TABELLEN EN DATA WIL WISSEN EN OPNIEUW BEGINNEN
        db.create_all()
        print("Tables checked/created.")

        # --- Demo Data Generatie ---
        # Definieer de Nederlandse provinciale hoofdsteden
        dutch_capitals = [
            "Amsterdam", "Rotterdam", "Den Haag", "Utrecht", "Groningen", 
            "Leeuwarden", "Arnhem", "Zwolle", "Middelburg", "Maastricht", 
            "Haarlem", "'s-Hertogenbosch", "Lelystad", "Assen"
        ]

        if not City.query.first():
            print("Adding demo City and Area data...")
            for capital_name in dutch_capitals:
                city = City(name=capital_name)
                db.session.add(city)
                db.session.commit() # Commit na elke stad om ID te krijgen
                # Voor dit prototype, elke stad is zijn eigen 'area' voor de lampen
                area = Area(city_id=city.id, name=f'Centrum {capital_name}', description=f'Hoofdgebied van {capital_name}')
                db.session.add(area)
            db.session.commit()
            print(f"Demo Cities and Areas added ({len(dutch_capitals)} total).")
        else:
            print("City and Area data already exists, skipping demo data insertion.")

        # Genereer LightingUnits en EnergyConsumptionData voor elke Area
        if not LightingUnit.query.first():
            print("Adding demo LightingUnit and EnergyConsumptionData for all areas...")
            all_areas = Area.query.all()
            
            # Simulatie start vanaf 30 dagen terug om voldoende data voor 'month' en 'week' te hebben
            start_simulation_time = datetime.now() - timedelta(days=30) 

            for area in all_areas:
                # Elke area krijgt 3 lantaarnpalen
                lu1 = LightingUnit(area=area, unit_type='LED', location=f'Hoofdstraat {area.name}', power_watt=50)
                lu2 = LightingUnit(area=area, unit_type='LED', location=f'Kerklaan {area.name}', power_watt=50)
                lu3 = LightingUnit(area=area, unit_type='Hogedruk Natrium', location=f'Marktplein {area.name}', power_watt=100)
                db.session.add_all([lu1, lu2, lu3])
                db.session.commit()

                # Simuleer 30 dagen data, uur per uur voor elke lantaarnpaal
                for lu in [lu1, lu2, lu3]:
                    current_time = start_simulation_time
                    while current_time <= datetime.now():
                        consumption = 0.0
                        status = 'Normal'

                        if (current_time.hour >= 18 or current_time.hour < 7) or lu.unit_type == 'Hogedruk Natrium':
                            consumption = (lu.power_watt / 1000) * 1 # kWh voor 1 uur
                            if lu.unit_type == 'Hogedruk Natrium' and (current_time.hour >= 7 and current_time.hour < 18):
                                status = 'Daylight_Inefficiency'
                            elif current_time.hour >= 7 and current_time.hour < 18:
                                status = 'Daylight_Off'
                        
                        consumption += random.uniform(-0.005, 0.005)
                        if consumption < 0: consumption = 0
                        
                        data_entry = EnergyConsumptionData(
                            lighting_unit=lu,
                            timestamp=current_time,
                            consumption_kwh=consumption,
                            status_recording=status
                        )
                        db.session.add(data_entry)
                        current_time += timedelta(hours=1)
            db.session.commit()
            print("Demo LightingUnits and ConsumptionData added for all areas.")
        else:
            print("LightingUnit data already exists, skipping demo data insertion.")
            
    app.run(debug=True)