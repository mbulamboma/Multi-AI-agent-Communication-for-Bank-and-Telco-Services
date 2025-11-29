# Database Schema

## Tables

### 1. TelcoData (User Data & Transactions)
| Key | Type | Details |
|-----|------|---------|
| **PK** | String | `USER#{phone_number}` |
| **SK** | String | `METADATA` or `TRANS#{timestamp}` |

#### METADATA Item (User Profile)
```json
{
  "PK": "USER#+243891234567",
  "SK": "METADATA",
  "Type": "USER_PROFILE",
  "balance_credit": 15.75,
  "balance_mobile_money": 25000.50,
  "active_subs": [
    {
      "id": "F_D_1GB",
      "name": "Forfait Data 1GB",
      "activation_date": "2025-11-15T10:00:00Z",
      "expiration_date": "2025-11-22T10:00:00Z"
    }
  ]
}
```

#### TRANSACTION Item
```json
{
  "PK": "USER#+243891234567",
  "SK": "TRANS#2025-11-16T15:30:00Z",
  "Type": "TRANSACTION",
  "amount": -5,
  "transaction_type": "SUBSCRIPTION_ACTIVATION",
  "details": "Activation Forfait Data 1GB (F_D_1GB)"
}
```

**Transaction Types:**
- `SUBSCRIPTION_ACTIVATION` - Subscription purchase
- `MOBILE_MONEY_TRANSFER_SENT` - Money sent
- `MOBILE_MONEY_TRANSFER_RECEIVED` - Money received
- `CREDIT_PURCHASE` - Credit bought
- `CREDIT_ACTIVATION` - Credit used

---

### 2. Catalog (Subscription Plans)
| Key | Type | Details |
|-----|------|---------|
| **PK** | String | Category: `DATA`, `VOICE_SMS`, `PACK` |
| **SK** | String | Subscription ID: `F_D_1GB`, `F_V_50M`, `F_P_PREMIUM` |

```json
{
  "PK": "DATA",
  "SK": "F_D_1GB",
  "Type": "SUBSCRIPTION",
  "name": "Forfait Data 1GB",
  "description": "1 GB de données internet, valable 7 jours.",
  "price": 5,
  "duration_days": 7
}
```

---

## API Operations

| API | Operation | Tables Used |
|-----|-----------|------------|
| `/activateSubscription` | Query Catalog → Debit balance → Log transaction | TelcoData, Catalog |
| `/checkBalance` | Get user METADATA | TelcoData |
| `/transferMoney` | Debit sender → Credit receiver → Log 2 transactions | TelcoData |
| `/getSubscriptionRecommendation` | Get active subs → Query Catalog → Recommend | TelcoData, Catalog |

---

## Constraints
- `balance_credit` ≥ 0
- `balance_mobile_money` ≥ 0
- `price` > 0
- `duration_days` > 0
- Transactions use TransactWriteItems for consistency

