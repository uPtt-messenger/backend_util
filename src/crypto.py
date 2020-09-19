from Crypto.PublicKey import ECC

# https://pycryptodome.readthedocs.io/en/latest/src/public_key/ecc.html?highlight=EccPoint#Crypto.PublicKey.ECC.EccPoint

key_type = [
    'NIST P-521',
    'p521',
    'P-521',
    'prime521v1',
    'secp521r1'
]

for key in key_type:
    key = ECC.generate(curve=key)

    print(key.export_key(format='PEM'))

    print(key.public_key().export_key(format='PEM'))

    ECC.EccPoint
