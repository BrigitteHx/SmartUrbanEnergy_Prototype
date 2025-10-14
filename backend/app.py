from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import os
from datetime import datetime, timedelta
import random
from sqlalchemy import func, extract, cast
from sqlalchemy.types import String

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
    
    areas = db.relationship('Area', backref='city', lazy=True, cascade='all, delete-orphan') 

    def __repr__(self):
        return f"<City {self.name}>"

class Area(db.Model):
    __tablename__ = 'areas'
    id = db.Column(db.Integer, primary_key=True)
    city_id = db.Column(db.Integer, db.ForeignKey('cities.id'), nullable=False)
    name = db.Column(db.String(100), unique=True, nullable=False) 
    description = db.Column(db.Text)
    
    lighting_units = db.relationship('LightingUnit', backref='area', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f"<Area {self.name} in City {self.city.name}>"

class LightingUnit(db.Model):
    __tablename__ = 'lighting_units'
    id = db.Column(db.Integer, primary_key=True)
    area_id = db.Column(db.Integer, db.ForeignKey('areas.id'), nullable=False)
    unit_type = db.Column(db.String(50))
    location = db.Column(db.String(255))
    power_watt = db.Column(db.Integer)
    
    consumption_data = db.relationship('EnergyConsumptionData', backref='lighting_unit', lazy=True, cascade='all, delete-orphan')
    recommendations = db.relationship('Recommendation', backref='lighting_unit', lazy=True, cascade='all, delete-orphan')

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

@app.route('/cities')
def get_cities():
    with app.app_context():
        cities = City.query.all()
        return jsonify([{"id": city.id, "name": city.name} for city in cities])

@app.route('/city_area/<int:city_id>')
def get_city_area(city_id):
    with app.app_context():
        area = Area.query.filter_by(city_id=city_id).first()
        if not area:
            return jsonify({"error": "Area not found for this city"}), 404
        return jsonify({"id": area.id, "name": area.name, "description": area.description})


@app.route('/energy_data/<int:area_id>')
def get_energy_data(area_id):
    period_str = request.args.get('period', 'week') 

    with app.app_context():
        area = Area.query.get(area_id)
        if not area:
            return jsonify({"error": "Area not found"}), 404
        
        end_time = datetime.now()
        
        # Bepaal start_time en aggregation_interval/time_format_str
        if period_str == 'day':
            start_time = end_time - timedelta(hours=24)
            aggregation_interval = func.to_char(EnergyConsumptionData.timestamp, 'HH24:00:00')
        elif period_str == 'month':
            start_time = end_time - timedelta(days=30)
            aggregation_interval = func.to_char(EnergyConsumptionData.timestamp, 'YYYY-MM-DD')
        else: # Default is 'week'
            start_time = end_time - timedelta(days=7)
            aggregation_interval = func.to_char(EnergyConsumptionData.timestamp, 'YYYY-MM-DD')

        # Query voor geaggregeerd verbruik over de geselecteerde periode
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
        
        formatted_data = []
        for row in aggregated_consumption:
            formatted_data.append({
                "timestamp": row.interval_start, 
                "consumption_kwh": row.total_consumption,
            })
        
        # --- Simulatie voor inefficiëntie markering (verbruik overdag) ---
        inefficiency_data_query = db.session.query(
            aggregation_interval.label('interval_start'),
            func.sum(EnergyConsumptionData.consumption_kwh).label('inefficient_consumption')
        ).join(LightingUnit).filter(
            LightingUnit.area_id == area_id,
            EnergyConsumptionData.timestamp >= start_time,
            EnergyConsumptionData.timestamp <= end_time,
            EnergyConsumptionData.status_recording == 'Daylight_Inefficiency'
        ).group_by(
            'interval_start'
        ).order_by(
            'interval_start'
        ).all()

        inefficiency_markers = []
        for row in inefficiency_data_query:
            inefficiency_markers.append({
                "timestamp": row.interval_start, 
                "consumption_kwh": row.inefficient_consumption
            })
        
        total_consumption_kwh = sum([d['consumption_kwh'] for d in formatted_data]) if formatted_data else 0.0

        return jsonify({
            "area_id": area_id,
            "area_name": area.name,
            "total_consumption_kwh": total_consumption_kwh,
            "chart_data": formatted_data,
            "inefficiency_markers": inefficiency_markers
        })

@app.route('/recommendation/<int:area_id>')
def get_recommendation(area_id):
    with app.app_context():
        area = Area.query.get(area_id)
        if not area:
            return jsonify({"error": "Area not found"}), 404

        existing_rec = Recommendation.query.filter_by(
            area_id=area_id, 
            title='Optimaliseer Schakeltijden Openbare Verlichting'
        ).first()
        
        if existing_rec:
            rec_data = {
                "title": existing_rec.title,
                "description": existing_rec.description,
                "potential_savings_kwh": existing_rec.potential_savings_kwh,
                "potential_savings_euro": existing_rec.potential_savings_euro,
                "percentage_savings": existing_rec.potential_savings_kwh / 50 * 100 if existing_rec.potential_savings_kwh else 0 
            }
        else:
            potential_kwh_per_month = random.uniform(25.0, 75.0) 
            potential_euro_per_month = round(potential_kwh_per_month * 0.40, 2)

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
                "percentage_savings": new_rec.potential_savings_kwh / 50 * 100 
            }

        return jsonify(rec_data)


