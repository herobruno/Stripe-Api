from flask import jsonify, request
import requests
import traceback

def init_mensalidade_tests(app, db):
    @app.route('/testar-webhook-mensal', methods=['GET'])
    def testar_webhook_boleto():
        try:
            # Simular um evento do Stripe
            event_data = {
                "type": "payment_intent.succeeded",
                "data": {
                    "object": {
                        "metadata": {
                            "tipo_pagamento": "boleto",
                            "fatura_id": "proporcional-fat-47ca67cc",
                            "cliente_id": "MaiNCXusd8iuPpczSTKj",
                            "cliente_nome": "favio",
                            "cliente_email": "favio@gmail.com",
                            "cliente_cpf": "18667894060",
                            "servico_id": "1aIqO9jNYNeMPrZxJiwE",
                            "servico_nome": "imagem",
                            "periodo_inicio": "23/05/2025",
                            "periodo_fim": "10/06/2025",
                            "valor_original": 100,
                            "valor_proporcional": 73.2,
                            "data_vencimento": "10/06/2025"
                        }
                    }
                }
            }
            
            # Fazer a chamada para o webhook
            response = requests.post(
                'http://localhost:5000/webhook-mensal',
                json=event_data,
                headers={
                    'Content-Type': 'application/json',
                    'Stripe-Signature': 'test_signature'
                }
            )
            
            return jsonify({
                "status": response.status_code,
                "resposta": response.json() if response.ok else response.text
            })
            
        except Exception as e:
            return jsonify({"erro": str(e)}), 500
