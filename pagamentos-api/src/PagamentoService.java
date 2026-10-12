package br.loja.pagamentos;

public class PagamentoService {

    public Pagamento confirmar(Pedido pedido, Cupom cupom) {
        double valor = pedido.getTotal();
        return gateway.cobrar(pedido.getId(), valor);
    }
}
