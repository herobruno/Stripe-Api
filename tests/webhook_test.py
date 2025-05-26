from flask import jsonify, request
import time
import json
import requests
from datetime import datetime
import traceback

def init_webhook_tests(app, db):
    @app.route('/testar-webhook-opencode', methods=['GET'])
    def testar_webhook_opencode():
        try:
            print('=== TESTANDO WEBHOOK OPENCODE ===')

            # Dados simulados recebidos do frontend
            cliente_id = 'MaiNCXusd8iuPpczSTKj'
            projeto_id = 'm124yZcOF7evXvZwxpKD'
            nome_cliente = 'favio'
            email_cliente = 'favio@gmail.com'
            cpf_cliente = '186.678.940-60'
            telefone_cliente = '5594823462'
            valor_plano = '22'
            endereco_cliente = {
                'rua': 'Rua Exemplo',
                'numero': '123',
                'complemento': 'Apto 45',
                'cidade': 'São Paulo',
                'estado': 'SP',
                'cep': '12345678'
            }
            plano_titulo = 'Plano Open Code'
            projeto_titulo = 'carros'
            webhook_url = 'http://127.0.0.1:5000/webhook-opencode'
            download_link = 'https://firebasestorage.googleapis.com/v0/b/empresa-fe1a8.firebasestorage.app/o/codigo_fonte%2F1747444854433-imagemtde.zip?alt=media&token=a478a718-6dc5-41af-bab0-9e408aefaa56'

            print('✅ Simulando dados do cliente e projeto')

            # Montar payload simulando a estrutura Stripe
            payload_webhook = {
                'type': 'payment_intent.succeeded',
                'data': {
                    'object': {
                        'id': f'pi_opencode_{int(time.time())}',
                        'metadata': {
                            'tipo_pagamento': 'opencode',
                            'projeto_id': projeto_id,
                            'projeto_titulo': projeto_titulo,
                            'plano_titulo': plano_titulo,
                            'cliente_id': cliente_id,
                            'cliente_nome': nome_cliente,
                            'cliente_email': email_cliente,
                            'cliente_cpf': cpf_cliente,
                            'cliente_telefone': telefone_cliente,
                            'cliente_endereco': json.dumps(endereco_cliente),
                            'data_compra': datetime.now().isoformat(),
                            'valor_plano': valor_plano,
                            'status_pagamento': 'succeeded',
                            'webhook_url': webhook_url,
                            'download_link': download_link
                        },
                        'status': 'succeeded',
                        'amount': int(float(valor_plano) * 100),
                        'currency': 'brl'
                    }
                }
            }

            print('📤 Enviando webhook para rota local...')
            response = requests.post(
                webhook_url,
                json=payload_webhook,
                headers={
                    'Content-Type': 'application/json',
                    'Stripe-Signature': 'seu_webhook_secret'
                }
            )

            print('📨 Webhook enviado. Verificando resposta...')
            print(f'Status: {response.status_code}')
            print(f'Resposta: {response.text}')

            return jsonify({
                'status': 'success',
                'webhook_response': {
                    'status_code': response.status_code,
                    'response': response.json() if response.text else None
                },
                'payload_enviado': payload_webhook
            })

        except Exception as e:
            print('❌ Erro ao testar webhook:', str(e))
            print('Stack trace:', traceback.format_exc())
            return jsonify({
                'status': 'error',
                'erro': str(e)
            }), 500
