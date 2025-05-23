from flask import jsonify, request
import stripe
import os
from datetime import datetime
from firebase_admin import firestore

def init_software_personalizado_routes(app, db):
    @app.route('/webhook/software-personalizado', methods=['POST'])
    def webhook_software_personalizado():
        try:
            # Em ambiente de teste, não verificamos a assinatura
            if os.getenv('ENVIRONMENT') == 'test':
                event = request.json
            else:
                # Em produção, verificamos a assinatura do Stripe
                event = stripe.Webhook.construct_event(
                    request.data,
                    request.headers.get('Stripe-Signature'),
                    os.getenv('STRIPE_WEBHOOK_SECRET')
                )

            # Processar apenas eventos de pagamento
            if event.get('type', '').startswith('payment_intent.'):
                payment_intent = event.get('data', {}).get('object', {})
                
                # Extrair metadados
                metadata = payment_intent.get('metadata', {})
                projectId = metadata.get('projectId')
                projectName = metadata.get('projectName')
                
                if not projectId or not projectName:
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
                    return jsonify({'erro': 'Projeto não encontrado'}), 404

                # Atualizar status do pagamento
                for doc in projeto_query:
                    if event.get('type') == 'payment_intent.succeeded':
                        doc.reference.update({
                            'status_pagamento': 'Pago',
                            'data_pagamento': datetime.now().isoformat()
                        })
                    elif event.get('type') == 'payment_intent.canceled':
                        doc.reference.update({
                            'status_pagamento': 'Cancelado',
                            'data_cancelamento': datetime.now().isoformat()
                        })

                return jsonify({'status': 'success'})

        except Exception as e:
            print('❌ Erro no webhook:', str(e))
            return jsonify({'erro': str(e)}), 400