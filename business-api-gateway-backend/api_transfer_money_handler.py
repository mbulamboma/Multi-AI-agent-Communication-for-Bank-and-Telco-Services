import json
import boto3
import os
from datetime import datetime, timedelta
from decimal import Decimal

# Configuration AWS
DYNAMO_TABLE_DATA = "TelcoData" # TelcoData
DYNAMO_TABLE_CATALOG = "Catalog" # Catalog
dynamodb_resource = boto3.resource('dynamodb')
dynamodb_client = boto3.client('dynamodb')
table_data = dynamodb_resource.Table(DYNAMO_TABLE_DATA)
table_catalog = dynamodb_resource.Table(DYNAMO_TABLE_CATALOG)


def lambda_handler(event, context):
    """Effectue un transfert d'argent mobile entre deux utilisateurs."""
    # Handle API Gateway proxy format
    if 'body' in event and isinstance(event['body'], str):
        try:
            body = json.loads(event['body'])
        except json.JSONDecodeError:
            return {
                "statusCode": 400,
                "body": json.dumps({"status": "error", "message": "Invalid JSON in request body."})
            }
    else:
        body = event
    
    try:
        source_phone = body.get('source_phone')
        target_phone = body.get('target_phone')
        amount = Decimal(str(body.get('amount')))
        
        if not source_phone or not target_phone:
            raise KeyError('Missing phone number')
    except KeyError:
        return {
            "statusCode": 400,
            "body": json.dumps({"status": "error", "message": "Paramètres de transfert incomplets."})
        }
    except Exception:
        return {
            "statusCode": 400,
            "body": json.dumps({"status": "error", "message": "Le montant du transfert est invalide."})
        }

    if source_phone == target_phone or amount <= 0:
        return {
            "statusCode": 400,
            "body": json.dumps({"status": "error", "message": "Transfert invalide (même destinataire ou montant négatif/nul)."})
        }

    # Utilisation de l'API Client pour les transactions
    try:
        now = datetime.utcnow().isoformat()
        
        dynamodb_client.transact_write_items(
            TransactItems=[
                # 1. Débit du compte source (Mobile Money)
                {
                    'Update': {
                        'TableName': DYNAMO_TABLE_DATA,
                        'Key': {'PK': {'S': f'USER#{source_phone}'}, 'SK': {'S': 'METADATA'}},
                        'UpdateExpression': 'SET balance_mobile_money = balance_mobile_money - :amt',
                        # Condition pour éviter le découvert
                        'ConditionExpression': 'attribute_exists(PK) AND balance_mobile_money >= :amt', 
                        'ExpressionAttributeValues': {':amt': {'N': str(amount)}},
                    }
                },
                # 2. Crédit du compte cible (Mobile Money)
                {
                    'Update': {
                        'TableName': DYNAMO_TABLE_DATA,
                        'Key': {'PK': {'S': f'USER#{target_phone}'}, 'SK': {'S': 'METADATA'}},
                        'UpdateExpression': 'SET balance_mobile_money = balance_mobile_money + :amt',
                        'ConditionExpression': 'attribute_exists(PK)', # S'assurer que le compte cible existe
                        'ExpressionAttributeValues': {':amt': {'N': str(amount)}},
                    }
                },
                # 3. Enregistrement de la transaction (Débit)
                {
                    'Put': {
                        'TableName': DYNAMO_TABLE_DATA,
                        'Item': {
                            'PK': {'S': f'USER#{source_phone}'},
                            'SK': {'S': f'TRANS#{now}'},
                            'Type': {'S': 'TRANSACTION'},
                            'amount': {'N': str(-amount)}, 
                            'transaction_type': {'S': 'MOBILE_MONEY_TRANSFER_SENT'},
                            'details': {'S': f'Transfert envoyé à {target_phone}'}
                        }
                    }
                }
            ]
        )
        response_body = {
            "status": "success",
            "message": f"Transfert de {amount} vers {target_phone} effectué. Votre nouveau solde sera mis à jour."
        }
        return {
            "statusCode": 200,
            "body": json.dumps(response_body)
        }
    
    except dynamodb_client.exceptions.TransactionCanceledException as e:
        # Gérer spécifiquement l'échec de la condition (solde insuffisant ou cible inexistante)
        error_reason = str(e)
        if 'ConditionCheckFailed' in error_reason:
             # Une logique plus fine peut déterminer si c'est le compte source ou cible qui a échoué
            return {
                "statusCode": 400,
                "body": json.dumps({"status": "error", "message": "Transaction annulée : Solde insuffisant ou compte destinataire invalide."})
            }
        return {
            "statusCode": 500,
            "body": json.dumps({"status": "error", "message": f"Erreur de transaction DynamoDB : {error_reason}"})
        }
        
    except Exception as e:
        print(f"Erreur inattendue: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({"status": "error", "message": "Une erreur inattendue est survenue lors du transfert."})
        }
