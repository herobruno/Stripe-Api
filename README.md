# API de Boletos com Stripe

API para geração e verificação de boletos bancários usando o Stripe.

## Configuração

1. Instale as dependências:
```bash
pip install -r requirements.txt
```

2. Configure suas variáveis de ambiente:
```bash
# .env
STRIPE_SECRET_KEY=sk_test_...  # Chave secreta do Stripe
STRIPE_PUBLIC_KEY=pk_test_...  # Chave pública do Stripe
```

3. Execute o servidor:
```bash
python app.py
```

## Endpoints

### 1. Gerar Boleto
Gera um novo boleto bancário.

**URL:** `/gerar-boleto`  
**Método:** `POST`  
**Content-Type:** `application/json`

#### Campos Obrigatórios
```json
{
    "valor": "90.00",        // Valor em reais (string)
    "email": "cliente@exemplo.com",
    "nome": "Nome do Cliente",
    "cpf": "12345678909"     // CPF sem pontos e traços
}
```

#### Campos Opcionais
```json
{
    "descricao": "Pagamento da fatura #123",
    "endereco": {
        "rua": "Rua Exemplo",
        "numero": "123",
        "complemento": "Apto 45",
        "cidade": "São Paulo",
        "estado": "SP",
        "cep": "12345678"    // CEP sem traço
    }
}
```

#### Resposta de Sucesso
**Status Code:** 200 OK
```json
{
    "boleto_id": "pi_XXXXX...",
    "codigo_barras": "01010101010101010101010101010101010101010101010",
    "linha_digitavel": "01010.10101 01010.101010 10101.010101 0 10101010101010",
    "pdf_url": "https://payments.stripe.com/boleto/voucher/...",
    "valor": "90.00",
    "data_vencimento": "2025-05-23",
    "status": "requires_action",
    "public_key": "pk_test_...",
    "instrucoes": [
        "1. Copie o código de barras ou linha digitável",
        "2. Pague em qualquer banco ou lotérica",
        "3. Ou acesse o PDF do boleto para imprimir",
        "4. O pagamento será confirmado automaticamente"
    ]
}
```

#### Resposta de Erro
**Status Code:** 400 Bad Request
```json
{
    "erro": "Erro ao gerar boleto",
    "detalhes": "Mensagem de erro específica"
}
```

### 2. Verificar Boleto
Verifica o status de um boleto existente.

**URL:** `/verificar-boleto/<boleto_id>`  
**Método:** `GET`  
**Parâmetros:**
- `boleto_id`: ID do boleto (ex: pi_XXXXX...)

#### Resposta de Sucesso
**Status Code:** 200 OK
```json
{
    "status": "requires_action",  // ou "succeeded", "processing", "canceled"
    "valor": 90.0,
    "email": "cliente@exemplo.com",
    "data_criacao": "2025-05-16 00:53:45",
    "data_aprovacao": "2025-05-17 10:00:00",  // null se não pago
    "public_key": "pk_test_...",
    "boleto": {
        "codigo_barras": "01010101010101010101010101010101010101010101010",
        "linha_digitavel": "01010.10101 01010.101010 10101.010101 0 10101010101010",
        "pdf_url": "https://payments.stripe.com/boleto/voucher/..."
    },
    "debug_info": {
        "payment_intent_status": "requires_action",
        "has_charges": true,
        "charge_status": "succeeded",
        "is_paid": true
    }
}
```

#### Resposta de Erro
**Status Code:** 400 Bad Request
```json
{
    "erro": "Erro ao verificar boleto",
    "detalhes": "Mensagem de erro específica"
}
```

### 3. Webhook
Endpoint para receber notificações do Stripe sobre eventos de pagamento.

**URL:** `/webhook`  
**Método:** `POST`  
**Headers:**
- `Stripe-Signature`: Assinatura do webhook do Stripe

#### Resposta de Sucesso
**Status Code:** 200 OK
```json
{
    "status": "success"
}
```

#### Resposta de Erro
**Status Code:** 400 Bad Request
```json
{
    "erro": "Mensagem de erro específica"
}
```

## Status Codes

- `200 OK`: Requisição bem-sucedida
- `400 Bad Request`: Erro na requisição (dados inválidos)
- `500 Internal Server Error`: Erro interno do servidor

## Status do Boleto

- `requires_action`: Aguardando pagamento
- `processing`: Pagamento em processamento
- `succeeded`: Pago com sucesso
- `canceled`: Cancelado

## Opções de Pagamento

O cliente pode pagar o boleto de três formas:

1. **Código de Barras**
   - Copie o `codigo_barras` da resposta
   - Cole no aplicativo ou site do banco
   - Confirme o pagamento

2. **Linha Digitável**
   - Use o `linha_digitavel` da resposta
   - Digite no aplicativo ou site do banco
   - Confirme o pagamento

3. **PDF do Boleto**
   - Acesse o `pdf_url` da resposta
   - Imprima o boleto
   - Pague em qualquer banco ou lotérica

## Observações Importantes

1. O boleto tem validade de 7 dias
2. O pagamento é confirmado automaticamente pelo Stripe
3. Use as chaves de teste (`sk_test_` e `pk_test_`) para desenvolvimento
4. Em produção, use as chaves reais (`sk_live_` e `pk_live_`)
5. A API está configurada com CORS habilitado para todas as origens
6. Todas as chaves do Stripe devem ser configuradas via variáveis de ambiente

## Exemplos de Uso

### Python
```python
import requests

# Gerar boleto
response = requests.post(
    'http://localhost:5000/gerar-boleto',
    json={
        "valor": "90.00",
        "email": "cliente@exemplo.com",
        "nome": "Nome do Cliente",
        "cpf": "12345678909"
    }
)
boleto_data = response.json()

# Verificar boleto
boleto_id = boleto_data['boleto_id']
status = requests.get(f'http://localhost:5000/verificar-boleto/{boleto_id}')
boleto_status = status.json()
```

### JavaScript
```javascript
// Gerar boleto
const response = await fetch('http://localhost:5000/gerar-boleto', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json'
    },
    body: JSON.stringify({
        valor: "90.00",
        email: "cliente@exemplo.com",
        nome: "Nome do Cliente",
        cpf: "12345678909"
    })
});
const boletoData = await response.json();

// Verificar boleto
const boletoId = boletoData.boleto_id;
const status = await fetch(`http://localhost:5000/verificar-boleto/${boletoId}`);
const boletoStatus = await status.json();
``` 