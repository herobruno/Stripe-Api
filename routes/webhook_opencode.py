from flask import jsonify, request
import stripe
import time
import traceback
from datetime import datetime
from firebase_admin import firestore
import random

def init_webhook_routes(app, db):
    @app.route('/webhook-opencode', methods=['POST'])
    def webhook_opencode():
        try:
            print('\n=== WEBHOOK OPENCODE RECEBIDO ===')
            print('Headers:', dict(request.headers))
            print('Payload:', request.get_json())
            
            # Em ambiente de teste, não validamos a assinatura
            if request.headers.get('Stripe-Signature') == 'seu_webhook_secret':
                print('✅ Modo de teste: assinatura válida')
                # Modo de teste - não validar assinatura
                event = request.get_json()
            else:
                print('❌ Modo de teste: assinatura inválida')
                # Modo de produção - validar assinatura
                event = stripe.Webhook.construct_event(
                    request.data, 
                    request.headers['Stripe-Signature'], 
                    'seu_webhook_secret'
                )
            
            print('Tipo do evento:', event['type'])
            
            if event['type'] == 'checkout.session.completed':
                session = event['data']['object']
                print('Sessão completada:', session)
                
                # Extrair metadados do pagamento
                metadata = session.get('metadata', {})
                servico_id = metadata.get('servicoId')
                cliente_id = metadata.get('clienteId')
                
                print('Metadados:', {
                    'servico_id': servico_id,
                    'cliente_id': cliente_id
                })
                
                if servico_id and cliente_id:
                    try:
                        print('\n1. Buscando cliente no Firestore...')
                        # Atualizar no documento do cliente
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
                                if plano.get('servicoId') == servico_id:
                                    plano_existente = True
                                    print(f'Plano já existe para o serviço: {servico_id}')
                                    break
                            
                            if not plano_existente:
                                print('3. Plano não existe, buscando informações do projeto...')
                                # Buscar informações do projeto
                                projetos_ref = db.collection('projetos')
                                projetos_query = projetos_ref.where('servicoId', '==', servico_id)
                                projetos_docs = projetos_query.get()
                                print(f'Projetos encontrados: {len(projetos_docs)}')
                                
                                if len(projetos_docs) > 0:
                                    print('4. Projeto encontrado, criando novo plano...')
                                    projeto_doc = projetos_docs[0]
                                    projeto_data = projeto_doc.to_dict()
                                    
                                    # Gerar número da nota fiscal
                                    numero_nota = f"INV-{random.randint(1000, 9999)}-{datetime.now().year}"
                                    
                                    novo_plano = {
                                        'servicoId': servico_id,
                                        'servicoNome': projeto_data.get('titulo', ''),
                                        'titulo': 'Plano Open Code',
                                        'tipo': 'unico',
                                        'dataAdesao': datetime.now().strftime('%d/%m/%Y às %H:%M:%S'),
                                        'status': 'ativo',
                                        'downloadLink': projeto_data.get('downloadLink', ''),
                                        'valor': str(projeto_data.get('preco', '0')),
                                        'numeroNota': numero_nota
                                    }
                                    planos.append(novo_plano)
                                    print(f'✅ Novo plano OpenCode adicionado ao cliente: {servico_id}')
                                    
                                    # Atualizar documento do cliente
                                    print('5. Atualizando documento do cliente...')
                                    cliente_ref.update({'planos': planos})
                                    print(f'✅ Planos atualizados no documento do cliente')
                                else:
                                    print(f'❌ Projeto não encontrado para o servicoId: {servico_id}')
                        else:
                            print(f'❌ Cliente não encontrado: {cliente_id}')
                        
                    except Exception as e:
                        print('❌ Erro ao atualizar Firestore:', str(e))
                        print('Detalhes do erro:', e.__class__.__name__)
                        print('Stack trace:', e.__traceback__)
                        # Não retornamos erro para o Stripe para evitar reenvios
                        pass
                else:
                    print('❌ Metadados inválidos: servico_id ou cliente_id ausentes')
            
            return jsonify({'status': 'success'})
            
        except Exception as e:
            print('❌ Erro no webhook:', str(e))
            print('Detalhes do erro:', e.__class__.__name__)
            print('Stack trace:', e.__traceback__)
            return jsonify({'erro': str(e)}), 400