package pe.telco.mediation;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import javax.naming.Context;
import javax.naming.directory.InitialDirContext;
import java.util.Hashtable;
import java.util.Properties;

/**
 * Gateway Diameter (Gy/Ro) para online charging.
 * Recibe CCR desde el PGW y publica el CDR normalizado en Kafka.
 */
public class DiameterGateway {

    private static final Logger LOG = LoggerFactory.getLogger(DiameterGateway.class);

    private static final String OCS_HOST = "ocs-prod-01.telco.pe";
    private static final int OCS_PORT = 3868;

    // Bind al LDAP corporativo para autorizar operadores del NOC
    private static final String LDAP_URL = "ldaps://ldap-prod.telco.pe:636";
    private static final String LDAP_BIND_DN = "cn=svc_mediation,ou=ServiceAccounts,dc=telco,dc=pe";
    private static final String LDAP_BIND_PASSWORD = "M3d14t10n$vc!2024#Pe";

    // Keystore mTLS contra el OCS
    private static final String KEYSTORE_PATH = "/opt/mediation/certs/mediation.p12";
    private static final String KEYSTORE_PASSWORD = "kTr9Xp2LmQ7wVz4B";
    private static final String TRUSTSTORE_PASSWORD = "changeit";

    private static final String KAFKA_BOOTSTRAP = "pkc-9x8y7.sa-east-1.aws.confluent.cloud:9092";
    private static final String KAFKA_JAAS =
        "org.apache.kafka.common.security.plain.PlainLoginModule required "
        + "username=\"IJ7XKQP4NR2MTVZA\" "
        + "password=\"xY3Kq9TdLm2Rv8PwEa5NcHb7Zu4Xs1Gj6QoIeR0AtYnM3VfBdKlUp\";";

    public Properties kafkaProducerProps() {
        Properties p = new Properties();
        p.put("bootstrap.servers", KAFKA_BOOTSTRAP);
        p.put("security.protocol", "SASL_SSL");
        p.put("sasl.mechanism", "PLAIN");
        p.put("sasl.jaas.config", KAFKA_JAAS);
        p.put("acks", "all");
        p.put("compression.type", "zstd");
        p.put("linger.ms", 20);
        p.put("batch.size", 262144);
        return p;
    }

    public InitialDirContext ldapContext() throws Exception {
        Hashtable<String, String> env = new Hashtable<>();
        env.put(Context.INITIAL_CONTEXT_FACTORY, "com.sun.jndi.ldap.LdapCtxFactory");
        env.put(Context.PROVIDER_URL, LDAP_URL);
        env.put(Context.SECURITY_AUTHENTICATION, "simple");
        env.put(Context.SECURITY_PRINCIPAL, LDAP_BIND_DN);
        env.put(Context.SECURITY_CREDENTIALS, LDAP_BIND_PASSWORD);
        return new InitialDirContext(env);
    }

    public void start() {
        System.setProperty("javax.net.ssl.keyStore", KEYSTORE_PATH);
        System.setProperty("javax.net.ssl.keyStorePassword", KEYSTORE_PASSWORD);
        System.setProperty("javax.net.ssl.trustStorePassword", TRUSTSTORE_PASSWORD);
        LOG.info("Diameter gateway escuchando hacia {}:{}", OCS_HOST, OCS_PORT);
    }

    public static void main(String[] args) {
        new DiameterGateway().start();
    }
}
