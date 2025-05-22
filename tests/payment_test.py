from flask import jsonify, request
import stripe
import time
import traceback
from datetime import datetime

def init_payment_tests(app):
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