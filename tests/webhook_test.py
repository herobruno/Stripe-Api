from flask import jsonify, request
import time
import json
import requests
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
import random


def init_webhook_tests(app,db):
    @app.route('/testar-webhook-opencode', methods=['GET'])
    def testar_webhook_opencode():
        try:
            print('=== TESTANDO WEBHOOK OPENCODE ===')
            
            # IDs de teste
            servico_id = 'opencode_servico_123'  # ID fixo para teste
            cliente_id = 'opencode_cliente_456'  # ID fixo para teste
            
            # Dados mockados para teste
            projeto_mock = {
                'servicoId': servico_id,
                'titulo': 'Projeto OpenCode Teste',
                'descricao': 'Projeto de teste para OpenCode',
                'downloadLink': 'https://exemplo.com/download/teste',
                'preco': 100.00,
                'status': 'ativo'
            }

            cliente_mock = {
                'nome': 'Cliente Teste OpenCode',
                'email': 'teste@opencode.com',
                'planos': []
            }

            # Criar dados de teste no Firestore
            print('\n=== CRIANDO DADOS DE TESTE NO FIRESTORE ===')
            
            # Criar projeto de teste
            print('1. Criando projeto de teste...')
            projetos_ref = db.collection('projetos')
            projeto_query = projetos_ref.where('servicoId', '==', servico_id).get()
            
            if not projeto_query:
                projetos_ref.add(projeto_mock)
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
                'type': 'checkout.session.completed',
                'data': {
                    'object': {
                        'id': f'cs_opencode_{int(time.time())}',
                        'metadata': {
                            'servicoId': servico_id,
                            'clienteId': cliente_id
                        },
                        'payment_status': 'paid',
                        'amount_total': 10000,
                        'currency': 'brl'
                    }
                }
            }

            response_sucesso = requests.post(
                'http://localhost:5000/webhook-opencode',
                json=payload_sucesso,
                headers={
                    'Content-Type': 'application/json',
                    'Stripe-Signature': 'seu_webhook_secret'
                }
            )
            resultados_teste.append({
                'cenario': 'Pagamento bem-sucedido',
                'status': response_sucesso.status_code,
                'resposta': response_sucesso.json()
            })

            # 2. Teste de sessão expirada
            print('\n2. Testando sessão expirada...')
            payload_expirado = {
                'type': 'checkout.session.expired',
                'data': {
                    'object': {
                        'id': f'cs_opencode_{int(time.time())}',
                        'metadata': {
                            'servicoId': servico_id,
                            'clienteId': cliente_id
                        },
                        'payment_status': 'expired',
                        'amount_total': 10000,
                        'currency': 'brl'
                    }
                }
            }

            response_expirado = requests.post(
                'http://localhost:5000/webhook-opencode',
                json=payload_expirado,
                headers={
                    'Content-Type': 'application/json',
                    'Stripe-Signature': 'seu_webhook_secret'
                }
            )
            resultados_teste.append({
                'cenario': 'Sessão expirada',
                'status': response_expirado.status_code,
                'resposta': response_expirado.json()
            })

            # 3. Teste com assinatura inválida
            print('\n3. Testando assinatura inválida...')
            response_assinatura_invalida = requests.post(
                'http://localhost:5000/webhook-opencode',
                json=payload_sucesso,
                headers={
                    'Content-Type': 'application/json',
                    'Stripe-Signature': 'assinatura_invalida'
                }
            )
            resultados_teste.append({
                'cenario': 'Assinatura inválida',
                'status': response_assinatura_invalida.status_code,
                'resposta': response_assinatura_invalida.json()
            })

            # 4. Teste com dados inválidos
            print('\n4. Testando dados inválidos...')
            payload_dados_invalidos = {
                'type': 'checkout.session.completed',
                'data': {
                    'object': {
                        'id': f'cs_opencode_{int(time.time())}',
                        'metadata': {
                            'servicoId': '',  # ID inválido
                            'clienteId': ''   # ID inválido
                        },
                        'payment_status': 'paid',
                        'amount_total': 10000,
                        'currency': 'brl'
                    }
                }
            }

            response_dados_invalidos = requests.post(
                'http://localhost:5000/webhook-opencode',
                json=payload_dados_invalidos,
                headers={
                    'Content-Type': 'application/json',
                    'Stripe-Signature': 'seu_webhook_secret'
                }
            )
            resultados_teste.append({
                'cenario': 'Dados inválidos',
                'status': response_dados_invalidos.status_code,
                'resposta': response_dados_invalidos.json()
            })

            # 5. Teste com cliente não existente
            print('\n5. Testando cliente não existente...')
            payload_cliente_inexistente = {
                'type': 'checkout.session.completed',
                'data': {
                    'object': {
                        'id': f'cs_opencode_{int(time.time())}',
                        'metadata': {
                            'servicoId': servico_id,
                            'clienteId': 'cliente_inexistente'
                        },
                        'payment_status': 'paid',
                        'amount_total': 10000,
                        'currency': 'brl'
                    }
                }
            }

            response_cliente_inexistente = requests.post(
                'http://localhost:5000/webhook-opencode',
                json=payload_cliente_inexistente,
                headers={
                    'Content-Type': 'application/json',
                    'Stripe-Signature': 'seu_webhook_secret'
                }
            )
            resultados_teste.append({
                'cenario': 'Cliente não existente',
                'status': response_cliente_inexistente.status_code,
                'resposta': response_cliente_inexistente.json()
            })

            # Verificar se o plano foi adicionado
            cliente_atualizado = db.collection('clientes').document(cliente_id).get()
            plano_adicionado = False
            if cliente_atualizado.exists:
                cliente_data = cliente_atualizado.to_dict()
                planos = cliente_data.get('planos', [])
                plano_adicionado = any(plano.get('servicoId') == servico_id for plano in planos)

            return jsonify({
                'status': 'success',
                'message': 'Testes do webhook OpenCode concluídos',
                'resultados': resultados_teste,
                'dados_mock': {
                    'servico_id': servico_id,
                    'cliente_id': cliente_id,
                    'projeto_data': projeto_mock,
                    'cliente_data': cliente_mock,
                    'plano_adicionado': plano_adicionado
                }
            })

        except Exception as e:
            print('❌ Erro ao testar webhook:', str(e))
            print('Detalhes do erro:', e.__class__.__name__)
            print('Stack trace:', e.__traceback__)
            return jsonify({'erro': str(e)}), 400 