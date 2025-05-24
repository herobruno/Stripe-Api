from flask import jsonify, request
from datetime import datetime
from firebase_admin import firestore
import os
import stripe
from dotenv import load_dotenv

# Carregar variáveis do .env
load_dotenv()


stripe.api_key = os.getenv('STRIPE_SECRET_KEY')

def init_mensalidade_routes(app, db):
    @app.route('/webhook-mensal', methods=['POST'])
    def webhook_boleto():
        try:
            print("\n=== Novo Webhook Recebido ===")
            print("Dados recebidos:", request.get_data(as_text=True))
            
            # Extrair dados do payload
            payload = request.json
            print("Payload:", payload)
            
            # Extrair metadados do evento
            metadata = payload.get('data', {}).get('object', {}).get('metadata', {})
            if not metadata:
                metadata = payload.get('metadata', {})  # Fallback para payload direto
                
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
                    fatura_encontrada = True
                    print(f"Fatura {fatura_id} encontrada e atualizada")
                    break
            
            if not fatura_encontrada:
                print(f"Erro: Fatura não encontrada - ID: {fatura_id}")
                return jsonify({"erro": "Fatura não encontrada"}), 404
                
            # Atualizar o documento do cliente
            cliente_ref.update({
                'faturas': faturas
            })
            
            print(f"Fatura {fatura_id} marcada como paga para o cliente {cliente_id}")
            print("=== Webhook Processado com Sucesso ===\n")
            return jsonify({"mensagem": "Pagamento processado com sucesso"}), 200
            
        except Exception as e:
            print("Erro ao processar webhook:", str(e))
            return jsonify({"erro": str(e)}), 500