"""auth-api: emite tokens e valida JWT consultando o provedor de identidade."""

_cache_tokens = {}  # token -> claims, nunca é limpo


def validar_token(token, idp):
    if token not in _cache_tokens:
        _cache_tokens[token] = idp.validar(token)
    return _cache_tokens[token]
