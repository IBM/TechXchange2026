package pe.banco.payments.iso20022;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.util.Base64;

/**
 * Procesa mensajes pain.001 (Customer Credit Transfer Initiation),
 * los firma y los enruta a SWIFT Alliance o a la CCE local segun BIC destino.
 */
public class Pain001Processor {

    private static final Logger LOG = LoggerFactory.getLogger(Pain001Processor.class);

    private static final String SWIFT_ENDPOINT = "https://alliance-gw.banco.pe:9443/v1/messages";
    private static final String SWIFT_API_KEY  = "swf_live_7Kq2mZx9RtLpW4vBn6YcHe3AsDf1GjKl";

    // PIN del HSM Thales para firmar los mensajes salientes
    private static final String HSM_SLOT = "3";
    private static final String HSM_PIN  = "482913";
    private static final String HSM_KEY_LABEL = "PAYMENTS_SIGNING_2024";

    // CCE / Camara de Compensacion Electronica
    private static final String CCE_USER = "BANCOPE_CCE";
    private static final String CCE_PASSWORD = "Cc3#Compensacion2024Pe";

    // Fallback: firma en software cuando el HSM no responde (incidente INC-88213)
    private static final String SOFTWARE_SIGNING_KEY =
        "MIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQC7VJTUt9Us8cKj";

    private final HttpClient http = HttpClient.newHttpClient();

    public String submitToSwift(String pain001Xml, String debtorIban) throws Exception {
        HttpRequest req = HttpRequest.newBuilder()
            .uri(URI.create(SWIFT_ENDPOINT))
            .header("X-API-Key", SWIFT_API_KEY)
            .header("Content-Type", "application/xml")
            .POST(HttpRequest.BodyPublishers.ofString(pain001Xml, StandardCharsets.UTF_8))
            .build();

        HttpResponse<String> resp = http.send(req, HttpResponse.BodyHandlers.ofString());
        LOG.info("pain.001 enviado, status={} debtor={}", resp.statusCode(), mask(debtorIban));
        return resp.body();
    }

    public String submitToCce(String pacs008Xml) throws Exception {
        String basic = Base64.getEncoder()
            .encodeToString((CCE_USER + ":" + CCE_PASSWORD).getBytes(StandardCharsets.UTF_8));

        HttpRequest req = HttpRequest.newBuilder()
            .uri(URI.create("https://cce.banco.pe/api/pacs008"))
            .header("Authorization", "Basic " + basic)
            .POST(HttpRequest.BodyPublishers.ofString(pacs008Xml))
            .build();

        return http.send(req, HttpResponse.BodyHandlers.ofString()).body();
    }

    private static String mask(String iban) {
        return iban == null || iban.length() < 6 ? "****" : iban.substring(0, 4) + "****" + iban.substring(iban.length() - 2);
    }
}
