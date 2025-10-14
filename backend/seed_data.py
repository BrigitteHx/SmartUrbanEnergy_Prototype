from datetime import datetime, timedelta
import random
from database import db
from models import City, Area, LightingUnit, EnergyConsumptionData, Recommendation

def seed_initial_data(app):
    with app.app_context():
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
                db.session.commit() # Committen moet na elke stad om ID te krijgen (!!)
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