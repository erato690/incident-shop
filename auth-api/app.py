"""auth-api: emite tokens e valida JWT consultando o provedor de identidade."""


def validar_token(token, idp):
    return idp.validar(token)
