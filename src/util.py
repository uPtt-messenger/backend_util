import hashlib
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
    import random
    # import string
    #
    # letters = string.ascii_lowercase + string.ascii_uppercase
    # rand_str = ''.join(random.choice(letters) for i in range(256))
    #
    # return sha256(f'{rand_str}')

    random_value = random.getrandbits(256)
    current_token = hex(random_value)
    # print(current_token)

    return current_token
