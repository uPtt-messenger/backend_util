import random
import hashlib
import os
from zipfile import ZipFile


def sha256(value):
    s_lower = value.lower()
    hash_value = hashlib.sha256(s_lower.encode('utf-8')).hexdigest()
    return hash_value


def unzip(output_path, zip_file):
    with ZipFile(zip_file, mode='r') as z:
        z.extractall(path=output_path)


def compare_version(a, b):
    a = int(a.replace('.', ''))
    b = int(b.replace('.', ''))

    if a > b:
        return 1
    if a == b:
        return 0
    if a < b:
        return -1


def generate_token():
    random_value = random.getrandbits(256)
    current_token = hex(random_value)[2:]

    # return 64 char
    return current_token


def clean_path(path):
    path = path.replace('\\', '/')
    return path


def mkdir(path):
    path = path.replace('\\', '/')
    if path.endswith('.json'):
        path = path[:path.rfind('/')]

    for i in range(1, len(path.split('/'))):
        current_path = '/'.join(path.split('/')[:i + 1])
        if os.path.exists(current_path):
            continue
        os.makedirs(current_path)


def get_substring(main_string, start, end):
    main_string = main_string[main_string.find(start) + len(start):]
    main_string = main_string[:main_string.find(end)]

    return main_string.strip()


def get_verify_hash(a, b, c):
    value = f'{a}{b}{c}'
    return sha256(value)


if __name__ == '__main__':
    import time
    import datetime

    import pytz

    us = pytz.timezone('US/Pacific')
    dt = datetime.datetime.strptime('2015-07-03 20:25', '%Y-%m-%d %H:%M').replace(tzinfo=us)
