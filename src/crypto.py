from Crypto.PublicKey import ECC
from Crypto.Cipher import AES
from Crypto.Hash import SHA3_256

# https://pycryptodome.readthedocs.io/en/latest/src/public_key/ecc.html?highlight=EccPoint#Crypto.PublicKey.ECC.EccPoint

if __name__ == '__main__':
    curve_type = [
        'NIST P-521'
    ]

    for curve in curve_type:
        key_outside = ECC.generate(curve=curve)
        key_inside = ECC.generate(curve=curve)

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
        plaintext = cipher.decrypt(ciphertext)

        print(str(plaintext.decode('utf-8')))
