from SingleLog.log import Logger

from Crypto.PublicKey import ECC
from Crypto.Cipher import AES
from Crypto.Hash import SHA3_256


# https://pycryptodome.readthedocs.io/en/latest/src/public_key/ecc.html?highlight=EccPoint#Crypto.PublicKey.ECC.EccPoint

class Crypto:
    def __init__(self, console_obj):
        self.console = console_obj

        self.logger = Logger('Crypto', self.console.config.log_level, handler=self.console.config.log_handler)

        self.curve = 'NIST P-521'

        self.logger.show(
            Logger.INFO,
            '初始化',
            '啟動')

        self.logger.show(
            Logger.INFO,
            '橢圓曲線',
            self.curve)

        self.logger.show(
            Logger.INFO,
            '初始化',
            '完成')

    def generate_key(self):
        return ECC.generate(curve=self.curve)

    def key_agreement(self, key, public_str: str):

        if not key.has_private():
            self.logger.show(
                Logger.INFO,
                'key_agreement: This key is not have private key')
            raise ValueError('This key is not have private key')

        if not public_str.startswith('-----BEGIN PUBLIC KEY-----') or not public_str.endswith('-----END PUBLIC KEY-----'):
            self.logger.show(
                Logger.INFO,
                'key_agreement: public_str is not a valid public string')
            raise ValueError('public_str is not a valid public string')

        key_out = ECC.import_key(public_str)

        current_session_key = key.d * key_out.pointQ

        hash_key = f'{current_session_key.x}{current_session_key.y}'

        h = SHA3_256.new()
        h.update(hash_key.encode('utf-8'))

        return h.digest()

    def get_symmetric_key(self, key):
        if not key.has_private():
            self.logger.show(
                Logger.INFO,
                'get_symmetric_key: This key is not have private key')
            raise ValueError('This key is not have private key')

        hash_key = f'{key.d}'

        h = SHA3_256.new()
        h.update(hash_key.encode('utf-8'))

        return h.digest()


if __name__ == '__main__':
    curve_type = [
        'NIST P-521'
    ]

    for curve in curve_type:
        key_outside = ECC.generate(curve=curve)
        key_inside = ECC.generate(curve=curve)

        key_inside.has_private()

        public_key_outside = key_outside.public_key().export_key(format='PEM')
        print(public_key_outside)

        key_out = ECC.import_key(public_key_outside)

        point_inside = key_inside.public_key().pointQ
        point_outside = key_out.pointQ

        # 本人觀點
        session_key_0 = key_inside.d * point_outside
        print(session_key_0.xy)

        # 對方觀點
        session_key_1 = key_outside.d * key_inside.public_key().pointQ
        print(session_key_1.xy)

        assert (session_key_0 == session_key_1)

        # print('= ' * 40)

        hash_key = f'{session_key_0.x}{session_key_0.y}'
        print(hash_key)

        h = SHA3_256.new()
        h.update(hash_key.encode('utf-8'))

        key = h.digest()
        # print(key)

        data = 'Hello world'

        cipher = AES.new(key, AES.MODE_EAX)

        nonce = cipher.nonce
        ciphertext, tag = cipher.encrypt_and_digest(data.encode('utf-8'))

        cipher = AES.new(key, AES.MODE_EAX, nonce=nonce)
        plaintext = cipher.decrypt(ciphertext).decode('utf-8')

        assert (plaintext == data)
