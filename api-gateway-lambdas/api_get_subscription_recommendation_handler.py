import json
import boto3
import os
from datetime import datetime, timedelta
from decimal import Decimal

# Configuration AWS
DYNAMO_TABLE_DATA = "TelcoData"# TelcoData
DYNAMO_TABLE_CATALOG = "Catalog" # Catalog
dynamodb_resource = boto3.resource('dynamodb')
dynamodb_client = boto3.client('dynamodb')
table_data = dynamodb_resource.Table(DYNAMO_TABLE_DATA)
table_catalog = dynamodb_resource.Table(DYNAMO_TABLE_CATALOG)


def lambda_handler(event, context):
    """Recommande un forfait basé sur les forfaits actifs de l'utilisateur."""
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
        phone_number = body.get('phone_number')
        if not phone_number:
            raise KeyError('phone_number')
    except KeyError:
        return {
            "statusCode": 400,
            "body": json.dumps({"status": "error", "message": "Le numéro de téléphone est manquant."})
        }

    # 1. Récupérer les forfaits actifs de l'utilisateur (via check_balance, ou directement)
    try:
        user_data_response = table_data.get_item(Key={'PK': f'USER#{phone_number}', 'SK': 'METADATA'})
        active_subs = user_data_response['Item'].get('active_subs', [])
    except Exception:
        active_subs = [] # Supposons qu'il n'y ait pas de forfaits actifs

    # 2. Vérifier si un forfait Data est actif
    has_active_data = any('DATA' in sub['id'] for sub in active_subs)

    # 3. Logique de Recommandation
    
    # Si l'utilisateur n'a pas de forfait Data actif, recommandons le moins cher (F_D_1GB)
    if not has_active_data:
        pk_reco = 'DATA'
        
    # S'il a déjà un forfait, recommandons une mise à niveau (Pack Premium)
    else:
        pk_reco = 'PACK'

    # 4. Récupérer les détails des forfaits recommandés dans le catalogue
    try:
        # Requête pour obtenir tous les forfaits de la catégorie sélectionnée (PK)
        catalog_resp = table_catalog.query(
            KeyConditionExpression='PK = :pk',
            ExpressionAttributeValues={':pk': pk_reco}
        )
        
        # Simplement prendre le premier (le plus pertinent selon la logique du tri interne ou de la requête)
        recommendation_item = catalog_resp['Items'][0] if catalog_resp['Items'] else None

        if recommendation_item:
            response_body = {
                "status": "success",
                "recommendation": {
                    "id": recommendation_item['SK'],
                    "name": recommendation_item['name'],
                    "price": float(recommendation_item['price']),
                    "description": recommendation_item['description']
                },
                "message": f"Basé sur vos habitudes, nous vous recommandons le forfait {recommendation_item['name']}."
            }
            return {
                "statusCode": 200,
                "body": json.dumps(response_body)
            }
        else:
            response_body = {
                "status": "info",
                "message": "Nous n'avons pas de recommandation spécifique pour vous pour le moment, mais vous pouvez consulter tous nos forfaits."
            }
            return {
                "statusCode": 200,
                "body": json.dumps(response_body)
            }

    except Exception as e:
        print(f"Erreur de recommandation: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({"status": "error", "message": "Erreur interne lors de la génération de la recommandation."})
        }