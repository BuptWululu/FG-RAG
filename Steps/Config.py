from datetime import datetime

log_name = datetime.now().strftime('%Y-%m-%d %H:%M:%S') + '.txt'
work_dir = 'Datasets/example'
query_file = 'example.json'
query_type = 'default' # Switch it to 'precise' to get an answer in the form of a word or entity.

chunk_size = 1200
chunk_overlap = 100
max_gleaning_times = 1

generator_api_key = 'sk-xxx'
generator_base_url = 'https:'
generator_name = 'gpt-4o-mini'
generate_parallel = 32 # the number of parallel requests that may be made
generate_request_timeout = 60
generate_max_retries = 20

encoder_api_key = 'sk-xxx'
encoder_base_url = 'https://'
encoder_name = 'text-embedding-3-small'
encode_batch_size = 32 # the number of documents to send in a single request
encode_parallel = 32 # the number of parallel requests that may be made
encode_request_timeout = 120
encode_max_retries = 20

# FG-RAG related parameters
max_extract_entity_number = 9 # the maximum number of entities extracted from the query
initial_selected_entity_number = 20 # the number of entities initially matched from the vector database per entity
max_description_number = 75 # the maximum number of descriptions retrieved per entity

naive_topk = 10 # the number of text chunks retrieved in NaiveRAG

tuple_delimiter = '<|>'
record_delimiter = '##'
completion_delimiter = "<|COMPLETE|>"
