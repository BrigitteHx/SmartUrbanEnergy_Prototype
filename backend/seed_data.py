# backend/seed_data.py

from datetime import datetime, timedelta
import random
from database import db
from models import City, Area, LightingUnit, EnergyConsumptionData, Recommendation

def seed_initial_data(app):
    with app.app_context():
        # Definieer de Nederlandse provinciale hoofdsteden
        dutch_capitals = [
            "Amsterdam", "Rotterdam", "Den Haag", "Utrecht", "Groningen", 
            "Leeuwarden", "Arnhem", "Zwolle", "Middelburg", "Maastricht", 
            "Haarlem", "'s-Hertogenbosch", "Lelystad", "Assen"
        ]

        # --- Controleer en voeg Cities and Areas toe ---
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

        # --- Controleer en voeg LightingUnits en EnergyConsumptionData toe ---
        # Belangrijk: we genereren altijd 40 dagen data tot het einde van de huidige dag.
        # Dit zorgt ervoor dat er altijd recente data is, zelfs als het script niet elke dag draait met db.drop_all().
        
        # We halen alle bestaande LightingUnits op om te zien of we data moeten toevoegen
        all_lighting_units = LightingUnit.query.all()
        if not all_lighting_units: # Als er nog geen lighting units zijn, maak ze dan aan
            print("Adding demo LightingUnit and EnergyConsumptionData for all areas...")
            all_areas = Area.query.all()
            
            # Start de simulatie van data vanaf ~40 dagen geleden tot HET EINDE VAN VANDAAG
            start_simulation_time = datetime.now() - timedelta(days=40) 
            end_simulation_time = datetime.now().replace(hour=23, minute=0, second=0, microsecond=0) # Einde van de huidige dag

            for area in all_areas:
                lu1 = LightingUnit(area=area, unit_type='LED', location=f'Hoofdstraat {area.name}', power_watt=50)
                lu2 = LightingUnit(area=area, unit_type='LED', location=f'Kerklaan {area.name}', power_watt=50)
                lu3 = LightingUnit(area=area, unit_type='Hogedruk Natrium', location=f'Marktplein {area.name}', power_watt=100)
                db.session.add_all([lu1, lu2, lu3])
                db.session.commit() # Commit hier om IDs te krijgen voor de data generatie

                for lu in [lu1, lu2, lu3]:
                    current_time = start_simulation_time
                    while current_time <= end_simulation_time: # Loop tot het einde van de huidige dag
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
            # Als er al LightingUnits zijn, checken we of we nog nieuwe data moeten genereren voor de meest recente periode
            # Dit is de situatie als db.drop_all() NIET is aangeroepen
            last_timestamp = db.session.query(func.max(EnergyConsumptionData.timestamp)).scalar()
            if not last_timestamp or last_timestamp < datetime.now().replace(hour=0, minute=0, second=0, microsecond=0):
                print(f"Existing data ends at {last_timestamp}. Generating new data up to end of today...")
                all_areas = Area.query.all()
                all_lighting_units_db = LightingUnit.query.all()
                
                # Start vanaf het uur na de laatste opname, of begin vandaag om 00:00
                start_new_data_time = (last_timestamp or datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)) + timedelta(hours=1)
                end_new_data_time = datetime.now().replace(hour=23, minute=0, second=0, microsecond=0)

                for lu in all_lighting_units_db: # Loop over bestaande lampen
                    current_time = start_new_data_time
                    while current_time <= end_new_data_time:
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
                print("New EnergyConsumptionData generated up to end of today.")
            else:
                print("LightingUnit data already exists and is up-to-date, skipping demo data insertion.")