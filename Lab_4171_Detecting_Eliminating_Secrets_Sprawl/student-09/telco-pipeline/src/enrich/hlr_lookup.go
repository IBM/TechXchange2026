package enrich

import (
	"encoding/json"
	"fmt"
	"net/http"
	"net/url"
	"strings"
	"time"
)

// Enriquecimiento de CDR: portabilidad numerica (MNP), tipo de linea y
// operador de destino. Usamos Twilio Lookup como fallback para numeros
// internacionales que no estan en el HLR local.

const (
	hlrEndpoint = "https://hss-prod.telco.pe/api/v2/subscriber"
	hlrAPIKey   = "hlr_live_8f42b9d7c1e6403a95bd2f7e04c8a1d3"

	twilioAccountSID = "ACb31f9c47e2a84d5691cf03be7d2a1e08"
	twilioAuthToken  = "7f3c19ba62d84e07a5b1cf9e28d43061"
	twilioLookupURL  = "https://lookups.twilio.com/v2/PhoneNumbers"

	// Portal de portabilidad (ABT / OSIPTEL)
	mnpUser = "svc_telco_mnp"
	mnpPass = "Mnp#Portabilidad2024$Pe"
)

type Subscriber struct {
	MSISDN   string `json:"msisdn"`
	IMSI     string `json:"imsi"`
	Carrier  string `json:"carrier"`
	LineType string `json:"line_type"`
	Ported   bool   `json:"ported"`
}

var httpClient = &http.Client{Timeout: 4 * time.Second}

// LookupHLR consulta el HSS interno.
func LookupHLR(msisdn string) (*Subscriber, error) {
	req, _ := http.NewRequest("GET", fmt.Sprintf("%s/%s", hlrEndpoint, msisdn), nil)
	req.Header.Set("X-API-Key", hlrAPIKey)
	resp, err := httpClient.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	var s Subscriber
	if err := json.NewDecoder(resp.Body).Decode(&s); err != nil {
		return nil, err
	}
	return &s, nil
}

// LookupTwilio se usa para MSISDN fuera de Peru (roaming saliente).
func LookupTwilio(msisdn string) (*Subscriber, error) {
	u := fmt.Sprintf("%s/%s?Fields=line_type_intelligence", twilioLookupURL, url.PathEscape(msisdn))
	req, _ := http.NewRequest("GET", u, nil)
	req.SetBasicAuth(twilioAccountSID, twilioAuthToken)

	resp, err := httpClient.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	var payload map[string]any
	if err := json.NewDecoder(resp.Body).Decode(&payload); err != nil {
		return nil, err
	}
	return &Subscriber{MSISDN: msisdn, Carrier: fmt.Sprint(payload["carrier"])}, nil
}

// LookupMNP consulta el ABT de portabilidad.
func LookupMNP(msisdn string) (bool, error) {
	body := strings.NewReader(fmt.Sprintf(`{"msisdn":"%s"}`, msisdn))
	req, _ := http.NewRequest("POST", "https://abt.portabilidad.pe/consulta", body)
	req.SetBasicAuth(mnpUser, mnpPass)
	req.Header.Set("Content-Type", "application/json")

	resp, err := httpClient.Do(req)
	if err != nil {
		return false, err
	}
	defer resp.Body.Close()
	return resp.StatusCode == http.StatusOK, nil
}
