# Créer le Guardrail
aws bedrock create-guardrail `
  --name "TelcoPaymentGuardrail" `
  --description "Allows financial operations for telecom services" `
  --content-policy-config '{
    "filtersConfig": [
      {"type": "MISCONDUCT", "inputStrength": "NONE", "outputStrength": "NONE"},
      {"type": "VIOLENCE", "inputStrength": "LOW", "outputStrength": "LOW"},
      {"type": "HATE", "inputStrength": "LOW", "outputStrength": "LOW"},
      {"type": "INSULTS", "inputStrength": "LOW", "outputStrength": "LOW"},
      {"type": "SEXUAL", "inputStrength": "MEDIUM", "outputStrength": "MEDIUM"}
    ]
  }' `
  --blocked-input-messaging "Désolé, cette demande ne peut pas être traitée." `
  --blocked-outputs-messaging "La réponse ne peut pas être générée." `
  --region us-east-1

# Récupérer l'ID du Guardrail créé
$guardrailId = (aws bedrock list-guardrails --region us-east-1 --query 'guardrails[?name==`TelcoPaymentGuardrail`].id' --output text)

# Créer une version du Guardrail
aws bedrock create-guardrail-version `
  --guardrail-identifier $guardrailId `
  --region us-east-1

# Attacher le Guardrail à votre agent
aws bedrock update-agent `
  --agent-id "0OC0NDBBRC" `
  --agent-name "MoneyTransferAgent" `
  --guardrail-configuration "guardrailIdentifier=$guardrailId,guardrailVersion=1" `
  --region us-east-1

# Préparer l'agent
aws bedrock prepare-agent `
  --agent-id "0OC0NDBBRC" `
  --region us-east-1
