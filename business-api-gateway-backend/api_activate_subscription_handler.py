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
    """Active un forfait pour l'utilisateur spécifié."""
    # Handle API Gateway proxy format
    if 'body' in event and isinstance(event['body'], str):
        try:
            body = json.loads(event['body'])
        except:
            body = event
    else:
        body = event
    
    try:
        phone_number = body.get('phone_number') or body.get('phoneNumber')
        subscription_id = body.get('subscription_id') or body.get('subscriptionId') or body.get('planId')
        if not phone_number or not subscription_id:
            return {"status": "error", "message": "Numéro de téléphone ou ID de forfait manquant."}
    except (KeyError, AttributeError):
        return {"status": "error", "message": "Numéro de téléphone ou ID de forfait manquant."}

    # 1. Récupérer les détails du forfait et le coût (depuis la table Catalog)
    try:
        # Catalog structure: PK=category (DATA, VOIX_SMS, PACK), SK=subscription_id
        # Since we don't know PK, scan for the subscription_id in SK
        catalog_resp = table_catalog.scan(
            FilterExpression='SK = :sid',
            ExpressionAttributeValues={':sid': subscription_id}
        )
        sub_item = catalog_resp['Items'][0] if catalog_resp['Items'] else None
        if not sub_item:
            return {"status": "error", "message": f"Forfait ID '{subscription_id}' introuvable dans le catalogue."}
        
        price = Decimal(str(sub_item['price']))
        duration_days = int(sub_item['duration_days'])
        
    except Exception as e:
        print(f"Erreur lors de la récupération du forfait: {e}")
        return {"status": "error", "message": "Impossible de charger les détails du forfait."}
        
    # 2. Préparer l'objet du nouveau forfait
    now = datetime.utcnow()
    expiration_date = now + timedelta(days=duration_days)
    new_sub = {
        "id": subscription_id,
        "name": sub_item['name'],
        "activation_date": now.isoformat(),
        "expiration_date": expiration_date.isoformat()
    }

    # 3. Débiter le solde (crédit) et mettre à jour le profil de l'utilisateur (transactionnel pour le débit)
    try:
        # Utilisez TransactWriteItems pour le débit et la mise à jour des subs
        dynamodb_client.transact_write_items(
            TransactItems=[
                # Débit et ajout du forfait (via Update)
                {
                    'Update': {
                        'TableName': DYNAMO_TABLE_DATA,
                        'Key': {'PK': {'S': f'USER#{phone_number}'}, 'SK': {'S': 'METADATA'}},
                        'UpdateExpression': 'SET balance_credit = balance_credit - :cost, active_subs = list_append(active_subs, :newsub)',
                        'ConditionExpression': 'attribute_exists(PK) AND balance_credit >= :cost', 
                        'ExpressionAttributeValues': {
                            ':cost': {'N': str(price)},
                            ':newsub': {'L': [{'M': {
                                'id': {'S': new_sub['id']},
                                'name': {'S': new_sub['name']},
                                'activation_date': {'S': new_sub['activation_date']},
                                'expiration_date': {'S': new_sub['expiration_date']}
                            }}]}
                        }
                    }
                },
                # Enregistrement de la transaction
                {
                    'Put': {
                        'TableName': DYNAMO_TABLE_DATA,
                        'Item': {
                            'PK': {'S': f'USER#{phone_number}'},
                            'SK': {'S': f'TRANS#{now.isoformat()}'},
                            'Type': {'S': 'TRANSACTION'},
                            'amount': {'N': str(-price)},
                            'transaction_type': {'S': 'SUBSCRIPTION_ACTIVATION'},
                            'details': {'S': f"Activation du forfait {sub_item['name']}"}
                        }
                    }
                }
            ]
        )
        return {"status": "success", "message": f"Le forfait {sub_item['name']} a été activé avec succès et expire le {expiration_date.strftime('%d/%m/%Y')}."}

    except dynamodb_client.exceptions.TransactionCanceledException:
        return {"status": "error", "message": "Activation échouée : Votre solde de crédit est insuffisant ou le compte est invalide."}
    except Exception as e:
        print(f"Erreur d'activation de forfait: {e}")
        return {"status": "error", "message": "Une erreur inattendue est survenue lors de l'activation."}