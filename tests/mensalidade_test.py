from flask import jsonify, request
import requests
import traceback

def init_mensalidade_tests(app, db):
    @app.route('/testar-webhook-mensal', methods=['POST'])
    def testar_webhook_boleto():
        try:
            dados = request.json
            print("🔧 Dados recebidos para teste manual:", dados)

            # Criar estrutura que simula o webhook Stripe
            event_data = {
                "type": "payment_intent.succeeded",
                "data": {
                    "object": {
                        "id": dados.get('boleto_id', 'pi_test_fake_id'),
                        "amount": int(float(dados.get('valor', 0)) * 100),  # em centavos
                        "metadata": dados.get('metadata', {})
                    }
                }
            }

            # Enviar para o webhook da aplicação
            response = requests.post(
                'http://localhost:5000/webhook-mensal',
                json=event_data,
                headers={
                    'Content-Type': 'application/json',
                    'Stripe-Signature': 'test_signature'  # simulado
                }
            )

            return jsonify({
                "status": response.status_code,
                "resposta": response.json() if response.ok else response.text
            })

        except Exception as e:
            print("Erro ao testar webhook:", traceback.format_exc())
            return jsonify({"erro": str(e)}), 500
