from flask import jsonify, request
import time
import json
import requests
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
import random
import traceback


def init_webhook_tests(app,db):
    @app.route('/testar-webhook-opencode', methods=['GET'])
    def testar_webhook_opencode():
        try:
            print('=== TESTANDO WEBHOOK OPENCODE ===')
            
            # IDs reais
            projeto_id = '1aIqO9jNYNeMPrZxJiwE'  # ID real do projeto
            cliente_id = 'MaiNCXusd8iuPpczSTKj'  # ID do documento do cliente
            
            # Buscar dados reais do projeto
            print('\n1. Buscando dados do projeto...')
            projeto_ref = db.collection('projetos').document(projeto_id)
            projeto_doc = projeto_ref.get()
            
            if not projeto_doc.exists:
                print('❌ Projeto não encontrado')
                return jsonify({'erro': 'Projeto não encontrado'}), 404
                
            projeto_data = projeto_doc.to_dict()
            print('✅ Dados do projeto encontrados:', projeto_data)
            
            # Buscar o plano Open Code do projeto
            plano_open_code = None
            if 'planos' in projeto_data and isinstance(projeto_data['planos'], list):
                for plano in projeto_data['planos']:
                    if plano.get('titulo') == 'Plano Open Code':
                        plano_open_code = plano
                        break
            
            if not plano_open_code:
                print('❌ Plano Open Code não encontrado no projeto')
                return jsonify({'erro': 'Plano Open Code não encontrado'}), 404
                
            print('✅ Plano Open Code encontrado:', plano_open_code)
            
            # Buscar dados reais do cliente pelo ID do documento
            print('\n2. Buscando dados do cliente pelo ID...')
            cliente_ref = db.collection('clientes').document(cliente_id)
            cliente_doc = cliente_ref.get()
            
            if not cliente_doc.exists:
                print('❌ Cliente não encontrado')
                return jsonify({'erro': 'Cliente não encontrado'}), 404
                
            cliente_data = cliente_doc.to_dict()
            print('✅ Dados do cliente encontrados:', cliente_data)

            # Preparar payload do webhook
            print('\n3. Preparando payload do webhook...')
            payload_webhook = {
                'type': 'checkout.session.completed',
                'data': {
                    'object': {
                        'id': f'cs_opencode_{int(time.time())}',
                        'metadata': {
                            'tipo_pagamento': 'opencode',
                            'projeto_id': projeto_id,
                            'projeto_titulo': projeto_data.get('titulo', ''),
                            'plano_titulo': plano_open_code.get('titulo', ''),
                            'cliente_id': cliente_id,
                            'cliente_nome': cliente_data.get('nome', ''),
                            'cliente_email': cliente_data.get('email', ''),
                            'cliente_cpf': cliente_data.get('cpfCnpj', ''),
                            'cliente_telefone': cliente_data.get('telefone', ''),
                            'cliente_endereco': cliente_data.get('endereco', ''),
                            'data_compra': datetime.now().isoformat(),
                            'valor_plano': plano_open_code.get('preco', '0'),
                            'status_pagamento': 'pending',
                            'webhook_url': 'http://localhost:5000/webhook-opencode',
                            'download_link': plano_open_code.get('downloadLink', '')
                        },
                        'status': 'complete',
                        'amount_total': int(float(plano_open_code.get('preco', '0')) * 100),
                        'currency': 'brl'
                    }
                }
            }

            print('\n4. Enviando webhook...')
            response = requests.post(
                'http://localhost:5000/webhook-opencode',
                json=payload_webhook,
                headers={
                    'Content-Type': 'application/json',
                    'Stripe-Signature': 'seu_webhook_secret'
                }
            )

            print('\n5. Resultado do webhook:')
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