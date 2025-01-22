from datetime import datetime

log_name = datetime.now().strftime('%Y-%m-%d %H:%M:%S') + '.txt'
work_dir = 'Datasets/example'
query_file = 'example.json'
query_type = 'default'

chunk_size = 1200
chunk_overlap = 100
max_gleaning_times = 1

generator_api_key = 'sk-xxx'
generator_base_url = 'https:'
generator_name = 'gpt-4o-mini'
generate_parallel = 32
generate_request_timeout = 60
generate_max_retries = 20

encoder_api_key = 'sk-xxx'
encoder_base_url = 'https://'
encoder_name = 'text-embedding-3-small'
encode_batch_size = 32
encode_parallel = 32
encode_request_timeout = 120
encode_max_retries = 20

initial_selected_entity_number = 20
max_description_number = 75
max_extract_entity_number = 9

naive_topk = 10

tuple_delimiter = '<|>'
record_delimiter = '##'
completion_delimiter = "<|COMPLETE|>"
