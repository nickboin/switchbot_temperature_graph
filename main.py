from flask import Flask, render_template, request, jsonify
import sqlite3
import pandas as pd

app = Flask(__name__)
DATABASE = 'sensor_data.db'

def get_db_connection():
	"""SQLite DB connection"""
	conn = sqlite3.connect(DATABASE)
	conn.row_factory = sqlite3.Row
	return conn


def get_sensor_data(sensor_id=0, start_date=None, end_date=None):
	"""Find records from the database, filtering sensor and dates (if given)"""
	conn = get_db_connection()

	# if not given then act as per interface (first element on select)
	if not sensor_id:
		sensor_id = conn.execute("SELECT sensor_id FROM sensors ORDER BY name LIMIT 1").fetchone()[0]

	query = "SELECT * FROM sensor_data WHERE sensor_id = ?"
	params = [sensor_id]

	for op, val in {
		">=": start_date,
		"<="  : end_date,
	}.items():
		if val:
			query += f" AND date {op} ?"
			params.append(val)

	# TODO why pandas?
	df = pd.read_sql_query(query + " ORDER BY date ASC", conn, params=params)
	conn.close()

	# Converte la colonna 'date' in datetime se necessario
	df['date'] = pd.to_datetime(df['date'])

	return df


@app.route('/')
def index():
	"""Main page"""
	conn = get_db_connection()
	cursor = conn.cursor()

	# fetch basic data for page initialization
	cursor.execute("SELECT MIN(date) AS date_min, MAX(date) AS date_max FROM sensor_data")
	result = cursor.fetchone()
	date_min = result["date_min"] if result else ""
	date_max = result["date_max"] if result else ""

	cursor.execute("SELECT sensor_id, name FROM sensors ORDER BY name")
	sensors = cursor.fetchall()
	conn.close()

	return render_template(
		'index.html.j2',
		date_min=date_min,
		date_max=date_max,
		sensors=sensors
	)


@app.route('/api/graph_data')
def get_graph():
	"""Graph JSON data API"""
	sensor_id  = int(request.args.get('sensor', 0))
	start_date = request.args.get('start_date', None)
	end_date   = request.args.get('end_date', None)

	df = get_sensor_data(sensor_id, start_date, end_date)

	if df.empty:
		return jsonify({'error': 'No data available!'}), 400

	# Prepare data for Plotly
	return jsonify({
		'date': df['date'].dt.strftime('%Y-%m-%d %H:%M:%S').tolist(),
		'temp': df['temp'].tolist(),
		'rh': df['rh'].tolist()
	})


if __name__ == '__main__':
	app.run(debug=True)
