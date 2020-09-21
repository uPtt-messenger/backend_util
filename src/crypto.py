from Crypto.PublicKey import ECC

# https://pycryptodome.readthedocs.io/en/latest/src/public_key/ecc.html?highlight=EccPoint#Crypto.PublicKey.ECC.EccPoint

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
    #
    session_key_0 = key_inside.d * point_outside
    print(session_key_0.xy)
    #
    session_key_1 = key_outside.d * key_inside.public_key().pointQ
    print(session_key_1.xy)

    assert (session_key_0 == session_key_1)

    # print('= ' * 40)
