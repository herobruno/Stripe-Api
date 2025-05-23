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
            
            # IDs reais do projeto
            projeto_id = 'feijao'
            cliente_id = 'MaiNCXusd8iuPpczSTKj'
            
            # Dados reais do projeto
            projeto_mock = {
                'clienteId': cliente_id,
                'nomeProjeto': projeto_id,
                'clienteCpfCnpj': '186.678.940-60',
                'clienteEmail': 'favio@gmail.com',
                'clienteNome': 'favio',
                'clienteTelefone': '5594823462',
                'createdAt': datetime.now(),
                'dataReuniao': datetime(2025, 5, 31, 11, 0),
                'horaReuniao': '11:00',
                'numeroNota': 'INV-6760-2025',
                'status': 'Em Produção',
                'status_pagamento': 'Pendente',
                'valor': 1222
            }

            cliente_mock = {
                'nome': 'favio',
                'email': 'favio@gmail.com',
                'telefone': '5594823462',
                'cpfCnpj': '186.678.940-60'
            }

            # Criar dados de teste no Firestore
            print('\n=== CRIANDO DADOS DE TESTE NO FIRESTORE ===')
            
            # Criar projeto de teste
            print('1. Criando projeto de teste...')
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

            # Criar cliente de teste
            print('2. Criando cliente de teste...')
            cliente_ref = db.collection('clientes').document(cliente_id)
            cliente_doc = cliente_ref.get()
            
            if not cliente_doc.exists:
                cliente_ref.set(cliente_mock)
                print('✅ Cliente de teste criado')
            else:
                print('ℹ️ Cliente de teste já existe')

            resultados_teste = []

            # 1. Teste de pagamento bem-sucedido
            print('\n1. Testando pagamento bem-sucedido...')
            payload_sucesso = {
                'type': 'payment_intent.succeeded',
                'data': {
                    'object': {
                        'id': f'pi_software_{int(time.time())}',
                        'metadata': {
                            'projectId': cliente_id,
                            'projectName': projeto_id,
                            'cliente_cpf_cnpj': '186.678.940-60',
                            'cliente_email': 'favio@gmail.com',
                            'valor': 1222
                        },
                        'status': 'succeeded',
                        'amount': 122200,  # Valor em centavos
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
            print('Detalhes do erro:', e.__class__.__name__)
            print('Stack trace:', e.__traceback__)
            return jsonify({'erro': str(e)}), 400   