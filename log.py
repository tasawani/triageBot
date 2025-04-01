from google.cloud import bigquery

import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
# Initialize BigQuery client
client = bigquery.Client()

# Function to check if user exists and retrieve names by MRN
def save_chat_hostory(session_id, request, query, response):
    try:
        logger.info(f"Request: {request}")
        logger.info(f"Response: {response}")
        insert_query = """
            INSERT INTO `hospitalbot-bwpg.hospitalbot.transaction` (session_id, request, query, response, timestamp)
            VALUES (@session_id, @request, @query, @response, CURRENT_TIMESTAMP())
            """
            
        # Set up the job configuration with query parameters
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("session_id", "STRING", session_id),
                bigquery.ScalarQueryParameter("request", "STRING", request),
                bigquery.ScalarQueryParameter("query", "STRING", query),
                bigquery.ScalarQueryParameter("response", "STRING", response)
            ]
        )

        # Run the query with parameters
        query_job = client.query(insert_query, job_config=job_config)

        # Wait for the query to complete
        query_job.result()
        
        logger.info("Log has been successfully inserted.")
        return True
    except Exception as e:
        logger.info(e)
        return False
    
def get_session_chat_history(session_id):
    client = bigquery.Client()
    
    query = f"""
        SELECT 
            session_id, 
            STRING_AGG(query, ' ' ORDER BY timestamp ASC) AS chat_history
        FROM `hospitalbot-bwpg.hospitalbot.transaction`
        WHERE session_id = '{session_id}'
        GROUP BY session_id
    """
    
    logger.info(f"Running Query:{query}")
    query_job = client.query(query)
    results = query_job.result()

    # Assuming `results` contains the query result from BigQuery
    logger.info(f"Result:{results}")

    # Since you're expecting only one row, we can directly access it.
    # Extract the chat_history from the first (and only) row in the result.
    if results.total_rows > 0:
        # Get the first row
        row = list(results)[0]
        chat_history = row.chat_history
        logger.info(f"Chat History: {chat_history}")
    else:
        chat_history = ""
        logger.warning("No results found for the given session_id.")

    return chat_history + ", "


def save_chat_history_entity(session_id, response):
    try:
        logger.info(f"Response type: {type(response)}")
        logger.info(f"Response content: {response}")

        if isinstance(response, dict):
            query_result = response.get('queryResult', {})
            parameters = query_result.get('parameters', {})

            for entity_name, entity_values in parameters.items():
                # ตรวจสอบและแทนค่าที่เป็น None หรือ "" ด้วยค่าว่าง
                entity_value = entity_values[0] if entity_values and entity_values[0] else ''
                
                query_check = """
                    SELECT COUNT(1) 
                    FROM `hospitalbot-bwpg.hospitalbot.transaction_entity`
                    WHERE session_id = @session_id AND entity = @entity
                """
                job_config_check = bigquery.QueryJobConfig(
                    query_parameters=[
                        bigquery.ScalarQueryParameter("session_id", "STRING", session_id),
                        bigquery.ScalarQueryParameter("entity", "STRING", entity_name)
                    ]
                )
                query_job_check = client.query(query_check, job_config=job_config_check)
                result_check = query_job_check.result()
                count_rows = list(result_check)[0][0]
                
                if count_rows > 0:
                    update_query = """
                        UPDATE `hospitalbot-bwpg.hospitalbot.transaction_entity`
                        SET detail = CONCAT(detail, ', ', NULLIF(@detail, '')),
                            detail_original = CONCAT(detail_original, ', ', NULLIF(@detail_original, ''))
                        WHERE session_id = @session_id AND entity = @entity
                    """
                    job_config_update = bigquery.QueryJobConfig(
                        query_parameters=[
                            bigquery.ScalarQueryParameter("session_id", "STRING", session_id),
                            bigquery.ScalarQueryParameter("entity", "STRING", entity_name),
                            bigquery.ScalarQueryParameter("detail", "STRING", entity_value),
                            bigquery.ScalarQueryParameter("detail_original", "STRING", entity_name + '.original')
                        ]
                    )
                    query_job_update = client.query(update_query, job_config=job_config_update)
                    query_job_update.result()
                    logger.info(f"Appended details for entity: {entity_name} in session: {session_id}")
                else:
                    insert_query = """
                        INSERT INTO `hospitalbot-bwpg.hospitalbot.transaction_entity` 
                        (session_id, entity, detail, entity_original, detail_original)
                        VALUES (@session_id, @entity, NULLIF(@detail, ''), @entity_original, NULLIF(@detail_original, ''))
                    """
                    job_config_insert = bigquery.QueryJobConfig(
                        query_parameters=[
                            bigquery.ScalarQueryParameter("session_id", "STRING", session_id),
                            bigquery.ScalarQueryParameter("entity", "STRING", entity_name),
                            bigquery.ScalarQueryParameter("detail", "STRING", entity_value),
                            bigquery.ScalarQueryParameter("entity_original", "STRING", entity_name + '.original'),
                            bigquery.ScalarQueryParameter("detail_original", "STRING", entity_value)
                        ]
                    )
                    query_job_insert = client.query(insert_query, job_config=job_config_insert)
                    query_job_insert.result()
                    logger.info(f"Inserted new row for entity: {entity_name} in session: {session_id}")

            return True
        else:
            logger.error("Response is not in expected dictionary format")
            return False

    except Exception as e:
        logger.error(f"Error in saving chat history entity: {e}")
        return False