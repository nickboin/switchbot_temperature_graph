from flask import Flask, render_template, request, jsonify
import sqlite3

app = Flask(__name__)
DATABASE = 'sensor_data.db'

def get_db_connection():
	"""SQLite DB connection"""
	conn = sqlite3.connect(DATABASE)
	conn.row_factory = sqlite3.Row
	return conn


def get_sensor_data(sensor_id=0, start_date=None, end_date=None):
	"""Find records from the database, filtering sensor and dates (if given)"""

	with get_db_connection() as conn:
		# if not given then act as per interface (first element on select)
		if not sensor_id:
			sensor_id = conn.execute("SELECT sensor_id FROM sensors ORDER BY name LIMIT 1").fetchone()[0]

		query = "SELECT * FROM sensor_data WHERE sensor_id = ?"
		params = [sensor_id]

		# filtering, if set, for dates
		for op, val in {
			">=": start_date,
			"<="  : end_date,
		}.items():
			if val:
				query += f" AND date {op} ?"
				params.append(val)

		# executing query
		cursor = conn.cursor()
		cursor.execute(query + " ORDER BY date ASC", params)

		# mapping desired result in different parallel arrays
		df = {'empty': True, 'date': [], 'temp': [], 'rh': []}

		row = cursor.fetchone()
		df['empty'] = not row

		while row:
			df["date"].append(row['date'])
			df["temp"].append(row['temp'])
			df["rh"].append(row['rh'])
			row = cursor.fetchone()

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

	if df['empty']:
		return jsonify({'error': 'No data available!'}), 400

	# Prepare data for Plotly
	return jsonify(df)


if __name__ == '__main__':
	app.run(debug=True)
