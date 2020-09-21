from Crypto.PublicKey import ECC

# https://pycryptodome.readthedocs.io/en/latest/src/public_key/ecc.html?highlight=EccPoint#Crypto.PublicKey.ECC.EccPoint

curve_type = [
    'prime256v1'
]

for curve in curve_type:
    key_0 = ECC.generate(curve=curve)
    key_1 = ECC.generate(curve=curve)

    # print(key_0.export_key(format='PEM'))
    # print(key_1.export_key(format='PEM'))

    point_0 = key_0.public_key().pointQ
    point_1 = key_1.public_key().pointQ

    session_key_10 = point_1 * key_0.d
    # print(session_key_10.xy)

    session_key_01 = point_0 * key_1.d
    # print(session_key_01.xy)

    assert (session_key_10 == session_key_01)



    print('= ' * 40)

