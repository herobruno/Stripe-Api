from flask import Flask, jsonify, request
import stripe
import os
import time
import traceback
from datetime import datetime, timedelta
from flask_cors import CORS
from config import STRIPE_SECRET_KEY, STRIPE_PUBLIC_KEY

app = Flask(__name__)
CORS(app)  # Habilita CORS para todas as rotas

# Configuração do Stripe
stripe.api_key = STRIPE_SECRET_KEY

print("\n=== CONFIGURAÇÃO DO STRIPE ===")
print("Chave secreta:", stripe.api_key[:10] + "...")
print("Chave pública:", STRIPE_PUBLIC_KEY[:10] + "...")

@app.route('/gerar-boleto', methods=['POST'])
def gerar_boleto():
    try:
        print("\n=== INÍCIO DA REQUISIÇÃO ===")
        data = request.get_json()
        print("Dados recebidos:", data)
        
        # Validação dos dados
        valor = data.get('valor')
        email = data.get('email')
        nome = data.get('nome')
        cpf = data.get('cpf')
        descricao = data.get('descricao', 'Pagamento via Boleto')
        
        # Dados do endereço
        endereco = data.get('endereco', {})
        rua = endereco.get('rua', 'Rua não informada')
        numero = endereco.get('numero', 'S/N')
        complemento = endereco.get('complemento', '')
        cidade = endereco.get('cidade', 'Cidade não informada')
        estado = endereco.get('estado', 'Estado não informado')
        cep = endereco.get('cep', '00000000')
        
        if not valor:
            return jsonify({'erro': 'Valor é obrigatório'}), 400
        if not email:
            return jsonify({'erro': 'Email é obrigatório'}), 400
        if not nome:
            return jsonify({'erro': 'Nome é obrigatório'}), 400
        if not cpf:
            return jsonify({'erro': 'CPF é obrigatório'}), 400

        # Limpa o CPF (remove pontos e traços)
        cpf_limpo = cpf.replace('.', '').replace('-', '')
        
        # Limpa o CEP (remove traço)
        cep_limpo = cep.replace('-', '')
        
        print("\n=== CRIANDO PAGAMENTO ===")
        # Cria o pagamento do boleto
        payment_intent = stripe.PaymentIntent.create(
            amount=int(float(valor) * 100),  # Valor em centavos
            currency='brl',
            payment_method_types=['boleto'],
            payment_method_data={
                'type': 'boleto',
                'boleto': {
                    'tax_id': cpf_limpo
                },
                'billing_details': {
                    'name': nome,
                    'email': email,
                    'address': {
                        'line1': f"{rua}, {numero}",
                        'line2': complemento,
                        'city': cidade,
                        'state': estado,
                        'postal_code': cep_limpo,
                        'country': 'BR'
                    }
                }
            },
            description=descricao,
            confirm=True
        )
        print("Pagamento criado:", payment_intent.id)

        # Obtém os detalhes do boleto corretamente
        boleto_display = payment_intent.next_action['boleto_display_details']

        response_data = {
            'boleto_id': payment_intent.id,
            'codigo_barras': boleto_display.get('number'),
            'linha_digitavel': boleto_display.get('line'),
            'pdf_url': boleto_display.get('hosted_voucher_url'),
            'valor': valor,
            'data_vencimento': (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d'),
            'status': payment_intent.status,
            'public_key': STRIPE_PUBLIC_KEY,
            'instrucoes': [
                '1. Copie o código de barras ou linha digitável',
                '2. Pague em qualquer banco ou lotérica',
                '3. Ou acesse o PDF do boleto para imprimir',
                '4. O pagamento será confirmado automaticamente'
            ]
        }

        print("\n=== RESPOSTA FINAL ===")
        print("Dados que serão retornados:", response_data)
        return jsonify(response_data)

    except stripe.error.StripeError as e:
        print("\n=== ERRO DO STRIPE ===")
        print("Tipo do erro:", type(e).__name__)
        print("Mensagem do erro:", str(e))
        return jsonify({
            'erro': 'Erro ao gerar boleto',
            'detalhes': str(e)
        }), 400
    except Exception as e:
        print("\n=== ERRO GERAL ===")
        print("Tipo do erro:", type(e).__name__)
        print("Mensagem do erro:", str(e))
        return jsonify({
            'erro': 'Erro interno do servidor',
            'detalhes': str(e)
        }), 500

@app.route('/verificar-boleto/<boleto_id>', methods=['GET'])
def verificar_boleto(boleto_id):
    try:
        print("\n=== VERIFICANDO BOLETO ===")
        print("ID do boleto:", boleto_id)
        
        # Busca o PaymentIntent com expansão do campo charges
        payment_intent = stripe.PaymentIntent.retrieve(
            boleto_id,
            expand=['charges']
        )
        print("\n=== DADOS DO PAGAMENTO ===")
        print("Status do PaymentIntent:", payment_intent.status)
        print("Tem charges?", hasattr(payment_intent, 'charges'))
        if hasattr(payment_intent, 'charges'):
            print("Número de charges:", len(payment_intent.charges.data))
            for charge in payment_intent.charges.data:
                print("Status da charge:", charge.status)
                print("ID da charge:", charge.id)
        
        # Obtém os detalhes do boleto
        charge = payment_intent.charges.data[0] if hasattr(payment_intent, 'charges') and payment_intent.charges.data else None
        boleto_details = charge.payment_method_details.boleto if charge and hasattr(charge, 'payment_method_details') else None
        
        # Verifica se o boleto realmente foi pago
        is_paid = False
        if charge:
            is_paid = charge.status == 'succeeded'
            print("\n=== STATUS DO PAGAMENTO ===")
            print("Status da charge:", charge.status)
            print("Boleto pago:", is_paid)
        
        response_data = {
            'status': 'succeeded' if is_paid else 'requires_action',
            'valor': payment_intent.amount / 100,  # Converte de centavos para reais
            'email': payment_intent.receipt_email,
            'data_criacao': datetime.fromtimestamp(payment_intent.created).strftime('%Y-%m-%d %H:%M:%S'),
            'data_aprovacao': datetime.fromtimestamp(charge.created).strftime('%Y-%m-%d %H:%M:%S') if charge and is_paid else None,
            'public_key': STRIPE_PUBLIC_KEY,
            'boleto': {
                'codigo_barras': boleto_details.barcode if boleto_details else None,
                'linha_digitavel': boleto_details.line if boleto_details else None,
                'pdf_url': boleto_details.hosted_voucher_url if boleto_details else None
            } if boleto_details else None,
            'debug_info': {
                'payment_intent_status': payment_intent.status,
                'has_charges': hasattr(payment_intent, 'charges'),
                'charge_status': charge.status if charge else None,
                'is_paid': is_paid
            }
        }
        
        print("\n=== RESPOSTA FINAL ===")
        print("Dados que serão retornados:", response_data)
        return jsonify(response_data)
        
    except stripe.error.StripeError as e:
        print("\n=== ERRO DO STRIPE ===")
        print("Tipo do erro:", type(e).__name__)
        print("Mensagem do erro:", str(e))
        return jsonify({
            'erro': 'Erro ao verificar boleto',
            'detalhes': str(e)
        }), 400
    except Exception as e:
        print("\n=== ERRO GERAL ===")
        print("Tipo do erro:", type(e).__name__)
        print("Mensagem do erro:", str(e))
        return jsonify({
            'erro': 'Erro interno do servidor',
            'detalhes': str(e)
        }), 500

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        event = stripe.Webhook.construct_event(
            request.data, request.headers['Stripe-Signature'], 'seu_webhook_secret'
        )
        
        if event['type'] == 'checkout.session.completed':
            session = event['data']['object']
            # Removendo a lógica de atualização do banco de dados
            pass
            
        return jsonify({'status': 'success'})
        
    except Exception as e:
        return jsonify({'erro': str(e)}), 400


@app.route('/simular-pagamento/<boleto_id>', methods=['POST'])
def simular_pagamento(boleto_id):
    try:
        print(f"=== SIMULANDO PAGAMENTO DO BOLETO {boleto_id} ===")
        
        # Buscar o PaymentIntent no Stripe
        try:
            payment_intent = stripe.PaymentIntent.retrieve(boleto_id)
            print(f"PaymentIntent encontrado: {payment_intent.id}")
        except stripe.error.StripeError as e:
            print(f"Erro ao buscar PaymentIntent: {str(e)}")
            return jsonify({'erro': f'Erro ao buscar PaymentIntent: {str(e)}'}), 400

        # Em ambiente de teste, simular o pagamento usando o webhook
        if payment_intent.status == 'requires_action':
            try:
                # Criar um evento de webhook simulado
                event = stripe.Event.construct_from({
                    'id': f'evt_simulado_{int(time.time())}',
                    'object': 'event',
                    'type': 'payment_intent.succeeded',
                    'data': {
                        'object': {
                            'id': payment_intent.id,
                            'object': 'payment_intent',
                            'status': 'succeeded',
                            'amount': payment_intent.amount,
                            'currency': payment_intent.currency,
                            'payment_method': payment_intent.payment_method,
                            'charges': {
                                'data': [{
                                    'id': f'ch_simulado_{int(time.time())}',
                                    'object': 'charge',
                                    'status': 'succeeded',
                                    'amount': payment_intent.amount,
                                    'currency': payment_intent.currency,
                                    'payment_intent': payment_intent.id
                                }]
                            }
                        }
                    }
                }, stripe.api_key)

                # Processar o evento como se fosse um webhook real
                if event.type == 'payment_intent.succeeded':
                    payment_intent = event.data.object
                    print(f"PaymentIntent atualizado via webhook simulado: {payment_intent.id}")
                    print(f"Novo status: {payment_intent.status}")

            except stripe.error.StripeError as e:
                print(f"Erro ao simular webhook: {str(e)}")
                return jsonify({'erro': f'Erro ao simular webhook: {str(e)}'}), 400

        print("=== PAGAMENTO SIMULADO COM SUCESSO ===")
        print(f"PaymentIntent ID: {payment_intent.id}")
        print(f"Status: {payment_intent.status}")
        
        return jsonify({
            'status': 'succeeded',
            'payment_intent_id': payment_intent.id,
            'data_aprovacao': datetime.now().isoformat(),
            'debug_info': {
                'payment_intent_status': payment_intent.status,
                'has_charges': True,
                'charge_status': 'succeeded',
                'is_paid': True
            }
        })
        
    except Exception as e:
        print(f"=== ERRO AO SIMULAR PAGAMENTO ===")
        print(f"Erro: {str(e)}")
        print(f"Stack: {traceback.format_exc()}")
        return jsonify({'erro': str(e)}), 400 
    
if __name__ == '__main__':
    app.run(debug=True) 