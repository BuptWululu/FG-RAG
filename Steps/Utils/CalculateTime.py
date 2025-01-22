import time
from Utils.Log import Log
def calculate_time(func):
    def wrapper(*args, **kwargs):
        function_name = func.__name__
        start_time = time.time()
        Log().print(f'Executing Function {function_name}.')
        result = func(*args, **kwargs)
        execute_time = format(time.time() - start_time, '.2f')
        Log().print(f"Execute {execute_time} Seconds in Function {function_name}.")
        return result
    return wrapper