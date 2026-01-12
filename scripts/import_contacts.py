import psycopg2
import csv
from pathlib import Path

conn = psycopg2.connect(database="jobtracker",
                        host="psql.jobtracknow.com",
                        user="apiuser",
                        password="@p!u$3r70K3n",
                        port="5432")
csvfile = "contacts.csv"
data = []
good = 0
link = 0

cursor = conn.cursor()

# SQL for inserting job and returning the job_id
contact_sql = """
INSERT INTO contact(first_name, last_name, company, job_title, email, phone, linkedin, contact_created, location)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) 
RETURNING contact_id
"""

job_match_sql = """
SELECT job_id FROM job WHERE company = %s
"""


with open(csvfile, mode='r') as file:
	csvFile = csv.DictReader(file)
	for row in csvFile:
		company = row['company'] if row['company'] else None
		title = row['job_title'] if row['job_title'] else None
		linkedin = row['linkedin'] if row['linkedin'] else None
		location = row['location'] if row['location'] else None
		first_name = row['first_name'] if row['first_name'] else None
		last_name = row['last_name'] if row['last_name'] else None
		email = row['email'].lower() if row['email'] else None
		phone = row['phone'] if row['phone'] else None
		contact_created = row['contact_created'] if row['contact_created'] else None

		try:
			# Insert job and get the job_id
			cursor.execute(contact_sql, (first_name, last_name, company, title, email, phone, linkedin, contact_created, location,))
			contact_id = cursor.fetchone()[0]

			# lookup jobs for matching company name and link to those found
			cursor.execute(job_match_sql, (company,))
			matches = cursor.fetchall()
			for match in matches:
				job_id = match[0]
				cursor.execute("INSERT INTO job_contact (job_id, contact_id) VALUES (%s, %s)", [job_id, contact_id])
				link += 1

			good += 1
			conn.commit()
			print(f".")
		except IndexError as e:
			print(f"Error: {e}")
			conn.rollback()
		except Exception as e:
			print(f"Error inserting contact: {e}")
			conn.rollback()


#cursor.execute(sql, data)
#conn.commit()
print(f"\nSuccessfully inserted {good} contacts\nLinked to {link} jobs\n\n")
conn.close()
