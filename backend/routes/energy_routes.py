from flask import Blueprint, jsonify, request
from database import db
from models import Area
from services.energy_service import get_aggregated_energy_data, get_area_recommendation, get_simulated_savings_scenario

energy_bp = Blueprint('energy_bp', __name__, url_prefix='/energy')

@energy_bp.route('/data/<int:area_id>')
def energy_data_route(area_id):
    period_str = request.args.get('period', 'week')
    data, error = get_aggregated_energy_data(area_id, period_str)
    if error:
        return jsonify({"error": error}), 404
    return jsonify(data)

@energy_bp.route('/recommendation/<int:area_id>')
def recommendation_route(area_id):
    rec_data, error = get_area_recommendation(area_id)
    if error:
        return jsonify({"error": error}), 404
    return jsonify(rec_data)

@energy_bp.route('/savings_scenario/<int:area_id>')
def savings_scenario_route(area_id):
    period_str = request.args.get('period', 'week')
    savings_data, error = get_simulated_savings_scenario(area_id, period_str)
    if error:
        return jsonify({"error": error}), 404
    return jsonify(savings_data)