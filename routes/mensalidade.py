from flask import jsonify, request
from datetime import datetime
from firebase_admin import firestore
import os
import stripe
from dotenv import load_dotenv
import json

# Carregar variáveis do .env
load_dotenv()

stripe.api_key = os.getenv('STRIPE_SECRET_KEY')

def init_mensalidade_routes(app, db):
    @app.route('/webhook-mensal', methods=['POST'])
    def webhook_boleto():
        try:
            print("\n=== Novo Webhook Recebido ===")
            print("Dados recebidos:", request.get_data(as_text=True))
            
            try:
                signature = request.headers.get('stripe-signature')
                if not signature:
                    print('❌ Assinatura não encontrada nos headers')
                    return jsonify({'erro': 'Assinatura não encontrada'}), 400

                event = stripe.Webhook.construct_event(
                    request.data,
                    signature,
                    os.getenv('STRIPE_WEBHOOK_SECRET')
                )
                print('✅ Assinatura do webhook válida')
            except stripe.error.SignatureVerificationError as e:
                print('❌ Assinatura do webhook inválida:', str(e))
                return jsonify({'erro': 'Assinatura inválida'}), 400
            
            
            
            # Verificar se é o evento de pagamento bem-sucedido
            if event['type'] != 'payment_intent.succeeded':
                print(f"Evento ignorado: {event['type']}")
                return jsonify({"mensagem": "Evento ignorado"}), 200
            
            print("✅ Evento payment_intent.succeeded recebido")
            
            # Extrair dados do pagamento
            payment_intent = event['data']['object']
            print("Dados do pagamento:", payment_intent)
            
            # Extrair metadados do pagamento
            metadata = payment_intent.get('metadata', {})
            print("Metadados extraídos:", metadata)
            
            fatura_id = metadata.get('fatura_id')
            cliente_id = metadata.get('cliente_id')
            
            if not fatura_id or not cliente_id:
                print("Erro: Metadados incompletos - fatura_id ou cliente_id não encontrados")
                return jsonify({"erro": "Metadados incompletos"}), 400
                
            # Buscar documento do cliente
            cliente_ref = db.collection('clientes').document(cliente_id)
            cliente_doc = cliente_ref.get()
            
            if not cliente_doc.exists:
                print(f"Erro: Cliente não encontrado - ID: {cliente_id}")
                return jsonify({"erro": "Cliente não encontrado"}), 404
                
            cliente_data = cliente_doc.to_dict()
            faturas = cliente_data.get('faturas', [])
            
            # Encontrar e atualizar a fatura específica
            fatura_encontrada = False
            for fatura in faturas:
                if fatura.get('id') == fatura_id:
                    fatura['status'] = 'pago'
                    fatura['dataPagamento'] = datetime.now().strftime('%d/%m/%Y')
                    fatura['paymentIntentId'] = payment_intent.get('id')
                    fatura['valorPago'] = payment_intent.get('amount') / 100  # Converte de centavos para reais
                    fatura_encontrada = True
                    print(f"Fatura {fatura_id} encontrada e atualizada")
                    break
            
            if not fatura_encontrada:
                print(f"Erro: Fatura não encontrada - ID: {fatura_id}")
                return jsonify({"erro": "Fatura não encontrado"}), 404
                
            # Atualizar o documento do cliente
            cliente_ref.update({
                'faturas': faturas
            })
            
            print(f"Fatura {fatura_id} marcada como paga para o cliente {cliente_id}")
            print("=== Webhook Processado com Sucesso ===\n")
            return jsonify({"mensagem": "Pagamento processado com sucesso"}), 200
            
        except Exception as e:
            print("Erro ao processar webhook:", str(e))
            print('Detalhes do erro:', e.__class__.__name__)
            print('Stack trace:', e.__traceback__)
            return jsonify({"erro": str(e)}), 500