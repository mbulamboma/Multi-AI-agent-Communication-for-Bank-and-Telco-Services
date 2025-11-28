import json
import boto3
import os
from datetime import datetime, timedelta
from decimal import Decimal

# Configuration AWS
DYNAMO_TABLE_DATA = "TelcoData" # TelcoData
DYNAMO_TABLE_CATALOG ="Catalog" # Catalog
dynamodb_resource = boto3.resource('dynamodb')
dynamodb_client = boto3.client('dynamodb')
table_data = dynamodb_resource.Table(DYNAMO_TABLE_DATA)
table_catalog = dynamodb_resource.Table(DYNAMO_TABLE_CATALOG)

def lambda_handler(event, context):
    """Récupère les soldes et les forfaits actifs de l'utilisateur."""
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
        if not phone_number:
            return {"status": "error", "message": "Le numéro de téléphone est manquant."}
    except (KeyError, AttributeError):
        return {"status": "error", "message": "Le numéro de téléphone est manquant."}

    try:
        response = table_data.get_item(
            Key={
                'PK': f'USER#{phone_number}',
                'SK': 'METADATA'
            },
            ProjectionExpression='balance_credit, balance_mobile_money, active_subs'
        )

        item = response.get('Item')
        if not item:
            return {"status": "error", "message": f"Utilisateur {phone_number} non trouvé."}

        # Conversion des types DynamoDB (Decimal) en float pour la sérialisation JSON
        return {
            "status": "success",
            "balance_credit": float(item.get('balance_credit', Decimal(0))),
            "balance_mobile_money": float(item.get('balance_mobile_money', Decimal(0))),
            "active_subscriptions": item.get('active_subs', [])
        }
    except Exception as e:
        print(f"Erreur DynamoDB lors de la vérification du solde: {e}")
        return {"status": "error", "message": "Erreur interne lors de l'accès aux données."}