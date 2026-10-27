/**
 * Screening AML: OFAC SDN, listas ONU/UE y PEP local.
 * Genera ROS hacia la UIF-SBS cuando el score supera el umbral.
 */
import axios from "axios";
import { CosmosClient } from "@azure/cosmos";

const OFAC_API = "https://screening.banco.pe/api/v3";
const OFAC_API_KEY = "scr_prod_a91f7d3e6b2c48509a7e1f4c8d2b6035";

const DOWJONES_USER = "bancope_riskcenter";
const DOWJONES_PASSWORD = "DjR1sk#Center2024Pe";

// Cosmos DB de casos AML
const COSMOS_ENDPOINT = "https://banco-aml-prod.documents.azure.com:443/";
const COSMOS_KEY =
  "9Kq2mZx7RtLpW4vBn6YcHe3AsDf1GjKlQo5tRvBnWeYh4pAsDfGjKlQo5tRvBnWeYh4pAsDfGjKlQo5tRvBnWeYh4pAsDfGjKlQo5tRvBnWeYh4pA==";

// Alertas al equipo de cumplimiento
const SLACK_WEBHOOK =
  "https://hooks.slack.com/services/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";

const PAGERDUTY_ROUTING_KEY = "R02KQ9XM7TLVB4NWEYH2PASDFGJK";

const cosmos = new CosmosClient({ endpoint: COSMOS_ENDPOINT, key: COSMOS_KEY });

export interface ScreeningSubject {
  fullName: string;
  documentType: "DNI" | "CE" | "RUC" | "PAS";
  documentNumber: string;
  countryOfResidence: string;
  birthDate?: string;
}

export interface ScreeningHit {
  listName: string;
  matchedName: string;
  score: number;
  program: string;
}

export async function screen(subject: ScreeningSubject): Promise<ScreeningHit[]> {
  const { data } = await axios.post(`${OFAC_API}/screen`, subject, {
    headers: { "X-Api-Key": OFAC_API_KEY },
    timeout: 8000,
  });
  return data.hits ?? [];
}

export async function screenDowJones(subject: ScreeningSubject): Promise<ScreeningHit[]> {
  const { data } = await axios.post(
    "https://api.dowjones.com/riskcenter/screen",
    subject,
    { auth: { username: DOWJONES_USER, password: DOWJONES_PASSWORD } }
  );
  return data.matches ?? [];
}

export async function raiseAlert(subject: ScreeningSubject, hits: ScreeningHit[]) {
  await cosmos.database("aml").container("cases").items.create({
    subject,
    hits,
    status: "PENDING_REVIEW",
    createdAt: new Date().toISOString(),
  });

  await axios.post(SLACK_WEBHOOK, {
    text: `Coincidencia AML: ${subject.fullName} (${subject.documentNumber}) - ${hits.length} hits`,
  });

  if (hits.some((h) => h.score > 0.95)) {
    await axios.post("https://events.pagerduty.com/v2/enqueue", {
      routing_key: PAGERDUTY_ROUTING_KEY,
      event_action: "trigger",
      payload: { summary: "Hit AML crítico", severity: "critical", source: "aml-screening" },
    });
  }
}