@app.route('/savings_scenario/<int:area_id>')
def get_savings_scenario(area_id):
    period_str = request.args.get('period', 'week')
    
    with app.app_context():
        area = Area.query.get(area_id)
        if not area:
            return jsonify({"error": "Area not found"}), 404
        
        end_time = datetime.now()
        if period_str == 'day':
            start_time = end_time - timedelta(hours=24)
            aggregation_interval = func.to_char(EnergyConsumptionData.timestamp, 'HH24:00:00')
        elif period_str == 'month':
            start_time = end_time - timedelta(days=30)
            aggregation_interval = func.to_char(EnergyConsumptionData.timestamp, 'YYYY-MM-DD')
        else: # Default is 'week'
            start_time = end_time - timedelta(days=7)
            aggregation_interval = func.to_char(EnergyConsumptionData.timestamp, 'YYYY-MM-DD')
            
        # Haal het actuele verbruiksprofiel op (deze wordt verminderd met de besparing)
        actual_consumption_query = db.session.query(
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
        
        actual_consumption_map = {}
        for row in actual_consumption_query:
            key = row.interval_start 
            actual_consumption_map[key] = row.total_consumption


        inefficient_consumption_query = db.session.query(
            aggregation_interval.label('interval_start'),
            func.sum(EnergyConsumptionData.consumption_kwh).label('inefficient_kwh')
        ).join(LightingUnit).filter(
            LightingUnit.area_id == area_id,
            EnergyConsumptionData.timestamp >= start_time,
            EnergyConsumptionData.timestamp <= end_time,
            EnergyConsumptionData.status_recording == 'Daylight_Inefficiency'
        ).group_by(
            'interval_start'
        ).order_by(
            'interval_start'
        ).all()
        
        inefficient_consumption_map = {}
        for row in inefficient_consumption_query:
            key = row.interval_start 
            inefficient_consumption_map[key] = row.inefficient_kwh

        # Simuleer de besparing per interval: trek het inefficiënte deel af
        savings_scenario_data = []
        all_intervals = sorted(actual_consumption_map.keys())

        for interval_start_str in all_intervals:
            actual_kwh = actual_consumption_map.get(interval_start_str, 0.0)
            inefficient_kwh_for_interval = inefficient_consumption_map.get(interval_start_str, 0.0)
            
            new_kwh = actual_kwh - inefficient_kwh_for_interval
            if new_kwh < 0: new_kwh = 0

            savings_scenario_data.append({
                "timestamp": interval_start_str,
                "consumption_kwh": new_kwh,
            })

        return jsonify(savings_scenario_data)


if __name__ == '__main__':
    with app.app_context():
        print("Checking/Creating database tables...")
        # --- BELANGRIJK: DEZE LIJN VERWIJDERT AL JE TABELLEN EN DATA.
        # --- ZORG DAT DIT AANSTAAT VOOR DE EERSTE RUNS MET DEZE NIEUWE CODE!
        # db.drop_all() 
        db.create_all()
        print("Tables checked/created.")

        # --- Demo Data Generatie ---
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
                db.session.commit()
                area = Area(city_id=city.id, name=f'Centrum {capital_name}', description=f'Hoofdgebied van {capital_name}')
                db.session.add(area)
            db.session.commit()
            print(f"Demo Cities and Areas added ({len(dutch_capitals)} total).")
        else:
            print("City and Area data already exists, skipping demo data insertion.")

        if not LightingUnit.query.first():
            print("Adding demo LightingUnit and EnergyConsumptionData for all areas...")
            all_areas = Area.query.all()
            
            start_simulation_time = datetime.now() - timedelta(days=30) 

            for area in all_areas:
                lu1 = LightingUnit(area=area, unit_type='LED', location=f'Hoofdstraat {area.name}', power_watt=50)
                lu2 = LightingUnit(area=area, unit_type='LED', location=f'Kerklaan {area.name}', power_watt=50)
                lu3 = LightingUnit(area=area, unit_type='Hogedruk Natrium', location=f'Marktplein {area.name}', power_watt=100)
                db.session.add_all([lu1, lu2, lu3])
                db.session.commit()

                for lu in [lu1, lu2, lu3]:
                    current_time = start_simulation_time
                    while current_time <= datetime.now():
                        consumption = 0.0
                        status = 'Normal'

                        if (current_time.hour >= 18 or current_time.hour < 7) or lu.unit_type == 'Hogedruk Natrium':
                            base_consumption = (lu.power_watt / 1000) * random.uniform(0.2, 0.5)
                            consumption = base_consumption
                            if lu.unit_type == 'Hogedruk Natrium' and (current_time.hour >= 7 and current_time.hour < 18):
                                status = 'Daylight_Inefficiency'
                            elif current_time.hour >= 7 and current_time.hour < 18:
                                status = 'Daylight_Off'
                        
                        consumption += random.uniform(-consumption * 0.1, consumption * 0.1)
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