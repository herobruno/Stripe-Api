from flask import jsonify, request
import time
import json
import requests
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
import random
import hmac
import hashlib
import os

def get_stripe_signature(payload):
    secret = os.getenv('STRIPE_WEBHOOK_SECRET', 'seu_webhook_secret')
    timestamp = str(int(time.time()))
    signed_payload = f"{timestamp}.{json.dumps(payload)}"
    signature = hmac.new(
        secret.encode('utf-8'),
        signed_payload.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    return f"t={timestamp},v1={signature}"

def init_webhook_tests(app, db):
    @app.route('/testar-webhook-software', methods=['GET'])
    def testar_webhook_software():
        try:
            print('=== TESTANDO WEBHOOK SOFTWARE PERSONALIZADO ===')
            
            # Dados reais do projeto
            projeto_id = 'Carlinhos maia'
            cliente_id = 'MaiNCXusd8iuPpczSTKj'
            
            projeto_mock = {
                'clienteId': cliente_id,
                'nomeProjeto': projeto_id,
                'clienteCpfCnpj': '18667894060',
                'clienteEmail': 'favio@gmail.com',
                'clienteNome': 'favio',
                'clienteTelefone': '5594823462',
                'createdAt': datetime.now(),
                'dataReuniao': datetime.fromtimestamp(1747312200),
                'horaReuniao': '09:30',
                'numeroNota': 'INV-9151-2025',
                'status': 'Em Produção',
                'status_pagamento': 'Pendente',
                'valor': 2222
            }

            cliente_mock = {
                'nome': 'favio',
                'email': 'favio@gmail.com',
                'telefone': '5594823462',
                'cpfCnpj': '18667894060'
            }

            # Criar dados de teste no Firestore
            print('\n=== CRIANDO DADOS DE TESTE NO FIRESTORE ===')
            
            software_ref = db.collection('software_personalizado')
            projeto_query = software_ref.where(
                field_path='clienteId',
                op_string='==',
                value=cliente_id
            ).where(
                field_path='nomeProjeto',
                op_string='==',
                value=projeto_id
            ).get()
            
            if not projeto_query:
                software_ref.add(projeto_mock)
                print('✅ Projeto de teste criado')
            else:
                print('ℹ️ Projeto de teste já existe')

            cliente_ref = db.collection('clientes').document(cliente_id)
            cliente_doc = cliente_ref.get()
            
            if not cliente_doc.exists:
                cliente_ref.set(cliente_mock)
                print('✅ Cliente de teste criado')
            else:
                print('ℹ️ Cliente de teste já existe')

            resultados_teste = []

            # Simular evento de pagamento com sucesso
            print('\n1. Testando pagamento bem-sucedido...')

            payload_sucesso = {
                'type': 'payment_intent.succeeded',
                'data': {
                    'object': {
                        'id': f'pi_software_{int(time.time())}',
                        'metadata': {
                            'projectId': cliente_id,
                            'projectName': projeto_id,
                            'cliente_cpf_cnpj': '18667894060',
                            'cliente_email': 'favio@gmail.com',
                            'valor': 2222
                        },
                        'status': 'succeeded',
                        'amount': 222200,
                        'currency': 'brl'
                    }
                }
            }

            response_sucesso = requests.post(
                'http://localhost:5000/webhook/software-personalizado',
                json=payload_sucesso,
                headers={
                    'Content-Type': 'application/json',
                    'Stripe-Signature': get_stripe_signature(payload_sucesso)
                }
            )

            resultados_teste.append({
                'cenario': 'Pagamento bem-sucedido',
                'status': response_sucesso.status_code,
                'resposta': response_sucesso.json()
            })

            # Verificar se o status foi atualizado
            projeto_atualizado = software_ref.where(
                field_path='clienteId',
                op_string='==',
                value=cliente_id
            ).where(
                field_path='nomeProjeto',
                op_string='==',
                value=projeto_id
            ).get()

            status_atualizado = False
            if projeto_atualizado:
                for doc in projeto_atualizado:
                    projeto_data = doc.to_dict()
                    status_atualizado = projeto_data.get('status_pagamento') == 'Pago'
                    print(f'Status atual do projeto: {projeto_data.get("status_pagamento")}')

            return jsonify({
                'status': 'success',
                'message': 'Testes do webhook Software Personalizado concluídos',
                'resultados': resultados_teste,
                'dados_mock': {
                    'projeto_id': projeto_id,
                    'cliente_id': cliente_id,
                    'projeto_data': projeto_mock,
                    'cliente_data': cliente_mock,
                    'status_atualizado': status_atualizado
                }
            })

        except Exception as e:
            print('❌ Erro ao testar webhook:', str(e))
            return jsonify({'erro': str(e)}), 400