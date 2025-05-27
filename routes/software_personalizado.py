from flask import jsonify, request
import stripe
import os
from datetime import datetime
from firebase_admin import firestore
from dotenv import load_dotenv
import json

# Carregar variáveis do .env
load_dotenv()

# Configurar a chave do Stripe
stripe.api_key = os.getenv('STRIPE_SECRET_KEY')

def init_software_personalizado_routes(app, db):
    @app.route('/webhook/software-personalizado', methods=['POST'])
    def webhook_software_personalizado():
        try:
            print("\n=== Novo Webhook Software Personalizado Recebido ===")
            print("Dados recebidos:", request.get_data(as_text=True))
            
           
            try:
                 event = stripe.Webhook.construct_event(
                     request.data,
                     request.headers['Stripe-Signature'],
                     os.getenv('STRIPE_WEBHOOK_SECRET')
                 )
                
            except stripe.error.SignatureVerificationError as e:
                print('❌ Assinatura do webhook inválida:', str(e))
                return jsonify({'erro': 'Assinatura inválida'}), 400

            if event['type'] != 'payment_intent.succeeded':
                print(f"Evento ignorado: {event['type']}")
                return jsonify({"mensagem": "Evento ignorado"}), 200
            
            print("✅ Evento payment_intent.succeeded recebido")
            
            payment_intent = event['data']['object']
            print("Dados do pagamento:", payment_intent)
            
            # Extrair metadados
            metadata = payment_intent.get('metadata', {})
            print("Metadados extraídos:", metadata)
            
            projectId = metadata.get('projectId')
            projectName = metadata.get('projectName')
            
            if not projectId or not projectName:
                print("Erro: Metadados incompletos - projectId ou projectName não encontrados")
                return jsonify({'erro': 'Metadados inválidos'}), 400

            # Buscar projeto no Firestore
            software_ref = db.collection('software_personalizado')
            projeto_query = software_ref.where(
                field_path='clienteId',
                op_string='==',
                value=projectId
            ).where(
                field_path='nomeProjeto',
                op_string='==',
                value=projectName
            ).get()

            if not projeto_query:
                print(f"Erro: Projeto não encontrado - ID: {projectId}, Nome: {projectName}")
                return jsonify({'erro': 'Projeto não encontrado'}), 404

            # Atualizar status do pagamento
            for doc in projeto_query:
                doc.reference.update({
                    'status_pagamento': 'Pago',
                    'data_pagamento': datetime.now().isoformat(),
                    'paymentIntentId': payment_intent.get('id'),
                    'valorPago': payment_intent.get('amount') / 100  # Converte de centavos para reais
                })
                print(f"✅ Projeto {projectName} atualizado com sucesso")

            print("=== Webhook Processado com Sucesso ===\n")
            return jsonify({'status': 'success'})

        except Exception as e:
            print('❌ Erro no webhook:', str(e))
            print('Detalhes do erro:', e.__class__.__name__)
            print('Stack trace:', e.__traceback__)
            return jsonify({'erro': str(e)}), 500