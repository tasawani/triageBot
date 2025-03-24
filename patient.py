from google.cloud import bigquery

# Initialize BigQuery client
client = bigquery.Client()

# Function to check if user exists and retrieve names by MRN
def get_patient_name_by_mrn(mrn):
    query = f"""
        SELECT firstname, lastname
        FROM `hospitalbot-bwpg.hospitalbot.patient_info`
        WHERE MRN = '{mrn}'
    """
    
    # Run the query
    query_job = client.query(query)
    
    # Fetch the results
    results = query_job.result()  # Wait for the query to complete
    
    # Check if any result was found
    if results.total_rows > 0:
        # Get the first record (we expect only one MRN match)
        for row in results:
            firstname = row['firstname']
            lastname = row['lastname']
        return (firstname, lastname)
    else:
        return None