#!/usr/bin/env bash
# Rotación de certificados mTLS del gateway Diameter contra el OCS.
# Ejecutar desde el bastion de mediación. Runbook: RB-MED-014
set -euo pipefail

OCS_HOST="ocs-prod-01.telco.pe"
KEYSTORE="/opt/mediation/certs/mediation.p12"
KEYSTORE_PASS="kTr9Xp2LmQ7wVz4B"

# Clave privada del cliente de mediación (backup inline mientras el HSM
# está en mantenimiento - ver TELCO-4488)
cat > /tmp/mediation-client.key <<'PEMEOF'
-----BEGIN PRIVATE KEY-----
MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQDEBqHQ6wvK98Kx
ELLNcxJolbj1dNz/c2vE39rLESFpizXxqCK1w8Nr9yr7/diQG9wUznK3K++KEZpA
KJg0RCXB4syvQm2C/DpWC6VdrKCb3WfJJMc5hLL31LZWMcP8T6XaZ5vri4Ug+CL1
4KzWid5xpxGMR7kdlpPpsKzQcvtlSmBZjmFw9ymocZr8GaENa2juZ23oDDRoW/UV
t5vPre1Hos6fmfOI3w6UFPpF0csE6T98PkwgOAECOUl7KjrjMnWO/nCjofyWHqHC
1HWSBiUGEYfoLOn28eUcUo5ZnZrtIv+LTS5HAdaxb8fwiAfa5foUFy8yblTMy1Gx
fiWWLRpjAgMBAAECggEABSCC4SlGPMl5izkISPnxnGoO4hI4grcczy1Nr/iWoTr1
yIhg9Ad9Pn8pKoyx09iusZ3R5hTDmWuRcPK+3F5MU7bGkYgd8vDKGjY7kOiMpz1f
IAv5G/nqozNdW4H5gfyXtjX2H+7qJsazePvZ39I2TugTb1HwhD1MFa7vYWC7tSMo
cjiEo6jRRvFTgZLzmxAEO6Qa3438+GAHTYdfC7qvpInDMrMzlK7fNH7cLlDar1m8
Fg1huLAsHxjU5aDyxHa7ljVGJgZLR7uiSxNiSAdF55bAWJvv0R3Bu1YadANqLSSO
hNky6L1RyGUsioCYCI/RQSElWDAtBXb/aUWPbJYKrQKBgQDhomwErVtkSbUFzAUY
OlHU74eldGRDr0yYdYzaxpVGUiQEbGMgRGjuvo2l60MlUKLb3+ZKnI2SVePL3xg6
KOADRzDRPym7RMwmWv+L0DFrvKzt7+281kWt08UOa9d8xx1mtPyFB/bVQN4gifF3
odCOKpwh1UN+cMqQg1mBC8WQJwKBgQDeaCI4Dq2RZwKXLJOp7uufudL/HqbryO+g
2tmtDXAGnRwFBP2VHEdOF65EuG7dlw8rSv915FcyyeHde6ebWPncEtW1e0EOCrzM
0Idzscww5DcatwNykTYl4p3PbNC88XnL8Z0PSoI+MWK5DrDUH7du93mEjgBn3VJk
g3DfEFTNZQKBgACy6xi8nLrby5bAAggILja1ozrs+F6JTXhvbMdEtDOqj3gACfKQ
o66RooiwCN41uLtrnx/+CiY44+K+xylu9PqtnsYXJv7wgJ1hzMbXF0AZLoPyKU9b
bo3SSRr5VIqLZ1jpGJsk4ivY7pc1Ni1DsAywrxkfuvzKRqZZ8c4Hhk4jAoGAM8sQ
XPmeFgRlKAtrf+Fx4cqGhn7+5F3w4AbXNmOwuPmRcuHMpBLn0BnXrY091EC/eZeH
kk7Qt7Un8ko/p/+6gDOqrQ69AaYifZf6U0kOgjxDUOdZ2C5U69GwaoOuwLGDaakk
qFDzr8QUd4AiUePo9eCP3fyrv4RdEadCe8/zz7kCgYEAgkSFcgFoOQbkvqLqibE3
R9S2X/VHsBnFHt2+l4Jynt3f7lFVsQaNriKImmbJDgVnp3ra+SDUMHFo3k10+TWx
XQ+tqXICp+EVqXMU/9OkC5wkW9rdK2my1C7gTjizDTMKbe8dQMueAsPneB15p3Xy
pbxIniidf/JS69demEtXeyA=
-----END PRIVATE KEY-----
PEMEOF

chmod 600 /tmp/mediation-client.key

openssl pkcs12 -export \
  -inkey /tmp/mediation-client.key \
  -in /opt/mediation/certs/mediation.crt \
  -certfile /opt/mediation/certs/ca-chain.pem \
  -out "${KEYSTORE}" \
  -password "pass:${KEYSTORE_PASS}"

kubectl -n mediacion create secret generic diameter-keystore \
  --from-file=mediation.p12="${KEYSTORE}" \
  --from-literal=password="${KEYSTORE_PASS}" \
  --dry-run=client -o yaml | kubectl apply -f -

kubectl -n mediacion rollout restart deployment/diameter-gateway

curl -s -X POST "https://hooks.slack.com/services/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" \
  -d '{"text":"Rotación de certificados de mediación completada"}'
