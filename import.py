#!/usr/bin/env -S bash -c 'exec "`dirname $0`/.venv/bin/python" "$0" "$@"'

import sqlite3
import csv
import argparse
from datetime import datetime
from pathlib import Path

def init_db(conn):
	"""Create table if not exists"""
	cursor = conn.cursor()

	cursor.execute('''
        CREATE TABLE IF NOT EXISTS sensors (
            sensor_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        )
    ''')

	cursor.execute('''
        CREATE TABLE IF NOT EXISTS sensor_data (
            sensor_id INTEGER NOT NULL,
            date DATETIME NOT NULL,
            temp DECIMAL(3,1) NOT NULL,
            rh INTEGER NOT NULL,
            FOREIGN KEY (sensor_id) REFERENCES sensors(sensor_id),
            PRIMARY KEY (sensor_id, date)
        )
    ''')

	conn.commit()


def get_or_create_sensor(conn, sensor_name_or_id: int | str):
	"""Get or create a sensor on the DB"""
	cursor = conn.cursor()

	# find sensor by id or name
	for qry, param in (
		("SELECT sensor_id FROM sensors WHERE sensor_id = ?", sensor_name_or_id),
		("SELECT sensor_id FROM sensors WHERE UPPER(TRIM(name)) = ? LIMIT 1", sensor_name_or_id.strip().upper())
	):
		cursor.execute(qry, (param,))
		result = cursor.fetchone()

		if result:
			return result[0]

	# if not found assume it's not present on DB, insert it
	cursor.execute('INSERT INTO sensors (name) VALUES (?)', (sensor_name_or_id,))
	conn.commit()
	return cursor.lastrowid


def load_csv(conn, sensor_id, csv_path):
	"""Load CSV data to database"""
	cursor = conn.cursor()
	csv_path = Path(csv_path)

	if not csv_path.exists():
		raise FileNotFoundError(f"File non trovato: {csv_path}")

	loaded  = 0
	skipped = 0
	errors  = []

	FIELDS = {
		"date": "Date",
		"temp": "Temperature_Celsius(℃)",
		"rh"  : "Relative_Humidity(%)"
	}

	try:
		with open(csv_path, 'r', encoding='utf-8') as file:
			# total row count for percentage print
			reader    = csv.DictReader(file)
			totalrows = 0
			for row in reader:
				totalrows += 1

			file.seek(0)
			
			# actual reader for data
			reader = csv.DictReader(file)

			if not reader.fieldnames or len(set(reader.fieldnames).intersection(set(FIELDS.values()))) != len(FIELDS):
				raise ValueError("CSV must contains columns: %s" % ", ".join(FIELDS.values()))

			totalrows -= 1 # first row is for header
			printed_percentages = []
			def print_percentage(current_row: int):
				curr_percentage = int(current_row * 100 / totalrows)

				if curr_percentage % 10 == 0 and curr_percentage not in printed_percentages:
					if curr_percentage == 100:
						print("100%")
					else:
						print(f"{curr_percentage}% ...", end = " ")

					printed_percentages.append(curr_percentage)

			for row_num, row in enumerate(reader, start=2): # first row is for header
				try:
					date = datetime.strptime(row[FIELDS["date"]].strip(), "%d/%m/%Y %H:%M")
					temp = float(row[FIELDS["temp"]].strip().replace(",", "."))
					rh  = int(row[FIELDS["rh"]].strip())

					# data validation
					if not (-50 <= temp <= 60):
						raise ValueError(f"Temperature {temp} outside human living range")
					if not (0 <= rh <= 100):
						raise ValueError(f"Relative humidity {rh} is not a valid percentage")

					# Inserimento nel database se data non gia' presente
					cursor.execute('''
                        INSERT OR IGNORE INTO sensor_data (sensor_id, date, temp, rh)
                        VALUES (?, ?, ?, ?)
                    ''', (sensor_id, date, temp, rh))

					loaded += 1
					print_percentage(row_num)

				except sqlite3.IntegrityError:
					skipped += 1
				except (ValueError, TypeError) as e:
					skipped += 1
					errors.append(f"Row {row_num}: {str(e)}")

		conn.commit()
		print_percentage(totalrows)

	except Exception as e:
		conn.rollback()
		raise

	return loaded, skipped, errors


def main():
	parser = argparse.ArgumentParser(description='Load on SQLite DB sensor data from CSV export')
	parser.add_argument('sensor', help="Sensor's name or ID")
	parser.add_argument('csv_file', help='CSV file path')
	parser.add_argument('--db', default='sensor_data.db', help='SQLite DB path (default: sensor_data.db)')
	args   = parser.parse_args()

	try:
		# Connessione al database
		print(f"Connecting database: {args.db}")
		with sqlite3.connect(args.db) as conn:
			# Creazione tabelle
			init_db(conn)

			# Recupera o crea la sensor
			sensor_id = get_or_create_sensor(conn, args.sensor)
			print(f"Sensor '{args.sensor}' (ID: {sensor_id})")

			# Carica i dati
			print(f"Loading data from: {args.csv_file}")
			loaded, skipped, errors = load_csv(conn, sensor_id, args.csv_file)

			print(f"\nLoaded rows:\t{loaded}")
			print(f"Skipped rows:\t{skipped}")

			if errors:
				print("\nErrors:\n -%s" % "\n- ".join(errors))

			print("\nOperation completed")

	except Exception as e:
		print(f"Error: {str(e)}")
		exit(1)


if __name__ == '__main__':
	main()