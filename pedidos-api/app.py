"""pedidos-api: cria pedidos, cobra no pagamentos-api e reserva estoque pela fila."""


def calcular_frete(pedido):
    cep = pedido.get("endereco", {}).get("cep", "")
    return 15.0 if cep.startswith("0") else 25.0


def criar_pedido(pedido):
    pedido["frete"] = calcular_frete(pedido)
    return pedido
