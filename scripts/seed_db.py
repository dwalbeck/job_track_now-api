import psycopg2
import csv
from pathlib import Path

conn = psycopg2.connect(database="jobtracker",
                        host="psql.jobtracknow.com",
                        user="apiuser",
                        password="@p!u$3r70K3n",
                        port="5432")
csvfile = "job.csv"
data = []
good = 0

cursor = conn.cursor()

# SQL for inserting job and returning the job_id
job_sql = """
INSERT INTO job(company, job_title, salary, location, posting_url, job_status, date_applied, job_directory)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
RETURNING job_id
"""

# SQL for inserting job_detail with sample description
job_detail_sql = """
INSERT INTO job_detail(job_id, job_desc)
VALUES (%s, %s)
"""

# Sample job description template
sample_job_desc = """We are seeking a talented professional to join our team.

Responsibilities:
- Collaborate with cross-functional teams to deliver high-quality solutions
- Design, develop, and maintain software applications
- Participate in code reviews and technical discussions
- Contribute to architectural decisions and best practices

Requirements:
- Strong technical skills and problem-solving abilities
- Excellent communication and teamwork skills
- Experience with modern development tools and practices
- Bachelor's degree in Computer Science or related field, or equivalent experience

Preferred Qualifications:
- Experience with cloud platforms (AWS, GCP, Azure)
- Knowledge of containerization and orchestration
- Familiarity with CI/CD pipelines
- Strong understanding of software design patterns"""

with open(csvfile, mode='r') as file:
	csvFile = csv.DictReader(file)
	for row in csvFile:
		dir = row['company_name'].lower().replace("'", "").replace(" ", "_") + '/' + row['job_title'].lower().replace(' ', '_')
		#values = (row['company_name'], row['job_title'], row['salary'], row['location'], row['job_link'], row['status'].lower(), row['date_applied'], row['date_added'], dir)
		#data.append(values)
		dir_path = Path("../job_docs/" + dir)
		dir_path.mkdir(parents=True, exist_ok=True)

		company = row['company_name'] if row['company_name'] else None
		title = row['job_title'] if row['job_title'] else None
		salary = row['salary'] if row['salary'] else None
		location = row['location'] if row['location'] else None
		job_link = row['job_link'] if row['job_link'] else None
		status = row['status'].lower() if row['status'] else None
		date = row['date_applied'] if row['date_applied'] else row['date_added'] if row['date_added'] else None

		try:
			# Insert job and get the job_id
			cursor.execute(job_sql, (company, title, salary, location, job_link, status, date, dir))
			job_id = cursor.fetchone()[0]

			# Insert corresponding job_detail with sample description
			cursor.execute(job_detail_sql, (job_id, sample_job_desc))

			good += 1
			conn.commit()
			print(f"Inserted job_id {job_id}: {company} - {title}")
		except IndexError as e:
			print(f"Error: {e}")
			conn.rollback()
		except Exception as e:
			print(f"Error inserting job: {e}")
			conn.rollback()


#cursor.execute(sql, data)
#conn.commit()
print(f"\nSuccessfully inserted {good} jobs with job_detail records")
conn.close()
