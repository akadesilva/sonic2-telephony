# Security Guide

## Vonage Webhook Verification

### Overview

Vonage signs all webhook requests with a JWT token to verify authenticity. This prevents unauthorized requests from reaching your Lambda functions.

### How It Works

1. Vonage signs webhook requests with your **Signature Secret**
2. JWT token is sent in the `Authorization: Bearer <token>` header
3. Lambda verifies the JWT signature before processing the request
4. Invalid signatures return `401 Unauthorized`

### Setup

#### 1. Get Your Signature Secret

From Vonage Dashboard:
1. Go to your application settings
2. Find **Signature Secret** under Security
3. Copy the secret (looks like: `abc123def456...`)

#### 2. Deploy with Signature Verification

```bash
# Set the signature secret
export VONAGE_SIGNATURE_SECRET="your_signature_secret_here"

# Deploy infrastructure
cd infrastructure
./deploy.sh
```

#### 3. Verify It's Working

The deploy script will show:
```
✅ Vonage signature verification enabled
```

### Testing

#### Valid Request (from Vonage)
```bash
# Vonage will send JWT in Authorization header
curl -X POST https://your-api-url/answer \
  -H "Authorization: Bearer <valid_jwt_token>" \
  -H "Content-Type: application/json"

# Response: 200 OK with NCCO
```

#### Invalid Request (unauthorized)
```bash
# Missing or invalid JWT
curl -X POST https://your-api-url/answer \
  -H "Content-Type: application/json"

# Response: 401 Unauthorized
{
  "error": "Missing or invalid Authorization header"
}
```

### JWT Token Structure

Vonage JWT contains:
```json
{
  "iat": 1234567890,
  "jti": "unique-request-id",
  "application_id": "your-app-id",
  "iss": "vonage"
}
```

### Disabling Verification (Not Recommended)

If you need to disable verification for testing:

```bash
# Don't set VONAGE_SIGNATURE_SECRET
unset VONAGE_SIGNATURE_SECRET

# Deploy
cd infrastructure
./deploy.sh
```

**Warning:** This allows any request to reach your Lambda. Only use for development.

### Best Practices

1. **Always Enable in Production** - Never deploy without signature verification
2. **Rotate Secrets** - Periodically rotate your signature secret in Vonage dashboard
3. **Use Secrets Manager** - For production, store secret in AWS Secrets Manager:

```python
import boto3

def get_signature_secret():
    client = boto3.client('secretsmanager')
    response = client.get_secret_value(SecretId='vonage/signature-secret')
    return response['SecretString']
```

4. **Monitor Failed Attempts** - Set up CloudWatch alarms for 401 responses
5. **IP Allowlisting** - Consider adding Vonage IP ranges to API Gateway resource policy

### Additional Security Layers

#### API Gateway Resource Policy

Restrict access to Vonage IP ranges:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": "*",
      "Action": "execute-api:Invoke",
      "Resource": "arn:aws:execute-api:*:*:*",
      "Condition": {
        "IpAddress": {
          "aws:SourceIp": [
            "5.10.112.121/32",
            "5.10.112.122/32"
          ]
        }
      }
    }
  ]
}
```

#### Rate Limiting

Configure API Gateway throttling:
- Burst limit: 100 requests
- Rate limit: 50 requests/second

#### WAF Integration

Add AWS WAF for additional protection:
- SQL injection protection
- XSS protection
- Rate-based rules

### Troubleshooting

#### Error: "Invalid JWT"

**Causes:**
- Wrong signature secret
- Expired token
- Token tampered with

**Solution:**
- Verify `VONAGE_SIGNATURE_SECRET` matches Vonage dashboard
- Check Lambda logs for detailed error message

#### Error: "Missing Authorization header"

**Causes:**
- Request not from Vonage
- Vonage signature not configured

**Solution:**
- Ensure Vonage application has signature method enabled
- Check request headers in API Gateway logs

### References

- [Vonage Signature Verification](https://developer.vonage.com/en/getting-started/concepts/signing-messages)
- [JWT.io](https://jwt.io/) - Debug JWT tokens
- [AWS Secrets Manager](https://aws.amazon.com/secrets-manager/)
