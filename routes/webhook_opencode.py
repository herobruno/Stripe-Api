from flask import jsonify, request
import stripe
import time
import traceback
from datetime import datetime
from firebase_admin import firestore
import random
import os
from dotenv import load_dotenv
import json

# Carregar variáveis do .env
load_dotenv()

# Configurar a chave do Stripe
stripe.api_key = os.getenv('STRIPE_SECRET_KEY')

def init_webhook_routes(app, db):
    @app.route('/webhook-opencode', methods=['POST'])
    def webhook_pagamento():
        try:
            print('\n=== WEBHOOK PAGAMENTO RECEBIDO ===')
            print('Headers:', dict(request.headers))
            print('Payload:', request.get_json())
            
           
            try:
                event = stripe.Webhook.construct_event(
                    request.data,
                    request.headers['Stripe-Signature'],
                    os.getenv('STRIPE_WEBHOOK_SECRET')
                )
                print('✅ Assinatura do webhook válida')
            except stripe.error.SignatureVerificationError as e:
                print('❌ Assinatura do webhook inválida:', str(e))
                return jsonify({'erro': 'Assinatura inválida'}), 400
            
            
            
            print('Tipo do evento:', event['type'])
            
            # Verificar se é o evento de pagamento confirmado
            if event['type'] != 'payment_intent.succeeded':
                print(f"Evento ignorado: {event['type']}")
                return jsonify({"mensagem": "Evento ignorado"}), 200
            
            print("✅ Evento payment_intent.succeeded recebido")
            
            # Extrair dados do pagamento
            payment_intent = event['data']['object']
            print('Dados do pagamento:', payment_intent)
            
            # Extrair metadados do pagamento
            metadata = payment_intent.get('metadata', {})
            tipo_pagamento = metadata.get('tipo_pagamento')
            
            if tipo_pagamento == 'opencode':
                projeto_id = metadata.get('projeto_id')
                cliente_id = metadata.get('cliente_id')
                
                print('Metadados OpenCode:', {
                    'projeto_id': projeto_id,
                    'cliente_id': cliente_id,
                    'tipo_pagamento': tipo_pagamento
                })
                
                if projeto_id and cliente_id:
                    try:
                        print('\n1. Buscando cliente no Firestore...')
                        cliente_ref = db.collection('clientes').document(cliente_id)
                        print(f'Referência do cliente criada: {cliente_id}')
                        
                        cliente_doc = cliente_ref.get()
                        print(f'Documento do cliente obtido: {cliente_doc.exists}')
                        
                        if cliente_doc.exists:
                            print('2. Cliente encontrado, verificando planos...')
                            cliente_data = cliente_doc.to_dict()
                            planos = cliente_data.get('planos', [])
                            print(f'Planos encontrados: {len(planos)}')
                            
                            # Verificar se o plano já existe
                            plano_existente = False
                            for plano in planos:
                                if plano.get('servicoId') == projeto_id:
                                    plano_existente = True
                                    print(f'Plano já existe para o projeto: {projeto_id}')
                                    break
                            
                            if not plano_existente:
                                print('3. Plano não existe, criando novo plano...')
                                
                                # Gerar número da nota fiscal
                                numero_nota = f"INV-{random.randint(1000, 9999)}-{datetime.now().year}"
                                
                                novo_plano = {
                                    'servicoId': projeto_id,
                                    'servicoNome': metadata.get('projeto_titulo'),
                                    'titulo': metadata.get('plano_titulo'),
                                    'tipo': 'unico',
                                    'dataAdesao': metadata.get('data_compra'),
                                    'status': 'ativo',
                                    'downloadLink': metadata.get('download_link', ''),
                                    'valor': metadata.get('valor_plano'),
                                'numeroNota': numero_nota,
                                'paymentIntentId': payment_intent.get('id'),
                                'valorPago': payment_intent.get('amount') / 100  # Converte de centavos para reais
                                }
                                planos.append(novo_plano)
                                print(f'✅ Novo plano OpenCode adicionado ao cliente: {projeto_id}')
                                
                                # Atualizar documento do cliente
                                print('4. Atualizando documento do cliente...')
                                cliente_ref.update({'planos': planos})
                                print(f'✅ Planos atualizados no documento do cliente')
                        else:
                            print(f'❌ Cliente não encontrado: {cliente_id}')
                        
                    except Exception as e:
                        print('❌ Erro ao atualizar Firestore:', str(e))
                        print('Detalhes do erro:', e.__class__.__name__)
                        print('Stack trace:', e.__traceback__)
                        # Não retornamos erro para o Stripe para evitar reenvios
                        pass
                else:
                    print('❌ Metadados inválidos: projeto_id ou cliente_id ausentes')
            
            return jsonify({'status': 'success'})
            
        except Exception as e:
            print('❌ Erro no webhook:', str(e))
            print('Detalhes do erro:', e.__class__.__name__)
            print('Stack trace:', e.__traceback__)
            return jsonify({'erro': str(e)}), 500